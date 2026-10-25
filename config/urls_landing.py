"""
The only URLs that exist on a customer's connected domain.

`LandingHostMiddleware` points `request.urlconf` here for any request whose Host
is a connected landing domain. The list is short on purpose: the API, the admin
and the SPA are not reachable on a customer's hostname because they are not
routed there at all. A route that does not exist cannot be reached by a view
that forgot to check something.
"""
from django.conf import settings
from django.urls import include, path

from apps.landing_pages.views import (
    DomainVerificationTokenView,
    PublicLandingPageView,
)

urlpatterns = [
    # Served before the slug route so a page can never claim this path.
    path(
        '.well-known/mailflow-domain-verification/<str:token>/',
        DomainVerificationTokenView.as_view(),
        name='landing-domain-verification',
    ),

    # The domain root: whichever page the customer marked as its home.
    path('', PublicLandingPageView.as_view(), name='landing-domain-home'),

    # Every other page on this domain.
    path('<slug:slug>/', PublicLandingPageView.as_view(), name='landing-domain-page'),
    # Without a trailing slash too: a link in an advert will not have one, and
    # APPEND_SLASH's redirect costs a round trip on the page that matters most.
    path('<slug:slug>', PublicLandingPageView.as_view(), name='landing-domain-page-bare'),
]

# Development only. The debug toolbar's middleware runs on every request and
# reverses `djdt:` names while rendering, so a URLconf without them turns every
# page on a connected domain into a NoReverseMatch 500 — which is exactly how
# this was found locally. It is absent in production, where the toolbar is not
# installed.
if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
