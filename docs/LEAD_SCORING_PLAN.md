# Lead Scoring Engine — Implementation Plan

> Created: 2026-04-27  
> Estimated effort: ~59 hours (7.5 developer-days)  
> Priority: P1 — required for Professional plan tier

---

## Why This Feature

1. **Unblocks three other gaps simultaneously** — workflow trigger (`lead_score_threshold`), workflow action (`update_lead_score`), segment filter (`lead score range`)
2. **Foundation already in place** — `Contact.lead_score` field, Celery/Redis, segment rule engine, signal infrastructure
3. **Closes the marketing → sales loop** — workflows can hand off hot leads to CRM automatically

---

## Files to Create

### Backend — new app `apps/lead_scoring/`

```
apps/lead_scoring/__init__.py
apps/lead_scoring/apps.py
apps/lead_scoring/models.py
apps/lead_scoring/services.py
apps/lead_scoring/serializers.py
apps/lead_scoring/views.py
apps/lead_scoring/urls.py
apps/lead_scoring/tasks.py
apps/lead_scoring/signals.py
apps/lead_scoring/permissions.py
apps/lead_scoring/admin.py
apps/lead_scoring/migrations/0001_initial.py
```

### Frontend — new files

```
frontend/src/types/leadScoring.ts
frontend/src/api/leadScoring.ts
frontend/src/hooks/useLeadScoring.ts
frontend/src/hooks/useScoreHistory.ts
frontend/src/pages/settings/LeadScoringTab.tsx
frontend/src/components/lead-scoring/ScoringRuleList.tsx
frontend/src/components/lead-scoring/ScoringRuleForm.tsx
frontend/src/components/lead-scoring/ThresholdEditor.tsx
frontend/src/components/lead-scoring/ScoreBadge.tsx
frontend/src/components/lead-scoring/ScoreHistoryDrawer.tsx
frontend/src/components/lead-scoring/ManualAdjustDialog.tsx
```

## Files to Modify

### Backend

```
config/settings/base.py           — add 'apps.lead_scoring' to INSTALLED_APPS + two Beat entries
config/urls.py                    — add path('api/v1/', include('apps.lead_scoring.urls'))
apps/contacts/views.py            — add 4 @action methods to ContactViewSet
apps/workflows/models.py          — add 2 new node type constants + NODE_TYPE_CHOICES entries
apps/workflows/services.py        — add trigger handler, action handler, validation cases
```

### Frontend

```
frontend/src/pages/settings/SettingsPage.tsx       — add LeadScoringTab (plan-gated)
frontend/src/pages/contacts/ContactDetailPage.tsx  — embed ScoreBadge + ScoreHistoryDrawer
frontend/src/types/workflow.ts                     — add 2 new node type literals + configs
frontend/src/hooks/usePermissions.ts               — add isProfessionalOrAbove flag
```

---

## Data Models

### `ScoringRule`

```python
class ScoringRule(TimeStampedModel, SoftDeleteModel):
    RULE_TYPE_DEMOGRAPHIC = 'demographic'
    RULE_TYPE_BEHAVIORAL  = 'behavioral'

    EVENT_EMAIL_OPENED       = 'email_opened'
    EVENT_EMAIL_CLICKED      = 'email_clicked'
    EVENT_FORM_SUBMITTED     = 'form_submitted'
    EVENT_TAG_ADDED          = 'tag_added'
    EVENT_TAG_REMOVED        = 'tag_removed'
    EVENT_WORKFLOW_COMPLETED = 'workflow_completed'
    EVENT_UNSUBSCRIBED       = 'unsubscribed'
    EVENT_BOUNCED            = 'bounced'

    id           = UUIDField(primary_key=True, default=uuid4, editable=False)
    organization = ForeignKey(Organization, on_delete=CASCADE, related_name='scoring_rules')
    name         = CharField(max_length=255)
    description  = TextField(blank=True)
    rule_type    = CharField(max_length=20, choices=RULE_TYPE_CHOICES)
    points       = IntegerField()               # positive = award, negative = deduct
    is_active    = BooleanField(default=True)
    priority     = PositiveIntegerField(default=0)

    # Demographic: {"field": "company", "operator": "is_not_empty", "value": ""}
    condition    = JSONField(default=dict, blank=True)

    # Behavioral: which event fires this rule
    event_type   = CharField(max_length=30, choices=EVENT_CHOICES, blank=True)

    # Optional: restrict to specific tag_id / form_id
    # e.g. {"tag_id": "uuid"} or {"form_id": "uuid"}
    event_filter = JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'lead_scoring_rules'
        ordering = ['priority', 'name']
        indexes  = [
            Index(fields=['organization', 'is_active']),
            Index(fields=['organization', 'rule_type']),
            Index(fields=['organization', 'event_type']),
        ]
```

**Supported condition fields:**
- Built-in: `email`, `company`, `job_title`, `first_name`, `last_name`, `phone`, `is_subscribed`, `is_verified`, `lead_score`, `created_at`, `last_activity_at`
- Custom: `custom.<field_name>` → reads from `contact.custom_fields.get(key)`

**Supported condition operators:**
`equals`, `not_equals`, `contains`, `not_contains`, `starts_with`, `ends_with`, `is_empty`, `is_not_empty`, `greater_than`, `less_than`, `greater_or_equal`, `less_or_equal`

---

### `ScoreHistory`

```python
class ScoreHistory(TimeStampedModel):
    # NOT SoftDeleteModel — history is immutable

    REASON_RULE   = 'rule'
    REASON_MANUAL = 'manual'
    REASON_RECALC = 'recalculation'

    id           = UUIDField(primary_key=True, default=uuid4, editable=False)
    contact      = ForeignKey(Contact, on_delete=CASCADE, related_name='score_history')
    rule         = ForeignKey(ScoringRule, on_delete=SET_NULL, null=True, blank=True)
    reason       = CharField(max_length=20, choices=REASON_CHOICES)
    points_delta = IntegerField()
    score_before = IntegerField()
    score_after  = IntegerField()
    note         = CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'lead_score_history'
        ordering = ['-created_at']
        indexes  = [
            Index(fields=['contact', '-created_at']),
        ]
```

---

### `ScoreThreshold`

```python
class ScoreThreshold(TimeStampedModel):
    id               = UUIDField(primary_key=True, default=uuid4, editable=False)
    organization     = ForeignKey(Organization, on_delete=CASCADE, related_name='score_thresholds')
    label            = CharField(max_length=50)       # e.g. "Hot"
    min_score        = IntegerField()                 # inclusive lower bound
    color            = CharField(max_length=20, default='blue')
    engagement_level = CharField(max_length=10, choices=Contact.ENGAGEMENT_LEVEL_CHOICES)

    class Meta:
        db_table        = 'lead_score_thresholds'
        ordering        = ['min_score']
        unique_together = [['organization', 'label']]
        indexes         = [Index(fields=['organization', 'min_score'])]
```

**Default thresholds (seeded for Professional+ orgs):**

| Label    | min_score | engagement_level | color  |
|----------|-----------|------------------|--------|
| Inactive | 0         | none             | gray   |
| Cold     | 10        | low              | blue   |
| Warm     | 40        | medium           | yellow |
| Hot      | 70        | high             | red    |

---

## Service Layer — `apps/lead_scoring/services.py`

### `LeadScoringService`

```
recalculate_contact(contact, reason='recalculation')
  1. Fetch all active demographic rules for contact.organization
  2. Evaluate each rule's condition against the contact (in-memory)
  3. Sum all matched rule points → raw_score
  4. Clamp to [0, 1000]
  5. Resolve engagement_level from ScoreThresholds
  6. If score/level changed: update contact + write ScoreHistory
  7. Fire WorkflowTriggerService.trigger_lead_score_threshold(contact, old, new)
  Returns: (new_score, engagement_level)

apply_behavioral_rule(contact, rule, note='')
  1. score_before = contact.lead_score
  2. new_score = clamp(score_before + rule.points, 0, 1000)
  3. Resolve engagement_level
  4. Save contact + write ScoreHistory(reason='rule')
  5. Fire WorkflowTriggerService.trigger_lead_score_threshold(...)
  Returns: new_score

manual_adjust(contact, points_delta, note, adjusted_by_user)
  1. new_score = clamp(contact.lead_score + points_delta, 0, 1000)
  2. Save contact + write ScoreHistory(reason='manual', note=note)
  Returns: new_score

resolve_engagement_level(score, organization)
  Fetches thresholds DESC, returns engagement_level of highest min_score <= score.
  Returns 'none' if no thresholds defined.

_evaluate_condition(condition: dict, contact: Contact) -> bool
  Mirrors SegmentEvaluator logic but operates on in-memory Contact object.
  No Q objects — pure Python boolean evaluation.

preview_score(contact) -> dict
  Runs demographic evaluation without saving.
  Returns: {score, matched_rules: [{id, name, points}], engagement_level}

bulk_recalculate(organization) -> int
  Iterates all contacts in chunks of 100.
  Calls recalculate_contact() for each.
  Returns count of updated contacts.
```

**Anti-loop guard:** The service always saves with `update_fields=['lead_score', 'engagement_level', 'updated_at']`. The `on_contact_field_changed` signal must skip if `update_fields` equals exactly this set.

---

## API Endpoints

### New endpoints in `apps/lead_scoring/urls.py`

```
router.register('scoring-rules',    ScoringRuleViewSet,    basename='scoring-rule')
router.register('score-thresholds', ScoreThresholdViewSet, basename='score-threshold')
```

All endpoints require `IsAuthenticated + IsOrganizationMember + LeadScoringEnabled`.

#### ScoringRule

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/v1/scoring-rules/` | List rules (filter: `is_active`, `rule_type`) |
| POST | `/api/v1/scoring-rules/` | Create rule |
| GET | `/api/v1/scoring-rules/{id}/` | Retrieve rule |
| PATCH | `/api/v1/scoring-rules/{id}/` | Update rule |
| DELETE | `/api/v1/scoring-rules/{id}/` | Soft-delete rule |
| POST | `/api/v1/scoring-rules/{id}/toggle/` | Toggle `is_active` |
| POST | `/api/v1/scoring-rules/reorder/` | Bulk update `priority` |

**Create/Update request:**
```json
// Demographic rule:
{
  "name": "Has Company",
  "rule_type": "demographic",
  "points": 15,
  "is_active": true,
  "condition": { "field": "company", "operator": "is_not_empty", "value": "" }
}

// Behavioral rule:
{
  "name": "Email Click",
  "rule_type": "behavioral",
  "points": 5,
  "event_type": "email_clicked",
  "event_filter": {}
}

// Behavioral with filter:
{
  "name": "VIP Tag Added",
  "rule_type": "behavioral",
  "points": 20,
  "event_type": "tag_added",
  "event_filter": { "tag_id": "uuid-of-vip-tag" }
}
```

#### ScoreThreshold

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/v1/score-thresholds/` | List thresholds for org |
| POST | `/api/v1/score-thresholds/` | Create single threshold |
| PATCH | `/api/v1/score-thresholds/{id}/` | Update single threshold |
| DELETE | `/api/v1/score-thresholds/{id}/` | Delete threshold |
| POST | `/api/v1/score-thresholds/bulk-update/` | Replace entire set atomically |

**bulk-update request** (preferred for ThresholdEditor):
```json
{
  "thresholds": [
    { "label": "Inactive", "min_score": 0,  "color": "gray",   "engagement_level": "none"   },
    { "label": "Cold",     "min_score": 10, "color": "blue",   "engagement_level": "low"    },
    { "label": "Warm",     "min_score": 40, "color": "yellow", "engagement_level": "medium" },
    { "label": "Hot",      "min_score": 70, "color": "red",    "engagement_level": "high"   }
  ]
}
```
Runs in a transaction: deletes all existing, creates new. Returns the saved list.

#### Contact-scoped actions (added to `ContactViewSet`)

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/v1/contacts/{id}/score-history/` | Paginated score history |
| POST | `/api/v1/contacts/{id}/adjust-score/` | Manual point adjustment |
| POST | `/api/v1/contacts/{id}/recalculate-score/` | Force full recalculation |
| POST | `/api/v1/contacts/{id}/preview-score/` | Preview without saving |

**score-history item:**
```json
{
  "id": "uuid",
  "rule": { "id": "uuid", "name": "Email Click", "rule_type": "behavioral" },
  "reason": "rule",
  "points_delta": 5,
  "score_before": 30,
  "score_after": 35,
  "note": "",
  "created_at": "2026-04-27T10:00:00Z"
}
```

**adjust-score request:**
```json
{ "points_delta": -10, "note": "Incorrect engagement data" }
```

**preview-score response:**
```json
{
  "current_score": 45,
  "projected_score": 70,
  "matched_rules": [
    { "id": "uuid", "name": "Has Company", "points": 15 },
    { "id": "uuid", "name": "Job Title Set", "points": 10 }
  ],
  "engagement_level": "medium"
}
```

---

## Celery Tasks — `apps/lead_scoring/tasks.py`

```python
recalculate_contact_score(contact_id: str)
  # Fired by: signal on Contact field change
  # Queue: default
  @shared_task(bind=True, max_retries=3, default_retry_delay=30)

apply_behavioral_score(contact_id: str, rule_id: str)
  # Fired by: behavioral event signals
  # Queue: default
  @shared_task(bind=True, max_retries=3, default_retry_delay=30)

bulk_recalculate_organization(organization_id: str)
  # Called by the periodic coordinator
  # Queue: default

periodic_bulk_recalculate_all_orgs()
  # Beat entry — iterates all active Professional+ orgs,
  # fires bulk_recalculate_organization.delay() for each
  # Schedule: daily at 03:00 UTC
```

**Beat schedule entry** (add to `CELERY_BEAT_SCHEDULE` in `config/settings/base.py`):
```python
'lead-scoring-daily-recalculation': {
    'task': 'apps.lead_scoring.tasks.periodic_bulk_recalculate_all_orgs',
    'schedule': crontab(hour=3, minute=0),
},
```

---

## Signal Handlers — `apps/lead_scoring/signals.py`

All handlers silently absorb exceptions (try/except + logger) so scoring never breaks the primary event flow.

```
on_campaign_recipient_updated   @post_save CampaignRecipient
  Detect: if 'opened_at' in update_fields → fire behavioral rules (event_type='email_opened')
  Detect: if 'clicked_at' in update_fields → fire behavioral rules (event_type='email_clicked')
  Note: tracking_views.py saves with explicit update_fields, so this is safe.

on_form_submission_created      @post_save FormSubmission (created=True only)
  Fire behavioral rules with event_type='form_submitted'
  Match rule.event_filter.get('form_id') if present

on_contact_tag_added            @post_save ContactTag (created=True only)
  Fire behavioral rules with event_type='tag_added'
  Match rule.event_filter.get('tag_id') if present

on_contact_tag_removed          @pre_delete ContactTag
  Fire behavioral rules with event_type='tag_removed'

on_workflow_execution_completed @post_save WorkflowExecution
  If status just became 'completed': fire event_type='workflow_completed'
  Use pre_save to cache old status for comparison

on_contact_unsubscribed         @post_save Contact
  If update_fields contains 'is_subscribed' AND new value is False:
  Fire event_type='unsubscribed'

on_contact_bounced              @post_save Contact
  If update_fields contains 'bounced_at' AND value is not None:
  Fire event_type='bounced'

on_contact_field_changed        @post_save Contact
  Fires recalculate_contact_score.delay() for demographic re-evaluation
  ANTI-LOOP GUARD: skip if update_fields == {'lead_score', 'engagement_level', 'updated_at'}
  This exact set is what LeadScoringService saves — prevents infinite recursion
```

Register in `apps/lead_scoring/apps.py`:
```python
def ready(self):
    import apps.lead_scoring.signals  # noqa
```

---

## Workflow Integration

### New node type constants in `apps/workflows/models.py`

```python
TRIGGER_LEAD_SCORE_THRESHOLD = 'trigger_lead_score_threshold'
ACTION_UPDATE_LEAD_SCORE     = 'action_update_lead_score'
```

### Node config schemas

**`trigger_lead_score_threshold`:**
```json
{
  "threshold_value": 70,
  "direction": "above"    // "above" | "below" | "equals"
}
```

**`action_update_lead_score`:**
```json
{
  "operation": "add",     // "add" | "subtract" | "set"
  "points": 10,
  "note": "Workflow reward"
}
```

### New method in `WorkflowTriggerService` (`apps/workflows/services.py`)

```python
@staticmethod
def trigger_lead_score_threshold(contact, old_score, new_score):
    # Finds all active workflows with trigger_lead_score_threshold nodes
    # Checks if old_score → new_score crossed the configured threshold+direction
    # If crossed: calls WorkflowExecutionService.start_execution()
```

### New handler in `WorkflowExecutionService._handle_node()`

```python
WorkflowNode.ACTION_UPDATE_LEAD_SCORE: WorkflowExecutionService._handle_update_lead_score
```

Where `_handle_update_lead_score` calls `LeadScoringService.manual_adjust()` with the configured delta.

### Called from `LeadScoringService`

After every score update (in both `recalculate_contact` and `apply_behavioral_rule`), call:
```python
WorkflowTriggerService.trigger_lead_score_threshold(contact, old_score, new_score)
```

---

## Frontend

### TypeScript types — `frontend/src/types/leadScoring.ts`

```typescript
export type RuleType = 'demographic' | 'behavioral';

export type EventType =
  | 'email_opened' | 'email_clicked' | 'form_submitted'
  | 'tag_added' | 'tag_removed' | 'workflow_completed'
  | 'unsubscribed' | 'bounced';

export type ConditionOperator =
  | 'equals' | 'not_equals' | 'contains' | 'not_contains'
  | 'starts_with' | 'ends_with' | 'is_empty' | 'is_not_empty'
  | 'greater_than' | 'less_than' | 'greater_or_equal' | 'less_or_equal';

export interface RuleCondition {
  field: string;
  operator: ConditionOperator;
  value: string | number;
}

export interface ScoringRule {
  id: string;
  name: string;
  description?: string;
  rule_type: RuleType;
  points: number;          // positive or negative
  is_active: boolean;
  priority: number;
  condition: RuleCondition;
  event_type?: EventType;
  event_filter?: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface ScoreThreshold {
  id: string;
  label: string;
  min_score: number;
  color: string;
  engagement_level: 'high' | 'medium' | 'low' | 'none';
}

export interface ScoreHistoryEntry {
  id: string;
  rule?: { id: string; name: string; rule_type: RuleType };
  reason: 'rule' | 'manual' | 'recalculation';
  points_delta: number;
  score_before: number;
  score_after: number;
  note: string;
  created_at: string;
}

export interface ScorePreview {
  current_score: number;
  projected_score: number;
  matched_rules: Array<{ id: string; name: string; points: number }>;
  engagement_level: string;
}
```

### Hooks — `frontend/src/hooks/useLeadScoring.ts`

```typescript
// Query keys
export const scoringKeys = {
  rules:      (params?) => ['scoring', 'rules', params],
  thresholds: () => ['scoring', 'thresholds'],
};

// Exported hooks
useScoringRules(params?)        // useQuery — lists rules with optional filters
useScoreThresholds()            // useQuery, staleTime: 5min
useCreateScoringRule()          // useMutation — invalidates rules
useUpdateScoringRule()          // useMutation
useDeleteScoringRule()          // useMutation
useToggleScoringRule()          // useMutation
useBulkUpdateThresholds()       // useMutation — invalidates thresholds
```

### Hooks — `frontend/src/hooks/useScoreHistory.ts`

```typescript
useScoreHistory(contactId, params?)   // useQuery — paginated history
useAdjustScore()                      // useMutation — invalidates history + contact
useRecalculateScore()                 // useMutation
usePreviewScore(contactId)            // useQuery, enabled: !!contactId
```

### Components

| Component | Description |
|---|---|
| `ScoreBadge` | Colored badge showing numeric score + threshold label. `onClick` opens history drawer. |
| `ScoreHistoryDrawer` | Side sheet (`<Sheet>`). Timeline of `ScoreHistoryEntry` with delta badges. "Adjust Score" button → `ManualAdjustDialog`. |
| `ManualAdjustDialog` | Modal form. Signed integer input for `points_delta`, note field. Shows projected new score as user types. |
| `ScoringRuleList` | Table of all rules. Per-row: name, type badge, points badge (green/red), event pill, active toggle, edit/delete. "Add Rule" → `ScoringRuleForm`. |
| `ScoringRuleForm` | Dialog. `rule_type` selector. Demographic: field/operator/value row (reuse `ConditionRow` pattern from segments). Behavioral: `event_type` select + optional filter. Points input. react-hook-form + zod. |
| `ThresholdEditor` | Editable list of threshold rows. Per-row: label, min_score, color swatches, engagement_level select. "Save All" → `useBulkUpdateThresholds`. Real-time score → label preview. |

### Settings page integration (`SettingsPage.tsx`)

Add a fourth tab (gated by `isProfessionalOrAbove` from `usePermissions`):
```tsx
// Tab trigger:
<TabsTrigger value="lead-scoring">
  <TrendingUp className="h-4 w-4 mr-2" /> Lead Scoring
</TabsTrigger>

// Tab content:
<TabsContent value="lead-scoring">
  <LeadScoringTab />     {/* ScoringRuleList + ThresholdEditor */}
</TabsContent>
```

### Contact detail integration (`ContactDetailPage.tsx`)

Replace static lead score display with:
```tsx
<ScoreBadge
  score={contact.lead_score}
  engagementLevel={contact.engagement_level}
  onClick={() => setHistoryOpen(true)}
/>
<ScoreHistoryDrawer
  contactId={contact.id}
  open={historyOpen}
  onClose={() => setHistoryOpen(false)}
/>
```

### Workflow types (`frontend/src/types/workflow.ts`)

```typescript
// Add to TriggerNodeType union:
| 'trigger_lead_score_threshold'

// Add to ActionNodeType union:
| 'action_update_lead_score'

// Add to NODE_TYPES array:
{
  type: 'trigger_lead_score_threshold',
  category: 'trigger',
  label: 'Lead Score Threshold',
  description: 'When a contact crosses a score threshold',
  icon: 'TrendingUp',
},
{
  type: 'action_update_lead_score',
  category: 'action',
  label: 'Update Lead Score',
  description: 'Add, subtract, or set a contact lead score',
  icon: 'BarChart2',
},
```

---

## Integration Points

| Existing System | How It Connects | Mechanism |
|---|---|---|
| `CampaignRecipient` (open/click) | Fires behavioral scoring | `post_save` signal; detects `opened_at`/`clicked_at` in `update_fields` |
| `FormSubmission` | Fires behavioral scoring | `post_save` signal (created=True) |
| `ContactTag` | Fires behavioral scoring | `post_save` (add) + `pre_delete` (remove) |
| `WorkflowExecution` | Fires behavioral scoring on completion | `post_save` detecting status → 'completed' |
| `Contact` (unsub/bounce) | Fires behavioral scoring | `post_save` detecting field changes |
| `Contact` (any field) | Re-runs demographic rules | `post_save` → `recalculate_contact_score.delay()` |
| `SegmentEvaluator` | Condition logic reuse | `_evaluate_condition()` mirrors segment logic, no Q objects |
| Workflow engine | New trigger + action | `WorkflowTriggerService.trigger_lead_score_threshold()` called after every score change |
| `Contact.lead_score` + `Contact.engagement_level` | Always in sync | Service writes both atomically in one `save(update_fields=...)` |
| `SettingsPage` | New tab | Additive — no breaking changes |
| `ContactDetailPage` | Score badge + history drawer | Additive — no breaking changes |

---

## Execution Order

### Phase 1 — Data Foundation (Day 1–2, ~4h)
1. Create `apps/lead_scoring/` directory structure
2. Write `apps.py`, `__init__.py`
3. Write `models.py` — all three models
4. Write `migrations/0001_initial.py`
5. Add to `INSTALLED_APPS` and run `migrate`

**Gate:** All other phases depend on this.

---

### Phase 2 — Service Layer (Day 2–3, ~10h)
1. Write `services.py` — `LeadScoringService` all methods
2. Write `tasks.py` — all four tasks
3. Unit tests: condition evaluation, threshold resolution, anti-loop guard, score clamping

**Gate:** API, signals, and workflow integration all depend on this.

---

### Phase 3 — REST API (Day 3–4, ~8h)
1. Write `serializers.py` — `ScoringRuleSerializer`, `ScoreThresholdSerializer`, `ScoreHistorySerializer`, `ManualAdjustSerializer`, `BulkUpdateThresholdsSerializer`
2. Write `permissions.py` — `LeadScoringEnabled`
3. Write `views.py` — `ScoringRuleViewSet` (with `toggle`, `reorder`), `ScoreThresholdViewSet` (with `bulk_update`)
4. Write `urls.py`
5. Update `config/urls.py`
6. Add 4 `@action` methods to `apps/contacts/views.py`

---

### Phase 4 — Signals + Beat Schedule (Day 4, ~5h)
1. Write `signals.py` — all handlers with anti-loop guards
2. Wire `ready()` in `apps.py`
3. Add Beat entry to `config/settings/base.py`
4. Smoke-test signal firing in shell

---

### Phase 5 — Workflow Integration (Day 5, ~5h)
1. Update `apps/workflows/models.py` — two new constants
2. Update `apps/workflows/services.py` — trigger handler, action handler, validation
3. Smoke-test: create workflow with lead_score_threshold trigger in shell

---

### Phase 6 — Frontend Foundation (Day 5–6, ~8h)
1. `types/leadScoring.ts`
2. `api/leadScoring.ts`
3. `hooks/useLeadScoring.ts`
4. `hooks/useScoreHistory.ts`
5. Extend `hooks/usePermissions.ts` with `isProfessionalOrAbove`

---

### Phase 7 — Frontend Components (Day 6–7, ~10h)
Order by complexity (simplest first):
1. `ScoreBadge.tsx`
2. `ManualAdjustDialog.tsx`
3. `ScoreHistoryDrawer.tsx`
4. `ThresholdEditor.tsx`
5. `ScoringRuleForm.tsx`
6. `ScoringRuleList.tsx`

---

### Phase 8 — Page Integration + Workflow UI (Day 7–8, ~6h)
1. `LeadScoringTab.tsx`
2. Modify `SettingsPage.tsx`
3. Modify `ContactDetailPage.tsx`
4. Modify `frontend/src/types/workflow.ts`
5. Write trigger/action config panel components for workflow builder

---

### Phase 9 — Polish + Admin (Day 8, ~3h)
1. `admin.py` — register all three models
2. Management command or data migration for default thresholds
3. End-to-end smoke test: create rules → submit a form → verify score updated → verify engagement_level updated → verify threshold workflow fires

---

## Effort Summary

| Phase | Description | Hours |
|---|---|---|
| 1 | Models + migrations | 4 h |
| 2 | Service layer + unit tests | 10 h |
| 3 | REST API (serializers, views, urls, contact actions) | 8 h |
| 4 | Signals + Celery + Beat | 5 h |
| 5 | Workflow engine integration | 5 h |
| 6 | Frontend types + API client + hooks | 8 h |
| 7 | Frontend components (6 components) | 10 h |
| 8 | Page integration + workflow UI nodes | 6 h |
| 9 | Admin + polish + smoke test | 3 h |
| **Total** | | **~59 hours / 7.5 dev-days** |

---

## Key Design Decisions

**Behavioral rules apply delta immediately; demographic rules recalculate from scratch.**
- Behavioral events (click, form submit) call `apply_behavioral_rule()` → immediate delta.
- Demographic field changes (company filled in) call `recalculate_contact()` → recomputes full score from all active demographic rules.
- This is clean but means a full recalculation resets behavioral accumulation. Acceptable trade-off for V1.

**Scores clamped to `[0, 1000]`.**
Prevents runaway scores from many behavioral events or looping workflows.

**`ScoreThreshold.bulk-update/` atomically replaces all thresholds.**
Avoids complex diff-and-patch UI. The `ThresholdEditor` component always submits the full desired state. One transaction: delete all, insert new.

**Anti-loop guard is `update_fields`-based.**
`LeadScoringService` always saves with `update_fields=['lead_score', 'engagement_level', 'updated_at']`. The `on_contact_field_changed` signal skips if it sees exactly this set. Robust as long as the service is the only code that saves that exact combination — which it is.

**Plan gating via permission class, not middleware.**
`LeadScoringEnabled` permission class on ViewSets is the cleanest DRF pattern. Frontend additionally hides the tab using `isProfessionalOrAbove`. This means Professional+ orgs see the feature; Free/Starter see nothing.
