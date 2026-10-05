"""
URL patterns for email tracking endpoints (open pixel, click redirect).
Included under /track/ prefix in config/urls.py.
"""
from django.urls import path
from .tracking_views import TrackClickView, TrackOpenView

urlpatterns = [
    path('o/<uuid:tracking_id>/', TrackOpenView.as_view(), name='track-open'),
    path('c/<uuid:link_id>/<uuid:tracking_id>/', TrackClickView.as_view(), name='track-click'),
]
