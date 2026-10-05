"""
Serializers for the billing app.
"""
from rest_framework import serializers
from .models import Plan, Subscription, PaymentMethod, Invoice, BillingEvent


class PlanSerializer(serializers.ModelSerializer):
    monthly_equivalent = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'plan_type', 'interval', 'price', 'annual_price',
            'monthly_equivalent',
            'max_contacts', 'max_emails_per_month', 'max_automations',
            'max_landing_pages', 'max_users',
            'has_ab_testing', 'has_advanced_segmentation', 'has_lead_scoring',
            'has_crm', 'has_api_access', 'has_custom_reports',
            'has_sms_marketing', 'has_ai_features', 'has_dedicated_ip',
            'has_sso', 'has_white_labeling', 'remove_watermark',
            'is_active', 'is_popular', 'sort_order',
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_trialing = serializers.BooleanField(read_only=True)
    trial_days_remaining = serializers.IntegerField(read_only=True)
    is_on_free_plan = serializers.BooleanField(read_only=True)
    contacts_usage_percent = serializers.IntegerField(read_only=True)
    emails_usage_percent = serializers.IntegerField(read_only=True)
    has_stripe_subscription = serializers.SerializerMethodField()

    def get_has_stripe_subscription(self, obj):
        return bool(obj.stripe_subscription_id)

    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'status', 'interval',
            'stripe_customer_id', 'has_stripe_subscription',
            'current_period_start', 'current_period_end',
            'trial_start', 'trial_end',
            'cancel_at_period_end', 'cancelled_at', 'cancellation_reason',
            'emails_sent_this_month', 'usage_reset_date',
            'is_active', 'is_trialing', 'trial_days_remaining',
            'is_on_free_plan', 'contacts_usage_percent', 'emails_usage_percent',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'stripe_customer_id',
            'current_period_start', 'current_period_end',
            'trial_start', 'trial_end',
            'cancelled_at', 'emails_sent_this_month', 'usage_reset_date',
            'created_at', 'updated_at',
        ]


class PaymentMethodSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'card_brand', 'card_last4',
            'card_exp_month', 'card_exp_year',
            'is_default', 'is_expired',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class InvoiceSerializer(serializers.ModelSerializer):
    total_dollars = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    subtotal_dollars = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    tax_dollars = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    amount_due_dollars = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Invoice
        fields = [
            'id', 'number', 'status', 'currency',
            'subtotal', 'tax', 'total', 'amount_paid', 'amount_due',
            'total_dollars', 'subtotal_dollars', 'tax_dollars', 'amount_due_dollars',
            'invoice_date', 'due_date', 'paid_at',
            'stripe_hosted_invoice_url', 'stripe_invoice_pdf',
            'description', 'line_items',
            'created_at',
        ]


class BillingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingEvent
        fields = [
            'id', 'event_type', 'description', 'metadata', 'created_at',
        ]


class ChangePlanSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    interval = serializers.ChoiceField(
        choices=['month', 'year'], default='month'
    )


class CancelSubscriptionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class BillingOverviewSerializer(serializers.Serializer):
    plan = PlanSerializer()
    subscription = SubscriptionSerializer()
    contact_count = serializers.IntegerField()
    contacts_limit = serializers.IntegerField()
    contacts_usage_percent = serializers.IntegerField()
    emails_sent = serializers.IntegerField()
    emails_limit = serializers.IntegerField()
    emails_usage_percent = serializers.IntegerField()
    trial_days_remaining = serializers.IntegerField()
    is_trialing = serializers.BooleanField()
    cancel_at_period_end = serializers.BooleanField()
    current_period_end = serializers.DateTimeField()


class PlanChangePreviewSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    interval = serializers.ChoiceField(
        choices=['month', 'year'], default='month'
    )


class UsageLimitSerializer(serializers.Serializer):
    allowed = serializers.BooleanField()
    current = serializers.IntegerField(required=False)
    limit = serializers.IntegerField(required=False)
    usage_percent = serializers.IntegerField(required=False)
    reason = serializers.CharField(required=False)


class CheckoutSessionSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    interval = serializers.ChoiceField(choices=['month', 'year'], default='month')


class AddPaymentMethodSerializer(serializers.Serializer):
    card_brand = serializers.ChoiceField(
        choices=['visa', 'mastercard', 'amex', 'discover', 'other'],
        default='visa',
    )
    card_last4 = serializers.RegexField(
        regex=r'^\d{4}$',
        error_messages={'invalid': 'Must be exactly 4 digits'},
    )
    card_exp_month = serializers.IntegerField(min_value=1, max_value=12)
    card_exp_year = serializers.IntegerField(min_value=2024, max_value=2099)
    set_default = serializers.BooleanField(default=True)
