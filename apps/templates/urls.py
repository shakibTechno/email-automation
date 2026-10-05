"""
URL configuration for templates app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailTemplateViewSet, TemplateImageViewSet

app_name = 'templates'

router = DefaultRouter()
router.register(r'templates', EmailTemplateViewSet, basename='emailtemplate')
router.register(r'template-images', TemplateImageViewSet, basename='templateimage')

urlpatterns = [
    path('', include(router.urls)),
]
