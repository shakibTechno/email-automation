"""
URL configuration for contacts app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContactViewSet, TagViewSet, CustomFieldViewSet

app_name = 'contacts'

router = DefaultRouter()
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'custom-fields', CustomFieldViewSet, basename='customfield')

urlpatterns = [
    path('', include(router.urls)),
]
