from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PopupTemplateViewSet, PopupViewSet

app_name = 'popups'

router = DefaultRouter()
router.register(r'popups', PopupViewSet, basename='popup')
router.register(r'popup-templates', PopupTemplateViewSet, basename='popup-template')

urlpatterns = [
    path('', include(router.urls)),
]
