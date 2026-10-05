"""
URL configuration for the integrations app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Analytics
    path('integrations/analytics/', views.AnalyticsIntegrationListView.as_view(), name='analytics-integrations-list'),
    path('integrations/analytics/upsert/', views.AnalyticsIntegrationUpsertView.as_view(), name='analytics-integration-upsert'),
    path('integrations/analytics/<str:provider>/', views.AnalyticsIntegrationDeleteView.as_view(), name='analytics-integration-delete'),
    # Social
    path('integrations/social/', views.SocialIntegrationListView.as_view(), name='social-integrations-list'),
    path('integrations/social/demo-connect/', views.DemoConnectView.as_view(), name='social-demo-connect'),
    path('integrations/social/<uuid:pk>/credentials/', views.SocialIntegrationUpdateCredentialsView.as_view(), name='social-integration-credentials'),
    path('integrations/social/<uuid:pk>/connect/', views.SocialIntegrationConnectView.as_view(), name='social-integration-connect'),
    path('integrations/social/<uuid:pk>/', views.SocialIntegrationUpdateView.as_view(), name='social-integration-update'),
    path('integrations/social/<uuid:pk>/disconnect/', views.SocialIntegrationDisconnectView.as_view(), name='social-integration-disconnect'),
    path('integrations/social/<uuid:pk>/sync/', views.SocialIntegrationSyncView.as_view(), name='social-integration-sync'),
    path('integrations/social/<uuid:pk>/sync-history/', views.SyncHistoryView.as_view(), name='social-sync-history'),
    # Field mapping options
    path('integrations/field-mapping-options/', views.FieldMappingOptionsView.as_view(), name='field-mapping-options'),
]
