"""
Billing & Subscription models for the Email Marketing Automation Platform.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel


class Plan(TimeStampedModel):
    """
    Subscription plan definitions.
    Plans are system-defined and map to Stripe Price objects.
    """
    PLAN_TYPE_CHOICES = [
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('business', 'Business'),
        ('enterprise', 'Enterprise'),
    ]

    INTERVAL_CHOICES = [
        ('month', 'Monthly'),
        ('year', 'Annual'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES)
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, default='month')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    annual_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Stripe mapping
    stripe_price_id_monthly = models.CharField(max_length=255, blank=True)
    stripe_price_id_annual = models.CharField(max_length=255, blank=True)
    stripe_product_id = models.CharField(max_length=255, blank=True)

    # Plan limits
    max_contacts = models.IntegerField(default=500)
    max_emails_per_month = models.IntegerField(default=1000)
    max_automations = models.IntegerField(default=0)
    max_landing_pages = models.IntegerField(default=0)
    max_users = models.IntegerField(default=1)

    # Feature flags
    has_ab_testing = models.BooleanField(default=False)
    has_advanced_segmentation = models.BooleanField(default=False)
    has_lead_scoring = models.BooleanField(default=False)
    has_crm = models.BooleanField(default=False)
    has_api_access = models.BooleanField(default=False)
    has_custom_reports = models.BooleanField(default=False)
    has_sms_marketing = models.BooleanField(default=False)
    has_ai_features = models.BooleanField(default=False)
    has_dedicated_ip = models.BooleanField(default=False)
    has_sso = models.BooleanField(default=False)
    has_white_labeling = models.BooleanField(default=False)
    remove_watermark = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'billing_plans'
        ordering = ['sort_order', 'price']
        unique_together = ['plan_type', 'interval']

    def __str__(self):
        return f"{self.name} ({self.get_interval_display()})"

    @property
    def monthly_equivalent(self):
        if self.interval == 'year' and self.annual_price > 0:
            return (self.annual_price / 12).quantize(Decimal('0.01'))
        return self.price


class Subscription(TimeStampedModel):
    """
    Organization subscription to a plan.
    One active subscription per organization.
    """
    STATUS_CHOICES = [
        ('trialing', 'Trialing'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('incomplete', 'Incomplete'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trialing')
    interval = models.CharField(
        max_length=10,
        choices=Plan.INTERVAL_CHOICES,
        default='month'
    )

    # Stripe references
    stripe_customer_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, db_index=True)

    # Billing cycle
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    # Trial info
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)

    # Cancellation
    cancel_at_period_end = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    # Usage tracking (reset monthly)
    emails_sent_this_month = models.IntegerField(default=0)
    usage_reset_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'billing_subscriptions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['stripe_subscription_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.plan.name} ({self.status})"

    @property
    def is_active(self):
        return self.status in ('active', 'trialing')

    @property
    def is_trialing(self):
        return self.status == 'trialing'

    @property
    def trial_days_remaining(self):
        if not self.is_trialing or not self.trial_end:
            return 0
        remaining = (self.trial_end - timezone.now()).days
        return max(0, remaining)

    @property
    def is_on_free_plan(self):
        return self.plan.plan_type == 'free'

    @property
    def contacts_usage_percent(self):
        from apps.contacts.models import Contact
        count = Contact.objects.filter(
            organization=self.organization
        ).count()
        if self.plan.max_contacts == 0:
            return 0
        return min(100, round((count / self.plan.max_contacts) * 100))

    @property
    def emails_usage_percent(self):
        if self.plan.max_emails_per_month == 0:
            return 0
        return min(100, round(
            (self.emails_sent_this_month / self.plan.max_emails_per_month) * 100
        ))


class PaymentMethod(TimeStampedModel):
    """
    Stored payment methods for an organization.
    """
    CARD_BRAND_CHOICES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('discover', 'Discover'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    stripe_payment_method_id = models.CharField(max_length=255, unique=True)

    # Card details (non-sensitive display info)
    card_brand = models.CharField(max_length=20, choices=CARD_BRAND_CHOICES, default='other')
    card_last4 = models.CharField(max_length=4)
    card_exp_month = models.IntegerField()
    card_exp_year = models.IntegerField()

    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = 'billing_payment_methods'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.card_brand} ****{self.card_last4} ({self.organization.name})"

    @property
    def is_expired(self):
        now = timezone.now()
        return (
            self.card_exp_year < now.year or
            (self.card_exp_year == now.year and self.card_exp_month < now.month)
        )


class Invoice(TimeStampedModel):
    """
    Invoice records synced from Stripe.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('void', 'Void'),
        ('uncollectible', 'Uncollectible'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices'
    )

    # Stripe reference
    stripe_invoice_id = models.CharField(max_length=255, unique=True, db_index=True)
    stripe_hosted_invoice_url = models.URLField(max_length=2000, blank=True)
    stripe_invoice_pdf = models.URLField(max_length=2000, blank=True)

    # Invoice details
    number = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    currency = models.CharField(max_length=3, default='usd')

    # Amounts (in cents for precision, displayed as dollars)
    subtotal = models.IntegerField(default=0)
    tax = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    amount_paid = models.IntegerField(default=0)
    amount_due = models.IntegerField(default=0)

    # Dates
    invoice_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Description
    description = models.TextField(blank=True)
    line_items = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'billing_invoices'
        ordering = ['-invoice_date']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['stripe_invoice_id']),
        ]

    def __str__(self):
        return f"Invoice {self.number or self.id} - {self.organization.name}"

    @property
    def total_dollars(self):
        return Decimal(self.total) / 100

    @property
    def subtotal_dollars(self):
        return Decimal(self.subtotal) / 100

    @property
    def tax_dollars(self):
        return Decimal(self.tax) / 100

    @property
    def amount_due_dollars(self):
        return Decimal(self.amount_due) / 100


class BillingEvent(TimeStampedModel):
    """
    Audit log of billing events.
    """
    EVENT_TYPE_CHOICES = [
        ('subscription_created', 'Subscription Created'),
        ('subscription_updated', 'Subscription Updated'),
        ('subscription_cancelled', 'Subscription Cancelled'),
        ('plan_upgraded', 'Plan Upgraded'),
        ('plan_downgraded', 'Plan Downgraded'),
        ('payment_succeeded', 'Payment Succeeded'),
        ('payment_failed', 'Payment Failed'),
        ('invoice_created', 'Invoice Created'),
        ('invoice_paid', 'Invoice Paid'),
        ('trial_started', 'Trial Started'),
        ('trial_ending', 'Trial Ending'),
        ('trial_expired', 'Trial Expired'),
        ('payment_method_added', 'Payment Method Added'),
        ('payment_method_removed', 'Payment Method Removed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='billing_events'
    )
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    stripe_event_id = models.CharField(max_length=255, blank=True, db_index=True)

    class Meta:
        db_table = 'billing_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'event_type']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.organization.name}"
