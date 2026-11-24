"""
URL configuration for team management endpoints.
"""
from django.urls import path
from .views import (
    TeamMemberListView,
    InviteMemberView,
    InvitationListView,
    ResendInvitationView,
    CancelInvitationView,
    AcceptInvitationView,
    RemoveMemberView,
    ChangeRoleView,
    TransferOwnershipView,
    ActivityLogView,
    OrganizationSettingsView,
    PermissionCatalogView,
    RoleListView,
    RoleDetailView,
)

app_name = 'team'

urlpatterns = [
    # Members
    path('members/', TeamMemberListView.as_view(), name='member-list'),
    path('members/<uuid:member_id>/', RemoveMemberView.as_view(), name='member-remove'),
    path('members/<uuid:member_id>/role/', ChangeRoleView.as_view(), name='member-role'),

    # Roles and the permission vocabulary they are built from
    path('permissions/', PermissionCatalogView.as_view(), name='permission-catalog'),
    path('roles/', RoleListView.as_view(), name='role-list'),
    path('roles/<uuid:role_id>/', RoleDetailView.as_view(), name='role-detail'),

    # Invitations
    path('invite/', InviteMemberView.as_view(), name='invite'),
    path('invitations/', InvitationListView.as_view(), name='invitation-list'),
    path('invitations/<uuid:invitation_id>/resend/', ResendInvitationView.as_view(), name='invitation-resend'),
    path('invitations/<uuid:invitation_id>/', CancelInvitationView.as_view(), name='invitation-cancel'),

    # Accept invitation (public)
    path('accept-invitation/', AcceptInvitationView.as_view(), name='accept-invitation'),

    # Ownership transfer
    path('transfer-ownership/', TransferOwnershipView.as_view(), name='transfer-ownership'),

    # Activity log
    path('activity/', ActivityLogView.as_view(), name='activity-log'),

    # Organization settings
    path('organization/', OrganizationSettingsView.as_view(), name='organization-settings'),
]
