"""
Custom permissions for the application.

Every tenant endpoint resolves to one permission code from apps/core/access.py
and asks whether the caller's role holds it. The classes here only translate a
request into that code; what a role may do is declared in access.py and nowhere
else.
"""
from rest_framework import permissions

from apps.core import access


class IsOrganizationMember(permissions.BasePermission):
    """
    Permission to check if user is a member of the organization.
    """
    message = 'You must be a member of an organization to perform this action.'
    suspended_message = (
        'This account has been suspended. Contact support to restore access.'
    )

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        organization = getattr(request.user, 'organization', None)
        if organization is None:
            return False

        # A suspended organization keeps its data but loses API access. Checked
        # here rather than only at login, because an access token issued before
        # the suspension stays valid for an hour and would otherwise keep
        # working against every endpoint.
        if not organization.is_active:
            self.message = self.suspended_message
            return False

        return True

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'organization'):
            return obj.organization == request.user.organization
        # No direct organization FK — queryset already enforces org isolation
        return True


class HasResourcePermission(permissions.BasePermission):
    """
    The caller's role must hold the permission this request needs.

    The resource comes from the view's app (apps/campaigns/views.py -> the
    `campaigns` resource) unless the view sets `permission_resource`, and the
    verb from the ViewSet action or the HTTP method. A view whose resource is
    not declared in access.RESOURCES is denied to everyone, so adding an
    endpoint outside the registry fails closed instead of opening up.
    """
    message = 'You do not have permission to perform this action.'

    # None: the verb follows the ViewSet action or the HTTP method.
    permission_verb = None

    def _allows(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        # The organization check is not redundant with the permission check.
        # create_superuser() sets role='owner' and platform staff have no
        # organization, so testing the role alone admitted an org-less staff
        # user to tenant endpoints, which then misbehaved on
        # request.user.organization. Membership is a precondition of everything
        # here.
        if getattr(user, 'organization', None) is None:
            return False

        code = access.required_permission(view, request, verb=self.permission_verb)
        if code is None:
            return False
        return access.has_permission(user, code)

    def has_permission(self, request, view):
        return self._allows(request, view)

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'organization') and obj.organization != request.user.organization:
            return False
        return self._allows(request, view)


class RequiresResourceManage(HasResourcePermission):
    """
    Like HasResourcePermission, but the whole view is a `manage` surface.

    For endpoints that are privileged even to read: the pending-invitation list
    hands out live accept links, and the activity log is an audit trail. Reading
    those is not a `view` on the resource.
    """
    permission_verb = access.MANAGE


# Kept under their old names: every ViewSet and APIView in the project already
# names these, and the enforcement behind them is what changed, not where it
# applies. IsOrganizationAdmin now means "may manage this resource", which for
# the four built-in roles is the same set of people as before.
IsAdminForDestructiveActions = HasResourcePermission
IsOrganizationAdmin = RequiresResourceManage


class IsOrganizationOwner(permissions.BasePermission):
    """
    Permission to check if user is the owner of the organization.
    """
    message = 'You must be the owner of this organization.'

    def has_permission(self, request, view):
        # See IsOrganizationAdmin: role alone is not enough, because an
        # org-less platform-staff account carries role='owner'.
        return (
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'organization', None) is not None and
            request.user.role == 'owner'
        )

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'organization'):
            return (
                obj.organization == request.user.organization and
                request.user.role == 'owner'
            )
        return False
