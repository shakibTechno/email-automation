"""
Plan tier ranking, and the Business tier that every hand-written tuple omitted.

Organization.PLAN_CHOICES listed four tiers while billing.Plan had five, and
BillingService wrote 'business' into that column on upgrade. Django only
validates choices in full_clean(), which save() skips, so the value persisted —
and the gating tuples, written by hand at each call site, then excluded a tier
that sits *above* the one they were gating on.
"""
from django.test import TestCase

from apps.accounts.models import Organization, User
from apps.lead_scoring.permissions import LEAD_SCORING_MIN_PLAN, LeadScoringEnabled


class PlanRankTestCase(TestCase):
    def test_all_five_tiers_are_ranked_in_order(self):
        order = ['free', 'starter', 'professional', 'business', 'enterprise']
        ranks = [Organization.PLAN_RANK[p] for p in order]
        self.assertEqual(ranks, sorted(ranks), 'tiers must rank in ascending order')
        self.assertEqual(len(set(ranks)), len(order), 'each tier needs a distinct rank')

    def test_rank_covers_every_declared_choice(self):
        """A tier that exists but is unranked would silently fail every gate."""
        declared = {value for value, _ in Organization.PLAN_CHOICES}
        self.assertEqual(declared, set(Organization.PLAN_RANK))

    def test_plan_choices_match_the_billing_plan_tiers(self):
        """The drift between these two lists is what caused the bug."""
        from apps.billing.models import Plan
        self.assertEqual(
            {v for v, _ in Organization.PLAN_CHOICES},
            {v for v, _ in Plan.PLAN_TYPE_CHOICES},
        )

    def test_plan_at_least(self):
        org = Organization.objects.create(name='Mid Co', slug='mid-co', plan='professional')
        self.assertTrue(org.plan_at_least('free'))
        self.assertTrue(org.plan_at_least('professional'))
        self.assertFalse(org.plan_at_least('business'))
        self.assertFalse(org.plan_at_least('enterprise'))

    def test_an_unknown_plan_fails_closed(self):
        """A bad value in the column must deny features, not unlock them."""
        org = Organization.objects.create(name='Odd Co', slug='odd-co')
        org.plan = 'not-a-real-tier'
        self.assertFalse(org.plan_at_least('free'))


class BusinessTierGatingTestCase(TestCase):
    """The exact case that was failing: Business denied a Professional feature."""

    def _request_for(self, plan):
        org = Organization.objects.create(name=f'{plan} Co', slug=f'{plan}-co', plan=plan)
        user = User.objects.create_user(
            email=f'{plan}@test.co', password='x', organization=org, role='owner',
        )
        return type('R', (), {'user': user})()

    def test_business_passes_a_professional_gate(self):
        self.assertTrue(
            LeadScoringEnabled().has_permission(self._request_for('business'), None),
            'Business ranks above Professional and has lead scoring in its plan '
            'data — it was being denied a feature it pays for',
        )

    def test_the_other_tiers_are_gated_as_expected(self):
        expected = {
            'free': False,
            'starter': False,
            'professional': True,
            'business': True,
            'enterprise': True,
        }
        for plan, allowed in expected.items():
            with self.subTest(plan=plan):
                self.assertEqual(
                    LeadScoringEnabled().has_permission(self._request_for(plan), None),
                    allowed,
                )

    def test_the_nightly_task_selects_the_same_tiers_as_the_permission(self):
        """
        These drifted apart before: Business passed the API permission check but
        was excluded from the recalculation query, so its scores went stale
        while the feature looked enabled.
        """
        eligible = {
            plan for plan, rank in Organization.PLAN_RANK.items()
            if rank >= Organization.PLAN_RANK[LEAD_SCORING_MIN_PLAN]
        }
        for plan in Organization.PLAN_RANK:
            with self.subTest(plan=plan):
                permitted = LeadScoringEnabled().has_permission(
                    self._request_for(plan), None
                )
                self.assertEqual(plan in eligible, permitted)
