"""
Creating a pipeline and adding stages to it.

Both failed from the UI: the create response carried no id, so the client could
not address the pipeline it had just made, and a repeated stage name reached
the database as an IntegrityError.
"""
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, User
from apps.crm.models import Pipeline


class PipelineCreateTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.client.force_authenticate(user=self.user)

    def test_the_create_response_carries_the_id(self):
        """Without it the client cannot open or add a stage to what it made."""
        response = self.client.post(
            '/api/v1/pipelines/', {'name': 'Sales'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            str(response.data['id']), str(Pipeline.objects.get(name='Sales').id),
        )

    def test_the_created_stages_come_back_with_ids(self):
        response = self.client.post(
            '/api/v1/pipelines/',
            {'name': 'Sales', 'stages': [{'name': 'Lead'}, {'name': 'Won'}]},
            format='json',
        )

        stages = response.data['stages']
        self.assertEqual([s['name'] for s in stages], ['Lead', 'Won'])
        self.assertTrue(all(s.get('id') for s in stages))

    def test_two_stages_with_one_name_is_a_field_error(self):
        response = self.client.post(
            '/api/v1/pipelines/',
            {'name': 'Sales', 'stages': [{'name': 'Lead'}, {'name': 'lead'}]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Pipeline.objects.filter(name='Sales').exists())


class AddStageTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme Inc', slug='acme-inc')
        self.user = User.objects.create_user(
            email='owner@acme.test', password='x', organization=self.org,
            role='owner',
        )
        self.client.force_authenticate(user=self.user)
        self.pipeline = Pipeline.objects.create(
            organization=self.org, name='Sales', created_by=self.user,
        )

    def _add(self, name):
        return self.client.post(
            f'/api/v1/pipelines/{self.pipeline.id}/add_stage/',
            {'name': name}, format='json',
        )

    def test_a_stage_is_added_at_the_end(self):
        self._add('Lead')
        response = self._add('Demo booked')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            list(self.pipeline.stages.order_by('position')
                 .values_list('name', flat=True)),
            ['Lead', 'Demo booked'],
        )

    def test_a_repeated_name_is_refused_as_a_field_error(self):
        """It used to reach the database and come back as a 500."""
        self._add('Demo booked')
        response = self._add('Demo booked')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data.get('details', response.data))
        self.assertEqual(self.pipeline.stages.filter(name='Demo booked').count(), 1)

    def test_the_check_ignores_case(self):
        self._add('Demo booked')
        self.assertEqual(
            self._add('demo BOOKED').status_code, status.HTTP_400_BAD_REQUEST,
        )
