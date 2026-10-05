"""
Billing services for subscription management and Stripe integration.
"""
import logging
from datetime import timedelta
from decimal import Decimal

import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Plan, Subscription, PaymentMethod, Invoice, BillingEvent

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service for Stripe API interactions."""

    @staticmethod
    def create_customer(organization, email):
        if not settings.STRIPE_SECRET_KEY:
            logger.warning("Stripe not configured, skipping customer creation")
            return None
        try:
            customer = stripe.Customer.create(
                email=email,
                name=organization.name,
                metadata={
                    'organization_id': str(organization.id),
                    'organization_name': organization.name,
                },
            )
            return customer
        except stripe.StripeError as e:
            logger.error(f"Stripe customer creation failed: {e}")
            raise

    @staticmethod
    def create_subscription(customer_id, price_id, trial_days=None):
        if not settings.STRIPE_SECRET_KEY:
            return None
        try:
            params = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'payment_behavior': 'default_incomplete',
                'expand': ['latest_invoice.payment_intent'],
            }
            if trial_days:
                params['trial_period_days'] = trial_days
            sub = stripe.Subscription.create(**params)
            return sub
        except stripe.StripeError as e:
            logger.error(f"Stripe subscription creation failed: {e}")
            raise

    @staticmethod
    def update_subscription(stripe_subscription_id, new_price_id):
        if not settings.STRIPE_SECRET_KEY:
            return None
        try:
            sub = stripe.Subscription.retrieve(stripe_subscription_id)
            updated = stripe.Subscription.modify(
                stripe_subscription_id,
                items=[{
                    'id': sub['items']['data'][0].id,
                    'price': new_price_id,
                }],
                proration_behavior='create_prorations',
            )
            return updated
        except stripe.StripeError as e:
            logger.error(f"Stripe subscription update failed: {e}")
            raise

    @staticmethod
    def cancel_subscription(stripe_subscription_id, at_period_end=True):
        if not settings.STRIPE_SECRET_KEY:
            return None
        try:
            if at_period_end:
                sub = stripe.Subscription.modify(
                    stripe_subscription_id,
                    cancel_at_period_end=True,
                )
            else:
                sub = stripe.Subscription.cancel(stripe_subscription_id)
            return sub
        except stripe.StripeError as e:
            logger.error(f"Stripe subscription cancellation failed: {e}")
            raise

    @staticmethod
    def reactivate_subscription(stripe_subscription_id):
        if not settings.STRIPE_SECRET_KEY:
            return None
        try:
            sub = stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=False,
            )
            return sub
        except stripe.StripeError as e:
            logger.error(f"Stripe subscription reactivation failed: {e}")
            raise

    @staticmethod
    def create_setup_intent(customer_id):
        if not settings.STRIPE_SECRET_KEY:
            return None
        try:
            intent = stripe.SetupIntent.create(
                customer=customer_id,
                payment_method_types=['card'],
            )
            return intent
        except stripe.StripeError as e:
            logger.error(f"Stripe setup intent creation failed: {e}")
            raise

    @staticmethod
    def detach_payment_method(stripe_payment_method_id):
        if not settings.STRIPE_SECRET_KEY:
            return None
        try:
            pm = stripe.PaymentMethod.detach(stripe_payment_method_id)
            return pm
        except stripe.StripeError as e:
            logger.error(f"Stripe payment method detach failed: {e}")
            raise

    @staticmethod
    def set_default_payment_method(customer_id, payment_method_id):
        if not settings.STRIPE_SECRET_KEY:
            return None
        try:
            customer = stripe.Customer.modify(
                customer_id,
                invoice_settings={'default_payment_method': payment_method_id},
            )
            return customer
        except stripe.StripeError as e:
            logger.error(f"Stripe default payment method update failed: {e}")
            raise

    @staticmethod
    def get_upcoming_invoice(customer_id, subscription_id=None, new_price_id=None):
        if not settings.STRIPE_SECRET_KEY:
            return None
        try:
            params = {'customer': customer_id}
            if subscription_id and new_price_id:
                sub = stripe.Subscription.retrieve(subscription_id)
                params['subscription'] = subscription_id
                params['subscription_items'] = [{
                    'id': sub['items']['data'][0].id,
                    'price': new_price_id,
                }]
                params['subscription_proration_behavior'] = 'create_prorations'
            invoice = stripe.Invoice.upcoming(**params)
            return invoice
        except stripe.StripeError as e:
            logger.error(f"Stripe upcoming invoice retrieval failed: {e}")
            raise

    @staticmethod
    def create_checkout_session(customer_id, price_id, success_url, cancel_url, metadata=None):
        """Create a Stripe Checkout Session for subscription."""
        if not settings.STRIPE_SECRET_KEY:
            return None
        try:
            params = {
                'customer': customer_id,
                'mode': 'subscription',
                'line_items': [{'price': price_id, 'quantity': 1}],
                'success_url': success_url,
                'cancel_url': cancel_url,
                'allow_promotion_codes': True,
            }
            if metadata:
                params['metadata'] = metadata
            session = stripe.checkout.Session.create(**params)
            return session
        except stripe.StripeError as e:
            logger.error(f"Stripe checkout session creation failed: {e}")
            raise

    @staticmethod
    def construct_webhook_event(payload, sig_header):
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except (ValueError, stripe.SignatureVerificationError) as e:
            logger.error(f"Stripe webhook verification failed: {e}")
            raise


class BillingService:
    """Service for subscription and billing management."""

    @staticmethod
    @transaction.atomic
    def initialize_subscription(organization, owner_email):
        """Create a free plan subscription for a new organization."""
        free_plan = Plan.objects.filter(
            plan_type='free', interval='month', is_active=True
        ).first()

        if not free_plan:
            logger.warning("No free plan found, cannot initialize subscription")
            return None

        subscription, created = Subscription.objects.get_or_create(
            organization=organization,
            defaults={
                'plan': free_plan,
                'status': 'trialing',
                'interval': 'month',
                'trial_start': timezone.now(),
                'trial_end': timezone.now() + timedelta(days=settings.FREE_TRIAL_DAYS),
                'current_period_start': timezone.now(),
                'current_period_end': timezone.now() + timedelta(days=settings.FREE_TRIAL_DAYS),
                'usage_reset_date': timezone.now().date(),
            },
        )

        if created:
            # Create Stripe customer if configured
            if settings.STRIPE_SECRET_KEY:
                try:
                    customer = StripeService.create_customer(organization, owner_email)
                    if customer:
                        subscription.stripe_customer_id = customer.id
                        subscription.save(update_fields=['stripe_customer_id'])
                except Exception:
                    pass  # Non-fatal, can be retried

            # Update organization limits
            organization.max_contacts = free_plan.max_contacts
            organization.max_emails_per_month = free_plan.max_emails_per_month
            organization.save(update_fields=['max_contacts', 'max_emails_per_month'])

            BillingEvent.objects.create(
                organization=organization,
                event_type='trial_started',
                description=f"Started {settings.FREE_TRIAL_DAYS}-day free trial",
            )

        return subscription

    @staticmethod
    def requires_checkout(organization):
        """Check if plan change requires Stripe Checkout (no existing Stripe subscription)."""
        sub = Subscription.objects.get(organization=organization)
        return not sub.stripe_subscription_id

    @staticmethod
    def create_checkout_for_plan_change(organization, new_plan, interval, success_url, cancel_url):
        """Create a Stripe Checkout Session for upgrading to a paid plan."""
        import uuid as _uuid
        subscription = Subscription.objects.select_related('plan').get(
            organization=organization
        )

        # Demo mode: return a fake session pointing to the frontend demo checkout page
        if not settings.STRIPE_SECRET_KEY:
            demo_session_id = f"demo_{_uuid.uuid4().hex[:16]}"
            frontend_url = settings.FRONTEND_URL
            demo_url = (
                f"{frontend_url}/checkout/demo"
                f"?session_id={demo_session_id}"
                f"&plan_id={new_plan.id}"
                f"&plan_name={new_plan.name}"
                f"&interval={interval}"
                f"&price={new_plan.annual_price if interval == 'year' else new_plan.price}"
            )

            class DemoSession:
                def __init__(self, url, id):
                    self.url = url
                    self.id = id

            return DemoSession(url=demo_url, id=demo_session_id)

        # Ensure Stripe customer exists
        if not subscription.stripe_customer_id:
            owner = organization.users.filter(role='owner').first()
            email = owner.email if owner else ''
            customer = StripeService.create_customer(organization, email)
            if customer:
                subscription.stripe_customer_id = customer.id
                subscription.save(update_fields=['stripe_customer_id'])

        price_id = new_plan.stripe_price_id_annual if interval == 'year' else new_plan.stripe_price_id_monthly
        if not price_id:
            raise ValueError("Plan has no Stripe price configured")

        session = StripeService.create_checkout_session(
            customer_id=subscription.stripe_customer_id,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'organization_id': str(organization.id),
                'plan_id': str(new_plan.id),
                'interval': interval,
            },
        )
        return session

    @staticmethod
    @transaction.atomic
    def complete_demo_checkout(organization, plan_id, interval='month'):
        """Complete a demo checkout (no Stripe) — directly apply plan change."""
        import uuid as _uuid

        new_plan = Plan.objects.get(id=plan_id, is_active=True)
        subscription = Subscription.objects.select_for_update().get(
            organization=organization
        )
        old_plan = subscription.plan
        is_upgrade = new_plan.sort_order > old_plan.sort_order

        now = timezone.now()
        if interval == 'year':
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)

        subscription.plan = new_plan
        subscription.status = 'active'
        subscription.interval = interval
        subscription.current_period_start = now
        subscription.current_period_end = period_end
        if subscription.cancel_at_period_end:
            subscription.cancel_at_period_end = False
            subscription.cancelled_at = None
            subscription.cancellation_reason = ''
        subscription.save()

        organization.plan = new_plan.plan_type
        organization.max_contacts = new_plan.max_contacts
        organization.max_emails_per_month = new_plan.max_emails_per_month
        organization.save(update_fields=['plan', 'max_contacts', 'max_emails_per_month'])

        # Generate demo invoice
        price = new_plan.annual_price if interval == 'year' else new_plan.price
        total_cents = int(price * 100)
        invoice_number = f"DEMO-{now.strftime('%Y%m%d')}-{_uuid.uuid4().hex[:6].upper()}"

        Invoice.objects.create(
            organization=organization,
            subscription=subscription,
            stripe_invoice_id=f"demo_inv_{_uuid.uuid4().hex}",
            number=invoice_number,
            status='paid',
            currency='usd',
            subtotal=total_cents,
            tax=0,
            total=total_cents,
            amount_paid=total_cents,
            amount_due=0,
            invoice_date=now,
            paid_at=now,
            description=f"{new_plan.name} plan — {'Annual' if interval == 'year' else 'Monthly'} subscription",
            line_items=[{
                'description': f"{new_plan.name} ({'Annual' if interval == 'year' else 'Monthly'})",
                'amount': total_cents,
                'quantity': 1,
                'period_start': int(now.timestamp()),
                'period_end': int(period_end.timestamp()),
            }],
        )

        event_type = 'plan_upgraded' if is_upgrade else 'plan_downgraded'
        BillingEvent.objects.create(
            organization=organization,
            event_type=event_type,
            description=f"Changed from {old_plan.name} to {new_plan.name} ({interval}) via demo checkout",
            metadata={
                'old_plan': str(old_plan.id),
                'new_plan': str(new_plan.id),
                'interval': interval,
            },
        )

        return subscription

    @staticmethod
    @transaction.atomic
    def change_plan(organization, new_plan, interval='month'):
        """Upgrade or downgrade the subscription plan."""
        subscription = Subscription.objects.select_for_update().get(
            organization=organization
        )
        old_plan = subscription.plan
        is_upgrade = new_plan.sort_order > old_plan.sort_order

        # Guard: if no Stripe subscription exists and new plan is paid, checkout is required
        if (not subscription.stripe_subscription_id and
                new_plan.plan_type != 'free'):
            raise ValueError("Checkout is required for this plan change")

        # Determine the Stripe price ID
        price_id = (
            new_plan.stripe_price_id_annual if interval == 'year'
            else new_plan.stripe_price_id_monthly
        )

        # Update Stripe subscription if exists
        if subscription.stripe_subscription_id and price_id:
            StripeService.update_subscription(
                subscription.stripe_subscription_id, price_id
            )

        # Update local subscription
        subscription.plan = new_plan
        subscription.interval = interval
        if subscription.status == 'trialing' and new_plan.plan_type != 'free':
            subscription.status = 'active'
        if subscription.cancel_at_period_end:
            subscription.cancel_at_period_end = False
            subscription.cancelled_at = None
            subscription.cancellation_reason = ''
        subscription.save()

        # Update organization limits
        organization.plan = new_plan.plan_type
        organization.max_contacts = new_plan.max_contacts
        organization.max_emails_per_month = new_plan.max_emails_per_month
        organization.save(update_fields=[
            'plan', 'max_contacts', 'max_emails_per_month'
        ])

        event_type = 'plan_upgraded' if is_upgrade else 'plan_downgraded'
        BillingEvent.objects.create(
            organization=organization,
            event_type=event_type,
            description=f"Changed from {old_plan.name} to {new_plan.name} ({interval})",
            metadata={
                'old_plan': str(old_plan.id),
                'new_plan': str(new_plan.id),
                'interval': interval,
            },
        )

        return subscription

    @staticmethod
    @transaction.atomic
    def cancel_subscription(organization, reason=''):
        """Cancel the subscription at period end."""
        subscription = Subscription.objects.select_for_update().get(
            organization=organization
        )

        if subscription.stripe_subscription_id:
            StripeService.cancel_subscription(
                subscription.stripe_subscription_id, at_period_end=True
            )

        subscription.cancel_at_period_end = True
        subscription.cancelled_at = timezone.now()
        subscription.cancellation_reason = reason
        subscription.save(update_fields=[
            'cancel_at_period_end', 'cancelled_at', 'cancellation_reason'
        ])

        BillingEvent.objects.create(
            organization=organization,
            event_type='subscription_cancelled',
            description=f"Subscription scheduled for cancellation: {reason}",
        )

        return subscription

    @staticmethod
    @transaction.atomic
    def reactivate_subscription(organization):
        """Reactivate a cancelled subscription before period end."""
        subscription = Subscription.objects.select_for_update().get(
            organization=organization
        )

        if not subscription.cancel_at_period_end:
            return subscription

        if subscription.stripe_subscription_id:
            StripeService.reactivate_subscription(
                subscription.stripe_subscription_id
            )

        subscription.cancel_at_period_end = False
        subscription.cancelled_at = None
        subscription.cancellation_reason = ''
        subscription.save(update_fields=[
            'cancel_at_period_end', 'cancelled_at', 'cancellation_reason'
        ])

        BillingEvent.objects.create(
            organization=organization,
            event_type='subscription_updated',
            description="Subscription reactivated",
        )

        return subscription

    @staticmethod
    def get_billing_overview(organization):
        """Get billing overview data for the dashboard."""
        try:
            subscription = Subscription.objects.select_related('plan').get(
                organization=organization
            )
        except Subscription.DoesNotExist:
            return None

        from apps.contacts.models import Contact
        contact_count = Contact.objects.filter(
            organization=organization
        ).count()

        return {
            'subscription': subscription,
            'plan': subscription.plan,
            'contact_count': contact_count,
            'contacts_limit': subscription.plan.max_contacts,
            'contacts_usage_percent': subscription.contacts_usage_percent,
            'emails_sent': subscription.emails_sent_this_month,
            'emails_limit': subscription.plan.max_emails_per_month,
            'emails_usage_percent': subscription.emails_usage_percent,
            'trial_days_remaining': subscription.trial_days_remaining,
            'is_trialing': subscription.is_trialing,
            'cancel_at_period_end': subscription.cancel_at_period_end,
            'current_period_end': subscription.current_period_end,
        }

    @staticmethod
    def check_usage_limit(organization, limit_type):
        """Check if organization has exceeded a usage limit."""
        try:
            subscription = Subscription.objects.select_related('plan').get(
                organization=organization
            )
        except Subscription.DoesNotExist:
            return {'allowed': False, 'reason': 'No active subscription'}

        plan = subscription.plan

        if limit_type == 'contacts':
            from apps.contacts.models import Contact
            count = Contact.objects.filter(organization=organization).count()
            return {
                'allowed': count < plan.max_contacts,
                'current': count,
                'limit': plan.max_contacts,
                'usage_percent': subscription.contacts_usage_percent,
            }
        elif limit_type == 'emails':
            return {
                'allowed': subscription.emails_sent_this_month < plan.max_emails_per_month,
                'current': subscription.emails_sent_this_month,
                'limit': plan.max_emails_per_month,
                'usage_percent': subscription.emails_usage_percent,
            }
        elif limit_type == 'automations':
            from apps.workflows.models import Workflow
            count = Workflow.objects.filter(
                organization=organization, is_active=True
            ).count()
            limit = plan.max_automations
            if limit == 0:  # 0 means unlimited
                return {'allowed': True, 'current': count, 'limit': 0, 'usage_percent': 0}
            return {
                'allowed': count < limit,
                'current': count,
                'limit': limit,
                'usage_percent': min(100, round((count / limit) * 100)) if limit else 0,
            }
        elif limit_type == 'landing_pages':
            from apps.landing_pages.models import LandingPage
            count = LandingPage.objects.filter(
                organization=organization, status='published'
            ).count()
            limit = plan.max_landing_pages
            if limit == 0:
                return {'allowed': True, 'current': count, 'limit': 0, 'usage_percent': 0}
            return {
                'allowed': count < limit,
                'current': count,
                'limit': limit,
                'usage_percent': min(100, round((count / limit) * 100)) if limit else 0,
            }

        return {'allowed': True}

    @staticmethod
    def increment_email_usage(organization, count=1):
        """Increment email usage counter."""
        from django.db.models import F
        Subscription.objects.filter(
            organization=organization
        ).update(
            emails_sent_this_month=F('emails_sent_this_month') + count
        )

    @staticmethod
    def reset_monthly_usage(subscription):
        """Reset monthly email usage counter."""
        subscription.emails_sent_this_month = 0
        subscription.usage_reset_date = timezone.now().date()
        subscription.save(update_fields=['emails_sent_this_month', 'usage_reset_date'])

    @staticmethod
    def get_plan_comparison():
        """Get all active plans for comparison."""
        plans = Plan.objects.filter(
            is_active=True, interval='month'
        ).order_by('sort_order')
        return plans

    @staticmethod
    def preview_plan_change(organization, new_plan_id, interval='month'):
        """Preview the cost of changing plans."""
        try:
            subscription = Subscription.objects.select_related('plan').get(
                organization=organization
            )
            new_plan = Plan.objects.get(id=new_plan_id, is_active=True)
        except (Subscription.DoesNotExist, Plan.DoesNotExist):
            return None

        price = new_plan.annual_price if interval == 'year' else new_plan.price
        current_price = (
            subscription.plan.annual_price if subscription.interval == 'year'
            else subscription.plan.price
        )

        is_upgrade = new_plan.sort_order > subscription.plan.sort_order
        price_difference = price - current_price

        result = {
            'current_plan': subscription.plan,
            'new_plan': new_plan,
            'interval': interval,
            'current_price': current_price,
            'new_price': price,
            'price_difference': price_difference,
            'is_upgrade': is_upgrade,
        }

        # Get Stripe proration preview if available
        if subscription.stripe_subscription_id and subscription.stripe_customer_id:
            price_id = (
                new_plan.stripe_price_id_annual if interval == 'year'
                else new_plan.stripe_price_id_monthly
            )
            if price_id:
                try:
                    upcoming = StripeService.get_upcoming_invoice(
                        subscription.stripe_customer_id,
                        subscription.stripe_subscription_id,
                        price_id,
                    )
                    if upcoming:
                        result['proration_amount'] = Decimal(upcoming.total) / 100
                except Exception:
                    pass

        return result


class InvoiceService:
    """Service for invoice management."""

    @staticmethod
    def sync_invoice_from_stripe(stripe_invoice):
        """Create or update an invoice from Stripe data."""
        try:
            subscription = Subscription.objects.get(
                stripe_customer_id=stripe_invoice.customer
            )
            organization = subscription.organization
        except Subscription.DoesNotExist:
            logger.warning(
                f"No subscription found for Stripe customer {stripe_invoice.customer}"
            )
            return None

        line_items = []
        if stripe_invoice.lines and stripe_invoice.lines.data:
            for line in stripe_invoice.lines.data:
                line_items.append({
                    'description': line.description or '',
                    'amount': line.amount,
                    'quantity': line.quantity,
                    'period_start': line.period.start if line.period else None,
                    'period_end': line.period.end if line.period else None,
                })

        invoice, created = Invoice.objects.update_or_create(
            stripe_invoice_id=stripe_invoice.id,
            defaults={
                'organization': organization,
                'subscription': subscription,
                'number': stripe_invoice.number or '',
                'status': stripe_invoice.status or 'draft',
                'currency': stripe_invoice.currency or 'usd',
                'subtotal': stripe_invoice.subtotal or 0,
                'tax': stripe_invoice.tax or 0,
                'total': stripe_invoice.total or 0,
                'amount_paid': stripe_invoice.amount_paid or 0,
                'amount_due': stripe_invoice.amount_due or 0,
                'invoice_date': (
                    timezone.datetime.fromtimestamp(
                        stripe_invoice.created, tz=timezone.utc
                    ) if stripe_invoice.created else None
                ),
                'due_date': (
                    timezone.datetime.fromtimestamp(
                        stripe_invoice.due_date, tz=timezone.utc
                    ) if stripe_invoice.due_date else None
                ),
                'paid_at': (
                    timezone.datetime.fromtimestamp(
                        stripe_invoice.status_transitions.paid_at, tz=timezone.utc
                    ) if (
                        stripe_invoice.status_transitions and
                        stripe_invoice.status_transitions.paid_at
                    ) else None
                ),
                'stripe_hosted_invoice_url': stripe_invoice.hosted_invoice_url or '',
                'stripe_invoice_pdf': stripe_invoice.invoice_pdf or '',
                'description': stripe_invoice.description or '',
                'line_items': line_items,
            },
        )

        return invoice

    @staticmethod
    def list_invoices(organization, limit=20):
        """List invoices for an organization."""
        return Invoice.objects.filter(
            organization=organization
        ).order_by('-invoice_date')[:limit]


class WebhookService:
    """Service for handling Stripe webhook events."""

    @staticmethod
    def handle_event(event):
        """Route and handle a Stripe webhook event."""
        event_type = event['type']
        data = event['data']['object']

        handlers = {
            'checkout.session.completed': WebhookService._handle_checkout_completed,
            'customer.subscription.created': WebhookService._handle_subscription_created,
            'customer.subscription.updated': WebhookService._handle_subscription_updated,
            'customer.subscription.deleted': WebhookService._handle_subscription_deleted,
            'invoice.created': WebhookService._handle_invoice_created,
            'invoice.paid': WebhookService._handle_invoice_paid,
            'invoice.payment_failed': WebhookService._handle_payment_failed,
            'payment_method.attached': WebhookService._handle_payment_method_attached,
            'payment_method.detached': WebhookService._handle_payment_method_detached,
            'customer.subscription.trial_will_end': WebhookService._handle_trial_ending,
        }

        handler = handlers.get(event_type)
        if handler:
            handler(data, event.get('id', ''))
        else:
            logger.info(f"Unhandled Stripe event type: {event_type}")

    @staticmethod
    @transaction.atomic
    def _handle_checkout_completed(data, event_id):
        """Handle checkout.session.completed — activate subscription after payment."""
        if data.get('mode') != 'subscription':
            return

        metadata = data.get('metadata', {})
        organization_id = metadata.get('organization_id')
        plan_id = metadata.get('plan_id')
        interval = metadata.get('interval', 'month')

        if not organization_id or not plan_id:
            logger.warning(f"Checkout session missing metadata: {metadata}")
            return

        try:
            from apps.accounts.models import Organization
            organization = Organization.objects.get(id=organization_id)
            new_plan = Plan.objects.get(id=plan_id)
            subscription = Subscription.objects.select_for_update().get(
                organization=organization
            )
        except (Organization.DoesNotExist, Plan.DoesNotExist, Subscription.DoesNotExist) as e:
            logger.error(f"Checkout completed handler lookup failed: {e}")
            return

        old_plan = subscription.plan
        is_upgrade = new_plan.sort_order > old_plan.sort_order

        # Update subscription with Stripe data
        subscription.plan = new_plan
        subscription.status = 'active'
        subscription.interval = interval
        subscription.stripe_subscription_id = data.get('subscription', '')
        if subscription.cancel_at_period_end:
            subscription.cancel_at_period_end = False
            subscription.cancelled_at = None
            subscription.cancellation_reason = ''
        subscription.save()

        # Update organization limits
        organization.plan = new_plan.plan_type
        organization.max_contacts = new_plan.max_contacts
        organization.max_emails_per_month = new_plan.max_emails_per_month
        organization.save(update_fields=['plan', 'max_contacts', 'max_emails_per_month'])

        event_type = 'plan_upgraded' if is_upgrade else 'plan_downgraded'
        BillingEvent.objects.create(
            organization=organization,
            event_type=event_type,
            stripe_event_id=event_id,
            description=f"Changed from {old_plan.name} to {new_plan.name} ({interval}) via checkout",
            metadata={
                'old_plan': str(old_plan.id),
                'new_plan': str(new_plan.id),
                'interval': interval,
                'checkout_session_id': data.get('id', ''),
            },
        )

        logger.info(
            f"Checkout completed: org={organization_id} plan={new_plan.name} interval={interval}"
        )

    @staticmethod
    def _handle_subscription_created(data, event_id):
        try:
            subscription = Subscription.objects.get(
                stripe_customer_id=data['customer']
            )
            subscription.stripe_subscription_id = data['id']
            subscription.status = data['status']
            if data.get('current_period_start'):
                subscription.current_period_start = timezone.datetime.fromtimestamp(
                    data['current_period_start'], tz=timezone.utc
                )
            if data.get('current_period_end'):
                subscription.current_period_end = timezone.datetime.fromtimestamp(
                    data['current_period_end'], tz=timezone.utc
                )
            subscription.save()

            BillingEvent.objects.create(
                organization=subscription.organization,
                event_type='subscription_created',
                stripe_event_id=event_id,
                description="Stripe subscription created",
            )
        except Subscription.DoesNotExist:
            logger.warning(f"No subscription for customer {data['customer']}")

    @staticmethod
    def _handle_subscription_updated(data, event_id):
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=data['id']
            )
            subscription.status = data['status']
            subscription.cancel_at_period_end = data.get('cancel_at_period_end', False)
            if data.get('current_period_start'):
                subscription.current_period_start = timezone.datetime.fromtimestamp(
                    data['current_period_start'], tz=timezone.utc
                )
            if data.get('current_period_end'):
                subscription.current_period_end = timezone.datetime.fromtimestamp(
                    data['current_period_end'], tz=timezone.utc
                )
            subscription.save()

            BillingEvent.objects.create(
                organization=subscription.organization,
                event_type='subscription_updated',
                stripe_event_id=event_id,
                description=f"Subscription updated: status={data['status']}",
            )
        except Subscription.DoesNotExist:
            logger.warning(f"No subscription with stripe id {data['id']}")

    @staticmethod
    def _handle_subscription_deleted(data, event_id):
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=data['id']
            )
            # Downgrade to free plan
            free_plan = Plan.objects.filter(
                plan_type='free', interval='month', is_active=True
            ).first()
            if free_plan:
                subscription.plan = free_plan
                subscription.status = 'cancelled'
                subscription.stripe_subscription_id = ''
                subscription.save()

                org = subscription.organization
                org.plan = 'free'
                org.max_contacts = free_plan.max_contacts
                org.max_emails_per_month = free_plan.max_emails_per_month
                org.save(update_fields=['plan', 'max_contacts', 'max_emails_per_month'])

            BillingEvent.objects.create(
                organization=subscription.organization,
                event_type='subscription_cancelled',
                stripe_event_id=event_id,
                description="Subscription cancelled and downgraded to free",
            )
        except Subscription.DoesNotExist:
            logger.warning(f"No subscription with stripe id {data['id']}")

    @staticmethod
    def _handle_invoice_created(data, event_id):
        try:
            stripe_invoice = stripe.Invoice.retrieve(data['id'])
            InvoiceService.sync_invoice_from_stripe(stripe_invoice)
        except Exception as e:
            logger.error(f"Failed to sync invoice {data['id']}: {e}")

    @staticmethod
    def _handle_invoice_paid(data, event_id):
        try:
            stripe_invoice = stripe.Invoice.retrieve(data['id'])
            invoice = InvoiceService.sync_invoice_from_stripe(stripe_invoice)
            if invoice:
                BillingEvent.objects.create(
                    organization=invoice.organization,
                    event_type='invoice_paid',
                    stripe_event_id=event_id,
                    description=f"Invoice {invoice.number} paid: ${invoice.total_dollars}",
                    metadata={'invoice_id': str(invoice.id)},
                )
        except Exception as e:
            logger.error(f"Failed to handle invoice paid {data['id']}: {e}")

    @staticmethod
    def _handle_payment_failed(data, event_id):
        try:
            subscription = Subscription.objects.get(
                stripe_customer_id=data.get('customer', '')
            )
            BillingEvent.objects.create(
                organization=subscription.organization,
                event_type='payment_failed',
                stripe_event_id=event_id,
                description="Payment failed for invoice",
                metadata={'invoice_id': data['id']},
            )
            try:
                from apps.notifications.services import NotificationService
                NotificationService.notify_org_admins(
                    organization=subscription.organization,
                    notification_type='billing_payment_failed',
                    title='Payment failed',
                    message='Your latest payment failed. Please update your payment method to avoid service interruption.',
                    data={'invoice_id': data.get('id', '')},
                )
            except Exception:
                pass
        except Subscription.DoesNotExist:
            logger.warning(f"No subscription for customer {data.get('customer')}")

    @staticmethod
    def _handle_payment_method_attached(data, event_id):
        try:
            subscription = Subscription.objects.get(
                stripe_customer_id=data['customer']
            )
            card = data.get('card', {})
            PaymentMethod.objects.update_or_create(
                stripe_payment_method_id=data['id'],
                defaults={
                    'organization': subscription.organization,
                    'card_brand': card.get('brand', 'other'),
                    'card_last4': card.get('last4', '0000'),
                    'card_exp_month': card.get('exp_month', 1),
                    'card_exp_year': card.get('exp_year', 2030),
                    'is_default': not PaymentMethod.objects.filter(
                        organization=subscription.organization
                    ).exists(),
                },
            )

            BillingEvent.objects.create(
                organization=subscription.organization,
                event_type='payment_method_added',
                stripe_event_id=event_id,
                description=f"Payment method added: {card.get('brand', '')} ****{card.get('last4', '')}",
            )
        except Subscription.DoesNotExist:
            logger.warning(f"No subscription for customer {data['customer']}")

    @staticmethod
    def _handle_payment_method_detached(data, event_id):
        try:
            pm = PaymentMethod.objects.get(stripe_payment_method_id=data['id'])
            org = pm.organization
            pm.delete()

            BillingEvent.objects.create(
                organization=org,
                event_type='payment_method_removed',
                stripe_event_id=event_id,
                description="Payment method removed",
            )
        except PaymentMethod.DoesNotExist:
            pass

    @staticmethod
    def _handle_trial_ending(data, event_id):
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=data['id']
            )
            BillingEvent.objects.create(
                organization=subscription.organization,
                event_type='trial_ending',
                stripe_event_id=event_id,
                description="Trial period ending soon",
            )
            try:
                from apps.notifications.services import NotificationService
                days_left = subscription.trial_days_remaining or 3
                NotificationService.notify_org_admins(
                    organization=subscription.organization,
                    notification_type='billing_trial_expiring',
                    title='Trial ending soon',
                    message=f'Your free trial expires in {days_left} day(s). Upgrade to keep full access.',
                    data={},
                )
            except Exception:
                pass
        except Subscription.DoesNotExist:
            pass
