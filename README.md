# Email Marketing Automation Platform

A multi-tenant email marketing and automation platform — campaigns, visual
automation workflows, landing pages, forms, CRM and analytics — built on Django
and React.

Each organization is isolated: its own contacts, campaigns, sending domains and
billing. Mail is delivered through a self-hosted [Postal](https://postalserver.io)
server, so sending runs on your own infrastructure and your own domains rather
than a third-party ESP.

---

## Features

| Area | What it does |
|---|---|
| **Contacts** | Import, custom fields, tags, activity timeline, lead scoring |
| **Segmentation** | Dynamic rule-based and static segments, AND/OR logic, live preview |
| **Campaigns** | Drag-and-drop editor (Unlayer), scheduling, A/B testing, test sends |
| **Sequences** | Multi-step drip sequences with per-step delays and enrollment tracking |
| **Workflows** | Visual automation builder (React Flow) — 7 triggers, 7 actions, if/else |
| **Landing pages** | GrapesJS builder, 50+ blocks, templates, SEO settings, analytics |
| **Forms** | Multi-step builder, conditional logic, embeddable, CSV export |
| **CRM** | Deals, kanban pipeline, activities, win/loss reporting |
| **Analytics** | Campaign, contact, form and page reporting with period comparison |
| **Deliverability** | SPF/DKIM/DMARC verification, suppression lists, bounce auto-pause |
| **Billing** | Stripe subscriptions, five plan tiers, usage limits |
| **AI assistant** | Bring-your-own-key generation of pages, forms, emails and campaigns |

## Stack

**Backend** — Django 5, Django REST Framework, SimpleJWT, Celery + Redis,
drf-spectacular. SQLite by default; PostgreSQL supported.

**Frontend** — React 18, TypeScript, Vite, TanStack Query, Zustand, Tailwind CSS,
shadcn/ui, Recharts.

**Mail** — self-hosted Postal, reached over its HTTP API, with signed webhooks for
delivery, bounce and complaint events.

---

## Quick start

Requires Docker and Docker Compose.

```bash
git clone https://github.com/shakibTechno/email-automation.git
cd email-automation

cp .env.example .env          # then edit: set SECRET_KEY at minimum
docker compose up -d
```

The backend runs migrations on first boot. Once the containers are healthy:

| | |
|---|---|
| Application | http://localhost:3000 |
| API | http://localhost:8000/api/v1/ |
| API docs (Swagger) | http://localhost:8000/api/docs/ |

Create the first account by registering through the UI — the first user in an
organization becomes its owner.

### Development mode

The dev overlay runs Vite with hot reload on port 5173 instead of the production
nginx build:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

> On Windows and macOS, Vite does not always see edits through the bind mount.
> If changes don't appear, restart the frontend container.

## Running tests

```bash
docker compose exec backend python manage.py test --settings=config.settings.test
```

Frontend type-checking and linting:

```bash
cd frontend
npx tsc --noEmit
npx eslint src --max-warnings 0
```

---

## Architecture notes

**Multi-tenancy** runs through an `Organization` foreign key on every tenant-owned
model, enforced by permission classes in `apps/core/permissions.py`. Viewsets scope
their querysets to `request.user.organization`.

**Sending** resolves per organization through
`EmailConfigService.get_connection()`, which returns a Django email backend. The
default routes to the organization's own Postal mail server; organizations can
instead bring their own SMTP, SendGrid, Mailgun or SES credentials.

**Domain verification** is delegated to the Postal provisioning API, which queries
the domain's authoritative nameservers and enables sending only once SPF, DKIM,
return-path *and* DMARC all pass.

**Background work** runs on Celery with Redis as the broker — campaign batches,
sequence processing, workflow execution, lead scoring, and deliverability
guardrails that pause sending when bounce or complaint rates breach their
thresholds.

### Layout

```
apps/           Django applications, one per domain area
config/         Settings (base/development/production/test), URLs, Celery
frontend/       React + TypeScript single-page application
docs/           Setup, architecture and operational guides
  history/      Point-in-time development notes, kept for reference
scripts/        Ad-hoc operator and debugging scripts
seed/           Seed data
docker/         Container entrypoints and supporting config
```

## Documentation

- [Setup guide](docs/SETUP_GUIDE.md) — installation and first run
- [Technical architecture](docs/TECHNICAL_ARCHITECTURE.md) — detailed design
- [Docker](docs/DOCKER.md) — container layout and operations
- [Email configuration](docs/EMAIL_CONFIGURATION_GUIDE.md) — sending setup
- [Troubleshooting](docs/TROUBLESHOOTING.md) — common problems
- [Deployment checklist](docs/DEPLOYMENT_CHECKLIST.md)

---

## Status

Under active development. Two things to know before running it in production:

- **The default database is SQLite**, which allows a single writer at a time.
  Django, the Celery worker and beat all write concurrently, so switch to
  PostgreSQL before real sending volume.
- **Provider credentials are stored unencrypted** at the database level and masked
  only at the API boundary. Encryption at rest is not yet implemented.

The self-hosted mail server stack is maintained separately and is not part of this
repository.
