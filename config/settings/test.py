"""
Test settings for Email Marketing Automation Platform.
"""
from .base import *

DEBUG = True

# Use faster password hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# In-memory SQLite by default, because a full run takes seconds rather than
# minutes and that is what makes it worth running on every change.
#
# Set TEST_WITH_POSTGRES=1 to run against the real engine instead. SQLite is
# the more permissive of the two — it is lax about types, casts and some
# constraint timing — so a suite that only ever runs on SQLite cannot tell you
# the code works on the database production uses. Run the Postgres variant
# before releasing and in CI.
TEST_WITH_POSTGRES = env.bool('TEST_WITH_POSTGRES', default=False)

if TEST_WITH_POSTGRES:
    DATABASES = {'default': env.db('DATABASE_URL')}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

# Use local memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable Axes in tests
AXES_ENABLED = False

# Build the schema straight from the models instead of replaying every
# migration — much faster, and migration history is irrelevant to most tests.
#
# Not applied under Postgres: there the point of the run is to exercise what
# production actually does, and a migration that fails on Postgres is exactly
# the kind of breakage this mode exists to catch.
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

if not TEST_WITH_POSTGRES:
    MIGRATION_MODULES = DisableMigrations()

# Logging - Minimal in tests
LOGGING['handlers']['console']['level'] = 'ERROR'

# Throttle state lives in the cache and so leaks between tests in one process:
# the fifth test to call password reset would be rejected because of the four
# before it. Raised out of the way here, and exercised deliberately by the
# tests that override it back down.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_THROTTLE_RATES': {
        'password_reset': '10000/hour',
        'email_verification': '10000/hour',
    },
}
