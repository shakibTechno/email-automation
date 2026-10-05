"""
URL configuration for the Landing Pages app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import LandingPageViewSet, LandingPageTemplateViewSet

router = DefaultRouter()
router.register(r'landing-pages', LandingPageViewSet, basename='landing-page')
router.register(r'landing-page-templates', LandingPageTemplateViewSet, basename='landing-page-template')

urlpatterns = [
    path('', include(router.urls)),
]
