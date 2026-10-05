from django.contrib import admin
from .models import Plan, Subscription, PaymentMethod, Invoice, BillingEvent


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'interval', 'price', 'max_contacts',
                    'max_emails_per_month', 'is_active', 'sort_order']
    list_filter = ['plan_type', 'interval', 'is_active']
    search_fields = ['name', 'plan_type']
    list_editable = ['is_active', 'sort_order']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['organization', 'plan', 'status', 'interval',
                    'current_period_start', 'current_period_end', 'trial_end']
    list_filter = ['status', 'interval', 'plan__plan_type']
    search_fields = ['organization__name', 'stripe_customer_id', 'stripe_subscription_id']
    raw_id_fields = ['organization', 'plan']
    readonly_fields = ['stripe_customer_id', 'stripe_subscription_id']


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['organization', 'card_brand', 'card_last4',
                    'card_exp_month', 'card_exp_year', 'is_default']
    list_filter = ['card_brand', 'is_default']
    search_fields = ['organization__name', 'card_last4']
    raw_id_fields = ['organization']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['number', 'organization', 'status', 'total',
                    'currency', 'invoice_date', 'paid_at']
    list_filter = ['status', 'currency']
    search_fields = ['organization__name', 'number', 'stripe_invoice_id']
    raw_id_fields = ['organization', 'subscription']
    readonly_fields = ['stripe_invoice_id']


@admin.register(BillingEvent)
class BillingEventAdmin(admin.ModelAdmin):
    list_display = ['organization', 'event_type', 'created_at']
    list_filter = ['event_type']
    search_fields = ['organization__name', 'description']
    raw_id_fields = ['organization']
    readonly_fields = ['stripe_event_id']
