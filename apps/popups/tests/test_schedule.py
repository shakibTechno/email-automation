"""
Scheduled pop-ups becoming live.

The website script treats only `published` as live, so nothing shows until
this task runs -- which makes the task, not the start time, the thing that
has to be right.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Organization
from apps.popups.models import Popup
from apps.popups.tasks import publish_due_popups


class PublishDuePopupsTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')

    def _popup(self, **kwargs):
        return Popup.objects.create(
            organization=self.org, name='Offer', cta_text='Claim', **kwargs
        )

    def test_a_popup_whose_start_has_arrived_goes_live(self):
        popup = self._popup(
            status=Popup.STATUS_SCHEDULED,
            starts_at=timezone.now() - timedelta(minutes=1),
        )

        self.assertEqual(publish_due_popups(), 1)
        popup.refresh_from_db()
        self.assertEqual(popup.status, Popup.STATUS_PUBLISHED)
        self.assertTrue(popup.is_live())

    def test_one_still_in_the_future_is_left_alone(self):
        popup = self._popup(
            status=Popup.STATUS_SCHEDULED,
            starts_at=timezone.now() + timedelta(hours=1),
        )

        self.assertEqual(publish_due_popups(), 0)
        popup.refresh_from_db()
        self.assertEqual(popup.status, Popup.STATUS_SCHEDULED)

    def test_a_paused_popup_is_never_resurrected(self):
        """Pausing is a decision; a past start date must not undo it."""
        popup = self._popup(
            status=Popup.STATUS_PAUSED,
            starts_at=timezone.now() - timedelta(days=2),
        )

        publish_due_popups()
        popup.refresh_from_db()
        self.assertEqual(popup.status, Popup.STATUS_PAUSED)

    def test_a_draft_is_never_published_by_the_clock(self):
        popup = self._popup(
            status=Popup.STATUS_DRAFT,
            starts_at=timezone.now() - timedelta(days=2),
        )

        publish_due_popups()
        popup.refresh_from_db()
        self.assertEqual(popup.status, Popup.STATUS_DRAFT)

    def test_a_deleted_popup_stays_deleted(self):
        popup = self._popup(
            status=Popup.STATUS_SCHEDULED,
            starts_at=timezone.now() - timedelta(minutes=1),
        )
        popup.soft_delete()

        publish_due_popups()
        popup.refresh_from_db()
        self.assertEqual(popup.status, Popup.STATUS_SCHEDULED)

    def test_one_already_past_its_end_is_published_but_not_live(self):
        """
        Status and liveness are two questions. The task answers the first; the
        window still answers the second, so an expired pop-up never shows.
        """
        popup = self._popup(
            status=Popup.STATUS_SCHEDULED,
            starts_at=timezone.now() - timedelta(days=3),
            ends_at=timezone.now() - timedelta(days=1),
        )

        publish_due_popups()
        popup.refresh_from_db()
        self.assertEqual(popup.status, Popup.STATUS_PUBLISHED)
        self.assertFalse(popup.is_live())

    def test_running_it_twice_changes_nothing_the_second_time(self):
        self._popup(
            status=Popup.STATUS_SCHEDULED,
            starts_at=timezone.now() - timedelta(minutes=1),
        )

        publish_due_popups()
        self.assertEqual(publish_due_popups(), 0)
