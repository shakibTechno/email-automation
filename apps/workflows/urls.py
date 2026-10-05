"""
URL configuration for the Workflow Automation app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WorkflowViewSet,
    WorkflowExecutionViewSet,
    WorkflowTemplateViewSet,
)

router = DefaultRouter()
router.register(r'workflows', WorkflowViewSet, basename='workflow')
router.register(r'workflow-executions', WorkflowExecutionViewSet, basename='workflow-execution')
router.register(r'workflow-templates', WorkflowTemplateViewSet, basename='workflow-template')

urlpatterns = [
    path('', include(router.urls)),
]
