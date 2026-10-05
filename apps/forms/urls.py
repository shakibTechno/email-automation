from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FormViewSet, PublicFormViewSet

app_name = 'forms'

router = DefaultRouter()
router.register(r'forms', FormViewSet, basename='form')

public_router = DefaultRouter()
public_router.register(r'public/forms', PublicFormViewSet, basename='public-form')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(public_router.urls)),
]
