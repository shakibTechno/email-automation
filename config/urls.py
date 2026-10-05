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

    # Public landing page route
    path('p/<slug:slug>/',
         __import__('apps.landing_pages.views', fromlist=['PublicLandingPageView']).PublicLandingPageView.as_view(),
         name='public-landing-page'),

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
