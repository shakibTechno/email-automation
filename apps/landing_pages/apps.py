from django.apps import AppConfig


class LandingPagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.landing_pages'
    verbose_name = 'Landing Pages'

    def ready(self):
        """Import signals when the app is ready."""
        import apps.landing_pages.signals  # noqa: F401
