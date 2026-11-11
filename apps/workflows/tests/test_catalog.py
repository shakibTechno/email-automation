"""
The catalogue is the one list. These tests are what keep it that way.

Four node types once worked in the backend and were absent from the builder's
own copy of the list, so nobody could reach them — including two pop-up
triggers that shipped and sat unusable for a fortnight. Every test here exists
to make that class of mistake fail loudly instead of silently.
"""
from django.test import SimpleTestCase

from apps.workflows import catalog
from apps.workflows.definition import AssetResolver
from apps.workflows.models import WorkflowNode


class CatalogShapeTests(SimpleTestCase):
    def test_every_node_type_is_unique(self):
        types = [spec.type for spec in catalog.NODE_SPECS]
        self.assertEqual(len(types), len(set(types)))

    def test_every_node_type_is_named_by_its_category(self):
        """A node whose prefix lies breaks is_trigger/is_action on the model."""
        for spec in catalog.NODE_SPECS:
            with self.subTest(spec.type):
                self.assertTrue(spec.type.startswith(f'{spec.category}_'))

    def test_the_model_choices_come_from_the_catalogue(self):
        self.assertEqual(
            WorkflowNode.NODE_TYPE_CHOICES, catalog.NODE_TYPE_CHOICES
        )

    def test_every_node_type_fits_the_column(self):
        limit = WorkflowNode._meta.get_field('node_type').max_length
        for spec in catalog.NODE_SPECS:
            with self.subTest(spec.type):
                self.assertLessEqual(len(spec.type), limit)

    def test_every_model_constant_names_a_real_node_type(self):
        """A constant pointing at nothing is a handler that can never run."""
        for name in dir(WorkflowNode):
            if not name.startswith(('TRIGGER_', 'ACTION_', 'CONDITION_')):
                continue
            value = getattr(WorkflowNode, name)
            if not isinstance(value, str):
                continue
            with self.subTest(name):
                self.assertTrue(
                    catalog.exists(value),
                    f'WorkflowNode.{name} = {value!r} is not in the catalogue',
                )

    def test_every_asset_field_names_a_kind_the_resolver_knows(self):
        """
        An asset kind with no resolver cannot be re-pointed on import, so the
        id would survive from another account.
        """
        for spec in catalog.NODE_SPECS:
            for field in spec.asset_fields:
                with self.subTest(f'{spec.type}.{field.key}'):
                    self.assertIn(field.asset, AssetResolver.MODELS)

    def test_a_branching_node_declares_its_branches(self):
        for spec in catalog.NODE_SPECS:
            if spec.category != catalog.CONDITION:
                continue
            with self.subTest(spec.type):
                self.assertGreaterEqual(len(spec.branches), 1)

    def test_required_select_fields_offer_something_to_select(self):
        for spec in catalog.NODE_SPECS:
            for field in spec.config_fields:
                if field.type != 'select':
                    continue
                with self.subTest(f'{spec.type}.{field.key}'):
                    self.assertTrue(field.options)

    def test_a_dependent_field_depends_on_a_field_that_exists(self):
        for spec in catalog.NODE_SPECS:
            keys = {f.key for f in spec.config_fields}
            for field in spec.config_fields:
                if not field.depends_on:
                    continue
                with self.subTest(f'{spec.type}.{field.key}'):
                    self.assertIn(field.depends_on[0], keys)


class ExecutorCoverageTests(SimpleTestCase):
    """Every action in the catalogue must actually do something."""

    def _handlers(self):
        from apps.workflows.services import WorkflowExecutionService

        # The dispatch table is built inside _handle_node; reading it the same
        # way the executor does means this test cannot pass while the real
        # lookup fails.
        import inspect

        source = inspect.getsource(WorkflowExecutionService._handle_node)
        return {
            getattr(WorkflowNode, name)
            for name in dir(WorkflowNode)
            if name.startswith(('ACTION_', 'CONDITION_'))
            and isinstance(getattr(WorkflowNode, name), str)
            and f'WorkflowNode.{name}:' in source
        }

    def test_every_action_has_a_handler(self):
        handled = self._handlers()
        missing = sorted(catalog.ACTION_TYPES - handled)
        self.assertEqual(
            missing, [],
            f'These actions are offered in the builder and do nothing: {missing}',
        )

    def test_every_condition_has_a_handler(self):
        handled = self._handlers()
        missing = sorted(catalog.CONDITION_TYPES - handled)
        self.assertEqual(missing, [])


class TriggerCoverageTests(SimpleTestCase):
    """
    Every trigger must have something that fires it.

    This is the test that would have caught trigger_email_opened, which existed
    in the service, was offered in the builder, and was called from nowhere for
    the best part of a year.
    """

    def test_every_trigger_is_either_fired_or_polled(self):
        import inspect

        from apps.workflows import signals, tasks
        from apps.workflows.services import WorkflowTriggerService

        # Everywhere a trigger can be started from.
        haystack = '\n'.join([
            inspect.getsource(WorkflowTriggerService),
            inspect.getsource(signals),
            inspect.getsource(tasks),
        ])

        # Plus the other apps that call into us.
        for module_path in (
            'apps.crm.services', 'apps.tracking.services',
            'apps.lead_scoring.signals', 'apps.lead_scoring.services',
            'apps.campaigns.apps', 'apps.workflows.webhook_views',
        ):
            module = __import__(module_path, fromlist=['x'])
            haystack += '\n' + inspect.getsource(module)

        unreachable = []
        for spec in catalog.NODE_SPECS:
            if spec.category != catalog.TRIGGER:
                continue
            # The constant's name is how the firing code refers to it.
            constant = next(
                (
                    name for name in dir(WorkflowNode)
                    if name.startswith('TRIGGER_')
                    and getattr(WorkflowNode, name) == spec.type
                ),
                None,
            )
            if constant and f'WorkflowNode.{constant}' in haystack:
                continue
            unreachable.append(spec.type)

        self.assertEqual(
            unreachable, [],
            'These triggers are offered in the builder and nothing ever fires '
            f'them: {unreachable}',
        )


class SerialisationTests(SimpleTestCase):
    def test_the_catalogue_survives_json(self):
        import json

        payload = json.dumps(catalog.as_catalog())
        restored = json.loads(payload)
        self.assertEqual(len(restored), len(catalog.NODE_SPECS))

    def test_each_entry_carries_what_the_builder_needs(self):
        for entry in catalog.as_catalog():
            with self.subTest(entry['type']):
                for key in (
                    'type', 'category', 'label', 'description', 'icon', 'ui',
                    'terminal', 'branches', 'config_fields',
                ):
                    self.assertIn(key, entry)

    def test_a_custom_panel_is_only_claimed_where_one_exists(self):
        """
        `ui: 'custom'` tells the builder a hand-written panel owns this node.
        Claiming it for a node with no panel means an empty settings pane.
        """
        custom = {s.type for s in catalog.NODE_SPECS if s.ui == 'custom'}
        # The panels that exist, by what they cover.
        covered = (
            {t for t in custom if t.startswith('trigger_')}
            | {t for t in custom if t.startswith('action_')}
            | {t for t in custom if t.startswith('condition_')}
        )
        self.assertEqual(custom, covered)
