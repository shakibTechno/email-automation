# Feature Checklist — Email Automation Platform

> Last updated: 2026-04-27 (Lead Scoring Engine + Segment lead_score filter complete)  
> Reference: `docs/PRD.md`, `docs/FEATURE_LIST.md`, `docs/MVP_PLAN.md`  
> Legend: ✅ Done · ⚠️ Partial · ❌ Missing · `(P1)` = MVP priority · `(P2)` = post-MVP

---

## 1. Authentication & Security

- [x] User registration + auto org creation
- [x] JWT login / logout / token refresh
- [x] Password change
- [x] Password reset (request + confirm)
- [x] Email verification token model
- [ ] ❌ Email verification flow wired to registration `(P1)`
- [ ] ❌ Two-factor authentication (TOTP) `(P1)`
- [ ] ❌ Login activity logging `(P2)`
- [ ] ❌ Social login — Google / Microsoft `(P2)`
- [ ] ❌ SSO / SAML 2.0 for enterprise `(P2)`

---

## 2. Team & Organization

- [x] Organization model with plan/limits
- [x] User roles: Owner, Admin, Member, Viewer
- [x] RBAC permission enforcement
- [x] Team member invitation via email
- [x] Accept invitation page
- [x] Role change
- [x] Remove member
- [x] Transfer ownership
- [x] Team activity log (team management actions only)
- [ ] ❌ Comprehensive audit log (all user + data actions) `(P1)`
- [ ] ❌ Organization branding (logo, colors) `(P2)`
- [ ] ❌ Custom domain setup UI `(P2)`
- [ ] ❌ Notification preferences UI `(P2)`

---

## 3. Contact Management

- [x] Contact CRUD (create, read, update, soft delete)
- [x] Contact search, filter, sort
- [x] Tags with colors — create, apply, remove
- [x] Custom field definitions + storage (JSON)
- [x] Bulk delete contacts
- [x] Bulk tag / untag contacts
- [x] CSV export
- [x] Duplicate detection service (backend)
- [x] CSV import service (backend — `CSVImportService`)
- [x] ✅ CSV import — 3-step dialog: drag-and-drop upload → column mapping → results summary `(P1)`
- [ ] ⚠️ Contact Activity Timeline — `ContactDetailPage` shows only `last_activity_at`; no unified timeline of email opens/clicks, form submissions, workflow steps, CRM activities `(P1)`
- [ ] ❌ Duplicate merge UI `(P1)`
- [ ] ❌ Auto-tagging rules based on behavior `(P1)`
- [ ] ❌ Excel (.xlsx) import `(P2)`
- [ ] ❌ Scheduled automated exports `(P2)`
- [ ] ❌ Contact list / group management (separate from tags/segments) `(P2)`

---

## 4. Contact Segmentation

- [x] Dynamic segments (rule-based, auto-updating)
- [x] Static segments (manual membership)
- [x] Rule builder — field, tag, date, number, boolean, select operators
- [x] AND / OR logic with nested groups
- [x] Real-time segment preview
- [x] Segment export to CSV
- [x] Celery task: refresh dynamic segment counts
- [ ] ❌ Behavioral filters in rules (email opens, clicks, page visits) `(P1)`
- [x] ✅ Lead score range filter in rules `(P1)` — `lead_score` exposed as numeric field with all operators (equals, gt, lt, between, etc.)
- [ ] ❌ Segment intersection / union / exclusion operations `(P2)`
- [ ] ❌ E-commerce data filters `(P3)`

---

## 5. Email Templates

- [x] Unlayer drag-and-drop editor
- [x] Template CRUD (create, edit, delete, list)
- [x] Template categories
- [x] Image upload and management
- [x] Template preview
- [ ] ❌ Pre-built system template library (50+ templates per docs) `(P1)`
- [ ] ❌ Template folders / organization `(P1)`
- [ ] ❌ Conditional / dynamic content blocks `(P1)`
- [ ] ❌ Fallback values for merge tags `(P1)`
- [ ] ❌ Global brand styles (colors, fonts) `(P2)`
- [ ] ❌ Custom font uploads `(P2)`
- [ ] ❌ Image editing (crop, resize) `(P2)`
- [ ] ❌ Template sharing with team `(P2)`
- [ ] ❌ Stock image integration `(P2)`

---

## 6. Email Campaigns

- [x] Campaign CRUD
- [x] 4-step creation wizard
- [x] Status workflow (draft → scheduled → sending → sent / paused / cancelled)
- [x] Send test email
- [x] Preview dialog
- [x] Schedule for specific date/time
- [x] Campaign duplication
- [x] Recipient targeting by tags or all subscribed
- [x] Open tracking (pixel)
- [x] Click tracking (link wrapping)
- [x] Unsubscribe link + processing
- [x] Bounce handling via Anymail signal handlers
- [ ] ⚠️ Recipient timezone sending — UI scheduling exists, per-timezone delivery logic missing `(P1)`
- [x] ✅ Campaign archiving — `archived` status + backend action + Archive menu item + filter tab `(P1)`
- [ ] ❌ A/B Testing (subject line, content, sender) — no model, API, or UI `(P1)`
- [ ] ❌ Pre-send checklist (links valid, subject set, test sent) `(P1)`
- [ ] ❌ Spam score checking `(P1)`
- [ ] ❌ Hard-bounce auto-removal Celery task `(P1)`
- [ ] ❌ Global suppression list `(P1)`
- [ ] ❌ Campaign folders `(P2)`
- [ ] ❌ Multi-client email preview `(P2)`
- [ ] ❌ Recurring campaign scheduling `(P2)`
- [ ] ❌ RSS-to-email `(P2)`
- [ ] ❌ Campaign version history `(P2)`

---

## 7. Email Deliverability

- [x] Celery batch sender
- [x] Per-recipient HTML rendering (merge tags)
- [x] Click-wrapped tracking links
- [x] Tracking pixel (open events)
- [x] Signed unsubscribe URLs
- [x] Anymail signal handlers (open, click, bounce, complaint)
- [x] Celery Beat schedules
- [ ] ❌ SPF / DKIM / DMARC setup wizard / guidance UI `(P1)`
- [ ] ❌ Custom sending domain verification flow `(P1)`
- [ ] ❌ Blacklist monitoring `(P1)`
- [ ] ❌ Sender reputation score display `(P1)`
- [ ] ❌ Email validity verification before send `(P2)`
- [ ] ❌ Dedicated IP support `(P2)`
- [ ] ❌ IP warmup process `(P2)`

---

## 8. Forms & Lead Capture

- [x] Form CRUD
- [x] 3-step builder wizard (Fields → Design → Preview/Publish)
- [x] Field types: text, email, phone, dropdown, checkbox, radio, textarea, date, hidden, section header, divider
- [x] Required fields, placeholder, help text
- [x] Advanced design (colors, typography, button/input styles, layout)
- [x] Multi-column layouts, field widths
- [x] Branding: logo, header/footer, custom CSS, powered-by toggle
- [x] Conditional field logic (show/hide)
- [x] GDPR consent checkbox field type
- [x] Public form route `/f/:id`
- [x] Embed code + share URL
- [x] Submission management + CSV export
- [x] Form type model: inline / popup / slide-in / top-bar
- [ ] ⚠️ Slide-in / top-bar form types — model supports them, but frontend embedding/rendering behavior not differentiated `(P1)`
- [ ] ❌ Multi-step forms `(P1)`
- [ ] ❌ Double opt-in email verification on submission `(P1)`
- [ ] ❌ reCAPTCHA integration `(P1)`
- [ ] ❌ Form submission email notifications `(P1)`
- [ ] ❌ Exit-intent popup trigger `(P1)`
- [ ] ❌ Timed popup trigger `(P1)`
- [ ] ❌ Scroll-triggered popup trigger `(P1)`
- [ ] ❌ Delete individual submissions `(P1)`
- [ ] ❌ Form analytics page (submissions over time) `(P1)`
- [ ] ❌ Form duplication `(P2)`
- [ ] ❌ Form expiration dates `(P2)`
- [ ] ❌ Submission limits per user `(P2)`

---

## 9. Landing Pages

- [x] GrapesJS drag-and-drop builder
- [x] 50+ pre-built blocks (layout, heroes, features, pricing, testimonials, CTA, forms, media, nav, content)
- [x] Template system (system + user templates, by category)
- [x] Publish / unpublish
- [x] Public page route `/p/<slug>/` (served by Django)
- [x] SEO settings (title, description, keywords, OG image, favicon)
- [x] Analytics integration (GA ID, FB Pixel ID)
- [x] Custom code injection (head + body)
- [x] Page view analytics
- [x] Layers panel, enhanced style manager
- [ ] ⚠️ Mobile preview — GrapesJS has device toggle built-in but not explicitly surfaced in UI controls `(P1)`
- [ ] ❌ Landing page duplication `(P1)`
- [ ] ❌ Custom domain support for published pages `(P1)`
- [ ] ❌ Page version history `(P2)`
- [ ] ❌ Password-protected pages `(P2)`

---

## 10. Workflow Automation

- [x] React Flow visual canvas
- [x] Triggers: Form Submission, Tag Added, Tag Removed, Contact Created, Email Opened, Email Clicked, Date Field
- [x] Actions: Send Email, Add Tag, Remove Tag, Update Contact, Wait/Delay, Webhook, Goal
- [x] If/Else condition node
- [x] Celery async execution
- [x] Celery Beat: resume waiting (1 min), date triggers (daily)
- [x] Execution tracking (status, step history)
- [x] Goal reached tracking
- [x] Workflow stats (entered, active, completed, goal_reached)
- [x] 5 system templates (Welcome, Lead Nurture, Re-engagement, Birthday, Onboarding)
- [x] Workflow duplication
- [ ] ⚠️ Workflow execution logs UI — backend has `WorkflowExecutionStep` but detail view is limited `(P1)`
- [x] ✅ Trigger: Lead score threshold `(P1)`
- [ ] ❌ Trigger: List subscription `(P1)`
- [ ] ❌ Trigger: API event `(P1)`
- [ ] ❌ Trigger: Page visited `(P2)`
- [ ] ❌ Trigger: Purchase / Cart abandonment `(P2)`
- [ ] ❌ Action: Send SMS `(P1)`
- [ ] ❌ Action: Create CRM deal `(P1)` *(CRM exists but not wired to workflows)*
- [x] ✅ Action: Update lead score `(P1)`
- [ ] ❌ Action: Assign to sales user `(P2)`
- [ ] ❌ Canvas: auto-arrange layout `(P1)`
- [ ] ❌ Canvas: copy/paste nodes `(P1)`
- [ ] ❌ Workflow search + folders `(P2)`
- [ ] ❌ Debug / test mode `(P2)`
- [ ] ❌ Pause/resume individual execution `(P2)`

---

## 11. Lead Scoring

> ✅ **Module complete** — `apps/lead_scoring` with full backend + frontend.

- [x] ✅ ScoringRule model (demographic + behavioral rules) `(P1)`
- [x] ✅ Scoring rules API (CRUD + toggle + reorder) `(P1)`
- [x] ✅ Score calculation service + Celery tasks (recalculate on email open/click, form submit, tag change, workflow, contact update) `(P1)`
- [x] ✅ Lead scoring rules UI — ScoringRuleList + ScoringRuleForm in Settings → Lead Scoring tab `(P1)`
- [x] ✅ Score thresholds configuration — ThresholdEditor in Settings → Lead Scoring tab `(P1)`
- [x] ✅ Manual score adjustment from contact detail (ManualAdjustDialog) `(P1)`
- [x] ✅ Score history tracking + drawer on contact detail (ScoreHistoryDrawer) `(P2)`
- [x] ✅ Workflow trigger: Lead score threshold `(P1)`
- [x] ✅ Workflow action: Update lead score `(P1)`
- [x] ✅ Plan-gating: Professional/Enterprise plans only (LeadScoringEnabled permission) `(P1)`
- [ ] ❌ Score decay over time `(P2)`
- [ ] ❌ Lead score range filter in segment rules `(P1)` *(segment evaluator not yet updated)*
- [ ] ❌ Predictive ML-based scoring `(P3)`

---

## 12. CRM & Sales Pipeline

- [x] Pipeline CRUD (custom stages with probability)
- [x] Deal CRUD (value, currency, probability, weighted value)
- [x] Kanban board with drag-and-drop stage movement
- [x] Deal-contact relationships (roles: primary/decision_maker/influencer/champion)
- [x] Activities (call, email, meeting, task, note)
- [x] Activity timeline on deal detail
- [x] Win / lose dialog with reason tracking
- [x] Deal stage history audit
- [x] Sales reporting (pipeline value, win rate, avg deal size)
- [ ] ❌ CRM ↔ Workflow integration (create deal action, deal trigger) `(P1)`
- [ ] ❌ Multiple pipelines per org `(P2)`
- [ ] ❌ Sales forecast `(P2)`
- [ ] ❌ Sales velocity metrics `(P2)`
- [ ] ❌ Deal tasks / reminders `(P2)`

---

## 13. Analytics & Reporting

- [x] Overview page (trends, contacts, campaigns, forms, landing pages)
- [x] Campaign analytics (sent, delivered, open/click rates, bounce, unsub, period comparison)
- [x] Campaign comparison dialog (side-by-side)
- [x] Campaign CSV export
- [x] Contact analytics (growth chart, engagement distribution, sources, lead score histogram)
- [x] Form analytics (submissions chart, top forms, all forms table)
- [x] Landing page analytics (views/unique, referrers, devices)
- [x] Date range selector (7 / 30 / 90 days)
- [ ] ❌ Link-level click heatmap per campaign `(P1)`
- [ ] ❌ Geographic analytics `(P1)`
- [ ] ❌ Device / email client breakdown `(P1)`
- [ ] ❌ Workflow analytics dashboard `(P1)`
- [ ] ❌ Scheduled automated reports `(P2)`
- [ ] ❌ Custom report builder `(P2)`
- [ ] ❌ PDF export for reports `(P2)`
- [ ] ❌ White-label reports `(P2)`
- [ ] ❌ Revenue / ROI tracking `(P2)`

---

## 14. Billing & Subscriptions

- [x] 5-tier plans (Free / Starter / Professional / Business / Enterprise)
- [x] Stripe checkout integration
- [x] Plan upgrade / downgrade
- [x] Cancel / reactivate subscription
- [x] Payment method management
- [x] Invoice history
- [x] Stripe webhooks (payment events)
- [x] Trial expiration Celery tasks
- [x] Usage tracking (contacts, emails sent)
- [ ] ❌ Overage charge handling `(P1)`
- [ ] ❌ Coupon code / promo code support `(P2)`
- [ ] ❌ Invoice PDF download (currently view-only) `(P2)`
- [ ] ❌ Referral program `(P2)`
- [ ] ❌ PayPal support `(P2)`

---

## 15. Integrations

- [x] Google Analytics (GA4 ID configuration)
- [x] Facebook Pixel
- [x] Google Tag Manager
- [x] Facebook Lead Ads (demo + field mapping + sync history)
- [x] LinkedIn Lead Gen Forms (demo + field mapping + sync history)
- [x] Outbound webhook action in workflows
- [ ] ❌ Zapier / Make (Integromat) `(P1)`
- [ ] ❌ Salesforce CRM `(P2)`
- [ ] ❌ HubSpot CRM `(P2)`
- [ ] ❌ Pipedrive `(P2)`
- [ ] ❌ Shopify `(P2)`
- [ ] ❌ WooCommerce `(P2)`
- [ ] ❌ Slack notifications `(P2)`
- [ ] ❌ Zoom webinars `(P2)`
- [ ] ❌ WordPress plugin `(P2)`
- [ ] ❌ General outbound webhook system (with signing + retries) `(P2)`
- [ ] ❌ REST API keys for external access (currently JWT-only) `(P2)`
- [ ] ❌ SDK libraries `(P3)`

---

## 16. Compliance & GDPR

- [x] Unsubscribe link + one-click processing
- [x] `is_subscribed` flag on contacts
- [x] GDPR consent field type on forms
- [ ] ⚠️ Consent audit trail — consent field exists but no timestamp/source tracking `(P1)`
- [ ] ❌ Full data export per contact (GDPR right of access) `(P1)`
- [ ] ❌ Hard data deletion per contact (right to be forgotten) `(P1)`
- [ ] ❌ Double opt-in flow `(P1)`
- [ ] ❌ CAN-SPAM physical address in email footer `(P1)`
- [ ] ❌ Global suppression / do-not-contact list `(P1)`
- [ ] ❌ IP whitelisting `(P2)`

---

## 17. Multi-Channel (Post-MVP)

- [ ] ❌ SMS campaigns + templates + analytics `(P1)`
- [ ] ❌ SMS in workflow actions `(P1)`
- [ ] ❌ WhatsApp Business API `(P2)`
- [ ] ❌ Web push notifications `(P2)`
- [ ] ❌ In-app messages (JS SDK) `(P2)`

---

## 18. AI Features (Post-MVP)

- [ ] ❌ AI subject line generator `(P2)`
- [ ] ❌ AI email body copy generation `(P2)`
- [ ] ❌ Send time optimization `(P2)`
- [ ] ❌ Predictive lead scoring (ML) `(P3)`
- [ ] ❌ Smart segmentation suggestions `(P3)`

---

## Quick-Win Backlog (Low Effort, High Value)

These are small gaps where significant backend work already exists:

| Item | Effort | Blocker |
|---|---|---|
| ~~Contact CSV import UI~~ | ✅ Done | — |
| Landing page duplication button | ~2h | Backend done (campaigns have it as pattern) |
| ~~Campaign archive action + filter~~ | ✅ Done | — |
| Workflow execution detail view (step log) | ~1 day | `WorkflowExecutionStep` data exists |
| Duplicate merge UI (contacts) | ~1 day | `DuplicateDetectionService` done |
| Consent timestamp tracking | ~2h | Add `consented_at` + source field to Contact |

---

## Recommended Next Feature: Lead Scoring Engine

**Why this next:**

1. **It's P1** — classified as must-have for the Professional plan tier. Without it, the Professional plan ($99/mo) is undersold.
2. **It unblocks three other gaps** simultaneously:
   - Workflow trigger: "Lead score threshold" (currently missing)
   - Workflow action: "Update lead score"
   - Segment rule: "Lead score range" filter
3. **The foundation is already there** — `Contact.lead_score` integer field exists, Celery infrastructure is in place, the segment rule engine can be extended, and the workflow engine already handles custom actions.
4. **High user value** — lets marketers prioritize hot leads for sales handoff via CRM, which closes the marketing → sales loop the platform already supports (workflows → CRM).

**Suggested build order within the feature:**

1. `ScoringRule` model (org-scoped, type: demographic/behavioral, points, conditions)
2. Scoring calculation service + Celery task (recalculate on email open/click, form submit, contact update)
3. REST API (CRUD for rules, manual score adjustment endpoint)
4. Frontend: Lead Scoring settings page (rule builder, threshold labels)
5. Wire up workflow trigger + action + segment filter
6. Contact detail: score badge + adjustment control

**Runner-up:** Contact CSV Import UI — one day of frontend work, zero backend work, immediately useful for any new customer onboarding their existing list.
