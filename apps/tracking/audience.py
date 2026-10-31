"""
Who the visitor is, as far as targeting needs to know.

The website script is one response cached for a whole organization, so it
cannot carry anything about an individual. Targeting on a contact's properties,
tags or segments therefore needs a second, per-visitor call — and that call is
the reason this file exists rather than the rules living in the script config.

Two rules of its own:

* **Booleans only.** Whatever this returns, the visitor can read. It answers
  "are you in segment X" for segments a popup already names, never "which
  segments are you in". Handing a browser the list would publish an
  organization's audience structure to anyone who opened dev tools.
* **Only what is asked for.** The questions come from the popups themselves,
  so an organization that targets nothing exposes nothing.
"""
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_SECONDS = 120


def questions_for(organization):
    """
    The segments, tags and contact fields this organization's popups target.

    Derived from the popups rather than configured, so the answer set shrinks
    the moment a rule is removed.
    """
    from apps.popups.models import Popup

    segments, tags, fields = set(), set(), set()
    live = Popup.objects.filter(
        organization=organization, deleted_at__isnull=True,
    ).values_list('targeting', flat=True)

    for targeting in live:
        audience = (targeting or {}).get('audience') or {}
        segments.update(str(s) for s in audience.get('segments', []))
        tags.update(str(t) for t in audience.get('tags', []))
        for rule in audience.get('contactFields', []):
            if isinstance(rule, dict) and rule.get('field'):
                fields.add((rule['field'], rule.get('operator', 'is_not_empty'),
                            str(rule.get('value', ''))))
    return {'segments': segments, 'tags': tags, 'fields': fields}


def answer(organization, visitor_key):
    """
    `{segments: {id: bool}, tags: {id: bool}, fields: {key: bool}, known: bool}`

    `known` is false for a visitor we have never tied to a contact, which is
    most of them. A popup targeting contact properties simply does not show to
    those, which is the honest answer rather than a guess.
    """
    asked = questions_for(organization)
    empty = {'segments': {}, 'tags': {}, 'fields': {}, 'known': False}
    if not (asked['segments'] or asked['tags'] or asked['fields']):
        return empty

    cache_key = f'trk:aud:{organization.id}:{visitor_key}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    contact = _contact_for(organization, visitor_key)
    if contact is None:
        cache.set(cache_key, empty, CACHE_SECONDS)
        return empty

    # One query for every tag asked about rather than one each: the browser
    # waits on this call before it may draw anything.
    held = set(
        str(t) for t in contact.contact_tags
        .filter(tag_id__in=asked['tags'])
        .values_list('tag_id', flat=True)
    )

    result = {
        'known': True,
        'tags': {tag_id: tag_id in held for tag_id in asked['tags']},
        'segments': {
            segment_id: _in_segment(contact, segment_id)
            for segment_id in asked['segments']
        },
        'fields': {
            f'{field}:{operator}:{value}': _field_matches(contact, field, operator, value)
            for field, operator, value in asked['fields']
        },
    }
    cache.set(cache_key, result, CACHE_SECONDS)
    return result


def _contact_for(organization, visitor_key):
    from .models import Visitor

    visitor = (
        Visitor.objects
        .filter(organization=organization, visitor_id=visitor_key)
        .select_related('contact')
        .first()
    )
    return visitor.contact if visitor else None


def _in_segment(contact, segment_id):
    try:
        from apps.segments.evaluator import SegmentEvaluator
        from apps.segments.models import Segment

        segment = Segment.objects.filter(
            id=segment_id, organization=contact.organization,
        ).first()
        if segment is None:
            return False
        return SegmentEvaluator.contact_matches_segment(contact, segment)
    except Exception:
        logger.exception('Could not evaluate segment %s', segment_id)
        return False


def _field_matches(contact, field, operator, value):
    """One contact-property rule, using the operators segments already define."""
    try:
        from apps.contacts import fields as contact_fields

        if contact_fields.is_custom_target(field):
            actual = (contact.custom_fields or {}).get(
                contact_fields.custom_key(field)
            )
        else:
            actual = getattr(contact, field, None)

        text = '' if actual is None else str(actual)
        if operator == 'is_not_empty':
            return bool(text.strip())
        if operator == 'is_empty':
            return not text.strip()
        if operator == 'equals':
            return text.lower() == value.lower()
        if operator == 'not_equals':
            return text.lower() != value.lower()
        if operator == 'contains':
            return value.lower() in text.lower()
        return False
    except Exception:
        logger.exception('Could not evaluate contact field %s', field)
        return False


def country_for(request):
    """
    The visitor's country, or None.

    Needs a MaxMind GeoLite2 database on disk and `GEOIP_PATH` pointing at it.
    Without one this returns None, and a popup with a location rule does not
    show -- the alternative, treating "unknown" as a match, would show an
    Ireland-only offer to the whole world.
    """
    if not getattr(settings, 'GEOIP_PATH', None):
        return None

    ip = _client_ip(request)
    if not ip:
        return None

    cache_key = f'trk:geo:{ip}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached or None

    try:
        from django.contrib.gis.geoip2 import GeoIP2

        country = (GeoIP2().country(ip) or {}).get('country_code') or ''
    except Exception:
        # A missing database or an address not in it are both "we do not know".
        logger.debug('No geo lookup for %s', ip, exc_info=True)
        country = ''

    cache.set(cache_key, country, 24 * 3600)
    return country or None


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
