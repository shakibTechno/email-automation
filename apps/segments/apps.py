"""
Segments app configuration.
"""
from django.apps import AppConfig


class SegmentsConfig(AppConfig):
    """Configuration for the segments app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.segments'
    verbose_name = 'Contact Segmentation'
