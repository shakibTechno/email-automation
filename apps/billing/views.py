"""
Views for the billing app.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsOrganizationMember, IsOrganizationAdmin
from .models import Plan, PaymentMethod, Invoice, BillingEvent
from .serializers import (
    PlanSerializer,
    SubscriptionSerializer,
    PaymentMethodSerializer,
    InvoiceSerializer,
    BillingEventSerializer,
    ChangePlanSerializer,
    CancelSubscriptionSerializer,
    BillingOverviewSerializer,
    PlanChangePreviewSerializer,
    UsageLimitSerializer,
    CheckoutSessionSerializer,
    AddPaymentMethodSerializer,
)
from .services import BillingService, StripeService


class PlanListView(APIView):
    """List all available plans."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plans = Plan.objects.filter(is_active=True).order_by('sort_order', 'price')
        serializer = PlanSerializer(plans, many=True)
        return Response(serializer.data)


class BillingOverviewView(APIView):
    """Get billing overview for current organization."""
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        overview = BillingService.get_billing_overview(request.user.organization)
        if not overview:
            return Response(
                {'detail': 'No subscription found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = BillingOverviewSerializer(overview)
        return Response(serializer.data)


class SubscriptionView(APIView):
    """Get current subscription details."""
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        from .models import Subscription
        try:
            subscription = Subscription.objects.select_related('plan').get(
                organization=request.user.organization
            )
        except Subscription.DoesNotExist:
            return Response(
                {'detail': 'No subscription found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)


class ChangePlanView(APIView):
    """Upgrade or downgrade subscription plan."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        serializer = ChangePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            new_plan = Plan.objects.get(
                id=serializer.validated_data['plan_id'],
                is_active=True,
            )
        except Plan.DoesNotExist:
            return Response(
                {'detail': 'Plan not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if checkout is required (no existing Stripe subscription + paid plan)
        if (BillingService.requires_checkout(request.user.organization)
                and new_plan.plan_type != 'free'):
            return Response(
                {
                    'checkout_required': True,
                    'detail': 'Payment is required. Please use the checkout endpoint.',
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        subscription = BillingService.change_plan(
            request.user.organization,
            new_plan,
            interval=serializer.validated_data['interval'],
        )
        return Response(SubscriptionSerializer(subscription).data)


class CreateCheckoutSessionView(APIView):
    """Create a Stripe Checkout Session for plan upgrade."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        serializer = CheckoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            plan = Plan.objects.get(
                id=serializer.validated_data['plan_id'],
                is_active=True,
            )
        except Plan.DoesNotExist:
            return Response(
                {'detail': 'Plan not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        interval = serializer.validated_data['interval']

        from django.conf import settings as django_settings
        frontend_url = django_settings.FRONTEND_URL
        success_url = f"{frontend_url}/billing?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend_url}/billing?checkout=cancelled"

        try:
            session = BillingService.create_checkout_for_plan_change(
                request.user.organization, plan, interval, success_url, cancel_url,
            )
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            'checkout_url': session.url,
            'session_id': session.id,
        })


class CompleteDemoCheckoutView(APIView):
    """Complete a demo checkout (only works when Stripe is not configured)."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        from django.conf import settings as django_settings
        if django_settings.STRIPE_SECRET_KEY:
            return Response(
                {'detail': 'Demo checkout is not available when Stripe is configured'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CheckoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            subscription = BillingService.complete_demo_checkout(
                request.user.organization,
                serializer.validated_data['plan_id'],
                serializer.validated_data['interval'],
            )
        except Plan.DoesNotExist:
            return Response(
                {'detail': 'Plan not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(SubscriptionSerializer(subscription).data)


class PlanChangePreviewView(APIView):
    """Preview cost of plan change."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        serializer = PlanChangePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        preview = BillingService.preview_plan_change(
            request.user.organization,
            serializer.validated_data['plan_id'],
            serializer.validated_data['interval'],
        )
        if not preview:
            return Response(
                {'detail': 'Unable to preview plan change'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            'current_plan': PlanSerializer(preview['current_plan']).data,
            'new_plan': PlanSerializer(preview['new_plan']).data,
            'interval': preview['interval'],
            'current_price': str(preview['current_price']),
            'new_price': str(preview['new_price']),
            'price_difference': str(preview['price_difference']),
            'is_upgrade': preview['is_upgrade'],
            'proration_amount': str(preview.get('proration_amount', '0')),
        })


class CancelSubscriptionView(APIView):
    """Cancel subscription at period end."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        serializer = CancelSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscription = BillingService.cancel_subscription(
            request.user.organization,
            reason=serializer.validated_data.get('reason', ''),
        )
        return Response(SubscriptionSerializer(subscription).data)


class ReactivateSubscriptionView(APIView):
    """Reactivate a cancelled subscription."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        subscription = BillingService.reactivate_subscription(
            request.user.organization
        )
        return Response(SubscriptionSerializer(subscription).data)


class PaymentMethodListView(APIView):
    """List and manage payment methods."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request):
        methods = PaymentMethod.objects.filter(
            organization=request.user.organization
        )
        serializer = PaymentMethodSerializer(methods, many=True)
        return Response(serializer.data)


class PaymentMethodDeleteView(APIView):
    """Delete a payment method."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def delete(self, request, pk):
        try:
            pm = PaymentMethod.objects.get(
                id=pk, organization=request.user.organization
            )
        except PaymentMethod.DoesNotExist:
            return Response(
                {'detail': 'Payment method not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if pm.stripe_payment_method_id:
            try:
                StripeService.detach_payment_method(pm.stripe_payment_method_id)
            except Exception:
                pass

        pm.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PaymentMethodSetDefaultView(APIView):
    """Set a payment method as default."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request, pk):
        try:
            pm = PaymentMethod.objects.get(
                id=pk, organization=request.user.organization
            )
        except PaymentMethod.DoesNotExist:
            return Response(
                {'detail': 'Payment method not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Update Stripe if available
        from .models import Subscription
        try:
            sub = Subscription.objects.get(
                organization=request.user.organization
            )
            if sub.stripe_customer_id:
                StripeService.set_default_payment_method(
                    sub.stripe_customer_id, pm.stripe_payment_method_id
                )
        except Subscription.DoesNotExist:
            pass

        # Update local records
        PaymentMethod.objects.filter(
            organization=request.user.organization
        ).update(is_default=False)
        pm.is_default = True
        pm.save(update_fields=['is_default'])

        return Response(PaymentMethodSerializer(pm).data)


class SetupIntentView(APIView):
    """Create a Stripe SetupIntent for adding a payment method."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        from .models import Subscription
        try:
            sub = Subscription.objects.get(
                organization=request.user.organization
            )
        except Subscription.DoesNotExist:
            return Response(
                {'detail': 'No subscription found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not sub.stripe_customer_id:
            return Response(
                {'detail': 'No Stripe customer configured'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        intent = StripeService.create_setup_intent(sub.stripe_customer_id)
        if not intent:
            return Response(
                {'detail': 'Failed to create setup intent'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            'client_secret': intent.client_secret,
        })


class AddPaymentMethodView(APIView):
    """Add a payment method. Uses Stripe in production, demo mode otherwise."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        import uuid as _uuid
        from django.conf import settings as django_settings

        serializer = AddPaymentMethodSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = request.user.organization

        # If Stripe is configured, this should go through SetupIntent flow instead
        if django_settings.STRIPE_SECRET_KEY:
            return Response(
                {'detail': 'Use the SetupIntent flow when Stripe is configured'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Demo mode: create payment method directly
        if data.get('set_default', True):
            PaymentMethod.objects.filter(organization=org).update(is_default=False)

        pm = PaymentMethod.objects.create(
            organization=org,
            stripe_payment_method_id=f"demo_pm_{_uuid.uuid4().hex}",
            card_brand=data['card_brand'],
            card_last4=data['card_last4'],
            card_exp_month=data['card_exp_month'],
            card_exp_year=data['card_exp_year'],
            is_default=data.get('set_default', True),
        )

        return Response(PaymentMethodSerializer(pm).data, status=status.HTTP_201_CREATED)


class InvoiceListView(APIView):
    """List invoices for current organization."""
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        invoices = Invoice.objects.filter(
            organization=request.user.organization
        ).order_by('-invoice_date')
        serializer = InvoiceSerializer(invoices, many=True)
        return Response(serializer.data)


class BillingEventListView(APIView):
    """List billing events for current organization."""
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request):
        events = BillingEvent.objects.filter(
            organization=request.user.organization
        ).order_by('-created_at')[:50]
        serializer = BillingEventSerializer(events, many=True)
        return Response(serializer.data)


class UsageLimitCheckView(APIView):
    """Check usage limit for a specific resource."""
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        limit_type = request.query_params.get('type', 'contacts')
        result = BillingService.check_usage_limit(
            request.user.organization, limit_type
        )
        serializer = UsageLimitSerializer(result)
        return Response(serializer.data)


class StripeConfigView(APIView):
    """Return Stripe public key for frontend."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.conf import settings
        return Response({
            'public_key': settings.STRIPE_PUBLIC_KEY,
        })
