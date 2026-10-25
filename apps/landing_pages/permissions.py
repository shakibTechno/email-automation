from rest_framework import permissions

# The minimum tier, not a list of tiers — the same shape as
# LEAD_SCORING_MIN_PLAN, and for the same reason: a hardcoded tuple of tiers
# silently excluded Business, a tier that sits above the one it named.
CUSTOM_DOMAIN_MIN_PLAN = 'starter'


class CustomDomainsEnabled(permissions.BasePermission):
    """
    Restricts connected landing-page domains to paid plans.

    Not only an upsell: a connected domain causes this server to request a
    certificate for someone else's hostname, so the feature should sit behind a
    payment relationship rather than a free signup.
    """
    message = (
        'Connecting your own domain requires a paid plan. '
        'Please upgrade your subscription to access this feature.'
    )

    def has_permission(self, request, view):
        org = getattr(request.user, 'organization', None)
        if org is None:
            return False
        return org.plan_at_least(CUSTOM_DOMAIN_MIN_PLAN)
