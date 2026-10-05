from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PipelineViewSet, DealViewSet, ActivityViewSet, CRMTaskViewSet, CompanyViewSet

app_name = 'crm'

router = DefaultRouter()
router.register(r'pipelines', PipelineViewSet, basename='pipeline')
router.register(r'deals', DealViewSet, basename='deal')
router.register(r'activities', ActivityViewSet, basename='activity')
router.register(r'tasks', CRMTaskViewSet, basename='crm-task')
router.register(r'companies', CompanyViewSet, basename='company')

urlpatterns = [
    path('', include(router.urls)),
]
