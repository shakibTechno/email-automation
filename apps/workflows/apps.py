"""
Workflows app configuration.
"""
from django.apps import AppConfig


class WorkflowsConfig(AppConfig):
    """Configuration for the workflows app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.workflows'
    verbose_name = 'Workflow Automation'

    def ready(self):
        """Import signals when the app is ready."""
        import apps.workflows.signals  # noqa: F401
