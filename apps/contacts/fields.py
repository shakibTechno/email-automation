"""
The one declaration of what fields a contact has.

Before this, six places each kept their own list — the CSV importer, the CSV
exporter, the form-to-contact mapping, the segment rule engine, and two React
components. Six lists that had to agree and did not: the segment engine offered
a "Status" field the model has never had (a 500 for anyone who built a rule on
it), and the Birthday workflow template shipped with no date field to drive it.

Worse than the drift, two of those places had no list at all. The CSV importer
took its column mapping straight from the request and assigned to whatever
attribute name it was handed, so a mapping of `{"col": "organization_id"}`
wrote contacts into another tenant's organization. The workflow "update
contact" action did the same from node config.

So this module answers three questions, and every caller asks it rather than
remembering:

  * which fields exist, with what type and label
  * which of them a given channel may *write* — an importer may set `company`,
    nothing may set `organization_id`
  * how to turn a CSV cell into the right Python value

`custom.<key>` targets are handled by the caller against the organization's
`CustomField` definitions; this module covers the physical columns only, and
`is_custom_target()` recognises the other form so callers can route it.
"""
from dataclasses import dataclass, field as dataclass_field
from datetime import date, datetime

from django.utils.dateparse import parse_date, parse_datetime

# Channels that write to a contact. Named rather than boolean-per-caller so a
# new channel has to state its intent for every field.
IMPORT = 'import'
FORM = 'form'
WORKFLOW = 'workflow'

CUSTOM_PREFIX = 'custom.'


@dataclass(frozen=True)
class FieldSpec:
    """One contact field, and who is allowed to do what with it."""

    key: str
    label: str
    type: str  # string | email | phone | url | number | date | datetime | boolean | select
    options: tuple = ()
    # Writable defaults to False: a field has to be opted in to being written by
    # an outside channel. The failure this module exists to prevent came from
    # the opposite default.
    writable_by: frozenset = dataclass_field(default_factory=frozenset)
    exportable: bool = True
    segmentable: bool = True

    def writable(self, channel):
        return channel in self.writable_by


def _spec(key, label, type_, *, options=(), writable_by=(), exportable=True, segmentable=True):
    return FieldSpec(
        key=key,
        label=label,
        type=type_,
        options=tuple(options),
        writable_by=frozenset(writable_by),
        exportable=exportable,
        segmentable=segmentable,
    )


# Mirrors apps.contacts.models.Contact. Kept as data rather than derived from
# the model by introspection: "who may write this" is a policy decision that
# does not live in a column definition, and introspection would have happily
# included organization_id — the field that must never be writable.
_SPECS = (
    # ── Identity ──────────────────────────────────────────────────────────────
    _spec('email', 'Email', 'email', writable_by=(IMPORT, FORM)),
    _spec('first_name', 'First Name', 'string', writable_by=(IMPORT, FORM, WORKFLOW)),
    _spec('last_name', 'Last Name', 'string', writable_by=(IMPORT, FORM, WORKFLOW)),
    _spec('phone', 'Phone', 'phone', writable_by=(IMPORT, FORM, WORKFLOW)),
    _spec('company', 'Company', 'string', writable_by=(IMPORT, FORM, WORKFLOW)),
    _spec('job_title', 'Job Title', 'string', writable_by=(IMPORT, FORM, WORKFLOW)),

    _spec('salutation', 'Salutation', 'string', writable_by=(IMPORT, FORM)),
    _spec('middle_name', 'Middle Name', 'string', writable_by=(IMPORT, FORM)),
    _spec(
        'preferred_name', 'Preferred Name', 'string',
        writable_by=(IMPORT, FORM, WORKFLOW),
    ),
    _spec('mobile_phone', 'Mobile Phone', 'phone', writable_by=(IMPORT, FORM)),
    _spec('website', 'Website', 'url', writable_by=(IMPORT, FORM)),
    _spec('linkedin_url', 'LinkedIn URL', 'url', writable_by=(IMPORT, FORM)),
    # Drives the Birthday workflow template, which shipped without a field.
    _spec('date_of_birth', 'Date of Birth', 'date', writable_by=(IMPORT, FORM)),

    # ── Address and locale ──────────────────────────────────────────────────
    _spec('address_line1', 'Address Line 1', 'string', writable_by=(IMPORT, FORM)),
    _spec('address_line2', 'Address Line 2', 'string', writable_by=(IMPORT, FORM)),
    _spec('city', 'City', 'string', writable_by=(IMPORT, FORM)),
    _spec('region', 'State / Region', 'string', writable_by=(IMPORT, FORM)),
    _spec('postal_code', 'Postal Code', 'string', writable_by=(IMPORT, FORM)),
    _spec('country', 'Country', 'string', writable_by=(IMPORT, FORM)),
    _spec('timezone', 'Time Zone', 'string', writable_by=(IMPORT, FORM)),
    _spec('locale', 'Language', 'string', writable_by=(IMPORT, FORM)),

    # ── Consent ─────────────────────────────────────────────────────────────
    # Importable: a customer migrating from another platform has to bring the
    # consent record with them, or they arrive unable to prove any of it.
    _spec('consent_at', 'Consent Given At', 'datetime', writable_by=(IMPORT,)),
    _spec('consent_source', 'Consent Source', 'string', writable_by=(IMPORT,)),
    _spec('double_opt_in_at', 'Double Opt-in At', 'datetime', writable_by=(IMPORT,)),
    # Not importable: an IP address is evidence, and evidence that any CSV can
    # assert is not evidence. Set by the form that captured it.
    _spec('opt_in_ip', 'Opt-in IP', 'string', writable_by=()),
    _spec('external_id', 'External ID', 'string', writable_by=(IMPORT,)),

    # ── Lifecycle ───────────────────────────────────────────────────────────
    _spec(
        'lifecycle_stage', 'Lifecycle Stage', 'select',
        options=('subscriber', 'lead', 'qualified', 'customer', 'evangelist'),
        writable_by=(IMPORT, WORKFLOW),
    ),
    # Derived from the flags below by Contact.save(), so nothing may write it.
    # Segmentable because that is what the builder always offered.
    _spec(
        'status', 'Status', 'select',
        options=('active', 'unsubscribed', 'bounced', 'complained'),
        writable_by=(),
    ),
    _spec(
        'bounce_type', 'Bounce Type', 'select', options=('soft', 'hard'),
        writable_by=(),
    ),
    _spec('complained_at', 'Complained At', 'datetime', writable_by=()),

    # ── Subscription ─────────────────────────────────────────────────────────
    # Writable by a workflow so an automation can unsubscribe someone, but never
    # by an import: a CSV should not be able to resurrect an unsubscribed
    # contact, which is the one mistake here with legal consequences.
    _spec('is_subscribed', 'Is Subscribed', 'boolean', writable_by=(WORKFLOW,)),
    _spec('is_verified', 'Is Verified', 'boolean'),
    _spec('unsubscribed_at', 'Unsubscribed At', 'datetime'),
    _spec('bounced_at', 'Bounced At', 'datetime'),

    # ── Engagement ───────────────────────────────────────────────────────────
    # Owned by the lead-scoring engine and the tracking pipeline. Letting an
    # import set a score would make the number mean nothing.
    _spec('lead_score', 'Lead Score', 'number'),
    _spec(
        'engagement_level', 'Engagement Level', 'select',
        options=('high', 'medium', 'low', 'none'),
    ),
    _spec('last_activity_at', 'Last Activity', 'datetime'),

    # ── Provenance ───────────────────────────────────────────────────────────
    # `source` records how a contact arrived, so the arriving channel sets it
    # rather than the payload.
    _spec(
        'source', 'Source', 'select',
        options=('manual', 'import', 'api', 'form', 'integration'),
    ),

    # ── Timestamps ───────────────────────────────────────────────────────────
    _spec('created_at', 'Created Date', 'datetime'),
    _spec('updated_at', 'Updated Date', 'datetime'),
)

CONTACT_FIELDS = {spec.key: spec for spec in _SPECS}

# Keys that look plausible and must never be writable, listed so the reason is
# recorded next to them rather than inferred from their absence.
#
#   organization / organization_id — writing it moves a contact to another
#       tenant, which is the hole this module closes
#   id                             — overwriting a primary key
#   deleted_at                     — un-deleting or silently deleting
#   custom_fields                  — must go through the CustomField
#       definitions, not be replaced wholesale
NEVER_WRITABLE = frozenset({
    'id', 'organization', 'organization_id', 'deleted_at',
    'custom_fields', 'company_ref', 'company_ref_id',
    'assigned_to', 'assigned_to_id', 'password',
})


def is_custom_target(target):
    """Whether a mapping target names a custom field rather than a column."""
    return bool(target) and str(target).startswith(CUSTOM_PREFIX)


def custom_key(target):
    """`custom.industry` → `industry`."""
    return str(target)[len(CUSTOM_PREFIX):] if is_custom_target(target) else ''


def writable_keys(channel):
    """The column names `channel` may write."""
    return {key for key, spec in CONTACT_FIELDS.items() if spec.writable(channel)}


def writable_choices(channel):
    """(key, label) pairs for a channel, for use as Django/serializer choices."""
    return [
        (spec.key, spec.label)
        for spec in _SPECS
        if spec.writable(channel)
    ]


def exportable_keys():
    return {key for key, spec in CONTACT_FIELDS.items() if spec.exportable}


def segmentable_specs():
    return {key: spec for key, spec in CONTACT_FIELDS.items() if spec.segmentable}


def rejection_reason(target, channel):
    """
    Why `channel` may not write `target`, or None when it may.

    A message rather than a boolean so every caller refuses in the same words,
    and so the words name the offending key — an import that fails without
    saying which column was at fault just moves the puzzle.
    """
    if not target:
        return 'A mapping target cannot be blank.'

    target = str(target)

    if is_custom_target(target):
        if not custom_key(target):
            return f'"{target}" does not name a custom field.'
        return None

    if target in NEVER_WRITABLE:
        return f'"{target}" cannot be set this way.'

    spec = CONTACT_FIELDS.get(target)
    if spec is None:
        return (
            f'"{target}" is not a contact field. Use one of: '
            f'{", ".join(sorted(writable_keys(channel)))}, '
            f'or "custom.<field>" for a custom field.'
        )
    if not spec.writable(channel):
        return f'"{target}" cannot be set by {channel}.'
    return None


# ── Coercion ────────────────────────────────────────────────────────────────
# A CSV cell is always a string. Writing "42" into an IntegerField or "yes" into
# a BooleanField used to work by accident or fail at the database; both are
# worse than converting here, where the failure can name the column.

_TRUE = {'1', 'true', 't', 'yes', 'y', 'on', 'subscribed'}
_FALSE = {'0', 'false', 'f', 'no', 'n', 'off', 'unsubscribed'}


class CoercionError(ValueError):
    """A value that cannot be stored in the field it was mapped to."""


def coerce(key, raw):
    """Convert a raw (usually string) value to what the field stores."""
    spec = CONTACT_FIELDS.get(key)
    if spec is None:
        return raw
    return coerce_value(spec.type, raw, label=spec.label, options=spec.options)


def coerce_value(type_, raw, *, label='value', options=()):
    """Coerce by declared type. Shared with the custom-field definitions."""
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = raw.strip()
        if raw == '':
            return None

    if type_ == 'number':
        if isinstance(raw, bool):
            raise CoercionError(f'{label} must be a number.')
        try:
            text = str(raw)
            return int(text) if '.' not in text else float(text)
        except (TypeError, ValueError):
            raise CoercionError(f'{label} must be a number, got "{raw}".')

    if type_ == 'boolean':
        if isinstance(raw, bool):
            return raw
        text = str(raw).strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
        raise CoercionError(f'{label} must be true or false, got "{raw}".')

    if type_ == 'date':
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, date):
            return raw
        parsed = parse_date(str(raw))
        if parsed is None:
            raise CoercionError(f'{label} must be a date as YYYY-MM-DD, got "{raw}".')
        return parsed

    if type_ == 'datetime':
        if isinstance(raw, datetime):
            return raw
        parsed = parse_datetime(str(raw))
        if parsed is None:
            raise CoercionError(f'{label} must be a date and time, got "{raw}".')
        return parsed

    if type_ == 'select' and options:
        text = str(raw).strip().lower()
        if text not in {str(o).lower() for o in options}:
            raise CoercionError(
                f'{label} must be one of: {", ".join(str(o) for o in options)}.'
            )
        return text

    return str(raw)
