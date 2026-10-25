from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DeliverabilityView,
    PlatformOverviewView,
    RevenueView,
    TenantViewSet,
)

router = DefaultRouter()
router.register(r'landlord/tenants', TenantViewSet, basename='landlord-tenant')

urlpatterns = [
    path('landlord/overview/', PlatformOverviewView.as_view(), name='landlord-overview'),
    path('landlord/deliverability/', DeliverabilityView.as_view(), name='landlord-deliverability'),
    path('landlord/revenue/', RevenueView.as_view(), name='landlord-revenue'),
    path('', include(router.urls)),
]
