"""
URL configuration for the Landing Pages app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import LandingDomainViewSet, LandingPageViewSet, LandingPageTemplateViewSet

router = DefaultRouter()
router.register(r'landing-pages', LandingPageViewSet, basename='landing-page')
router.register(r'landing-page-templates', LandingPageTemplateViewSet, basename='landing-page-template')
router.register(r'landing-domains', LandingDomainViewSet, basename='landing-domain')

urlpatterns = [
    path('', include(router.urls)),
]
