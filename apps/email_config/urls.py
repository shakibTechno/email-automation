from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailConfigView, EmailConfigTestView, EmailConfigResumeView, SendingDomainViewSet

router = DefaultRouter()
router.register(r'email-config/domains', SendingDomainViewSet, basename='sending-domain')

urlpatterns = [
    path('email-config/', EmailConfigView.as_view(), name='email-config'),
    path('email-config/test/', EmailConfigTestView.as_view(), name='email-config-test'),
    path('email-config/resume/', EmailConfigResumeView.as_view(), name='email-config-resume'),
    path('', include(router.urls)),
]
