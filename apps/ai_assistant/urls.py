from django.urls import path

from .views import (
    AIConfigTestView,
    AIConfigView,
    GenerateView,
    GenerationJobView,
)

urlpatterns = [
    path('ai/config/', AIConfigView.as_view(), name='ai-config'),
    path('ai/config/test/', AIConfigTestView.as_view(), name='ai-config-test'),
    # `kind` is one of GenerationJob.KIND_CHOICES.
    path('ai/generate/<str:kind>/', GenerateView.as_view(), name='ai-generate'),
    path('ai/jobs/<uuid:job_id>/', GenerationJobView.as_view(), name='ai-generation-job'),
]
