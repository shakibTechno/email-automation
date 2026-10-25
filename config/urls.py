"""
URL configuration for Email Marketing Automation Platform.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.email_config.webhooks import postal_webhook
from apps.landing_pages.internal_views import tls_allow
from apps.landing_pages.views import PublicLandingPageView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API endpoints
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/team/', include('apps.accounts.team_urls')),
    path('api/v1/', include('apps.core.urls')),
    path('api/v1/', include('apps.contacts.urls')),
    path('api/v1/', include('apps.templates.urls')),
    path('api/v1/', include('apps.campaigns.urls')),
    path('api/v1/', include('apps.forms.urls')),
    path('api/v1/', include('apps.landing_pages.urls')),
    path('api/v1/', include('apps.workflows.urls')),
    path('api/v1/', include('apps.segments.urls')),
    path('api/v1/', include('apps.analytics.urls')),
    path('api/v1/', include('apps.crm.urls')),
    path('api/v1/billing/', include('apps.billing.urls')),
    path('api/v1/', include('apps.integrations.urls')),
    path('api/v1/', include('apps.lead_scoring.urls')),
    path('api/v1/', include('apps.notifications.urls')),
    path('api/v1/', include('apps.sequences.urls')),
    path('api/v1/', include('apps.email_config.urls')),
    path('api/v1/', include('apps.ai_assistant.urls')),
    path('api/v1/', include('apps.landlord.urls')),

    # Public email tracking routes (no auth)
    path('track/', include('apps.campaigns.tracking_urls')),
    path(
        'unsubscribe/<str:token>/',
        __import__(
            'apps.campaigns.tracking_views', fromlist=['UnsubscribeView']
        ).UnsubscribeView.as_view(),
        name='unsubscribe',
    ),

    # Anymail webhook (SES/ESP delivery events) — optional, requires anymail package
    # path('anymail/', include('anymail.urls')),

    # Postal delivery events (no auth; the body carries an RSA signature).
    # Registered with AND without a trailing slash on purpose: the provisioner
    # writes the no-slash form into every tenant's webhook config, and
    # APPEND_SLASH would answer that POST with a 301 and lose the body.
    path('webhooks/postal', postal_webhook, name='postal-webhook'),
    path('webhooks/postal/', postal_webhook, name='postal-webhook-slash'),

    # Public landing pages. The organization-scoped form comes first and is the
    # one `LandingPage.public_url` hands out: page slugs are unique per tenant,
    # so the bare form below cannot identify a page once two tenants share a
    # slug. It stays only for links published before this route existed.
    path('p/<slug:org_slug>/<slug:slug>/',
         PublicLandingPageView.as_view(),
         name='public-landing-page'),
    path('p/<slug:slug>/',
         PublicLandingPageView.as_view(),
         name='public-landing-page-legacy'),

    # Caddy's on-demand TLS gate. `/internal/` is deliberately absent from
    # frontend/nginx.conf's proxied-path regex and from config.urls_landing, so
    # the only way here is Caddy reaching backend:8000 over the Docker network.
    # Exposing it publicly lets a stranger burn our Let's Encrypt quota.
    path('internal/tls-allow', tls_allow, name='internal-tls-allow'),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
