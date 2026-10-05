"""
URL configuration for core app.
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Health checks
    path('health/', views.health_check, name='health'),
    path('ready/', views.readiness_check, name='ready'),
    path('live/', views.liveness_check, name='live'),

    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/overview/', views.DashboardOverviewView.as_view(), name='dashboard-overview'),
    path('dashboard/campaigns/', views.DashboardCampaignStatsView.as_view(), name='dashboard-campaigns'),
    path('dashboard/contacts/', views.DashboardContactGrowthView.as_view(), name='dashboard-contacts'),
]
