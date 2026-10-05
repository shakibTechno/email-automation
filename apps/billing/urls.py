"""
URL configuration for the billing app.
"""
from django.urls import path
from . import views
from .webhooks import stripe_webhook

urlpatterns = [
    # Plans
    path('plans/', views.PlanListView.as_view(), name='billing-plans'),

    # Subscription
    path('overview/', views.BillingOverviewView.as_view(), name='billing-overview'),
    path('subscription/', views.SubscriptionView.as_view(), name='billing-subscription'),
    path('change-plan/', views.ChangePlanView.as_view(), name='billing-change-plan'),
    path('create-checkout-session/', views.CreateCheckoutSessionView.as_view(), name='billing-create-checkout'),
    path('complete-demo-checkout/', views.CompleteDemoCheckoutView.as_view(), name='billing-complete-demo-checkout'),
    path('preview-change/', views.PlanChangePreviewView.as_view(), name='billing-preview-change'),
    path('cancel/', views.CancelSubscriptionView.as_view(), name='billing-cancel'),
    path('reactivate/', views.ReactivateSubscriptionView.as_view(), name='billing-reactivate'),

    # Payment Methods
    path('payment-methods/', views.PaymentMethodListView.as_view(), name='billing-payment-methods'),
    path('payment-methods/<uuid:pk>/', views.PaymentMethodDeleteView.as_view(), name='billing-payment-method-delete'),
    path('payment-methods/<uuid:pk>/set-default/', views.PaymentMethodSetDefaultView.as_view(), name='billing-payment-method-set-default'),
    path('setup-intent/', views.SetupIntentView.as_view(), name='billing-setup-intent'),
    path('add-payment-method/', views.AddPaymentMethodView.as_view(), name='billing-add-payment-method'),

    # Invoices
    path('invoices/', views.InvoiceListView.as_view(), name='billing-invoices'),

    # Events
    path('events/', views.BillingEventListView.as_view(), name='billing-events'),

    # Usage
    path('usage/', views.UsageLimitCheckView.as_view(), name='billing-usage'),

    # Stripe config
    path('stripe-config/', views.StripeConfigView.as_view(), name='billing-stripe-config'),

    # Webhooks (no auth)
    path('webhooks/stripe/', stripe_webhook, name='stripe-webhook'),
]
