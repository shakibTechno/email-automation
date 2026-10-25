"""
Base settings for Email Marketing Automation Platform.
"""
import os
from pathlib import Path
from datetime import timedelta
import environ

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment variables
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, 'change-me-in-production'),
    ALLOWED_HOSTS=(list, []),
    FRONTEND_URL=(str, 'http://localhost:3000'),
    BACKEND_URL=(str, 'http://localhost:8000'),
)

# Frontend URL for embed codes and public form links
FRONTEND_URL = env('FRONTEND_URL')

# Backend URL for public landing pages
BACKEND_URL = env('BACKEND_URL')

# Read .env file if it exists
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(str(env_file))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

# Hostnames that serve the application itself. Everything else that reaches us
# must be a connected landing domain, which `LandingHostMiddleware` resolves per
# request; it cannot be enumerated here because customers add domains at will.
#
# `backend` is the Docker-network name Caddy uses for its on-demand TLS
# callback. Without it that callback is rejected as an unknown host and no
# customer domain ever gets a certificate.
# Defaults to the ALLOWED_HOSTS environment variable, which every existing
# deployment already sets — so this needs no new configuration and no
# deployment ends up with an empty platform list.
_DEFAULT_PLATFORM_HOSTS = ['localhost', '127.0.0.1', 'testserver', 'backend']
PLATFORM_HOSTS = sorted(
    set(env.list('PLATFORM_HOSTS', default=[]) or env.list('ALLOWED_HOSTS', default=[]))
    | set(_DEFAULT_PLATFORM_HOSTS)
)

# Deliberately permissive, in every environment, because the host check moved
# to LandingHostMiddleware — see that class for why, and the warning in
# config/settings/production.py for what depends on it.
#
# Pinning this to the platform hosts instead does not fail safe, it fails
# confusingly: the middleware resolves a customer's domain correctly and then
# Django rejects the very same request downstream with DisallowedHost. Found
# exactly that way, by curl, against a connected domain that should have
# worked.
ALLOWED_HOSTS = ['*']

# The CNAME value a customer publishes to point their domain at this platform.
LANDING_DOMAIN_CNAME_TARGET = env('LANDING_DOMAIN_CNAME_TARGET', default='')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'axes',

    # Local apps
    'apps.core',
    'apps.accounts',
    'apps.contacts',
    'apps.templates',
    'apps.campaigns',
    'apps.forms',
    'apps.landing_pages',
    'apps.workflows',
    'apps.segments',
    'apps.analytics',
    'apps.crm',
    'apps.billing',
    'apps.integrations',
    'apps.lead_scoring',
    'apps.notifications',
    'apps.sequences',
    'apps.email_config',
    'apps.ai_assistant',
    'apps.landlord',
]

MIDDLEWARE = [
    # First on purpose. It decides whether a Host belongs to the platform or to
    # a customer's connected landing domain, swaps in the landing-only URLconf
    # for the latter, and refuses anything else — so it has to run before
    # anything reads the host or resolves a URL.
    'apps.landing_pages.middleware.LandingHostMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': env.db(
        'DATABASE_URL',
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3')
    )
}

# Under Docker the web, Celery worker and Celery beat processes all open the
# same SQLite file from a shared volume. Without a busy timeout a concurrent
# writer fails immediately with "database is locked"; with it, it waits for the
# lock. (The matching journal_mode=WAL is set once in docker/entrypoint.sh.)
if 'sqlite' in DATABASES['default'].get('ENGINE', ''):
    DATABASES['default'].setdefault('OPTIONS', {})
    DATABASES['default']['OPTIONS'].setdefault('timeout', 30)

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S.%fZ',
    'DATE_FORMAT': '%Y-%m-%d',
}


# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=60)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=env.int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7)
    ),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}


# CORS Configuration
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=['http://localhost:3000', 'http://localhost:8000']
)

# Django rejects any HTTPS POST whose Origin is not listed here, so behind a
# TLS-terminating proxy this must name the public origin or the admin login
# and every session-authenticated form fail CSRF validation. The REST API is
# unaffected, since it authenticates with JWT rather than a session cookie —
# which is why this breaks in a way that looks like "only the admin is broken".
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])


# Cache Configuration (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'email_automation',
        'TIMEOUT': 300,
    }
}


# Email Configuration
EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=25)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@example.com')
SERVER_EMAIL = env('SERVER_EMAIL', default='admin@example.com')


# Password Reset
PASSWORD_RESET_TIMEOUT = env.int('PASSWORD_RESET_TIMEOUT', default=3600)


# Django Axes (Brute Force Protection)
AXES_FAILURE_LIMIT = env.int('AXES_FAILURE_LIMIT', default=5)
AXES_COOLOFF_TIME = env.int('AXES_COOLOFF_TIME', default=1)  # hours
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True
AXES_RESET_ON_SUCCESS = True


# Spectacular (API Documentation) Configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'Email Marketing Automation API',
    'DESCRIPTION': 'API documentation for Email Marketing Automation Platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}


# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': env('LOG_LEVEL', default='INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': env('LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


# Stripe Configuration
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')
STRIPE_PUBLIC_KEY = env('STRIPE_PUBLIC_KEY', default='')
STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET', default='')

# Billing Configuration
FREE_TRIAL_DAYS = env.int('FREE_TRIAL_DAYS', default=14)


# Security Settings
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True


# Celery Configuration
from celery.schedules import crontab

CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/1')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    'resume-waiting-executions': {
        'task': 'apps.workflows.tasks.resume_waiting_executions',
        'schedule': 60.0,  # Every minute
    },
    'process-date-triggers': {
        'task': 'apps.workflows.tasks.process_date_triggers',
        'schedule': crontab(hour=0, minute=5),  # Daily at 00:05
    },
    'check-trial-expirations': {
        'task': 'apps.billing.tasks.check_trial_expirations',
        'schedule': crontab(hour=0, minute=15),  # Daily at 00:15
    },
    'reset-monthly-email-usage': {
        'task': 'apps.billing.tasks.reset_monthly_email_usage',
        'schedule': crontab(hour=0, minute=30, day_of_month=1),  # First of every month
    },
    'send-trial-ending-reminders': {
        'task': 'apps.billing.tasks.send_trial_ending_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9:00 AM
    },
    'lead-scoring-daily-recalculation': {
        'task': 'apps.lead_scoring.tasks.periodic_bulk_recalculate_all_orgs',
        'schedule': crontab(hour=3, minute=0),  # Daily at 03:00 UTC
    },
    'sync-social-integrations': {
        'task': 'apps.integrations.tasks.sync_all_auto_integrations',
        'schedule': 300.0,  # Every 5 minutes
    },
    'process-scheduled-campaigns': {
        'task': 'apps.campaigns.tasks.process_scheduled_campaigns',
        'schedule': 60.0,  # Every minute
    },
    'check-stuck-campaigns': {
        'task': 'apps.campaigns.tasks.check_stuck_campaigns',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    'flag-rotting-deals': {
        'task': 'apps.crm.tasks.flag_rotting_deals',
        'schedule': crontab(hour=1, minute=0),  # Daily at 01:00
    },
    'process-sequence-enrollments': {
        'task': 'apps.sequences.tasks.process_sequence_enrollments',
        'schedule': 60.0,  # Every minute
    },
    # Re-run DNS checks for domains waiting to be verified. DNS propagation
    # takes minutes to hours, so customers should not have to keep pressing
    # Verify; the task gives up after 72 hours.
    'recheck-pending-sending-domains': {
        'task': 'apps.email_config.tasks.recheck_pending_domains',
        'schedule': 600.0,  # Every 10 minutes
    },
    # Deliverability guardrails. Every tenant shares one sending IP, so a
    # breach has to be caught in minutes, not on a daily sweep.
    'evaluate-sending-guardrails': {
        'task': 'apps.email_config.tasks.evaluate_all_guardrails',
        'schedule': crontab(minute='*/15'),
    },
    'sync-postal-tenants': {
        'task': 'apps.email_config.tasks.sync_postal_tenants',
        'schedule': crontab(minute=5),  # Hourly, just after the hour
    },
    # Customers publish a DNS record and walk away; this is what notices when
    # it goes live without them coming back to press a button.
    'recheck-pending-landing-domains': {
        'task': 'apps.landing_pages.tasks.recheck_pending_domains',
        'schedule': crontab(minute='*/10'),
    },
}


# Base URL for tracking/unsubscribe links injected into campaign emails
BASE_URL = env('BASE_URL', default='http://127.0.0.1:8000')

# Anymail / Amazon SES configuration (optional)
ANYMAIL = {
    'AMAZON_SES_CLIENT_PARAMS': {
        'region_name': env('AWS_SES_REGION_NAME', default='us-east-1'),
    },
    'WEBHOOK_SECRET': env('ANYMAIL_WEBHOOK_SECRET', default=''),
}

# ── Postal (self-hosted mail server, see mailstack/) ─────────────────────────
# POSTAL_URL          : the Postal server that accepts sends and signs webhooks.
# PROVISIONER_*       : the management API that creates one Postal mail server
#                       ("tenant") per organization. See mailstack/MULTI-TENANT.md.
# POSTAL_ENABLED      : master switch. Off, every org keeps using the SMTP paths.
# POSTAL_WEBHOOK_VERIFY: only ever set False in tests — it disables the RSA
#                       signature check that stops anyone forging delivery events.
POSTAL_ENABLED = env.bool('POSTAL_ENABLED', default=False)
POSTAL_URL = env('POSTAL_URL', default='')
POSTAL_PROVISIONER_URL = env('POSTAL_PROVISIONER_URL', default='')
POSTAL_PROVISIONER_TOKEN = env('POSTAL_PROVISIONER_TOKEN', default='')
POSTAL_WEBHOOK_VERIFY = env.bool('POSTAL_WEBHOOK_VERIFY', default=True)
# Hard stop per tenant, in messages/hour. Postal *holds* mail over this limit and
# it must be released by hand, so it is a circuit breaker, not a throttle:
# set it well above the pace the sending queue actually allows.
POSTAL_SEND_LIMIT_MULTIPLIER = env.int('POSTAL_SEND_LIMIT_MULTIPLIER', default=2)
