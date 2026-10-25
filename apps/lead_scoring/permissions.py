from rest_framework import permissions

# The minimum tier, not a list of tiers. This was
# ('professional', 'enterprise'), which silently excluded Business — a tier
# that sits above Professional and has has_lead_scoring=True in the plan data.
# Business customers were denied a feature they had paid for.
LEAD_SCORING_MIN_PLAN = 'professional'


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
        return org.plan_at_least(LEAD_SCORING_MIN_PLAN)
