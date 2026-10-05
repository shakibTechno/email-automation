# Technical Architecture Document
## Email Marketing Automation Platform (Django)

**Version:** 1.0
**Date:** January 19, 2026
**Framework:** Django 5.x
**Status:** Draft

---

## Table of Contents
1. [System Overview](#1-system-overview)
2. [Technology Stack](#2-technology-stack)
3. [Django Project Structure](#3-django-project-structure)
4. [Database Architecture](#4-database-architecture)
5. [API Architecture](#5-api-architecture)
6. [Email Sending Architecture](#6-email-sending-architecture)
7. [Automation Engine](#7-automation-engine)
8. [Analytics & Tracking](#8-analytics--tracking)
9. [Security Architecture](#9-security-architecture)
10. [Caching Strategy](#10-caching-strategy)
11. [Background Jobs & Queue System](#11-background-jobs--queue-system)
12. [Infrastructure & Deployment](#12-infrastructure--deployment)
13. [Scalability Considerations](#13-scalability-considerations)
14. [Development Workflow](#14-development-workflow)
15. [Monitoring & Logging](#15-monitoring--logging)

---

## 1. System Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Client Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Web App    │  │  Mobile App  │  │  API Clients │         │
│  │   (React)    │  │ (iOS/Android)│  │  (External)  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Load Balancer                            │
│                     (Nginx / AWS ALB)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Django Application Layer                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Django REST Framework                  │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  Authentication  │  Campaign  │  Contact  │  Automation  │  │
│  │     Service      │  Service   │  Service  │   Service    │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │   Email Editor   │  Analytics │  Forms    │  Landing     │  │
│  │     Service      │  Service   │  Service  │   Pages      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
┌──────────────────┐ ┌──────────────┐ ┌────────────────┐
│   PostgreSQL     │ │    Redis     │ │  Elasticsearch │
│   (Primary DB)   │ │ (Cache/Queue)│ │    (Search)    │
└──────────────────┘ └──────────────┘ └────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Background Workers (Celery)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Email Sender │  │   Automation │  │   Analytics  │         │
│  │    Worker    │  │    Worker    │  │    Worker    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   AWS SES    │  │    Twilio    │  │   Stripe     │         │
│  │ (Email SMTP) │  │    (SMS)     │  │  (Payments)  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Architecture Principles

1. **Separation of Concerns:** Each Django app handles a specific domain
2. **Scalability:** Horizontal scaling with stateless application servers
3. **Reliability:** Queue-based async processing for critical operations
4. **Performance:** Multi-layer caching strategy
5. **Security:** Defense in depth with multiple security layers
6. **Maintainability:** Clean code, comprehensive testing, documentation

---

## 2. Technology Stack

### 2.1 Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Backend Framework** | Django | 5.0+ | Core application framework |
| **API Framework** | Django REST Framework | 3.14+ | RESTful API development |
| **Async Tasks** | Celery | 5.3+ | Background job processing |
| **Task Queue** | Redis | 7.0+ | Message broker for Celery |
| **Primary Database** | PostgreSQL | 15+ | Relational data storage |
| **Cache** | Redis | 7.0+ | Application caching |
| **Search Engine** | Elasticsearch | 8.0+ | Full-text search, analytics |
| **Web Server** | Gunicorn | 21+ | WSGI HTTP server |
| **Reverse Proxy** | Nginx | 1.24+ | Load balancing, static files |
| **Task Monitoring** | Flower | 2.0+ | Celery monitoring UI |

### 2.2 Supporting Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Email Service** | AWS SES / SendGrid | Email delivery |
| **SMS Service** | Twilio | SMS delivery |
| **Payment Processing** | Stripe | Subscription billing |
| **File Storage** | AWS S3 | Media and static files |
| **CDN** | CloudFront | Content delivery |
| **Monitoring** | Sentry + Prometheus | Error tracking, metrics |
| **Logging** | ELK Stack | Centralized logging |
| **Container Runtime** | Docker | Application containerization |
| **Orchestration** | Kubernetes | Container orchestration |
| **CI/CD** | GitHub Actions | Automated deployment |

### 2.3 Django Packages

```python
# Core Django packages
django>=5.0
djangorestframework>=3.14
django-environ>=0.11  # Environment variable management
django-cors-headers>=4.3  # CORS handling
django-filter>=23.5  # API filtering
drf-spectacular>=0.27  # OpenAPI documentation

# Database & ORM
psycopg2-binary>=2.9  # PostgreSQL adapter
django-postgres-extra>=2.0  # PostgreSQL specific features

# Caching & Performance
django-redis>=5.4  # Redis cache backend
django-cachalot>=2.6  # ORM query caching

# Async Tasks
celery>=5.3
celery[redis]>=5.3
django-celery-beat>=2.5  # Periodic tasks
django-celery-results>=2.5  # Task result backend
flower>=2.0  # Task monitoring

# Authentication & Security
djangorestframework-simplejwt>=5.3  # JWT authentication
django-allauth>=0.58  # Social auth
django-otp>=1.3  # Two-factor authentication
django-axes>=6.1  # Brute force protection
django-permissions-policy>=4.18  # Security headers

# Email & Communication
django-anymail>=10.2  # Email backend abstraction
django-templated-mail>=1.1  # Email templates

# File & Media Management
django-storages>=1.14  # S3 integration
Pillow>=10.1  # Image processing

# Search & Analytics
elasticsearch-dsl>=8.11
django-elasticsearch-dsl>=8.0

# API & Documentation
drf-yasg>=1.21  # Swagger UI (alternative)
django-silk>=5.0  # API profiling

# Utilities
python-decouple>=3.8  # Settings management
python-dateutil>=2.8
pytz>=2023.3
requests>=2.31
celery-progress>=0.3  # Task progress tracking

# Development & Testing
pytest>=7.4
pytest-django>=4.7
pytest-cov>=4.1
factory-boy>=3.3  # Test fixtures
faker>=20.1  # Fake data generation
django-debug-toolbar>=4.2  # Development debugging
django-extensions>=3.2  # Management command extensions
ipython>=8.18  # Enhanced shell

# Code Quality
black>=23.12  # Code formatting
flake8>=6.1  # Linting
isort>=5.13  # Import sorting
mypy>=1.7  # Type checking
pre-commit>=3.6  # Git hooks
```

---

## 3. Django Project Structure

### 3.1 Project Organization

```
email_automation/
│
├── config/                          # Project configuration
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                 # Base settings
│   │   ├── development.py          # Dev settings
│   │   ├── production.py           # Prod settings
│   │   └── test.py                 # Test settings
│   ├── urls.py                     # Root URL configuration
│   ├── wsgi.py                     # WSGI configuration
│   ├── asgi.py                     # ASGI configuration
│   └── celery.py                   # Celery configuration
│
├── apps/                           # Django applications
│   │
│   ├── accounts/                   # User management & authentication
│   │   ├── __init__.py
│   │   ├── models.py              # User, Organization, Team models
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── permissions.py
│   │   ├── signals.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── managers.py
│   │   └── tests/
│   │
│   ├── contacts/                   # Contact management
│   │   ├── __init__.py
│   │   ├── models.py              # Contact, CustomField, Tag models
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── filters.py
│   │   ├── services.py            # Business logic
│   │   ├── importers.py           # CSV import logic
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── segments/                   # Segmentation engine
│   │   ├── __init__.py
│   │   ├── models.py              # Segment, SegmentRule models
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── evaluator.py           # Segment evaluation logic
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── campaigns/                  # Email campaign management
│   │   ├── __init__.py
│   │   ├── models.py              # Campaign, Email, Template models
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── services.py
│   │   ├── tasks.py               # Celery tasks
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── email_editor/               # Email builder
│   │   ├── __init__.py
│   │   ├── models.py              # EmailTemplate, TemplateBlock models
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── renderers.py           # HTML rendering logic
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── automations/                # Workflow automation
│   │   ├── __init__.py
│   │   ├── models.py              # Workflow, WorkflowNode, WorkflowExecution
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── engine.py              # Automation execution engine
│   │   ├── triggers.py            # Trigger handlers
│   │   ├── actions.py             # Action handlers
│   │   ├── conditions.py          # Condition evaluators
│   │   ├── tasks.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── forms/                      # Lead capture forms
│   │   ├── __init__.py
│   │   ├── models.py              # Form, FormField, FormSubmission
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── validators.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── landing_pages/              # Landing page builder
│   │   ├── __init__.py
│   │   ├── models.py              # LandingPage, PageBlock models
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── renderers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── analytics/                  # Analytics & reporting
│   │   ├── __init__.py
│   │   ├── models.py              # Event, CampaignStats, ContactActivity
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── aggregators.py         # Data aggregation logic
│   │   ├── tasks.py               # Analytics processing tasks
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── tracking/                   # Event tracking
│   │   ├── __init__.py
│   │   ├── models.py              # EmailEvent (opens, clicks)
│   │   ├── serializers.py
│   │   ├── views.py               # Tracking pixel, link redirect
│   │   ├── services.py
│   │   ├── urls.py
│   │   └── tests/
│   │
│   ├── lead_scoring/               # Lead scoring system
│   │   ├── __init__.py
│   │   ├── models.py              # ScoringRule, LeadScore
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── calculator.py          # Score calculation logic
│   │   ├── tasks.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── crm/                        # CRM & pipeline
│   │   ├── __init__.py
│   │   ├── models.py              # Deal, Pipeline, Stage, Activity
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── integrations/               # Third-party integrations
│   │   ├── __init__.py
│   │   ├── models.py              # Integration, IntegrationConfig
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── webhooks.py            # Webhook handlers
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── salesforce.py
│   │   │   ├── shopify.py
│   │   │   ├── stripe.py
│   │   │   └── zapier.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── sms/                        # SMS marketing
│   │   ├── __init__.py
│   │   ├── models.py              # SMSCampaign, SMSMessage
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── services.py            # Twilio integration
│   │   ├── tasks.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── notifications/              # In-app notifications
│   │   ├── __init__.py
│   │   ├── models.py              # Notification model
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   └── tests/
│   │
│   └── billing/                    # Subscription & billing
│       ├── __init__.py
│       ├── models.py              # Subscription, Plan, Invoice
│       ├── serializers.py
│       ├── views.py
│       ├── services.py            # Stripe integration
│       ├── webhooks.py            # Stripe webhooks
│       ├── urls.py
│       ├── admin.py
│       └── tests/
│
├── core/                           # Shared utilities
│   ├── __init__.py
│   ├── middleware.py              # Custom middleware
│   ├── permissions.py             # Custom permissions
│   ├── pagination.py              # Custom pagination
│   ├── exceptions.py              # Custom exceptions
│   ├── validators.py              # Custom validators
│   ├── utils.py                   # Helper functions
│   ├── mixins.py                  # Model/View mixins
│   ├── managers.py                # Custom model managers
│   └── decorators.py              # Custom decorators
│
├── templates/                      # Django templates
│   ├── base.html
│   ├── email/
│   │   ├── base.html
│   │   ├── campaign.html
│   │   └── transactional.html
│   └── admin/
│
├── static/                         # Static files
│   ├── css/
│   ├── js/
│   ├── images/
│   └── fonts/
│
├── media/                          # User uploaded files
│   ├── uploads/
│   ├── email_assets/
│   └── landing_pages/
│
├── docs/                           # Documentation
│   ├── api/
│   ├── deployment/
│   └── development/
│
├── scripts/                        # Utility scripts
│   ├── seed_data.py
│   ├── cleanup.py
│   └── migration_helpers.py
│
├── tests/                          # Integration tests
│   ├── integration/
│   └── e2e/
│
├── docker/                         # Docker configurations
│   ├── Dockerfile.django
│   ├── Dockerfile.celery
│   └── docker-compose.yml
│
├── kubernetes/                     # K8s manifests
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
│
├── .github/                        # GitHub Actions
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
│
├── requirements/                   # Python dependencies
│   ├── base.txt
│   ├── development.txt
│   ├── production.txt
│   └── test.txt
│
├── manage.py
├── pytest.ini
├── .env.example
├── .gitignore
├── .dockerignore
├── README.md
└── setup.py
```

### 3.2 App Responsibilities

| App | Responsibility |
|-----|---------------|
| **accounts** | User authentication, organization management, permissions |
| **contacts** | Contact CRUD, custom fields, tagging, import/export |
| **segments** | Dynamic segmentation, segment rules, evaluation |
| **campaigns** | Email campaign creation, scheduling, sending |
| **email_editor** | Email template builder, block management, rendering |
| **automations** | Workflow builder, automation engine, execution |
| **forms** | Form builder, submission handling, validation |
| **landing_pages** | Landing page builder, publishing, hosting |
| **analytics** | Event aggregation, reporting, dashboards |
| **tracking** | Email opens/clicks tracking, link management |
| **lead_scoring** | Scoring rules, score calculation, updates |
| **crm** | Deal management, pipeline, sales activities |
| **integrations** | Third-party integrations, webhooks, API connectors |
| **sms** | SMS campaigns, delivery, Twilio integration |
| **notifications** | In-app notifications, notification center |
| **billing** | Subscription management, Stripe integration, invoicing |

---

## 4. Database Architecture

### 4.1 Database Design Principles

1. **Multi-tenancy:** Organization-based data isolation
2. **Soft Deletes:** Use `deleted_at` for important records
3. **Audit Trail:** Track `created_at`, `updated_at`, `created_by`, `updated_by`
4. **Indexing:** Strategic indexes for performance
5. **Partitioning:** For high-volume tables (events, analytics)

### 4.2 Core Database Schema

#### 4.2.1 Accounts & Organizations

```python
# apps/accounts/models.py
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from core.models import TimeStampedModel

class Organization(TimeStampedModel):
    """Multi-tenant organization model"""
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    domain = models.CharField(max_length=255, blank=True)
    plan = models.ForeignKey('billing.Plan', on_delete=models.PROTECT)
    settings = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'organizations'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """Custom user model"""
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='users'
    )
    role = models.CharField(
        max_length=20,
        choices=[
            ('admin', 'Admin'),
            ('manager', 'Manager'),
            ('editor', 'Editor'),
            ('viewer', 'Viewer'),
        ]
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['organization', 'is_active']),
        ]
```

#### 4.2.2 Contacts

```python
# apps/contacts/models.py
from django.db import models
from core.models import TimeStampedModel

class Contact(TimeStampedModel):
    """Contact model with custom fields support"""
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='contacts'
    )
    email = models.EmailField()
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=255, blank=True)
    job_title = models.CharField(max_length=255, blank=True)

    # Engagement metrics
    lead_score = models.IntegerField(default=0)
    engagement_level = models.CharField(
        max_length=20,
        choices=[
            ('cold', 'Cold'),
            ('warm', 'Warm'),
            ('hot', 'Hot'),
            ('qualified', 'Qualified'),
        ],
        default='cold'
    )

    # Status fields
    is_subscribed = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    bounced_at = models.DateTimeField(null=True, blank=True)

    # Custom fields stored as JSON
    custom_fields = models.JSONField(default=dict)

    # Tracking
    source = models.CharField(max_length=100, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'contacts'
        unique_together = [['organization', 'email']]
        indexes = [
            models.Index(fields=['organization', 'email']),
            models.Index(fields=['organization', 'is_subscribed']),
            models.Index(fields=['organization', 'lead_score']),
            models.Index(fields=['last_activity_at']),
        ]

class Tag(TimeStampedModel):
    """Contact tags for organization"""
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#3B82F6')

    class Meta:
        db_table = 'tags'
        unique_together = [['organization', 'name']]

class ContactTag(models.Model):
    """Many-to-many relationship between contacts and tags"""
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contact_tags'
        unique_together = [['contact', 'tag']]
        indexes = [
            models.Index(fields=['contact']),
            models.Index(fields=['tag']),
        ]

class CustomField(TimeStampedModel):
    """Define custom fields for contacts"""
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)
    field_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text'),
            ('number', 'Number'),
            ('date', 'Date'),
            ('boolean', 'Boolean'),
            ('dropdown', 'Dropdown'),
        ]
    )
    options = models.JSONField(default=list)  # For dropdown
    is_required = models.BooleanField(default=False)

    class Meta:
        db_table = 'custom_fields'
        unique_together = [['organization', 'name']]
```

#### 4.2.3 Segments

```python
# apps/segments/models.py
from django.db import models
from core.models import TimeStampedModel

class Segment(TimeStampedModel):
    """Contact segment for targeting"""
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Segment type
    segment_type = models.CharField(
        max_length=20,
        choices=[
            ('static', 'Static'),
            ('dynamic', 'Dynamic'),
        ],
        default='dynamic'
    )

    # Rules for dynamic segments (stored as JSON)
    rules = models.JSONField(default=dict)

    # Cached count (updated periodically)
    contact_count = models.IntegerField(default=0)
    last_calculated_at = models.DateTimeField(null=True, blank=True)

    # For static segments (many-to-many)
    contacts = models.ManyToManyField(
        'contacts.Contact',
        through='SegmentMembership',
        related_name='segments'
    )

    class Meta:
        db_table = 'segments'
        indexes = [
            models.Index(fields=['organization', 'segment_type']),
        ]

class SegmentMembership(models.Model):
    """Membership in static segments"""
    segment = models.ForeignKey(Segment, on_delete=models.CASCADE)
    contact = models.ForeignKey('contacts.Contact', on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'segment_memberships'
        unique_together = [['segment', 'contact']]
```

#### 4.2.4 Campaigns

```python
# apps/campaigns/models.py
from django.db import models
from core.models import TimeStampedModel

class Campaign(TimeStampedModel):
    """Email campaign"""
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    preview_text = models.CharField(max_length=255, blank=True)

    # Email content
    email_template = models.ForeignKey(
        'email_editor.EmailTemplate',
        on_delete=models.SET_NULL,
        null=True
    )
    html_content = models.TextField()
    plain_content = models.TextField(blank=True)

    # Sender information
    from_name = models.CharField(max_length=255)
    from_email = models.EmailField()
    reply_to = models.EmailField(blank=True)

    # Campaign type
    campaign_type = models.CharField(
        max_length=20,
        choices=[
            ('regular', 'Regular'),
            ('ab_test', 'A/B Test'),
            ('automated', 'Automated'),
        ],
        default='regular'
    )

    # Targeting
    segment = models.ForeignKey(
        'segments.Segment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Scheduling
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('scheduled', 'Scheduled'),
            ('sending', 'Sending'),
            ('sent', 'Sent'),
            ('paused', 'Paused'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft'
    )
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    # Statistics (denormalized for performance)
    total_recipients = models.IntegerField(default=0)
    total_sent = models.IntegerField(default=0)
    total_delivered = models.IntegerField(default=0)
    total_opened = models.IntegerField(default=0)
    total_clicked = models.IntegerField(default=0)
    total_bounced = models.IntegerField(default=0)
    total_unsubscribed = models.IntegerField(default=0)

    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        db_table = 'campaigns'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['scheduled_at']),
            models.Index(fields=['sent_at']),
        ]

class CampaignRecipient(models.Model):
    """Individual recipient for campaign"""
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='recipients'
    )
    contact = models.ForeignKey('contacts.Contact', on_delete=models.CASCADE)

    # Sending status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('sent', 'Sent'),
            ('delivered', 'Delivered'),
            ('bounced', 'Bounced'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )

    # Tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    bounced_at = models.DateTimeField(null=True, blank=True)

    # Counts
    open_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)

    # Error handling
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'campaign_recipients'
        unique_together = [['campaign', 'contact']]
        indexes = [
            models.Index(fields=['campaign', 'status']),
            models.Index(fields=['contact']),
        ]
```

#### 4.2.5 Automations

```python
# apps/automations/models.py
from django.db import models
from core.models import TimeStampedModel

class Workflow(TimeStampedModel):
    """Automation workflow"""
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Workflow configuration (nodes and connections)
    config = models.JSONField(default=dict)

    # Trigger configuration
    trigger_type = models.CharField(
        max_length=50,
        choices=[
            ('form_submit', 'Form Submission'),
            ('tag_added', 'Tag Added'),
            ('list_subscribe', 'List Subscribe'),
            ('email_opened', 'Email Opened'),
            ('link_clicked', 'Link Clicked'),
            ('page_visited', 'Page Visited'),
            ('date_based', 'Date Based'),
            ('api_trigger', 'API Trigger'),
        ]
    )
    trigger_config = models.JSONField(default=dict)

    # Status
    is_active = models.BooleanField(default=False)

    # Statistics
    total_entered = models.IntegerField(default=0)
    total_completed = models.IntegerField(default=0)
    total_active = models.IntegerField(default=0)

    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        db_table = 'workflows'
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['trigger_type']),
        ]

class WorkflowExecution(TimeStampedModel):
    """Individual execution of workflow for a contact"""
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    contact = models.ForeignKey('contacts.Contact', on_delete=models.CASCADE)

    # Current state
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('paused', 'Paused'),
        ],
        default='active'
    )
    current_node_id = models.CharField(max_length=100, blank=True)

    # Execution context (variables, history)
    context = models.JSONField(default=dict)

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'workflow_executions'
        indexes = [
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['contact', 'status']),
            models.Index(fields=['started_at']),
        ]

class WorkflowNodeExecution(models.Model):
    """Execution of individual workflow node"""
    execution = models.ForeignKey(
        WorkflowExecution,
        on_delete=models.CASCADE,
        related_name='node_executions'
    )
    node_id = models.CharField(max_length=100)
    node_type = models.CharField(max_length=50)

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('running', 'Running'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('skipped', 'Skipped'),
        ],
        default='pending'
    )

    # Input/Output data
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)

    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'workflow_node_executions'
        indexes = [
            models.Index(fields=['execution', 'node_id']),
            models.Index(fields=['status']),
        ]
```

#### 4.2.6 Analytics & Tracking

```python
# apps/tracking/models.py
from django.db import models

class EmailEvent(models.Model):
    """Email tracking events (opens, clicks, etc.)"""
    # Using UUID as primary key for distributed writes
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    organization_id = models.IntegerField(db_index=True)
    campaign_id = models.IntegerField(null=True, db_index=True)
    contact_id = models.IntegerField(db_index=True)

    # Event details
    event_type = models.CharField(
        max_length=20,
        choices=[
            ('sent', 'Sent'),
            ('delivered', 'Delivered'),
            ('opened', 'Opened'),
            ('clicked', 'Clicked'),
            ('bounced', 'Bounced'),
            ('unsubscribed', 'Unsubscribed'),
            ('spam', 'Spam Complaint'),
        ],
        db_index=True
    )

    # Additional data
    link_url = models.TextField(blank=True)  # For click events
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    geo_location = models.JSONField(default=dict)

    # Device info
    device_type = models.CharField(max_length=20, blank=True)
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)

    # Timestamp (partition key for time-series data)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'email_events'
        # Partition by month for better performance
        indexes = [
            models.Index(fields=['organization_id', 'timestamp']),
            models.Index(fields=['campaign_id', 'event_type']),
            models.Index(fields=['contact_id', 'timestamp']),
        ]
        # PostgreSQL specific: Table partitioning by timestamp
        # This should be done via migration

class LinkClick(models.Model):
    """Separate table for link click tracking"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.CASCADE)
    contact = models.ForeignKey('contacts.Contact', on_delete=models.CASCADE)

    original_url = models.TextField()
    tracking_url = models.CharField(max_length=255, unique=True)

    clicked_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        db_table = 'link_clicks'
        indexes = [
            models.Index(fields=['campaign', 'clicked_at']),
            models.Index(fields=['tracking_url']),
        ]
```

### 4.3 Database Optimization Strategies

#### 4.3.1 Indexing Strategy

```python
# Strategic indexes for common queries
class Contact(models.Model):
    # ... fields ...

    class Meta:
        indexes = [
            # Composite index for filtered queries
            models.Index(
                fields=['organization', 'is_subscribed', 'lead_score'],
                name='contact_org_sub_score_idx'
            ),
            # Index for search queries
            models.Index(
                fields=['organization', 'email'],
                name='contact_org_email_idx'
            ),
            # GIN index for JSON fields (PostgreSQL specific)
            GinIndex(fields=['custom_fields'], name='contact_custom_fields_gin_idx'),
        ]
```

#### 4.3.2 Table Partitioning

```sql
-- PostgreSQL partitioning for email_events table
-- Run this in a migration

CREATE TABLE email_events_template (
    id UUID PRIMARY KEY,
    organization_id INTEGER NOT NULL,
    campaign_id INTEGER,
    contact_id INTEGER NOT NULL,
    event_type VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    -- other fields
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE email_events_2026_01 PARTITION OF email_events_template
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE email_events_2026_02 PARTITION OF email_events_template
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- Create indexes on partitions
CREATE INDEX ON email_events_2026_01 (organization_id, timestamp);
CREATE INDEX ON email_events_2026_01 (campaign_id, event_type);
```

#### 4.3.3 Query Optimization

```python
# Use select_related and prefetch_related
from django.db.models import Prefetch

# Bad - causes N+1 queries
campaigns = Campaign.objects.filter(organization=org)
for campaign in campaigns:
    print(campaign.created_by.name)  # N+1 query!

# Good - single query with join
campaigns = Campaign.objects.filter(
    organization=org
).select_related('created_by')

# Good - for many-to-many or reverse FK
contacts = Contact.objects.filter(
    organization=org
).prefetch_related(
    Prefetch('tags', queryset=Tag.objects.filter(is_active=True))
)

# Use only() and defer() to limit fields
contacts = Contact.objects.filter(
    organization=org
).only('id', 'email', 'first_name')  # Only fetch needed fields
```

---

## 5. API Architecture

### 5.1 API Design Principles

1. **RESTful conventions** with resource-based URLs
2. **Versioning** via URL path (`/api/v1/`)
3. **JWT authentication** for API access
4. **Pagination** for list endpoints
5. **Filtering, sorting, searching** support
6. **Rate limiting** per organization
7. **Comprehensive error responses**

### 5.2 API Structure

```python
# config/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

urlpatterns = [
    path('admin/', admin.site.urls),

    # API v1
    path('api/v1/', include([
        path('auth/', include('apps.accounts.urls')),
        path('contacts/', include('apps.contacts.urls')),
        path('segments/', include('apps.segments.urls')),
        path('campaigns/', include('apps.campaigns.urls')),
        path('automations/', include('apps.automations.urls')),
        path('forms/', include('apps.forms.urls')),
        path('landing-pages/', include('apps.landing_pages.urls')),
        path('analytics/', include('apps.analytics.urls')),
        path('integrations/', include('apps.integrations.urls')),
        path('billing/', include('apps.billing.urls')),
    ])),

    # Public endpoints (tracking, form submissions)
    path('track/', include('apps.tracking.urls')),
    path('forms/', include('apps.forms.public_urls')),

    # API documentation
    path('api/docs/', include('drf_spectacular.urls')),
]
```

### 5.3 ViewSet Examples

```python
# apps/contacts/views.py
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Contact
from .serializers import ContactSerializer, ContactListSerializer
from .filters import ContactFilter
from core.permissions import IsOrganizationMember

class ContactViewSet(viewsets.ModelViewSet):
    """
    Contact management endpoints

    list: Get all contacts for organization
    create: Create new contact
    retrieve: Get contact details
    update: Update contact
    partial_update: Partial update contact
    destroy: Delete contact
    """
    permission_classes = [IsOrganizationMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ContactFilter
    search_fields = ['email', 'first_name', 'last_name', 'company']
    ordering_fields = ['created_at', 'last_activity_at', 'lead_score']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter contacts by user's organization"""
        return Contact.objects.filter(
            organization=self.request.user.organization
        ).select_related('organization')

    def get_serializer_class(self):
        """Use different serializers for list vs detail"""
        if self.action == 'list':
            return ContactListSerializer
        return ContactSerializer

    def perform_create(self, serializer):
        """Automatically set organization on create"""
        serializer.save(organization=self.request.user.organization)

    @action(detail=False, methods=['post'])
    def bulk_import(self, request):
        """Bulk import contacts from CSV"""
        from .importers import CSVContactImporter

        file = request.FILES.get('file')
        if not file:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        importer = CSVContactImporter(request.user.organization)
        result = importer.import_file(file)

        return Response(result)

    @action(detail=False, methods=['post'])
    def bulk_tag(self, request):
        """Add tags to multiple contacts"""
        contact_ids = request.data.get('contact_ids', [])
        tag_ids = request.data.get('tag_ids', [])

        contacts = self.get_queryset().filter(id__in=contact_ids)
        tags = Tag.objects.filter(
            id__in=tag_ids,
            organization=request.user.organization
        )

        for contact in contacts:
            contact.tags.add(*tags)

        return Response({
            'message': f'Tagged {contacts.count()} contacts'
        })

    @action(detail=True, methods=['get'])
    def activity(self, request, pk=None):
        """Get contact activity timeline"""
        contact = self.get_object()

        # Fetch recent activities
        activities = EmailEvent.objects.filter(
            contact_id=contact.id
        ).order_by('-timestamp')[:50]

        # Serialize and return
        from apps.tracking.serializers import EmailEventSerializer
        serializer = EmailEventSerializer(activities, many=True)

        return Response(serializer.data)
```

### 5.4 Authentication

```python
# config/settings/base.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.CustomPageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
}

# JWT settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

```python
# apps/accounts/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, RegisterView, LogoutView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
```

### 5.5 API Documentation

```python
# config/settings/base.py
INSTALLED_APPS = [
    # ...
    'drf_spectacular',
]

REST_FRAMEWORK = {
    # ...
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Email Marketing Automation API',
    'DESCRIPTION': 'API documentation for Email Marketing platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}
```

```python
# config/urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # ...
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
]
```

---

## 6. Email Sending Architecture

### 6.1 Email Sending Flow

```
Campaign Created → Queue Recipients → Batch Processing → Send via ESP → Track Events
```

### 6.2 Email Sending Service

```python
# apps/campaigns/services.py
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from anymail.message import attach_alternative
import logging

logger = logging.getLogger(__name__)

class EmailSendingService:
    """Service for sending emails via ESP"""

    def __init__(self, campaign):
        self.campaign = campaign
        self.esp_backend = settings.EMAIL_BACKEND

    def send_to_recipient(self, recipient):
        """Send email to a single recipient"""
        try:
            # Personalize content
            html_content = self.personalize_content(
                self.campaign.html_content,
                recipient.contact
            )

            # Create tracking pixel
            html_content = self.add_tracking_pixel(html_content, recipient)

            # Replace links with tracking links
            html_content = self.replace_with_tracking_links(html_content, recipient)

            # Create email message
            message = EmailMultiAlternatives(
                subject=self.campaign.subject,
                body=self.campaign.plain_content,
                from_email=f"{self.campaign.from_name} <{self.campaign.from_email}>",
                to=[recipient.contact.email],
                reply_to=[self.campaign.reply_to] if self.campaign.reply_to else None,
            )

            # Attach HTML content
            message.attach_alternative(html_content, "text/html")

            # Add custom headers for tracking
            message.extra_headers = {
                'X-Campaign-ID': str(self.campaign.id),
                'X-Recipient-ID': str(recipient.id),
            }

            # Send email
            message.send()

            # Update recipient status
            recipient.status = 'sent'
            recipient.sent_at = timezone.now()
            recipient.save()

            logger.info(f"Email sent to {recipient.contact.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {recipient.contact.email}: {str(e)}")
            recipient.status = 'failed'
            recipient.error_message = str(e)
            recipient.save()
            return False

    def personalize_content(self, content, contact):
        """Replace personalization tokens with contact data"""
        replacements = {
            '{{first_name}}': contact.first_name or '',
            '{{last_name}}': contact.last_name or '',
            '{{email}}': contact.email,
            '{{company}}': contact.company or '',
        }

        # Add custom fields
        for key, value in contact.custom_fields.items():
            replacements[f'{{{{{key}}}}}'] = str(value)

        # Perform replacements
        for token, value in replacements.items():
            content = content.replace(token, value)

        return content

    def add_tracking_pixel(self, html_content, recipient):
        """Add tracking pixel for open tracking"""
        tracking_url = f"{settings.BASE_URL}/track/open/{recipient.id}/"
        pixel = f'<img src="{tracking_url}" width="1" height="1" alt="" />'

        # Insert before closing body tag
        return html_content.replace('</body>', f'{pixel}</body>')

    def replace_with_tracking_links(self, html_content, recipient):
        """Replace links with tracking links"""
        from apps.tracking.services import LinkTrackingService

        service = LinkTrackingService()
        return service.replace_links(html_content, self.campaign, recipient)
```

### 6.3 Email Sending Tasks (Celery)

```python
# apps/campaigns/tasks.py
from celery import shared_task, group
from django.utils import timezone
from .models import Campaign, CampaignRecipient
from .services import EmailSendingService

@shared_task(bind=True, max_retries=3)
def send_campaign(self, campaign_id):
    """
    Main task to send a campaign
    Queues individual send tasks for each recipient
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id)

        # Update status
        campaign.status = 'sending'
        campaign.save()

        # Get all pending recipients
        recipients = campaign.recipients.filter(status='pending')

        # Create batch tasks (1000 recipients per batch)
        batch_size = 1000
        recipient_ids = list(recipients.values_list('id', flat=True))

        # Create batches and queue them
        for i in range(0, len(recipient_ids), batch_size):
            batch = recipient_ids[i:i + batch_size]
            send_campaign_batch.delay(campaign_id, batch)

        return f"Queued {len(recipient_ids)} emails for sending"

    except Exception as e:
        # Retry on failure
        raise self.retry(exc=e, countdown=60)

@shared_task(bind=True, max_retries=3)
def send_campaign_batch(self, campaign_id, recipient_ids):
    """Send a batch of campaign emails"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        recipients = CampaignRecipient.objects.filter(id__in=recipient_ids)

        service = EmailSendingService(campaign)

        sent_count = 0
        failed_count = 0

        for recipient in recipients:
            if service.send_to_recipient(recipient):
                sent_count += 1
            else:
                failed_count += 1

            # Rate limiting (adjust based on ESP limits)
            time.sleep(0.1)  # 10 emails per second

        # Update campaign stats
        campaign.total_sent += sent_count
        campaign.save()

        return f"Batch complete: {sent_count} sent, {failed_count} failed"

    except Exception as e:
        raise self.retry(exc=e, countdown=60)

@shared_task
def schedule_campaigns():
    """
    Periodic task to check for scheduled campaigns and send them
    Run every minute via Celery Beat
    """
    now = timezone.now()

    # Get campaigns that should be sent now
    campaigns = Campaign.objects.filter(
        status='scheduled',
        scheduled_at__lte=now
    )

    for campaign in campaigns:
        send_campaign.delay(campaign.id)

    return f"Scheduled {campaigns.count()} campaigns"
```

### 6.4 ESP Configuration (Django Anymail)

```python
# config/settings/production.py
# AWS SES Configuration
EMAIL_BACKEND = 'anymail.backends.amazon_ses.EmailBackend'
ANYMAIL = {
    'AMAZON_SES_CLIENT_PARAMS': {
        'aws_access_key_id': env('AWS_ACCESS_KEY_ID'),
        'aws_secret_access_key': env('AWS_SECRET_ACCESS_KEY'),
        'region_name': 'us-east-1',
    },
    'AMAZON_SES_CONFIGURATION_SET_NAME': 'EmailMarketingPlatform',
}

# Webhook handling for delivery events
ANYMAIL_WEBHOOK_SECRET = env('ANYMAIL_WEBHOOK_SECRET')

# Alternative: SendGrid
# EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
# ANYMAIL = {
#     'SENDGRID_API_KEY': env('SENDGRID_API_KEY'),
# }
```

```python
# apps/integrations/webhooks.py
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from anymail.signals import tracking
from django.dispatch import receiver
from apps.tracking.services import EventTrackingService

@receiver(tracking)
def handle_email_event(sender, event, esp_name, **kwargs):
    """Handle email events from ESP (delivered, bounced, etc.)"""

    service = EventTrackingService()

    # Extract data from event
    event_type = event.event_type  # 'delivered', 'bounced', etc.
    recipient_id = event.metadata.get('recipient_id')

    # Process event
    service.process_event(event_type, recipient_id, event)

    return HttpResponse(status=200)
```

---

## 7. Automation Engine

### 7.1 Automation Architecture

```
Trigger Event → Evaluate Conditions → Execute Actions → Update State → Next Node
```

### 7.2 Automation Engine Implementation

```python
# apps/automations/engine.py
from django.utils import timezone
from .models import Workflow, WorkflowExecution, WorkflowNodeExecution
from .actions import ActionRegistry
from .conditions import ConditionEvaluator
import logging

logger = logging.getLogger(__name__)

class AutomationEngine:
    """Core automation execution engine"""

    def __init__(self, workflow):
        self.workflow = workflow
        self.action_registry = ActionRegistry()
        self.condition_evaluator = ConditionEvaluator()

    def trigger(self, contact, trigger_data=None):
        """
        Trigger workflow for a contact
        Creates new execution and starts processing
        """
        # Check if contact is already in this workflow
        existing = WorkflowExecution.objects.filter(
            workflow=self.workflow,
            contact=contact,
            status='active'
        ).first()

        if existing:
            logger.info(f"Contact {contact.id} already in workflow {self.workflow.id}")
            return existing

        # Create new execution
        execution = WorkflowExecution.objects.create(
            workflow=self.workflow,
            contact=contact,
            status='active',
            context={'trigger_data': trigger_data or {}}
        )

        # Start from first node
        first_node = self.get_first_node()
        if first_node:
            execution.current_node_id = first_node['id']
            execution.save()

            # Process first node asynchronously
            from .tasks import process_workflow_node
            process_workflow_node.delay(execution.id, first_node['id'])

        # Update workflow stats
        self.workflow.total_entered += 1
        self.workflow.total_active += 1
        self.workflow.save()

        return execution

    def process_node(self, execution, node_id):
        """Process a single workflow node"""
        node = self.get_node_by_id(node_id)
        if not node:
            logger.error(f"Node {node_id} not found in workflow {self.workflow.id}")
            return

        # Create node execution record
        node_execution = WorkflowNodeExecution.objects.create(
            execution=execution,
            node_id=node_id,
            node_type=node['type'],
            status='running',
            started_at=timezone.now()
        )

        try:
            # Execute node based on type
            if node['type'] == 'action':
                self.execute_action(execution, node, node_execution)

            elif node['type'] == 'condition':
                self.evaluate_condition(execution, node, node_execution)

            elif node['type'] == 'delay':
                self.schedule_delay(execution, node, node_execution)

            elif node['type'] == 'goal':
                self.check_goal(execution, node, node_execution)

            # Mark node as completed
            node_execution.status = 'completed'
            node_execution.completed_at = timezone.now()
            node_execution.save()

            # Move to next node(s)
            self.proceed_to_next(execution, node, node_execution)

        except Exception as e:
            logger.error(f"Error executing node {node_id}: {str(e)}")
            node_execution.status = 'failed'
            node_execution.error_message = str(e)
            node_execution.completed_at = timezone.now()
            node_execution.save()

            # Mark execution as failed
            execution.status = 'failed'
            execution.save()

    def execute_action(self, execution, node, node_execution):
        """Execute an action node"""
        action_type = node['data']['action_type']
        action_config = node['data']['config']

        # Get action handler from registry
        action_handler = self.action_registry.get(action_type)
        if not action_handler:
            raise ValueError(f"Unknown action type: {action_type}")

        # Execute action
        result = action_handler.execute(
            contact=execution.contact,
            config=action_config,
            context=execution.context
        )

        # Store result in node execution
        node_execution.output_data = result
        node_execution.save()

    def evaluate_condition(self, execution, node, node_execution):
        """Evaluate a condition node"""
        condition_config = node['data']['condition']

        # Evaluate condition
        result = self.condition_evaluator.evaluate(
            contact=execution.contact,
            condition=condition_config,
            context=execution.context
        )

        # Store result
        node_execution.output_data = {'result': result, 'branch': 'true' if result else 'false'}
        node_execution.save()

    def schedule_delay(self, execution, node, node_execution):
        """Schedule a delay before next action"""
        delay_config = node['data']
        delay_type = delay_config['delay_type']  # 'duration' or 'until_date'

        if delay_type == 'duration':
            # Delay for specific duration
            from datetime import timedelta
            duration = timedelta(
                days=delay_config.get('days', 0),
                hours=delay_config.get('hours', 0),
                minutes=delay_config.get('minutes', 0)
            )
            resume_at = timezone.now() + duration

        elif delay_type == 'until_date':
            # Delay until specific date field
            field_name = delay_config['field_name']
            resume_at = getattr(execution.contact, field_name, None)
            if not resume_at:
                raise ValueError(f"Invalid date field: {field_name}")

        # Schedule task to resume after delay
        from .tasks import resume_workflow_execution
        resume_workflow_execution.apply_async(
            args=[execution.id, node['id']],
            eta=resume_at
        )

        node_execution.output_data = {'resume_at': resume_at.isoformat()}
        node_execution.save()

    def proceed_to_next(self, execution, current_node, node_execution):
        """Move to next node in workflow"""
        # Get connections from current node
        connections = [
            conn for conn in self.workflow.config.get('connections', [])
            if conn['source'] == current_node['id']
        ]

        if not connections:
            # No more nodes - workflow complete
            self.complete_execution(execution)
            return

        # For condition nodes, choose branch based on result
        if current_node['type'] == 'condition':
            branch = node_execution.output_data.get('branch', 'false')
            connections = [
                conn for conn in connections
                if conn.get('label') == branch
            ]

        # Process next node(s)
        for conn in connections:
            next_node_id = conn['target']

            # Update execution state
            execution.current_node_id = next_node_id
            execution.save()

            # Queue next node for processing
            from .tasks import process_workflow_node
            process_workflow_node.delay(execution.id, next_node_id)

    def complete_execution(self, execution):
        """Mark execution as completed"""
        execution.status = 'completed'
        execution.completed_at = timezone.now()
        execution.save()

        # Update workflow stats
        self.workflow.total_active -= 1
        self.workflow.total_completed += 1
        self.workflow.save()

    def get_first_node(self):
        """Get the first node in workflow (after trigger)"""
        nodes = self.workflow.config.get('nodes', [])
        for node in nodes:
            if node.get('type') == 'trigger':
                # Find node connected to trigger
                connections = self.workflow.config.get('connections', [])
                for conn in connections:
                    if conn['source'] == node['id']:
                        return self.get_node_by_id(conn['target'])
        return None

    def get_node_by_id(self, node_id):
        """Get node configuration by ID"""
        nodes = self.workflow.config.get('nodes', [])
        for node in nodes:
            if node['id'] == node_id:
                return node
        return None
```

### 7.3 Action Handlers

```python
# apps/automations/actions.py
from abc import ABC, abstractmethod
from django.core.mail import send_mail

class BaseAction(ABC):
    """Base class for all actions"""

    @abstractmethod
    def execute(self, contact, config, context):
        """Execute the action"""
        pass

class SendEmailAction(BaseAction):
    """Send email action"""

    def execute(self, contact, config, context):
        from apps.campaigns.services import EmailSendingService

        email_template_id = config['email_template_id']
        # ... send email logic

        return {'status': 'sent', 'email_id': email_id}

class AddTagAction(BaseAction):
    """Add tag to contact"""

    def execute(self, contact, config, context):
        from apps.contacts.models import Tag

        tag_id = config['tag_id']
        tag = Tag.objects.get(id=tag_id)

        contact.tags.add(tag)

        return {'status': 'success', 'tag': tag.name}

class UpdateFieldAction(BaseAction):
    """Update contact field"""

    def execute(self, contact, config, context):
        field_name = config['field_name']
        field_value = config['field_value']

        setattr(contact, field_name, field_value)
        contact.save()

        return {'status': 'success', 'field': field_name, 'value': field_value}

class WebhookAction(BaseAction):
    """Send webhook to external URL"""

    def execute(self, contact, config, context):
        import requests

        url = config['url']
        method = config.get('method', 'POST')
        payload = config.get('payload', {})

        # Personalize payload
        # ...

        response = requests.request(method, url, json=payload)

        return {
            'status': 'success',
            'status_code': response.status_code,
            'response': response.text[:1000]
        }

class ActionRegistry:
    """Registry of all available actions"""

    def __init__(self):
        self.actions = {
            'send_email': SendEmailAction(),
            'add_tag': AddTagAction(),
            'remove_tag': RemoveTagAction(),
            'update_field': UpdateFieldAction(),
            'send_webhook': WebhookAction(),
            'send_sms': SendSMSAction(),
            'create_deal': CreateDealAction(),
        }

    def get(self, action_type):
        return self.actions.get(action_type)
```

### 7.4 Automation Tasks

```python
# apps/automations/tasks.py
from celery import shared_task
from .models import WorkflowExecution
from .engine import AutomationEngine

@shared_task
def process_workflow_node(execution_id, node_id):
    """Process a workflow node"""
    try:
        execution = WorkflowExecution.objects.select_related('workflow').get(id=execution_id)
        engine = AutomationEngine(execution.workflow)
        engine.process_node(execution, node_id)
    except Exception as e:
        logger.error(f"Error processing workflow node: {str(e)}")

@shared_task
def resume_workflow_execution(execution_id, current_node_id):
    """Resume workflow after a delay"""
    try:
        execution = WorkflowExecution.objects.get(id=execution_id)
        engine = AutomationEngine(execution.workflow)

        # Get next node after delay
        current_node = engine.get_node_by_id(current_node_id)
        engine.proceed_to_next(execution, current_node, None)
    except Exception as e:
        logger.error(f"Error resuming workflow: {str(e)}")

@shared_task
def trigger_workflow_for_event(workflow_id, contact_id, event_data):
    """Trigger workflow when an event occurs"""
    from apps.automations.models import Workflow
    from apps.contacts.models import Contact

    try:
        workflow = Workflow.objects.get(id=workflow_id, is_active=True)
        contact = Contact.objects.get(id=contact_id)

        engine = AutomationEngine(workflow)
        engine.trigger(contact, trigger_data=event_data)
    except Exception as e:
        logger.error(f"Error triggering workflow: {str(e)}")
```

---

## 8. Analytics & Tracking

### 8.1 Event Tracking Service

```python
# apps/tracking/services.py
from django.utils import timezone
from .models import EmailEvent, LinkClick
from apps.campaigns.models import CampaignRecipient
from user_agents import parse
import logging

logger = logging.getLogger(__name__)

class EventTrackingService:
    """Service for tracking email events"""

    def track_open(self, recipient_id, request):
        """Track email open event"""
        try:
            recipient = CampaignRecipient.objects.select_related(
                'campaign', 'contact'
            ).get(id=recipient_id)

            # Extract user agent and IP
            user_agent_string = request.META.get('HTTP_USER_AGENT', '')
            ip_address = self.get_client_ip(request)

            # Parse user agent
            user_agent = parse(user_agent_string)

            # Create event
            event = EmailEvent.objects.create(
                organization_id=recipient.campaign.organization_id,
                campaign_id=recipient.campaign_id,
                contact_id=recipient.contact_id,
                event_type='opened',
                user_agent=user_agent_string,
                ip_address=ip_address,
                device_type=self.get_device_type(user_agent),
                browser=user_agent.browser.family,
                os=user_agent.os.family,
                timestamp=timezone.now()
            )

            # Update recipient if first open
            if not recipient.opened_at:
                recipient.opened_at = timezone.now()
                recipient.status = 'delivered'

            recipient.open_count += 1
            recipient.save()

            # Update campaign stats
            if recipient.open_count == 1:  # Only count unique opens
                recipient.campaign.total_opened += 1
                recipient.campaign.save()

            logger.info(f"Tracked open for recipient {recipient_id}")

        except CampaignRecipient.DoesNotExist:
            logger.error(f"Recipient {recipient_id} not found")
        except Exception as e:
            logger.error(f"Error tracking open: {str(e)}")

    def track_click(self, tracking_id, request):
        """Track link click event"""
        try:
            # Find link click record
            link = LinkClick.objects.select_related(
                'campaign', 'contact'
            ).filter(tracking_url__contains=tracking_id).first()

            if not link:
                logger.error(f"Link {tracking_id} not found")
                return None

            # Extract user agent and IP
            user_agent_string = request.META.get('HTTP_USER_AGENT', '')
            ip_address = self.get_client_ip(request)
            user_agent = parse(user_agent_string)

            # Create event
            event = EmailEvent.objects.create(
                organization_id=link.campaign.organization_id,
                campaign_id=link.campaign_id,
                contact_id=link.contact_id,
                event_type='clicked',
                link_url=link.original_url,
                user_agent=user_agent_string,
                ip_address=ip_address,
                device_type=self.get_device_type(user_agent),
                browser=user_agent.browser.family,
                os=user_agent.os.family,
                timestamp=timezone.now()
            )

            # Update recipient
            recipient = CampaignRecipient.objects.filter(
                campaign=link.campaign,
                contact=link.contact
            ).first()

            if recipient:
                if not recipient.clicked_at:
                    recipient.clicked_at = timezone.now()
                    # Update campaign stats for unique clicks
                    link.campaign.total_clicked += 1
                    link.campaign.save()

                recipient.click_count += 1
                recipient.save()

            # Update contact activity
            link.contact.last_activity_at = timezone.now()
            link.contact.save()

            logger.info(f"Tracked click for link {tracking_id}")

            return link.original_url

        except Exception as e:
            logger.error(f"Error tracking click: {str(e)}")
            return None

    def get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def get_device_type(self, user_agent):
        """Determine device type from user agent"""
        if user_agent.is_mobile:
            return 'mobile'
        elif user_agent.is_tablet:
            return 'tablet'
        else:
            return 'desktop'

class LinkTrackingService:
    """Service for creating tracking links"""

    def create_tracking_link(self, original_url, campaign, contact):
        """Create a tracking link for URL"""
        import hashlib
        import uuid

        # Generate unique tracking ID
        tracking_id = str(uuid.uuid4())[:12]
        tracking_url = f"{settings.BASE_URL}/t/{tracking_id}"

        # Create link click record
        link = LinkClick.objects.create(
            campaign=campaign,
            contact=contact,
            original_url=original_url,
            tracking_url=tracking_url
        )

        return tracking_url

    def replace_links(self, html_content, campaign, recipient):
        """Replace all links in HTML with tracking links"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, 'html.parser')

        # Find all links
        for link in soup.find_all('a', href=True):
            original_url = link['href']

            # Skip mailto, tel, and anchor links
            if original_url.startswith(('mailto:', 'tel:', '#')):
                continue

            # Create tracking link
            tracking_url = self.create_tracking_link(
                original_url,
                campaign,
                recipient.contact
            )

            # Replace href
            link['href'] = tracking_url

        return str(soup)
```

### 8.2 Tracking Views

```python
# apps/tracking/views.py
from django.shortcuts import redirect
from django.http import HttpResponse
from django.views import View
from .services import EventTrackingService
import base64

class EmailOpenTrackingView(View):
    """Endpoint for tracking email opens (tracking pixel)"""

    def get(self, request, recipient_id):
        """Return 1x1 transparent pixel and track open"""
        service = EventTrackingService()
        service.track_open(recipient_id, request)

        # Return 1x1 transparent GIF
        pixel = base64.b64decode(
            b'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
        )
        return HttpResponse(pixel, content_type='image/gif')

class LinkClickTrackingView(View):
    """Endpoint for tracking link clicks"""

    def get(self, request, tracking_id):
        """Track click and redirect to original URL"""
        service = EventTrackingService()
        original_url = service.track_click(tracking_id, request)

        if original_url:
            return redirect(original_url)
        else:
            return HttpResponse('Link not found', status=404)
```

### 8.3 Analytics Aggregation

```python
# apps/analytics/aggregators.py
from django.db.models import Count, Q, F
from django.utils import timezone
from datetime import timedelta
from apps.tracking.models import EmailEvent

class CampaignAnalytics:
    """Aggregate campaign analytics"""

    def __init__(self, campaign):
        self.campaign = campaign

    def get_overview_stats(self):
        """Get overview statistics"""
        return {
            'total_sent': self.campaign.total_sent,
            'total_delivered': self.campaign.total_delivered,
            'total_opened': self.campaign.total_opened,
            'total_clicked': self.campaign.total_clicked,
            'total_bounced': self.campaign.total_bounced,
            'total_unsubscribed': self.campaign.total_unsubscribed,
            'open_rate': self.calculate_open_rate(),
            'click_rate': self.calculate_click_rate(),
            'click_to_open_rate': self.calculate_click_to_open_rate(),
            'bounce_rate': self.calculate_bounce_rate(),
        }

    def calculate_open_rate(self):
        """Calculate open rate percentage"""
        if self.campaign.total_delivered == 0:
            return 0
        return round((self.campaign.total_opened / self.campaign.total_delivered) * 100, 2)

    def calculate_click_rate(self):
        """Calculate click rate percentage"""
        if self.campaign.total_delivered == 0:
            return 0
        return round((self.campaign.total_clicked / self.campaign.total_delivered) * 100, 2)

    def calculate_click_to_open_rate(self):
        """Calculate click-to-open rate"""
        if self.campaign.total_opened == 0:
            return 0
        return round((self.campaign.total_clicked / self.campaign.total_opened) * 100, 2)

    def calculate_bounce_rate(self):
        """Calculate bounce rate"""
        if self.campaign.total_sent == 0:
            return 0
        return round((self.campaign.total_bounced / self.campaign.total_sent) * 100, 2)

    def get_engagement_over_time(self, days=7):
        """Get engagement metrics over time"""
        start_date = timezone.now() - timedelta(days=days)

        events = EmailEvent.objects.filter(
            campaign_id=self.campaign.id,
            timestamp__gte=start_date
        ).values('event_type').annotate(
            count=Count('id'),
            date=F('timestamp__date')
        ).order_by('date')

        # Group by date and event type
        result = {}
        for event in events:
            date_str = event['date'].isoformat()
            if date_str not in result:
                result[date_str] = {}
            result[date_str][event['event_type']] = event['count']

        return result

    def get_device_stats(self):
        """Get statistics by device type"""
        return EmailEvent.objects.filter(
            campaign_id=self.campaign.id
        ).values('device_type').annotate(
            count=Count('id')
        )

    def get_geographic_stats(self):
        """Get statistics by location"""
        # This requires IP geolocation service
        pass

    def get_link_performance(self):
        """Get click statistics for each link"""
        from apps.tracking.models import LinkClick

        links = LinkClick.objects.filter(
            campaign=self.campaign
        ).values('original_url').annotate(
            click_count=Count('id')
        ).order_by('-click_count')

        return list(links)
```

---

## 9. Security Architecture

### 9.1 Authentication & Authorization

```python
# core/permissions.py
from rest_framework import permissions

class IsOrganizationMember(permissions.BasePermission):
    """Permission check for organization membership"""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Check if object belongs to user's organization
        if hasattr(obj, 'organization'):
            return obj.organization == request.user.organization
        return True

class CanManageCampaigns(permissions.BasePermission):
    """Permission for campaign management"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Check user role
        allowed_roles = ['admin', 'manager', 'editor']
        return request.user.role in allowed_roles

class IsOrganizationAdmin(permissions.BasePermission):
    """Permission for admin-only operations"""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )
```

### 9.2 Data Isolation

```python
# core/middleware.py
from django.utils.deprecation import MiddlewareMixin

class OrganizationIsolationMiddleware(MiddlewareMixin):
    """Ensure all queries are scoped to user's organization"""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.user.is_authenticated:
            # Store organization in request for easy access
            request.organization = request.user.organization
        return None
```

### 9.3 Security Headers

```python
# config/settings/production.py

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# CORS settings
CORS_ALLOWED_ORIGINS = [
    'https://app.yourdomain.com',
]

# Rate limiting
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login': '5/minute',
        'register': '3/hour',
    }
}
```

### 9.4 Input Validation

```python
# core/validators.py
from django.core.exceptions import ValidationError
import re

def validate_email_content(value):
    """Validate email content for security issues"""
    # Check for malicious scripts
    if re.search(r'<script[^>]*>.*?</script>', value, re.IGNORECASE | re.DOTALL):
        raise ValidationError('Script tags are not allowed')

    # Check for suspicious patterns
    suspicious_patterns = [
        r'javascript:',
        r'data:text/html',
        r'vbscript:',
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            raise ValidationError('Suspicious content detected')

    return value

def validate_webhook_url(value):
    """Validate webhook URL"""
    if not value.startswith(('http://', 'https://')):
        raise ValidationError('Invalid URL scheme')

    # Block private IP ranges
    import ipaddress
    from urllib.parse import urlparse

    parsed = urlparse(value)
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private:
            raise ValidationError('Private IP addresses are not allowed')
    except ValueError:
        # Not an IP address, that's fine
        pass

    return value
```

---

## 10. Caching Strategy

### 10.1 Redis Configuration

```python
# config/settings/base.py

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
        },
        'KEY_PREFIX': 'email_automation',
        'TIMEOUT': 300,  # 5 minutes default
    },
    'session': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/2'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 86400,  # 24 hours
    },
}

# Use Redis for sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'session'
```

### 10.2 Cache Usage Examples

```python
# apps/contacts/views.py
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from rest_framework.decorators import action

class ContactViewSet(viewsets.ModelViewSet):
    # ...

    @action(detail=False, methods=['get'])
    @cache_page(60 * 5)  # Cache for 5 minutes
    def stats(self, request):
        """Get contact statistics (cached)"""
        cache_key = f'contact_stats_{request.user.organization_id}'

        stats = cache.get(cache_key)
        if stats is None:
            # Calculate stats
            stats = {
                'total': Contact.objects.filter(
                    organization=request.user.organization
                ).count(),
                'subscribed': Contact.objects.filter(
                    organization=request.user.organization,
                    is_subscribed=True
                ).count(),
                # ... more stats
            }

            # Cache for 5 minutes
            cache.set(cache_key, stats, 60 * 5)

        return Response(stats)

# Invalidate cache on updates
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Contact)
def invalidate_contact_stats_cache(sender, instance, **kwargs):
    """Invalidate stats cache when contact is updated"""
    cache_key = f'contact_stats_{instance.organization_id}'
    cache.delete(cache_key)
```

### 10.3 Query Caching with Django-Cachalot

```python
# config/settings/base.py
INSTALLED_APPS = [
    # ...
    'cachalot',
]

CACHALOT_ENABLED = True
CACHALOT_CACHE = 'default'

# In views - automatic query caching
# No code changes needed, Cachalot caches ORM queries automatically
```

---

## 11. Background Jobs & Queue System

### 11.1 Celery Configuration

```python
# config/celery.py
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

app = Celery('email_automation')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'schedule-campaigns': {
        'task': 'apps.campaigns.tasks.schedule_campaigns',
        'schedule': crontab(minute='*/1'),  # Every minute
    },
    'calculate-segment-sizes': {
        'task': 'apps.segments.tasks.calculate_all_segment_sizes',
        'schedule': crontab(hour='*/4'),  # Every 4 hours
    },
    'update-lead-scores': {
        'task': 'apps.lead_scoring.tasks.update_all_lead_scores',
        'schedule': crontab(hour='2'),  # Daily at 2 AM
    },
    'cleanup-old-events': {
        'task': 'apps.analytics.tasks.cleanup_old_events',
        'schedule': crontab(hour='3', day_of_week='sunday'),  # Weekly
    },
}
```

```python
# config/settings/base.py

# Celery Configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Task routing
CELERY_TASK_ROUTES = {
    'apps.campaigns.tasks.send_campaign': {'queue': 'email_sending'},
    'apps.campaigns.tasks.send_campaign_batch': {'queue': 'email_sending'},
    'apps.automations.tasks.*': {'queue': 'automations'},
    'apps.analytics.tasks.*': {'queue': 'analytics'},
}

# Task execution limits
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes

# Worker configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Task result expiration
CELERY_RESULT_EXPIRES = 3600  # 1 hour
```

### 11.2 Running Workers

```bash
# Start Celery worker for email sending
celery -A config worker -Q email_sending --concurrency=10 --loglevel=info

# Start Celery worker for automations
celery -A config worker -Q automations --concurrency=5 --loglevel=info

# Start Celery worker for analytics
celery -A config worker -Q analytics --concurrency=2 --loglevel=info

# Start Celery Beat (scheduler)
celery -A config beat --loglevel=info

# Start Flower (monitoring)
celery -A config flower --port=5555
```

---

## 12. Infrastructure & Deployment

### 12.1 Docker Configuration

```dockerfile
# docker/Dockerfile.django
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/production.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "config.wsgi:application"]
```

```dockerfile
# docker/Dockerfile.celery
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/production.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . /app/

RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Default command (can be overridden)
CMD ["celery", "-A", "config", "worker", "--loglevel=info"]
```

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: email_automation
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  web:
    build:
      context: ..
      dockerfile: docker/Dockerfile.django
    command: gunicorn --bind 0.0.0.0:8000 config.wsgi:application
    volumes:
      - ../:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    ports:
      - "8000:8000"
    env_file:
      - ../.env
    depends_on:
      - db
      - redis

  celery_worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile.celery
    command: celery -A config worker --loglevel=info
    volumes:
      - ../:/app
    env_file:
      - ../.env
    depends_on:
      - db
      - redis

  celery_beat:
    build:
      context: ..
      dockerfile: docker/Dockerfile.celery
    command: celery -A config beat --loglevel=info
    volumes:
      - ../:/app
    env_file:
      - ../.env
    depends_on:
      - db
      - redis

  flower:
    build:
      context: ..
      dockerfile: docker/Dockerfile.celery
    command: celery -A config flower --port=5555
    ports:
      - "5555:5555"
    env_file:
      - ../.env
    depends_on:
      - redis

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    ports:
      - "80:80"
    depends_on:
      - web

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

### 12.2 Kubernetes Deployment

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: django-app
  labels:
    app: django
spec:
  replicas: 3
  selector:
    matchLabels:
      app: django
  template:
    metadata:
      labels:
        app: django
    spec:
      containers:
      - name: django
        image: your-registry/email-automation:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: django-service
spec:
  selector:
    app: django
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

```yaml
# kubernetes/celery-worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
spec:
  replicas: 5
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
      - name: worker
        image: your-registry/email-automation:latest
        command: ["celery", "-A", "config", "worker", "--loglevel=info"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: CELERY_BROKER_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: celery-broker-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### 12.3 CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [ main, staging ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements/test.txt

    - name: Run tests
      run: |
        pytest --cov=apps --cov-report=xml

    - name: Run linting
      run: |
        flake8 apps/
        black --check apps/
        isort --check apps/

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Build Docker image
      run: |
        docker build -f docker/Dockerfile.django -t email-automation:${{ github.sha }} .

    - name: Push to registry
      run: |
        docker push your-registry/email-automation:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/django-app django=your-registry/email-automation:${{ github.sha }}
        kubectl rollout status deployment/django-app
```

---

## 13. Scalability Considerations

### 13.1 Database Scaling

1. **Read Replicas:** Route read queries to replicas
2. **Connection Pooling:** Use PgBouncer for connection management
3. **Partitioning:** Partition large tables by organization or date
4. **Sharding:** Shard contacts table by organization_id

```python
# Database routing for read replicas
class ReplicaRouter:
    def db_for_read(self, model, **hints):
        return 'replica'

    def db_for_write(self, model, **hints):
        return 'default'
```

### 13.2 Application Scaling

1. **Horizontal Scaling:** Add more web servers
2. **Celery Workers:** Scale workers based on queue depth
3. **Auto-scaling:** Use Kubernetes HPA
4. **CDN:** Serve static/media files via CDN

### 13.3 Performance Optimization

1. **Database Indexes:** Add strategic indexes
2. **Query Optimization:** Use select_related, prefetch_related
3. **Caching:** Multi-layer caching (Redis, CDN)
4. **Async Processing:** Move heavy tasks to Celery
5. **Database Connection Pooling**
6. **Load Balancing:** Distribute traffic across servers

---

## 14. Development Workflow

### 14.1 Local Development Setup

```bash
# Clone repository
git clone https://github.com/yourorg/email-automation.git
cd email-automation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/development.txt

# Copy environment file
cp .env.example .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load seed data
python manage.py loaddata scripts/seed_data.json

# Run development server
python manage.py runserver

# In separate terminals:
# Run Celery worker
celery -A config worker --loglevel=info

# Run Celery beat
celery -A config beat --loglevel=info
```

### 14.2 Testing

```python
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
python_files = tests.py test_*.py *_tests.py
addopts = --cov=apps --cov-report=html --cov-report=term-missing

# Run tests
pytest

# Run specific test
pytest apps/contacts/tests/test_models.py

# Run with coverage
pytest --cov=apps --cov-report=html
```

### 14.3 Code Quality

```bash
# Format code
black apps/

# Sort imports
isort apps/

# Lint code
flake8 apps/

# Type checking
mypy apps/

# Run all checks
pre-commit run --all-files
```

---

## 15. Monitoring & Logging

### 15.1 Application Monitoring

```python
# config/settings/production.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=env('SENTRY_DSN'),
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
    ],
    traces_sample_rate=0.1,
    send_default_pii=True,
    environment=env('ENVIRONMENT', default='production'),
)
```

### 15.2 Logging Configuration

```python
# config/settings/base.py
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
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### 15.3 Health Check Endpoint

```python
# apps/core/views.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

def health_check(request):
    """Health check endpoint for load balancer"""
    status = {
        'status': 'ok',
        'database': 'unknown',
        'cache': 'unknown',
    }

    # Check database
    try:
        connection.ensure_connection()
        status['database'] = 'ok'
    except Exception as e:
        status['database'] = 'error'
        status['status'] = 'error'

    # Check cache
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            status['cache'] = 'ok'
    except Exception as e:
        status['cache'] = 'error'
        status['status'] = 'error'

    status_code = 200 if status['status'] == 'ok' else 503
    return JsonResponse(status, status=status_code)
```

---

## Appendix

### A. Environment Variables

```bash
# .env.example

# Django
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=.yourdomain.com
DJANGO_SETTINGS_MODULE=config.settings.production

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/email_automation

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Email
EMAIL_BACKEND=anymail.backends.amazon_ses.EmailBackend
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_SES_REGION=us-east-1

# Twilio (SMS)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# AWS S3
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_S3_CUSTOM_DOMAIN=cdn.yourdomain.com

# Sentry
SENTRY_DSN=https://...@sentry.io/...

# Other
BASE_URL=https://yourdomain.com
ENVIRONMENT=production
```

---

**Document Version:** 1.0
**Last Updated:** January 19, 2026
**Next Review:** February 2026
