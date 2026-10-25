"""
Adding steps to a sequence.

Adding a step did not work, and the way it failed is the interesting part: the
*first* step always saved and every one after it always failed with 400.

`SequenceStep.Meta.unique_together` is `[['sequence', 'position']]` and
`position` was a writable serializer field defaulting to 0, so DRF's
auto-generated uniqueness validator checked `(sequence, 0)` — the position the
first step already occupied — and rejected the request before
`perform_create` could assign the real one. None of it reached the user,
because the frontend mutations had `onSuccess` and no `onError`.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.sequences.models import EmailSequence, SequenceStep


class AddStepTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Mine', slug='mine')
        self.other = Organization.objects.create(name='Theirs', slug='theirs')
        self.user = User.objects.create_user(
            email='me@mine.test', password='x', organization=self.org, role='owner',
        )
        self.sequence = EmailSequence.objects.create(
            organization=self.org, name='Welcome', created_by=self.user,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def _add(self, **payload):
        payload.setdefault('sequence', str(self.sequence.id))
        payload.setdefault('subject', 'Hello')
        return self.api.post('/api/v1/sequence-steps/', payload, format='json')

    # ------------------------------------------------------------- the bug
    def test_a_second_step_can_be_added(self):
        """The failure itself. One step worked; two never did."""
        self.assertEqual(self._add(subject='One').status_code, 201)

        response = self._add(subject='Two')

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.sequence.steps.count(), 2)

    def test_many_steps_get_consecutive_positions(self):
        for n in range(5):
            self.assertEqual(self._add(subject=f'Step {n}').status_code, 201)

        positions = list(
            self.sequence.steps.order_by('position').values_list('position', flat=True)
        )
        self.assertEqual(positions, [0, 1, 2, 3, 4])

    def test_a_step_can_be_added_after_one_is_deleted_from_the_middle(self):
        """
        The second bug on the same line. `position` was `steps.count()`, so
        after deleting a middle step the count pointed at a position that was
        still occupied — the next create hit the unique constraint as an
        IntegrityError 500.
        """
        ids = [self._add(subject=f'Step {n}').data['id'] for n in range(3)]
        self.api.delete(f'/api/v1/sequence-steps/{ids[1]}/')

        response = self._add(subject='After the gap')

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(
            sorted(self.sequence.steps.values_list('position', flat=True)), [0, 2, 3],
        )

    # ------------------------------------------------- who owns the position
    def test_a_client_cannot_choose_the_position(self):
        """
        Appending is the server's decision, and reordering has its own
        endpoint. Honouring a submitted position would also put the uniqueness
        validator back in the path that broke this.
        """
        self._add(subject='One')

        response = self._add(subject='Queue jumper', position=0)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['position'], 1)

    # ----------------------------------------------------------- refusals
    def test_a_missing_sequence_is_a_400_not_a_500(self):
        """
        The viewset used to read the id from request.data and look it up with
        an unguarded .get(), so this raised DoesNotExist and answered 500.
        """
        response = self.api.post(
            '/api/v1/sequence-steps/', {'subject': 'Orphan'}, format='json',
        )

        self.assertEqual(response.status_code, 400)

    def test_an_unknown_sequence_is_a_400(self):
        response = self._add(sequence='00000000-0000-0000-0000-000000000000')

        self.assertEqual(response.status_code, 400)

    def test_a_step_cannot_be_added_to_another_tenants_sequence(self):
        theirs = EmailSequence.objects.create(organization=self.other, name='Theirs')

        response = self._add(sequence=str(theirs.id))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(theirs.steps.count(), 0)

    def test_a_subject_is_required(self):
        response = self.api.post(
            '/api/v1/sequence-steps/',
            {'sequence': str(self.sequence.id)},
            format='json',
        )

        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------- reading
    def test_the_response_names_the_sequence_it_belongs_to(self):
        """
        `sequence` was absent from the serializer's fields entirely, so the
        step came back with no indication of what it was attached to.
        """
        response = self._add()

        self.assertEqual(str(response.data['sequence']), str(self.sequence.id))

    def test_the_delay_is_summarised_in_hours(self):
        response = self._add(delay_days=2, delay_hours=3)

        self.assertEqual(response.data['total_delay_hours'], 51)

    def test_steps_are_scoped_to_the_callers_organization(self):
        theirs = EmailSequence.objects.create(organization=self.other, name='Theirs')
        SequenceStep.objects.create(sequence=theirs, subject='Hidden', position=0)
        self._add(subject='Mine')

        listing = self.api.get('/api/v1/sequence-steps/')

        subjects = [row['subject'] for row in listing.data['results']]
        self.assertEqual(subjects, ['Mine'])
