from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailSequenceViewSet, SequenceStepViewSet, SequenceEnrollmentViewSet

router = DefaultRouter()
router.register(r'sequences', EmailSequenceViewSet, basename='sequence')
router.register(r'sequence-steps', SequenceStepViewSet, basename='sequence-step')
router.register(r'sequence-enrollments', SequenceEnrollmentViewSet, basename='sequence-enrollment')

urlpatterns = [
    path('', include(router.urls)),
]
