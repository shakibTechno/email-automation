"""
Custom roles, end to end: who may define one, what one may grant, and what a
member holding one can actually reach.

Every assertion here is about a status code from a routed endpoint rather than
about the registry, because a permission that is declared but not enforced is
the failure that matters.
"""
import uuid

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Organization, Role, User
from apps.campaigns.models import Campaign
from apps.contacts.models import Contact

ROLES_URL = '/api/v1/team/roles/'
PERMISSIONS_URL = '/api/v1/team/permissions/'
CONTACTS_URL = '/api/v1/contacts/'
CAMPAIGNS_URL = '/api/v1/campaigns/'
BILLING_URL = '/api/v1/billing/overview/'


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class RoleTestCaseMixin:
    def setUp(self):
        self.organization = Organization.objects.create(
            name='Acme', email='org@acme.test', plan='business'
        )
        self.owner = User.objects.create_user(
            email='owner@acme.test', password='pw', organization=self.organization,
            role='owner',
        )
        self.admin = User.objects.create_user(
            email='admin@acme.test', password='pw', organization=self.organization,
            role='admin',
        )

    def make_role(self, name, permissions):
        return Role.objects.create(
            organization=self.organization,
            name=name,
            slug=name.lower().replace(' ', '-'),
            permissions=permissions,
        )

    def member_with(self, role_slug, email='staff@acme.test'):
        return User.objects.create_user(
            email=email, password='pw', organization=self.organization,
            role=role_slug,
        )


class BuiltInRoleEnforcementTestCase(RoleTestCaseMixin, TestCase):
    """The presets still behave as they did before roles became data."""

    def test_a_member_can_create_a_contact_but_not_delete_one(self):
        member = self.member_with('member')
        client = client_for(member)

        created = client.post(
            CONTACTS_URL, {'email': 'lead@example.test'}, format='json'
        )
        self.assertEqual(created.status_code, 201)

        contact = Contact.objects.get(organization=self.organization)
        deleted = client.delete(f'{CONTACTS_URL}{contact.id}/')
        self.assertEqual(deleted.status_code, 403)

    def test_a_viewer_can_read_but_not_write(self):
        viewer = self.member_with('viewer')
        client = client_for(viewer)

        self.assertEqual(client.get(CONTACTS_URL).status_code, 200)
        self.assertEqual(
            client.post(
                CONTACTS_URL, {'email': 'lead@example.test'}, format='json'
            ).status_code,
            403,
        )

    def test_a_member_cannot_send_a_campaign(self):
        member = self.member_with('member')
        campaign = Campaign.objects.create(
            organization=self.organization, name='Newsletter',
            subject='Hi', created_by=self.owner,
        )
        response = client_for(member).post(f'{CAMPAIGNS_URL}{campaign.id}/send/')
        self.assertEqual(response.status_code, 403)

    def test_a_member_cannot_manage_the_team(self):
        member = self.member_with('member')
        client = client_for(member)
        # Listing members has always been open to the whole organization...
        self.assertEqual(client.get('/api/v1/team/members/').status_code, 200)
        # ...inviting has not.
        self.assertEqual(
            client.post(
                '/api/v1/team/invite/',
                {'email': 'new@acme.test', 'role': 'member'}, format='json',
            ).status_code,
            403,
        )

    def test_a_member_cannot_rewrite_the_organizations_email_settings(self):
        """
        This one is a tightening: PUT /email-config/ used to accept any
        member, which let a viewer replace the SMTP credentials the whole
        organization sends through.
        """
        member = self.member_with('member')
        client = client_for(member)
        self.assertEqual(client.get('/api/v1/email-config/').status_code, 200)
        self.assertEqual(
            client.put(
                '/api/v1/email-config/', {'from_name': 'Acme'}, format='json'
            ).status_code,
            403,
        )


class CustomRoleEnforcementTestCase(RoleTestCaseMixin, TestCase):
    def test_a_custom_role_grants_exactly_what_it_lists(self):
        role = self.make_role('Campaign Editor', [
            'campaigns.view', 'campaigns.create', 'campaigns.edit',
            'templates.view', 'analytics.view',
        ])
        editor = client_for(self.member_with(role.slug))

        self.assertEqual(editor.get(CAMPAIGNS_URL).status_code, 200)
        self.assertEqual(
            editor.post(
                CAMPAIGNS_URL,
                {'name': 'Promo', 'subject': 'Hello'}, format='json',
            ).status_code,
            201,
        )
        self.assertEqual(editor.get('/api/v1/analytics/').status_code, 200)

        # Not granted: contacts at all, and nothing destructive or billing.
        self.assertEqual(editor.get(CONTACTS_URL).status_code, 403)
        self.assertEqual(editor.get(BILLING_URL).status_code, 403)

        campaign = Campaign.objects.get(organization=self.organization)
        self.assertEqual(
            editor.delete(f'{CAMPAIGNS_URL}{campaign.id}/').status_code, 403
        )
        self.assertEqual(
            editor.post(f'{CAMPAIGNS_URL}{campaign.id}/send/').status_code, 403
        )

    def test_a_role_with_manage_can_send(self):
        role = self.make_role('Campaign Manager', [
            'campaigns.view', 'campaigns.create', 'campaigns.edit',
            'campaigns.manage',
        ])
        sender = client_for(self.member_with(role.slug))
        # A campaign that cannot be sent still proves the permission passed:
        # the refusal comes from the campaign's state, not from the role.
        campaign = Campaign.objects.create(
            organization=self.organization, name='Promo', subject='Hi',
            created_by=self.owner,
        )
        response = sender.post(f'{CAMPAIGNS_URL}{campaign.id}/send/')
        self.assertNotEqual(response.status_code, 403)

    def test_a_deleted_role_grants_nothing(self):
        role = self.make_role('Temp', ['contacts.view'])
        user = self.member_with(role.slug)
        self.assertEqual(client_for(user).get(CONTACTS_URL).status_code, 200)

        role.delete()
        # Reloaded, because permissions are cached on the user instance for
        # the life of a request and this test reuses one object across two.
        reloaded = User.objects.get(pk=user.pk)
        self.assertEqual(client_for(reloaded).get(CONTACTS_URL).status_code, 403)

    def test_an_unknown_role_slug_grants_nothing(self):
        user = self.member_with('made-up')
        self.assertEqual(client_for(user).get(CONTACTS_URL).status_code, 403)

    def test_the_owner_keeps_access_whatever_the_roles_say(self):
        self.assertEqual(client_for(self.owner).get(CONTACTS_URL).status_code, 200)
        # Not 200: with no subscription row the view answers 404. What matters
        # is that the owner is never the one refused.
        self.assertNotEqual(client_for(self.owner).get(BILLING_URL).status_code, 403)


class RoleManagementApiTestCase(RoleTestCaseMixin, TestCase):
    def test_an_admin_can_create_a_role(self):
        response = client_for(self.admin).post(ROLES_URL, {
            'name': 'Campaign Editor',
            'permissions': ['campaigns.view', 'campaigns.create'],
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['slug'], 'campaign-editor')
        self.assertEqual(response.data['member_count'], 0)
        self.assertTrue(
            Role.objects.filter(
                organization=self.organization, slug='campaign-editor'
            ).exists()
        )

    def test_a_member_cannot_create_a_role(self):
        member = self.member_with('member')
        response = client_for(member).post(ROLES_URL, {
            'name': 'Sneaky', 'permissions': ['contacts.view'],
        }, format='json')
        self.assertEqual(response.status_code, 403)

    def test_the_permission_catalog_is_readable_by_the_whole_organization(self):
        response = client_for(self.member_with('viewer')).get(PERMISSIONS_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.data['resources']), len(__import__(
                'apps.core.access', fromlist=['RESOURCES']
            ).RESOURCES)
        )

    def test_a_role_cannot_be_named_after_a_built_in(self):
        response = client_for(self.admin).post(ROLES_URL, {
            'name': 'Admin', 'permissions': ['contacts.view'],
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.data['details'])

    def test_two_roles_cannot_share_a_name(self):
        self.make_role('Editor', ['contacts.view'])
        response = client_for(self.admin).post(ROLES_URL, {
            'name': 'editor', 'permissions': ['contacts.view'],
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_unknown_permission_codes_are_refused(self):
        response = client_for(self.admin).post(ROLES_URL, {
            'name': 'Wrong', 'permissions': ['contacts.view', 'contacts.explode'],
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('permissions', response.data['details'])

    def test_nobody_can_grant_a_permission_they_do_not_hold(self):
        """
        The only way to reach this endpoint is to hold team.manage, which a
        custom role can carry without carrying everything else.
        """
        limited = self.make_role('Team Lead', ['team.view', 'team.manage'])
        lead = client_for(self.member_with(limited.slug))

        response = lead.post(ROLES_URL, {
            'name': 'Escalated', 'permissions': ['billing.manage'],
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Role.objects.filter(slug='escalated').exists())

        allowed = lead.post(ROLES_URL, {
            'name': 'Team Reader', 'permissions': ['team.view'],
        }, format='json')
        self.assertEqual(allowed.status_code, 201)

    def test_a_rename_keeps_the_slug_so_members_keep_their_access(self):
        role = self.make_role('Editor', ['contacts.view'])
        user = self.member_with(role.slug)

        response = client_for(self.admin).patch(
            f'{ROLES_URL}{role.id}/', {'name': 'Content Editor'}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['slug'], 'editor')
        self.assertEqual(client_for(user).get(CONTACTS_URL).status_code, 200)

    def test_editing_permissions_takes_effect(self):
        role = self.make_role('Editor', ['contacts.view'])
        user = self.member_with(role.slug)

        client_for(self.admin).patch(f'{ROLES_URL}{role.id}/', {
            'permissions': ['contacts.view', 'contacts.create'],
        }, format='json')

        response = client_for(user).post(
            CONTACTS_URL, {'email': 'lead@example.test'}, format='json'
        )
        self.assertEqual(response.status_code, 201)

    def test_a_role_in_use_cannot_be_deleted(self):
        role = self.make_role('Editor', ['contacts.view'])
        self.member_with(role.slug)

        response = client_for(self.admin).delete(f'{ROLES_URL}{role.id}/')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Role.objects.filter(pk=role.pk).exists())

    def test_an_unused_role_can_be_deleted(self):
        role = self.make_role('Editor', ['contacts.view'])
        response = client_for(self.admin).delete(f'{ROLES_URL}{role.id}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Role.objects.filter(pk=role.pk).exists())

    def test_another_organizations_role_is_not_reachable(self):
        other = Organization.objects.create(name='Other', email='o@other.test')
        stranger = Role.objects.create(
            organization=other, name='Theirs', slug='theirs',
            permissions=['contacts.view'],
        )
        response = client_for(self.admin).patch(
            f'{ROLES_URL}{stranger.id}/', {'name': 'Mine'}, format='json'
        )
        self.assertEqual(response.status_code, 404)

    def test_a_missing_role_is_a_404(self):
        response = client_for(self.admin).delete(f'{ROLES_URL}{uuid.uuid4()}/')
        self.assertEqual(response.status_code, 404)


class RoleAssignmentTestCase(RoleTestCaseMixin, TestCase):
    def test_a_member_can_be_moved_to_a_custom_role(self):
        role = self.make_role('Editor', ['contacts.view'])
        member = self.member_with('member')

        response = client_for(self.admin).patch(
            f'/api/v1/team/members/{member.id}/role/',
            {'role': role.slug}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        member.refresh_from_db()
        self.assertEqual(member.role, role.slug)

    def test_a_role_that_does_not_exist_cannot_be_assigned(self):
        member = self.member_with('member')
        response = client_for(self.admin).patch(
            f'/api/v1/team/members/{member.id}/role/',
            {'role': 'invented'}, format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_another_organizations_role_cannot_be_assigned(self):
        other = Organization.objects.create(name='Other', email='o@other.test')
        Role.objects.create(
            organization=other, name='Theirs', slug='theirs',
            permissions=['contacts.view'],
        )
        member = self.member_with('member')
        response = client_for(self.admin).patch(
            f'/api/v1/team/members/{member.id}/role/',
            {'role': 'theirs'}, format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_ownership_is_not_assignable(self):
        member = self.member_with('member')
        response = client_for(self.admin).patch(
            f'/api/v1/team/members/{member.id}/role/',
            {'role': 'owner'}, format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_an_invitation_can_carry_a_custom_role(self):
        role = self.make_role('Editor', ['contacts.view'])
        response = client_for(self.admin).post('/api/v1/team/invite/', {
            'email': 'new@acme.test', 'role': role.slug,
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['role'], role.slug)
        self.assertEqual(response.data['role_name'], 'Editor')


class RolesAreNotAPlanFeatureTestCase(RoleTestCaseMixin, TestCase):
    """
    Deciding who on your team may delete contacts or send a campaign is how an
    account stays safe, so it is not withheld from any plan.
    """

    def test_a_free_plan_can_define_and_use_a_role(self):
        self.organization.plan = 'free'
        self.organization.save(update_fields=['plan'])

        created = client_for(self.admin).post(ROLES_URL, {
            'name': 'Editor', 'permissions': ['contacts.view'],
        }, format='json')
        self.assertEqual(created.status_code, 201)

        user = self.member_with(created.data['slug'])
        self.assertEqual(client_for(user).get(CONTACTS_URL).status_code, 200)
        self.assertEqual(client_for(user).get(CAMPAIGNS_URL).status_code, 403)

    def test_a_free_plan_can_edit_and_delete_a_role(self):
        self.organization.plan = 'free'
        self.organization.save(update_fields=['plan'])
        role = self.make_role('Editor', ['contacts.view'])

        edited = client_for(self.admin).patch(f'{ROLES_URL}{role.id}/', {
            'permissions': ['contacts.view', 'contacts.create'],
        }, format='json')
        self.assertEqual(edited.status_code, 200)

        removed = client_for(self.admin).delete(f'{ROLES_URL}{role.id}/')
        self.assertEqual(removed.status_code, 204)
