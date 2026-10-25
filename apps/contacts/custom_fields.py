"""
Validating contact values against the organization's custom field definitions.

The definitions and the values have both existed from the start —
`CustomField`, and `Contact.custom_fields` — with nothing between them.
`ContactSerializer.validate_custom_fields` was documented as "Validate custom
fields against defined CustomField models" and only checked that the payload
was a dictionary. So any key could be written, with any value, of any type:
`is_required` was never required, `dropdown_options` never constrained
anything, and a field declared as a number held whatever string arrived. Which
in turn meant a segment could not compare it, because there was nothing to
compare.

One service rather than a check per caller, because four of them need it — the
API serializer, the CSV importer, form submissions and workflow actions — and
four implementations of "is this value allowed" would disagree within a month.
"""
import logging

from .fields import CoercionError, coerce_value

logger = logging.getLogger(__name__)


class CustomFieldError(ValueError):
    """
    Values that do not satisfy their definitions.

    Carries a per-key mapping so a serializer can report each offending field
    beside its own input instead of one message for the whole object.
    """

    def __init__(self, errors):
        self.errors = errors
        super().__init__('; '.join(f'{k}: {v}' for k, v in errors.items()))


class CustomFieldService:
    """Definitions in, validated values out."""

    @staticmethod
    def definitions(organization):
        """This organization's definitions, keyed by their JSON key."""
        from .models import CustomField

        if organization is None:
            return {}
        return {
            definition.key: definition
            for definition in CustomField.objects.filter(organization=organization)
        }

    @staticmethod
    def validate_and_coerce(organization, values, *, partial=True):
        """
        Check `values` against the definitions and return them typed.

        `partial=True` (an update) skips the required check, because an update
        that touches one field must not fail for another the caller never sent.
        A create passes `partial=False`.

        Unknown keys are refused rather than dropped. Silently discarding them
        is how a customer discovers months later that an integration has been
        writing to a field name nobody declared.
        """
        if values is None:
            return {}
        if not isinstance(values, dict):
            raise CustomFieldError({'custom_fields': 'Must be an object.'})

        defined = CustomFieldService.definitions(organization)
        errors = {}
        cleaned = {}

        for key, raw in values.items():
            definition = defined.get(key)
            if definition is None:
                errors[key] = (
                    f'"{key}" is not a custom field. '
                    f'Define it first under Settings, or remove it.'
                )
                continue
            try:
                cleaned[key] = CustomFieldService._coerce_one(definition, raw)
            except CoercionError as exc:
                errors[key] = str(exc)

        if not partial:
            for key, definition in defined.items():
                if definition.is_required and cleaned.get(key) in (None, '', []):
                    errors[key] = f'{definition.name} is required.'

        if errors:
            raise CustomFieldError(errors)
        return cleaned

    @staticmethod
    def _coerce_one(definition, raw):
        """One value, by its declared type."""
        options = tuple(definition.dropdown_options or ())

        if definition.field_type == 'multiselect':
            # Accepts a list, or the comma-separated form a CSV cell carries.
            if isinstance(raw, str):
                raw = [part.strip() for part in raw.split(',') if part.strip()]
            if not isinstance(raw, (list, tuple)):
                raise CoercionError(f'{definition.name} must be a list of values.')
            allowed = {str(o).lower() for o in options}
            chosen = []
            for item in raw:
                text = str(item).strip()
                if allowed and text.lower() not in allowed:
                    raise CoercionError(
                        f'{definition.name}: "{text}" is not one of '
                        f'{", ".join(str(o) for o in options)}.'
                    )
                chosen.append(text)
            return chosen

        value = coerce_value(
            definition.spec_type, raw, label=definition.name, options=options,
        )

        # A dropdown with no options defined constrains nothing, and refusing
        # every value for a field the customer has not finished setting up
        # would be worse than accepting it.
        if definition.field_type in ('url', 'email') and value:
            CustomFieldService._check_shape(definition, value)

        return value

    @staticmethod
    def _check_shape(definition, value):
        from django.core.exceptions import ValidationError
        from django.core.validators import EmailValidator, URLValidator

        validator = URLValidator() if definition.field_type == 'url' else EmailValidator()
        try:
            validator(value)
        except ValidationError:
            kind = 'URL' if definition.field_type == 'url' else 'email address'
            raise CoercionError(f'{definition.name} must be a valid {kind}.')

    @staticmethod
    def merge(organization, existing, incoming, *, partial=True):
        """
        Validate `incoming` and merge it over `existing`.

        Merging rather than replacing: a caller that sends one custom field
        means to set that one, not to clear the rest. Replacement is what let a
        single-column CSV wipe everything else a contact held.
        """
        cleaned = CustomFieldService.validate_and_coerce(
            organization, incoming, partial=partial,
        )
        return {**(existing or {}), **cleaned}

    @staticmethod
    def segment_fields(organization):
        """
        Definitions as the segment rule builder wants them: `custom.<key>` →
        {type, label, options}.

        The builder could not offer custom fields at all before — its field
        list was a module-level dict with no organization in scope — so a
        customer had to know to hand-write `custom.industry`.
        """
        fields = {}
        for key, definition in CustomFieldService.definitions(organization).items():
            entry = {
                'type': definition.spec_type,
                'label': definition.name,
                'custom': True,
            }
            if definition.dropdown_options:
                entry['options'] = list(definition.dropdown_options)
            fields[f'custom.{key}'] = entry
        return fields
