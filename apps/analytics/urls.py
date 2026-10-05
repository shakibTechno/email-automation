"""
URL configuration for analytics app.
"""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('analytics/', views.AnalyticsOverviewView.as_view(), name='overview'),
    path('analytics/campaigns/', views.CampaignAnalyticsListView.as_view(), name='campaign-list'),
    path('analytics/campaigns/compare/', views.CampaignComparisonView.as_view(), name='campaign-compare'),
    path('analytics/campaigns/<uuid:campaign_id>/', views.CampaignAnalyticsDetailView.as_view(), name='campaign-detail'),
    path('analytics/campaigns/<uuid:campaign_id>/export/', views.CampaignExportView.as_view(), name='campaign-export'),
    path('analytics/contacts/', views.ContactAnalyticsView.as_view(), name='contacts'),
    path('analytics/forms/', views.FormAnalyticsView.as_view(), name='forms'),
    path('analytics/landing-pages/', views.LandingPageAnalyticsView.as_view(), name='landing-pages'),
]
