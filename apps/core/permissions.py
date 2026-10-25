"""
Custom permissions for the application.
"""
from rest_framework import permissions


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


class IsOrganizationAdmin(permissions.BasePermission):
    """
    Permission to check if user is an admin of the organization.
    """
    message = 'You must be an admin of this organization.'

    def has_permission(self, request, view):
        # The organization check is not redundant with the role check.
        # create_superuser() sets role='owner' and platform staff have no
        # organization, so testing role alone admitted an org-less staff user
        # to tenant endpoints, which then misbehaved on
        # request.user.organization. Membership is a precondition of
        # administering anything.
        return (
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'organization', None) is not None and
            request.user.role in ['admin', 'owner']
        )

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'organization'):
            return (
                obj.organization == request.user.organization and
                request.user.role in ['admin', 'owner']
            )
        return False


class IsAdminForDestructiveActions(permissions.BasePermission):
    """
    Role-based permission enforcement:
    - Viewer: only SAFE_METHODS (GET, HEAD, OPTIONS)
    - Member: SAFE_METHODS + POST/PUT/PATCH, but NOT DELETE and NOT
      specific destructive ViewSet actions
    - Admin/Owner: everything allowed
    """
    # Actions a 'member' may not perform. `resume` belongs here with `send` and
    # `pause` because resuming a campaign sends mail — without it a member who
    # cannot start a campaign could still restart a paused one.
    RESTRICTED_ACTIONS = {
        'destroy', 'bulk_delete', 'send', 'pause', 'resume', 'cancel',
        'publish', 'unpublish', 'activate', 'deactivate', 'toggle_status',
    }

    message = 'You do not have permission to perform this action.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        role = getattr(request.user, 'role', None)

        # Owner and Admin can do everything
        if role in ('owner', 'admin'):
            return True

        # Viewer: read-only
        if role == 'viewer':
            return request.method in permissions.SAFE_METHODS

        # Member: allow safe methods + create/edit, block DELETE and restricted actions
        if role == 'member':
            if request.method == 'DELETE':
                return False
            action = getattr(view, 'action', None)
            if action in self.RESTRICTED_ACTIONS:
                return False
            return True

        return False


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
