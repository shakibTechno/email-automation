"""
Base classes for cross-tenant views.

Everything in this app deliberately reads across every tenant, which is the one
invariant the rest of the system exists to protect. That inversion is confined
to these base classes so it is declared rather than implied: a view that crosses
tenants says so by its base class, and the isolation guard in
apps/core/tests/test_tenant_isolation.py recognises that declaration instead of
treating it as a forgotten filter.
"""
from rest_framework import viewsets
from rest_framework.views import APIView

from .permissions import IsPlatformStaff


class PlatformScopedMixin:
    """
    Marks a view as intentionally cross-tenant and restricts it to staff.

    `permission_classes` is set here rather than left to each view because
    DRF's project default is a bare `IsAuthenticated` — a landlord view that
    forgot to declare its own would be readable by every logged-in customer,
    which is the worst failure this app could have. Setting it on the base
    means it cannot be omitted, only overridden on purpose.
    """
    permission_classes = [IsPlatformStaff]


class PlatformScopedViewSet(PlatformScopedMixin, viewsets.GenericViewSet):
    """Cross-tenant viewset. See the module docstring before adding one."""


class PlatformScopedAPIView(PlatformScopedMixin, APIView):
    """Cross-tenant APIView, for the aggregate endpoints that are not list/detail."""
