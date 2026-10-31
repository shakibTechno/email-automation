from django.urls import path

from .views import collect, snippet

app_name = 'tracking'

urlpatterns = [
    # Deliberately at the root and deliberately short: this URL ends up in the
    # page source of every customer site that installs it.
    path('t.js', snippet, name='snippet'),

    # Under /track/, which nginx already proxies to Django and which is
    # already the public, unauthenticated, CSRF-exempt namespace.
    path('track/collect', collect, name='collect'),
]
