"""
Access control for the landlord console.
"""
from rest_framework import permissions


class IsPlatformStaff(permissions.BasePermission):
    """
    Platform operators only — the people who run the service, not its customers.

    Deliberately the whole of the authorization model for this app. `is_staff`
    is binary and total here: `User.has_perm` is overridden to return True for
    every permission when it is set, so Django's permission framework cannot
    express anything finer without replacing that. A read-only landlord role
    would need that override replaced first, which is out of scope.

    Note this is *not* `role`, which is organization-scoped: an owner is the
    owner of one tenant and must never reach this console.
    """
    message = 'This area is restricted to platform staff.'

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_staff
        )
