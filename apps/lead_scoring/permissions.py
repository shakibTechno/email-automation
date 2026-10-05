from rest_framework import permissions

LEAD_SCORING_PLANS = ('professional', 'enterprise')


class LeadScoringEnabled(permissions.BasePermission):
    """
    Restricts lead scoring endpoints to Professional plan and above.
    Returns 403 with a plan-upgrade message for lower tiers.
    """
    message = (
        'Lead Scoring requires a Professional plan or above. '
        'Please upgrade your subscription to access this feature.'
    )

    def has_permission(self, request, view):
        org = getattr(request.user, 'organization', None)
        if org is None:
            return False
        return org.plan in LEAD_SCORING_PLANS
