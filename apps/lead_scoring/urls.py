from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScoringRuleViewSet, ScoreThresholdViewSet

router = DefaultRouter()
router.register(r'scoring-rules', ScoringRuleViewSet, basename='scoring-rule')
router.register(r'score-thresholds', ScoreThresholdViewSet, basename='score-threshold')

urlpatterns = [
    path('', include(router.urls)),
]
