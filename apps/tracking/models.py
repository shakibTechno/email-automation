"""
Who visited a customer's website, and what they looked at.

Two tables, both denormalised onto `organization`. `PageView` in
apps/landing_pages has no organization FK and every analytics query there has
to reach through a join to scope by tenant; these are the highest-volume tables
in the project and will not repeat that.
"""
import uuid

from django.db import models

from apps.core.models import TimeStampedModel


class Visitor(TimeStampedModel):
    """
    One browser on one customer's website.

    `visitor_id` is minted client-side and kept in localStorage on the
    customer's own origin — first-party, so it is not blocked the way a
    third-party cookie from our domain would be. It is therefore
    client-controlled and forgeable, which bounds what it is allowed to do:
    a visitor is only ever linked to a contact by a server-side event (a form
    submission), never by anything the browser claims.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization', on_delete=models.CASCADE,
        related_name='web_visitors',
    )
    visitor_id = models.CharField(max_length=64)

    # Null until they identify themselves by submitting a form.
    contact = models.ForeignKey(
        'contacts.Contact', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='web_visits',
    )
    identified_at = models.DateTimeField(null=True, blank=True)

    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now_add=True)
    page_view_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'web_visitors'
        unique_together = [['organization', 'visitor_id']]
        indexes = [
            models.Index(fields=['organization', 'last_seen_at']),
            models.Index(fields=['contact']),
        ]

    def __str__(self):
        return f'{self.visitor_id} ({self.organization_id})'


class TrackedEvent(TimeStampedModel):
    """
    One thing a visitor did. Today that is always a page view.

    `event_type` is a column rather than a second table because a custom-event
    API is the obvious next ask and a migration is a worse answer than a char
    field. Nothing writes anything but 'pageview' yet.
    """
    EVENT_PAGEVIEW = 'pageview'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization', on_delete=models.CASCADE,
        related_name='web_events',
    )
    visitor = models.ForeignKey(
        Visitor, on_delete=models.CASCADE, related_name='events',
    )
    # Denormalised from the visitor and backfilled when they identify, so
    # "what did they read before they converted" is one query.
    contact = models.ForeignKey(
        'contacts.Contact', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='web_events',
    )

    event_type = models.CharField(max_length=30, default=EVENT_PAGEVIEW)
    # Truncated, never rejected: a 400 to a visitor's browser is invisible and
    # the event is lost either way. A URLField would discard a weird-but-real
    # address for nothing.
    url = models.CharField(max_length=2000, blank=True, default='')
    path = models.CharField(max_length=500, blank=True, default='')
    title = models.CharField(max_length=255, blank=True, default='')
    referrer = models.CharField(max_length=2000, blank=True, default='')

    occurred_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'web_events'
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['organization', 'occurred_at']),
            models.Index(fields=['visitor', 'occurred_at']),
            models.Index(fields=['contact', 'occurred_at']),
        ]

    def __str__(self):
        return f'{self.event_type} {self.path}'
