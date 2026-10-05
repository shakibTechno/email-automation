"""
URL configuration for the Contact Segmentation app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SegmentViewSet, SegmentMembershipViewSet

router = DefaultRouter()
router.register(r'segments', SegmentViewSet, basename='segment')

urlpatterns = [
    path('', include(router.urls)),
    # Nested memberships endpoint
    path(
        'segments/<uuid:segment_pk>/memberships/',
        SegmentMembershipViewSet.as_view({'get': 'list'}),
        name='segment-memberships'
    ),
]
