from django.apps import AppConfig


class LeadScoringConfig(AppConfig):
    name = 'apps.lead_scoring'
    verbose_name = 'Lead Scoring'

    def ready(self):
        import apps.lead_scoring.signals  # noqa: F401
