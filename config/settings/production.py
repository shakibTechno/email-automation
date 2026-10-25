"""
Production settings for Email Marketing Automation Platform.
"""
from .base import *

DEBUG = False

# Security Settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Static files (whitenoise or S3)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# EMAIL_BACKEND is read from the environment in base.py and deliberately not
# overridden here. It used to be pinned to Anymail's Amazon SES backend, which
# meant production could not use any other provider no matter what was
# configured — and boto3 is not a dependency, so the first send that reached
# the global backend raised ImportError rather than sending anything.
#
# Per-organization sending does not come through here at all: it resolves a
# connection via EmailConfigService.get_connection(). This only sets the
# fallback used by anything that sends without one.

# Only JSON renderer in production
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
]

# Logging - Less verbose in production
LOGGING['loggers']['apps']['level'] = 'INFO'
LOGGING['loggers']['django']['level'] = 'WARNING'

# Add Sentry for error tracking in production
# import sentry_sdk
# from sentry_sdk.integrations.django import DjangoIntegration
#
# sentry_sdk.init(
#     dsn=env('SENTRY_DSN'),
#     integrations=[DjangoIntegration()],
#     traces_sample_rate=0.1,
#     send_default_pii=False,
# )
