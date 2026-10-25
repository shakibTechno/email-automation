"""
Test helpers for billing.

The test settings set MIGRATION_MODULES = DisableMigrations(), which builds the
schema straight from the models and so never runs data migrations. That means
`Plan` is empty in tests, and anything depending on it fails quietly rather than
loudly: initialize_subscription() returns None with a log line, and
check_usage_limit() reports 'No active subscription'. Tests that touch plans or
quotas must call create_plans() first.

The figures below mirror apps/billing/migrations/0002_create_default_plans.py.
Only the fields tests actually read are reproduced; the migration remains the
source of truth for real data.
"""
from apps.billing.models import Plan

# (plan_type, name, price, max_contacts, max_emails_per_month, sort_order)
_TIERS = [
    ('free', 'Free', 0, 500, 1000, 0),
    ('starter', 'Starter', 29, 2500, 25000, 1),
    ('professional', 'Professional', 99, 10000, 100000, 2),
    ('business', 'Business', 299, 50000, 500000, 3),
    ('enterprise', 'Enterprise', 0, 999999, 999999, 4),
]


def create_plans():
    """Create the five monthly plan tiers. Idempotent."""
    for plan_type, name, price, contacts, emails, order in _TIERS:
        Plan.objects.get_or_create(
            plan_type=plan_type,
            interval='month',
            defaults={
                'name': name,
                'price': price,
                'max_contacts': contacts,
                'max_emails_per_month': emails,
                'sort_order': order,
                'is_active': True,
                # Professional and above carry lead scoring in the real seed
                # data — the entitlement that the plan-tier bug denied to
                # Business customers.
                'has_lead_scoring': order >= 2,
            },
        )


def free_plan():
    create_plans()
    return Plan.objects.get(plan_type='free', interval='month')
