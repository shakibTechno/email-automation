"""
Custom permissions for the application.
"""
from rest_framework import permissions


class IsOrganizationMember(permissions.BasePermission):
    """
    Permission to check if user is a member of the organization.
    """
    message = 'You must be a member of an organization to perform this action.'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'organization', None) is not None
        )

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
        return (
            request.user and
            request.user.is_authenticated and
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
    RESTRICTED_ACTIONS = {
        'destroy', 'bulk_delete', 'send', 'pause', 'cancel',
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
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'owner'
        )

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'organization'):
            return (
                obj.organization == request.user.organization and
                request.user.role == 'owner'
            )
        return False
