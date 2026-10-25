"""
Shared viewset behaviour for tenant isolation.
"""


class OrganizationScopedQuerysetMixin:
    """
    Restrict every queryset to the requesting user's organization.

    Isolation in this project is enforced per viewset: each one filters
    `get_queryset()` by `request.user.organization`. That is correct in all of
    them today, but it is a convention, and conventions are forgotten. The
    failure is quiet and total — DRF only calls `has_object_permission` for
    detail routes, so a viewset with an unscoped queryset passes every
    permission check and returns every tenant's rows on its list endpoint.

    Inherit this ahead of the viewset class:

        class WidgetViewSet(OrganizationScopedQuerysetMixin, ModelViewSet):
            queryset = Widget.objects.all()

    Set `organization_field` when the FK is reached through a relation, e.g.
    `'campaign__organization'`.
    """

    organization_field = 'organization'

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = getattr(self.request.user, 'organization', None)

        # Fail closed. A user without an organization — an inconsistent record,
        # or a permission class omitted by mistake — gets nothing rather than
        # falling through to an unfiltered queryset.
        if organization is None:
            return queryset.none()

        return queryset.filter(**{self.organization_field: organization})

    def perform_create(self, serializer):
        """Stamp the organization on create so it cannot be supplied by the client."""
        serializer.save(organization=self.request.user.organization)
