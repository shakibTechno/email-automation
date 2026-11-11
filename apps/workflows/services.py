"""
Services for the Workflow Automation app.
"""
import logging
import re
import requests
from datetime import timedelta
from datetime import timezone as dt_timezone

from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Q
from django.db.models.functions import Greatest

from . import catalog
from .models import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowTemplate,
)
from apps.contacts.models import Contact, Tag, ContactTag
from apps.contacts import fields as contact_fields
from apps.templates.models import EmailTemplate
from apps.forms.models import Form

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service class for workflow management operations."""

    @staticmethod
    def validate_workflow(workflow):
        """
        Validate a workflow and return a list of errors.
        Returns empty list if workflow is valid.
        """
        errors = []
        nodes = list(workflow.nodes.all())
        edges = list(workflow.edges.all())

        if not nodes:
            errors.append("Workflow must have at least one node.")
            return errors

        # Check for at least one trigger
        triggers = [n for n in nodes if n.is_trigger]
        if not triggers:
            errors.append("Workflow must have at least one trigger node.")

        # Check that non-trigger nodes have incoming edges
        node_ids = {str(n.id) for n in nodes}
        targets_with_edges = {str(e.target_node_id) for e in edges}

        for node in nodes:
            if not node.is_trigger:
                if str(node.id) not in targets_with_edges:
                    label = node.label or node.get_node_type_display()
                    errors.append(f"Node '{label}' has no incoming connections.")

        # Validate node configurations
        for node in nodes:
            node_errors = WorkflowService._validate_node_config(node)
            errors.extend(node_errors)

        return errors

    @staticmethod
    def _validate_node_config(node):
        """Validate a single node's configuration."""
        errors = []
        config = node.config or {}
        label = node.label or node.get_node_type_display()

        # Trigger validations
        if node.node_type == WorkflowNode.TRIGGER_FORM_SUBMISSION:
            if not config.get('form_id'):
                errors.append(f"Node '{label}': Form must be selected.")

        elif node.node_type in (WorkflowNode.TRIGGER_TAG_ADDED, WorkflowNode.TRIGGER_TAG_REMOVED):
            if not config.get('tag_id'):
                errors.append(f"Node '{label}': Tag must be selected.")

        elif node.node_type == WorkflowNode.TRIGGER_DATE_FIELD:
            if not config.get('field_name'):
                errors.append(f"Node '{label}': Date field must be specified.")

        # Action validations
        elif node.node_type == WorkflowNode.ACTION_SEND_EMAIL:
            if not config.get('template_id'):
                errors.append(f"Node '{label}': Email template must be selected.")

        elif node.node_type in (WorkflowNode.ACTION_ADD_TAG, WorkflowNode.ACTION_REMOVE_TAG):
            if not config.get('tag_id'):
                errors.append(f"Node '{label}': Tag must be selected.")

        elif node.node_type == WorkflowNode.ACTION_UPDATE_CONTACT:
            if not config.get('field'):
                errors.append(f"Node '{label}': Contact field must be specified.")
            if not config.get('operation'):
                errors.append(f"Node '{label}': Operation must be specified.")

        elif node.node_type == WorkflowNode.ACTION_WAIT:
            if not config.get('duration'):
                errors.append(f"Node '{label}': Wait duration must be specified.")

        elif node.node_type == WorkflowNode.ACTION_WEBHOOK:
            if not config.get('url'):
                errors.append(f"Node '{label}': Webhook URL must be specified.")

        # Condition validations
        elif node.node_type == WorkflowNode.CONDITION_IF_ELSE:
            rules = config.get('rules', [])
            if not rules:
                errors.append(f"Node '{label}': At least one condition rule is required.")

        # Lead scoring validations
        elif node.node_type == WorkflowNode.TRIGGER_LEAD_SCORE_THRESHOLD:
            if config.get('threshold_value') is None:
                errors.append(f"Node '{label}': Threshold value must be specified.")
            if config.get('direction') not in ('above', 'below', 'equals', None):
                errors.append(f"Node '{label}': Direction must be above, below, or equals.")

        elif node.node_type == WorkflowNode.ACTION_UPDATE_LEAD_SCORE:
            if not config.get('points'):
                errors.append(f"Node '{label}': Points value must be specified.")
            if config.get('operation') not in ('add', 'subtract', 'set', None):
                errors.append(f"Node '{label}': Operation must be add, subtract, or set.")

        elif node.node_type == WorkflowNode.ACTION_UPDATE_DEAL:
            if not config.get('field'):
                errors.append(f"Node '{label}': Deal field must be specified.")

        return errors

    @staticmethod
    def activate_workflow(workflow):
        """Activate a workflow after validation."""
        errors = WorkflowService.validate_workflow(workflow)
        if errors:
            return False, errors

        workflow.status = 'active'
        workflow.activated_at = timezone.now()
        workflow.save(update_fields=['status', 'activated_at', 'updated_at'])

        # Take the "who is in it now" picture before anything can fire, so
        # switching on a segment-triggered workflow does not read every
        # existing member as a new arrival.
        try:
            WorkflowTriggerService.seed_segment_watch(workflow)
        except Exception:
            logger.exception(
                'Could not seed the segment watch for workflow %s', workflow.id
            )
        return True, []

    @staticmethod
    def deactivate_workflow(workflow):
        """Pause/deactivate a workflow."""
        workflow.status = 'paused'
        workflow.save(update_fields=['status', 'updated_at'])
        return True

    @staticmethod
    def duplicate_workflow(workflow, user=None):
        """Create a copy of a workflow with all nodes and edges."""
        with transaction.atomic():
            # Clone workflow
            new_workflow = Workflow.objects.create(
                organization=workflow.organization,
                name=f"{workflow.name} (Copy)",
                description=workflow.description,
                status='draft',
                canvas_data=workflow.canvas_data.copy() if workflow.canvas_data else {},
                goal_node_id='',
                goal_description=workflow.goal_description,
                created_by=user,
            )

            # Map old node IDs to new nodes
            node_mapping = {}

            # Clone nodes
            for node in workflow.nodes.all():
                new_node = WorkflowNode.objects.create(
                    workflow=new_workflow,
                    node_type=node.node_type,
                    position_x=node.position_x,
                    position_y=node.position_y,
                    config=node.config.copy() if node.config else {},
                    label=node.label,
                )
                node_mapping[str(node.id)] = new_node

            # Clone edges with new node references
            for edge in workflow.edges.all():
                source_new = node_mapping.get(str(edge.source_node_id))
                target_new = node_mapping.get(str(edge.target_node_id))
                if source_new and target_new:
                    WorkflowEdge.objects.create(
                        workflow=new_workflow,
                        source_node=source_new,
                        target_node=target_new,
                        edge_type=edge.edge_type,
                        source_handle=edge.source_handle,
                        target_handle=edge.target_handle,
                    )

            # Update goal node ID if set
            if workflow.goal_node_id and workflow.goal_node_id in node_mapping:
                new_workflow.goal_node_id = str(node_mapping[workflow.goal_node_id].id)
                new_workflow.save(update_fields=['goal_node_id'])

            return new_workflow

    @staticmethod
    def get_workflow_analytics(workflow, days=30):
        """Get workflow analytics for the specified time period."""
        from_date = timezone.now() - timedelta(days=days)

        executions = workflow.executions.filter(started_at__gte=from_date)

        return {
            'total_entered': executions.count(),
            'active': executions.filter(status='active').count(),
            'waiting': executions.filter(status='waiting').count(),
            'completed': executions.filter(status='completed').count(),
            'failed': executions.filter(status='failed').count(),
            'goal_reached': executions.filter(goal_reached=True).count(),
            'period_days': days,
        }

    @staticmethod
    def create_from_template(template, organization, user=None):
        """
        Create a new workflow from a template.

        Goes through the same builder as import and AI generation, so a
        template's node ids and asset references are re-pointed at this
        account exactly as an imported file's are. Before that, this wrote
        node_type and config straight through -- fine for a template whose
        data we author, and the reason an import could not reuse it.
        """
        from . import definition

        template_data = template.template_data or {}
        payload = {
            'format': definition.FORMAT,
            'version': definition.VERSION,
            'workflow': {
                'name': template.name,
                'description': template.description,
            },
            'canvas': template_data.get('canvas', {}),
            'nodes': template_data.get('nodes', []),
            'edges': template_data.get('edges', []),
        }

        workflow, report = definition.build_from_definition(
            organization, payload, user=user,
        )
        if report['unresolved']:
            # A system template names assets by kind, not by id, so anything
            # unplaced here is something this account has not created yet.
            logger.info(
                'Template %s needs attention in: %s',
                template.name, ', '.join(report['needs_attention']),
            )

        WorkflowTemplate.objects.filter(pk=template.pk).update(
            usage_count=F('usage_count') + 1
        )
        return workflow


class WorkflowExecutionService:
    """Service class for workflow execution operations."""

    @staticmethod
    def refusal_to_enter(workflow, contact):
        """
        Why this contact may not enter, or None if they may.

        A sentence rather than a boolean so the log says which rule stopped
        them: "did not enter" with no reason is the support ticket this
        avoids.
        """
        if workflow.entry_segment_id:
            from apps.segments.evaluator import SegmentEvaluator

            if not SegmentEvaluator.contact_matches_segment(
                contact, workflow.entry_segment
            ):
                return 'does not match the entry segment'

        runs = WorkflowExecution.objects.filter(workflow=workflow, contact=contact)

        if workflow.reentry == Workflow.REENTRY_ONCE:
            if runs.exists():
                return 'has already been through this workflow once'
        elif workflow.reentry == Workflow.REENTRY_ONE_AT_A_TIME:
            if runs.filter(status__in=('active', 'waiting')).exists():
                return 'is already part-way through this workflow'

        if workflow.reentry_cooldown_days:
            cutoff = timezone.now() - timedelta(days=workflow.reentry_cooldown_days)
            if runs.filter(started_at__gte=cutoff).exists():
                return (
                    f'entered within the last {workflow.reentry_cooldown_days} '
                    f'day(s)'
                )
        return None

    @staticmethod
    def start_execution(workflow, contact, trigger_data=None):
        """Start a new workflow execution for a contact."""
        refusal = WorkflowExecutionService.refusal_to_enter(workflow, contact)
        if refusal:
            logger.info(
                f"Contact {contact.email} not entering {workflow.name}: {refusal}"
            )
            return None

        # Find the first trigger node
        trigger_node = workflow.nodes.filter(
            node_type__startswith='trigger_'
        ).first()

        if not trigger_node:
            logger.error(f"Workflow {workflow.name} has no trigger node")
            return None

        # Create execution
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            contact=contact,
            status='active',
            current_node=trigger_node,
            trigger_data=trigger_data or {},
        )

        # Update workflow stats
        Workflow.objects.filter(id=workflow.id).update(
            contacts_entered=F('contacts_entered') + 1,
            contacts_active=F('contacts_active') + 1,
        )

        logger.info(
            f"Started workflow execution {execution.id} for "
            f"{contact.email} in {workflow.name}"
        )

        # Queue the first node execution
        WorkflowExecutionService._queue_node_execution(execution)

        return execution

    @staticmethod
    def _queue_node_execution(execution):
        """Queue a Celery task to execute the current node."""
        from .tasks import execute_workflow_node
        execute_workflow_node.delay(str(execution.id))

    # Nodes that put a message in front of a person. Only these are held back
    # by quiet hours -- delaying a tag or a score would change what the
    # workflow does, not when it is polite.
    OUTBOUND_NODES = (
        WorkflowNode.ACTION_SEND_EMAIL,
        WorkflowNode.ACTION_NOTIFY_TEAM,
    )

    @staticmethod
    def within_send_window(workflow, when=None):
        """Whether `when` falls inside the workflow's sending hours."""
        if not workflow.respect_quiet_hours:
            return True

        when = when or timezone.now()
        local = timezone.localtime(when)
        allowed_days = workflow.send_weekdays or []
        if allowed_days and local.weekday() not in allowed_days:
            return False

        start, end = workflow.send_window_start, workflow.send_window_end
        if start <= end:
            return start <= local.time() <= end
        # A window that wraps past midnight, e.g. 22:00-06:00.
        return local.time() >= start or local.time() <= end

    @staticmethod
    def next_send_slot(workflow, when=None):
        """The first moment from `when` that falls inside the sending hours."""
        when = when or timezone.now()
        if WorkflowExecutionService.within_send_window(workflow, when):
            return when

        candidate = timezone.localtime(when)
        # At most a fortnight of hops -- enough to clear any weekday rule, and
        # bounded so a nonsensical window cannot spin here.
        for _ in range(14 * 24):
            candidate += timedelta(hours=1)
            as_utc = candidate.astimezone(dt_timezone.utc)
            if WorkflowExecutionService.within_send_window(workflow, as_utc):
                return as_utc.replace(minute=0, second=0, microsecond=0)
        logger.warning(
            'Workflow %s has a sending window nothing falls inside; sending now.',
            workflow.id,
        )
        return when

    @staticmethod
    def goal_met(execution):
        """
        Whether this contact has done what the workflow was for.

        Checked before every step, so someone who converts stops being
        chased wherever they had got to. Reaching the goal *node* is the
        other way to get here and is handled by its own handler.
        """
        workflow = execution.workflow
        rules = workflow.goal_rules or {}
        if not (workflow.exit_on_goal and rules.get('rules')):
            return False
        return WorkflowExecutionService._rules_match(
            rules.get('rules', []), rules.get('logic', 'all'), execution,
        )

    @staticmethod
    def execute_node(execution):
        """Execute the current node in the workflow execution."""
        if execution.status not in ('active', 'waiting'):
            logger.warning(f"Execution {execution.id} is not active, skipping")
            return

        node = execution.current_node
        if not node:
            WorkflowExecutionService._complete_execution(execution)
            return

        if WorkflowExecutionService.goal_met(execution):
            logger.info(
                f"Execution {execution.id} met its goal before {node.node_type}; "
                f"leaving the workflow"
            )
            WorkflowExecutionService._mark_goal_reached(execution)
            WorkflowExecutionService._complete_execution(execution)
            return

        # Hold a message until the organization is willing to send one. The
        # step is not consumed: the same node runs again in the window.
        if node.node_type in WorkflowExecutionService.OUTBOUND_NODES:
            workflow = execution.workflow
            if not WorkflowExecutionService.within_send_window(workflow):
                resume_at = WorkflowExecutionService.next_send_slot(workflow)
                execution.status = 'waiting'
                execution.resume_at = resume_at
                execution.save(update_fields=['status', 'resume_at', 'updated_at'])
                logger.info(
                    f"Execution {execution.id} held outside sending hours until "
                    f"{resume_at.isoformat()}"
                )
                return

        # Create execution step
        step = WorkflowExecutionStep.objects.create(
            execution=execution,
            node=node,
            status='running',
            started_at=timezone.now(),
            input_data={
                'contact_id': str(execution.contact_id),
                'trigger_data': execution.trigger_data,
            }
        )

        try:
            result = WorkflowExecutionService._handle_node(execution, node)
            step.status = 'completed'
            step.completed_at = timezone.now()
            step.output_data = result.get('output', {})
            step.branch_taken = result.get('branch', '')
            step.save()

            # Handle wait nodes specially
            if result.get('wait'):
                execution.status = 'waiting'
                execution.resume_at = result['resume_at']
                execution.wait_deadline = result.get('deadline')
                execution.save(update_fields=[
                    'status', 'resume_at', 'wait_deadline', 'updated_at',
                ])
                return

            # Advance to next node
            WorkflowExecutionService._advance_to_next_node(execution, node, result)

        except Exception as e:
            logger.exception(f"Error executing node {node.id}: {e}")
            step.status = 'failed'
            step.error_message = str(e)
            step.completed_at = timezone.now()
            step.save()

            # Mark execution as failed after retries exceeded
            execution.retry_count += 1
            if execution.retry_count >= 3:
                execution.status = 'failed'
                execution.error_message = str(e)
                Workflow.objects.filter(id=execution.workflow_id).update(
                    contacts_active=Greatest(F('contacts_active') - 1, 0)
                )
                try:
                    from apps.notifications.services import NotificationService
                    workflow = execution.workflow
                    NotificationService.notify_org_admins(
                        organization=workflow.organization,
                        notification_type='workflow_failed',
                        title='Workflow execution failed',
                        message=f'An execution of "{workflow.name}" failed after 3 retries.',
                        data={
                            'workflow_id': str(workflow.id),
                            'execution_id': str(execution.id),
                        },
                    )
                except Exception:
                    pass
            execution.save()

    @staticmethod
    def _handle_node(execution, node):
        """Route to the appropriate node handler."""
        handlers = {
            WorkflowNode.ACTION_SEND_EMAIL: WorkflowExecutionService._handle_send_email,
            WorkflowNode.ACTION_ADD_TAG: WorkflowExecutionService._handle_add_tag,
            WorkflowNode.ACTION_REMOVE_TAG: WorkflowExecutionService._handle_remove_tag,
            WorkflowNode.ACTION_UPDATE_CONTACT: WorkflowExecutionService._handle_update_contact,
            WorkflowNode.ACTION_WAIT: WorkflowExecutionService._handle_wait,
            WorkflowNode.ACTION_WEBHOOK: WorkflowExecutionService._handle_webhook,
            WorkflowNode.ACTION_GOAL: WorkflowExecutionService._handle_goal,
            WorkflowNode.ACTION_UPDATE_LEAD_SCORE: WorkflowExecutionService._handle_update_lead_score,
            WorkflowNode.ACTION_UPDATE_DEAL: WorkflowExecutionService._handle_update_deal,
            WorkflowNode.CONDITION_IF_ELSE: WorkflowExecutionService._handle_condition,
            WorkflowNode.CONDITION_SWITCH: WorkflowExecutionService._handle_switch,
            WorkflowNode.CONDITION_SPLIT_TEST: WorkflowExecutionService._handle_split_test,
            WorkflowNode.ACTION_WAIT_UNTIL: WorkflowExecutionService._handle_wait_until,
            WorkflowNode.ACTION_ASSIGN_CONTACT: WorkflowExecutionService._handle_assign_contact,
            WorkflowNode.ACTION_ADD_TO_SEGMENT: WorkflowExecutionService._handle_add_to_segment,
            WorkflowNode.ACTION_REMOVE_FROM_SEGMENT: WorkflowExecutionService._handle_remove_from_segment,
            WorkflowNode.ACTION_ENROLL_SEQUENCE: WorkflowExecutionService._handle_enroll_sequence,
            WorkflowNode.ACTION_REMOVE_SEQUENCE: WorkflowExecutionService._handle_remove_sequence,
            WorkflowNode.ACTION_ENROLL_WORKFLOW: WorkflowExecutionService._handle_enroll_workflow,
            WorkflowNode.ACTION_REMOVE_FROM_WORKFLOW: WorkflowExecutionService._handle_remove_from_workflow,
            WorkflowNode.ACTION_CREATE_DEAL: WorkflowExecutionService._handle_create_deal,
            WorkflowNode.ACTION_CREATE_TASK: WorkflowExecutionService._handle_create_task,
            WorkflowNode.ACTION_ADD_NOTE: WorkflowExecutionService._handle_add_note,
            WorkflowNode.ACTION_NOTIFY_TEAM: WorkflowExecutionService._handle_notify_team,
            WorkflowNode.ACTION_UNSUBSCRIBE: WorkflowExecutionService._handle_unsubscribe,
            WorkflowNode.ACTION_END_FLOW: WorkflowExecutionService._handle_end_flow,
        }

        # Trigger nodes just pass through
        if node.is_trigger:
            return {'output': {'triggered': True}}

        handler = handlers.get(node.node_type)
        if handler:
            return handler(execution, node)

        logger.warning(f"No handler for node type: {node.node_type}")
        return {'output': {}}

    @staticmethod
    def _owned(execution, model, object_id, label):
        """
        One object named by node config, confirmed to belong to this account.

        Node config holds plain ids, and since a workflow can now arrive by
        import or be written by the generator, those ids are not necessarily
        ones this organization owns. An unscoped lookup here would act on
        another tenant's template, tag or deal.
        """
        if not object_id:
            return None
        organization_id = execution.workflow.organization_id
        found = model.objects.filter(
            id=object_id, organization_id=organization_id,
        ).first()
        if found is None:
            raise ValueError(
                f'{label} {object_id} does not exist in this account.'
            )
        return found

    @staticmethod
    def _handle_send_email(execution, node):
        """Send an email using the configured template."""
        config = node.config or {}
        template_id = config.get('template_id')
        subject_override = config.get('subject')

        if not template_id:
            raise ValueError("Email template not configured")

        template = WorkflowExecutionService._owned(
            execution, EmailTemplate, template_id, 'Email template'
        )

        contact = execution.contact
        html_content = WorkflowExecutionService._render_template(template, contact)
        subject = subject_override or template.subject or 'No Subject'

        # Replace merge tags in subject
        subject = WorkflowExecutionService._replace_merge_tags(subject, contact)

        # Send through the organization's own backend and from-address rather
        # than the platform default, so workflow mail comes from the same
        # verified domain as the organization's campaigns.
        from django.core.mail import EmailMultiAlternatives
        from apps.email_config.services import EmailConfigService

        organization = execution.workflow.organization
        identity = EmailConfigService.resolve(organization)
        if identity.unavailable:
            raise RuntimeError(identity.unavailable)
        from_email, reply_to = identity.sender()

        msg = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=from_email,
            to=[contact.email],
            reply_to=reply_to,
            connection=identity.connection,
        )
        msg.attach_alternative(html_content, 'text/html')
        msg.send(fail_silently=False)

        logger.info(f"Sent email to {contact.email} using template {template.name}")

        return {'output': {'email_sent': True, 'template_id': template_id}}

    @staticmethod
    def _render_template(template, contact):
        """Render email template with contact data."""
        html = template.html_content or ''
        return WorkflowExecutionService._replace_merge_tags(html, contact)

    @staticmethod
    def _replace_merge_tags(text, contact):
        """Replace merge tags with contact data."""
        merge_data = {
            'first_name': contact.first_name or '',
            'last_name': contact.last_name or '',
            'email': contact.email,
            'company': contact.company or '',
            'job_title': contact.job_title or '',
            'phone': contact.phone or '',
        }

        for key, value in merge_data.items():
            text = re.sub(
                r'\{\{\s*' + re.escape(key) + r'\s*\}\}',
                value,
                text
            )

        return text

    @staticmethod
    def _handle_add_tag(execution, node):
        """Add a tag to the contact."""
        config = node.config or {}
        tag_id = config.get('tag_id')

        if not tag_id:
            raise ValueError("Tag not configured")

        tag = WorkflowExecutionService._owned(execution, Tag, tag_id, 'Tag')
        if not tag:
            raise ValueError(f"Tag {tag_id} not found")

        ContactTag.objects.get_or_create(
            contact=execution.contact,
            tag=tag,
        )

        logger.info(f"Added tag '{tag.name}' to {execution.contact.email}")

        return {'output': {'tag_added': tag.name}}

    @staticmethod
    def _handle_remove_tag(execution, node):
        """Remove a tag from the contact."""
        config = node.config or {}
        tag_id = config.get('tag_id')

        if not tag_id:
            raise ValueError("Tag not configured")

        deleted_count, _ = ContactTag.objects.filter(
            contact=execution.contact,
            tag_id=tag_id,
        ).delete()

        logger.info(f"Removed tag {tag_id} from {execution.contact.email}")

        return {'output': {'tag_removed': True, 'deleted': deleted_count > 0}}

    @staticmethod
    def _handle_update_contact(execution, node):
        """
        Update a field on the contact.

        Every branch here used to `setattr` whatever name the node config
        carried — `set` behind a `hasattr` check, and increment, decrement and
        append behind nothing at all. A node configured with
        `field: "organization_id"` therefore moved the contact into another
        tenant's organization, and `lead_score` could be written straight past
        the scoring engine that owns it.

        A name that is not a contact column is treated as a custom field, which
        is what this did before and is safe: it writes into the JSON column, not
        onto the model. A name that *is* a column but is not writable by a
        workflow is refused rather than quietly becoming a custom field, because
        silently storing "organization_id" as custom data would hide the mistake
        instead of reporting it.
        """
        config = node.config or {}
        field = config.get('field')
        operation = config.get('operation', 'set')
        value = config.get('value')

        if not field:
            raise ValueError("Contact field not configured")

        contact = execution.contact
        spec = contact_fields.CONTACT_FIELDS.get(field)
        explicit_custom = contact_fields.is_custom_target(field)

        if explicit_custom:
            target_is_column = False
            custom_name = contact_fields.custom_key(field)
        elif spec is not None or field in contact_fields.NEVER_WRITABLE:
            reason = contact_fields.rejection_reason(field, contact_fields.WORKFLOW)
            if reason:
                raise ValueError(reason)
            target_is_column = True
            custom_name = None
        else:
            target_is_column = False
            custom_name = field

        if target_is_column:
            WorkflowExecutionService._apply_column_update(contact, spec, operation, value)
        else:
            WorkflowExecutionService._apply_custom_update(
                contact, custom_name, operation, value,
            )

        contact.save()
        contact.update_activity()

        logger.info(f"Updated contact {contact.email}: {field} = {operation}({value})")

        return {'output': {'field': field, 'operation': operation}}

    @staticmethod
    def _apply_column_update(contact, spec, operation, value):
        """Apply an operation to a writable contact column."""
        if operation == 'set':
            setattr(contact, spec.key, contact_fields.coerce(spec.key, value))
            return

        if operation in ('increment', 'decrement'):
            # Arithmetic on a name only makes sense for a number, and doing it
            # anyway used to produce "Acme1" on a company field.
            if spec.type != 'number':
                raise ValueError(
                    f'"{spec.label}" is not a number, so it cannot be {operation}ed.'
                )
            step = int(value) if value else 1
            current = getattr(contact, spec.key, 0) or 0
            setattr(
                contact, spec.key,
                current + step if operation == 'increment' else current - step,
            )
            return

        if operation == 'append':
            current = getattr(contact, spec.key, '') or ''
            setattr(contact, spec.key, f"{current}{value}")
            return

        raise ValueError(f'Unknown update operation "{operation}".')

    @staticmethod
    def _apply_custom_update(contact, name, operation, value):
        """Apply an operation to a key in the contact's custom_fields."""
        custom = dict(contact.custom_fields or {})

        if operation == 'set':
            custom[name] = value
        elif operation in ('increment', 'decrement'):
            try:
                current = float(custom.get(name) or 0)
                step = float(value) if value else 1
            except (TypeError, ValueError):
                raise ValueError(f'"{name}" does not hold a number.')
            total = current + step if operation == 'increment' else current - step
            custom[name] = int(total) if total == int(total) else total
        elif operation == 'append':
            custom[name] = f"{custom.get(name) or ''}{value}"
        else:
            raise ValueError(f'Unknown update operation "{operation}".')

        contact.custom_fields = custom

    @staticmethod
    def _handle_wait(execution, node):
        """Set up a wait/delay before continuing."""
        config = node.config or {}
        duration = config.get('duration', 1)
        unit = config.get('unit', 'hours')

        # Calculate resume time
        if unit == 'minutes':
            delta = timedelta(minutes=duration)
        elif unit == 'hours':
            delta = timedelta(hours=duration)
        elif unit == 'days':
            delta = timedelta(days=duration)
        else:
            delta = timedelta(hours=duration)

        resume_at = timezone.now() + delta

        logger.info(f"Execution {execution.id} waiting until {resume_at}")

        return {
            'wait': True,
            'resume_at': resume_at,
            'output': {'duration': duration, 'unit': unit},
        }

    @staticmethod
    def _handle_webhook(execution, node):
        """Send a webhook request."""
        config = node.config or {}
        url = config.get('url')
        method = config.get('method', 'POST').upper()
        headers = config.get('headers', {})
        payload_template = config.get('payload_template', '{}')

        if not url:
            raise ValueError("Webhook URL not configured")

        contact = execution.contact

        # Build payload with contact data
        payload = {
            'workflow_id': str(execution.workflow_id),
            'execution_id': str(execution.id),
            'contact': {
                'id': str(contact.id),
                'email': contact.email,
                'first_name': contact.first_name,
                'last_name': contact.last_name,
                'company': contact.company,
            },
            'trigger_data': execution.trigger_data,
        }

        # Add authorization header if provided
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'

        try:
            if method == 'POST':
                response = requests.post(url, json=payload, headers=headers, timeout=30)
            elif method == 'GET':
                response = requests.get(url, params=payload, headers=headers, timeout=30)
            else:
                response = requests.request(method, url, json=payload, headers=headers, timeout=30)

            response.raise_for_status()

            logger.info(f"Webhook sent to {url}, status: {response.status_code}")

            return {
                'output': {
                    'url': url,
                    'status_code': response.status_code,
                    'success': True,
                }
            }

        except requests.RequestException as e:
            logger.error(f"Webhook failed: {e}")
            raise ValueError(f"Webhook request failed: {e}")

    @staticmethod
    def _mark_goal_reached(execution):
        """
        Record that this contact did what the workflow was for.

        Idempotent: reaching a goal node and then matching the workflow's goal
        rules must not count the same conversion twice.
        """
        if execution.goal_reached:
            return

        execution.goal_reached = True
        execution.goal_reached_at = timezone.now()
        execution.save(update_fields=['goal_reached', 'goal_reached_at', 'updated_at'])
        Workflow.objects.filter(id=execution.workflow_id).update(
            contacts_goal_reached=F('contacts_goal_reached') + 1
        )
        logger.info(f"Goal reached for execution {execution.id}")

    @staticmethod
    def _handle_goal(execution, node):
        """Mark the goal as reached."""
        WorkflowExecutionService._mark_goal_reached(execution)
        return {'output': {'goal_reached': True}}

    @staticmethod
    def _handle_update_lead_score(execution, node):
        """Add, subtract, or set a contact's lead score from within a workflow."""
        from apps.lead_scoring.services import LeadScoringService
        config = node.config or {}
        operation = config.get('operation', 'add')
        points = int(config.get('points', 0))
        note = config.get('note', f'Workflow: {execution.workflow.name}')

        contact = execution.contact
        if operation == 'add':
            delta = points
        elif operation == 'subtract':
            delta = -points
        else:  # 'set'
            delta = points - contact.lead_score

        new_score = LeadScoringService.manual_adjust(
            contact=contact,
            points_delta=delta,
            note=note,
            adjusted_by_user=None,
        )
        logger.info(
            f"Updated lead score for {contact.email}: {operation}({points}) → {new_score}"
        )
        return {'output': {'new_score': new_score, 'operation': operation}}

    @staticmethod
    def _handle_update_deal(execution, node):
        """Update a field on the deal from the execution trigger context."""
        from apps.crm.models import Deal, Stage
        config = node.config or {}
        field = config.get('field')
        value = config.get('value')

        deal_id = (execution.trigger_data or {}).get('deal_id')
        if not deal_id:
            logger.warning("_handle_update_deal: no deal_id in trigger_data")
            return {'output': {}}

        deal = Deal.objects.filter(
            id=deal_id, organization_id=execution.workflow.organization_id,
        ).first()
        if not deal:
            logger.warning(f"_handle_update_deal: deal {deal_id} not found")
            return {'output': {}}

        if field == 'stage':
            stage = Stage.objects.filter(pipeline=deal.pipeline, name=value).first()
            if stage:
                from apps.crm.services import DealService
                DealService.move_deal(deal, stage.id)
        elif field == 'assigned_to':
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.filter(
                id=value, organization_id=execution.workflow.organization_id,
            ).first()
            if user:
                deal.assigned_to = user
                deal.save(update_fields=['assigned_to'])
        elif field == 'priority' and value in ('low', 'medium', 'high'):
            deal.priority = value
            deal.save(update_fields=['priority'])

        logger.info(f"Updated deal {deal.title}: {field} = {value}")
        return {'output': {'field': field, 'value': value}}

    # Behavioural rule fields. Everything not listed here is a contact
    # property and is handed to SegmentEvaluator, which already knows all the
    # operators and all the types.
    BEHAVIOUR_FIELDS = (
        'event.email_opened', 'event.email_clicked', 'event.page_visited',
        'event.form_submitted', 'in_segment', 'deal.in_stage',
    )

    @staticmethod
    def _rules_match(rules, logic, execution):
        """
        Whether this contact satisfies a list of rules.

        One evaluator for every place that asks the question: if/else, the
        switch node, wait-until and the workflow goal. There used to be a
        hand-rolled one here that compared everything as a lowercased string
        and knew one field name, `has_tag` -- a third definition of "does
        this contact match", after apps/segments/evaluator.py and
        apps/contacts/fields.py. Contact properties now go to the segment
        evaluator, so a workflow condition and a segment rule mean the same
        thing by construction.
        """
        if not rules:
            return True

        results = [
            WorkflowExecutionService._rule_matches(rule, execution)
            for rule in rules
        ]
        return all(results) if logic != 'any' else any(results)

    @staticmethod
    def _rule_matches(rule, execution):
        """One rule. Behaviour here, contact properties delegated."""
        field = (rule or {}).get('field', '')
        if field in WorkflowExecutionService.BEHAVIOUR_FIELDS:
            return WorkflowExecutionService._behaviour_matches(rule, execution)
        return WorkflowExecutionService._property_matches(rule, execution)

    @staticmethod
    def _property_matches(rule, execution):
        """
        A contact-property rule, answered by the segment engine.

        Builds the same Q a segment would and asks whether this one contact is
        in it. One query per rule, which at one workflow step per contact is
        not a hot path -- and it buys every operator and every type without a
        second implementation to keep in step.
        """
        from apps.segments.evaluator import SegmentEvaluator

        contact = execution.contact
        try:
            q = SegmentEvaluator.evaluate_condition({
                'field': rule.get('field', ''),
                'operator': rule.get('operator', 'equals'),
                'value': rule.get('value', ''),
            })
        except Exception:
            logger.exception(
                'Workflow %s has a condition the segment engine rejected: %r',
                execution.workflow_id, rule,
            )
            return False

        if q is None:
            return False
        return (
            Contact.objects
            .filter(pk=contact.pk, organization_id=contact.organization_id)
            .filter(q)
            .exists()
        )

    @staticmethod
    def _behaviour_matches(rule, execution):
        """Something the contact did, rather than something they are."""
        field = rule.get('field', '')
        value = rule.get('value', '')
        negate = rule.get('operator', 'is_true') in ('is_false', 'not_equals', 'false')
        contact = execution.contact
        organization_id = execution.workflow.organization_id

        if field == 'in_segment':
            from apps.segments.evaluator import SegmentEvaluator
            from apps.segments.models import Segment

            segment = Segment.objects.filter(
                id=value, organization_id=organization_id,
            ).first()
            found = bool(segment) and SegmentEvaluator.contact_matches_segment(
                contact, segment
            )

        elif field == 'deal.in_stage':
            from apps.crm.models import Deal

            found = Deal.objects.filter(
                organization_id=organization_id,
                deal_contacts__contact=contact,
                stage_id=value,
            ).exists()

        elif field == 'event.page_visited':
            from apps.tracking.models import TrackedEvent

            events = TrackedEvent.objects.filter(
                organization_id=organization_id, contact=contact,
                event_type=TrackedEvent.EVENT_PAGEVIEW,
            )
            # Measured from when this contact entered the workflow, so "did
            # they visit after we emailed them" means what it says.
            events = events.filter(occurred_at__gte=execution.started_at)
            if value:
                events = (
                    events.filter(path__startswith=value.rstrip('*'))
                    if value.endswith('*') else events.filter(path=value)
                )
            found = events.exists()

        elif field == 'event.form_submitted':
            from apps.forms.models import FormSubmission

            submissions = FormSubmission.objects.filter(
                contact=contact, created_at__gte=execution.started_at,
                form__organization_id=organization_id,
            )
            if value:
                submissions = submissions.filter(form_id=value)
            found = submissions.exists()

        else:  # event.email_opened / event.email_clicked
            from apps.campaigns.models import CampaignRecipient

            recipients = CampaignRecipient.objects.filter(
                contact=contact,
                campaign__organization_id=organization_id,
            )
            # Only mail sent since they entered: a open from last year must
            # not satisfy "did they open the one we just sent".
            if field == 'event.email_opened':
                recipients = recipients.filter(
                    opened_at__isnull=False, opened_at__gte=execution.started_at,
                )
            else:
                recipients = recipients.filter(
                    clicked_at__isnull=False, clicked_at__gte=execution.started_at,
                )
            found = recipients.exists()

        return (not found) if negate else found

    @staticmethod
    def _handle_condition(execution, node):
        """Evaluate condition rules and determine which branch to take."""
        config = node.config or {}
        met = WorkflowExecutionService._rules_match(
            config.get('rules', []), config.get('logic', 'all'), execution,
        )
        branch = 'true' if met else 'false'
        logger.info(f"Condition evaluated to {branch} for execution {execution.id}")
        return {
            'branch': branch,
            'output': {'condition_met': met, 'branch': branch},
        }

    @staticmethod
    def _handle_switch(execution, node):
        """
        Several named paths, first match wins.

        Edges for a switch carry the path's name in source_handle, so adding a
        fifth path costs a config entry rather than a new edge_type.
        """
        config = node.config or {}
        for entry in config.get('branches', []):
            name = (entry or {}).get('name', '')
            if not name:
                continue
            if WorkflowExecutionService._rules_match(
                entry.get('rules', []), entry.get('logic', 'all'), execution,
            ):
                logger.info(f"Switch took '{name}' for execution {execution.id}")
                return {'branch': name, 'output': {'branch': name}}

        return {'branch': 'fallback', 'output': {'branch': 'fallback'}}

    @staticmethod
    def _handle_split_test(execution, node):
        """
        Divide contacts between two paths by percentage.

        Keyed off the execution id rather than random() so a step that is
        retried lands on the same side twice -- a contact who flips branch on
        retry gets both variants, which is exactly what an A/B test must not
        do.
        """
        config = node.config or {}
        try:
            percent_a = max(0, min(int(config.get('percent_a', 50)), 100))
        except (TypeError, ValueError):
            percent_a = 50

        bucket = execution.id.int % 100
        branch = 'a' if bucket < percent_a else 'b'
        logger.info(f"Split test sent execution {execution.id} down {branch}")
        return {'branch': branch, 'output': {'branch': branch, 'bucket': bucket}}

    # ── Wait until something is true ─────────────────────────────────────────

    @staticmethod
    def _handle_wait_until(execution, node):
        """
        Hold the contact until the rules pass, or until the deadline.

        Polled by the same beat task that resumes a plain wait, so this adds
        no new schedule. Checking on arrival matters: a contact who already
        satisfies the rules must not sit here for the timeout first.
        """
        config = node.config or {}
        rules = config.get('rules', [])
        logic = config.get('logic', 'all')

        if WorkflowExecutionService._rules_match(rules, logic, execution):
            return {'branch': 'met', 'output': {'waited': False}}

        try:
            timeout_hours = max(1, int(config.get('timeout_hours', 72)))
        except (TypeError, ValueError):
            timeout_hours = 72

        deadline = execution.wait_deadline
        if deadline is None:
            deadline = timezone.now() + timedelta(hours=timeout_hours)

        if timezone.now() >= deadline:
            logger.info(f"Execution {execution.id} gave up waiting at {deadline}")
            return {'branch': 'timeout', 'output': {'waited': True, 'met': False}}

        # Look again in an hour, or at the deadline if that comes first.
        resume_at = min(timezone.now() + timedelta(hours=1), deadline)
        return {
            'wait': True,
            'resume_at': resume_at,
            'deadline': deadline,
            'output': {'waiting_for': rules, 'deadline': deadline.isoformat()},
        }

    @staticmethod
    def _handle_end_flow(execution, node):
        """Finish here. _advance_to_next_node completes on terminal nodes."""
        return {'output': {'ended': True}}

    # ── The contact ─────────────────────────────────────────────────────────

    @staticmethod
    def _handle_assign_contact(execution, node):
        """Give the contact an owner."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user_id = (node.config or {}).get('user_id')
        if not user_id:
            raise ValueError('No team member chosen to assign to.')

        user = User.objects.filter(
            id=user_id, organization_id=execution.workflow.organization_id,
        ).first()
        if not user:
            raise ValueError('That team member is not in this account.')

        contact = execution.contact
        contact.assigned_to = user
        contact.save(update_fields=['assigned_to', 'updated_at'])
        return {'output': {'assigned_to': str(user.id)}}

    @staticmethod
    def _handle_unsubscribe(execution, node):
        """
        Opt the contact out.

        Never raises on an already-unsubscribed contact: a workflow failing
        because it tried to do something that was already true is noise, and
        the end state is what was asked for either way.
        """
        contact = execution.contact
        if contact.is_subscribed:
            contact.is_subscribed = False
            contact.unsubscribed_at = timezone.now()
            contact.save(update_fields=[
                'is_subscribed', 'unsubscribed_at', 'updated_at',
            ])
        return {'output': {'is_subscribed': False}}

    @staticmethod
    def _handle_add_note(execution, node):
        """Record a note against the contact, visible on their timeline."""
        from apps.crm.models import Activity

        note = (node.config or {}).get('note', '').strip()
        if not note:
            raise ValueError('The note is empty.')

        Activity.objects.create(
            organization_id=execution.workflow.organization_id,
            contact=execution.contact,
            activity_type='note',
            title=f'Workflow: {execution.workflow.name}'[:255],
            description=WorkflowExecutionService._replace_merge_tags(
                note, execution.contact
            ),
        )
        return {'output': {'note_added': True}}

    # ── Segments ────────────────────────────────────────────────────────────

    @staticmethod
    def _segment_for(execution, node, require_static=True):
        from apps.segments.models import Segment

        segment_id = (node.config or {}).get('segment_id')
        if not segment_id:
            raise ValueError('No segment chosen.')

        segment = Segment.objects.filter(
            id=segment_id, organization_id=execution.workflow.organization_id,
        ).first()
        if not segment:
            raise ValueError('That segment is not in this account.')
        if require_static and not segment.is_static:
            # A dynamic segment decides its own members from its rules, so
            # writing a membership row would be overwritten and the workflow
            # would look like it had done nothing.
            raise ValueError(
                f'"{segment.name}" is a dynamic segment; its membership comes '
                f'from its rules. Only static segments can be edited here.'
            )
        return segment

    @staticmethod
    def _handle_add_to_segment(execution, node):
        from apps.segments.services import SegmentService

        segment = WorkflowExecutionService._segment_for(execution, node)
        SegmentService.add_contacts_to_segment(segment, [str(execution.contact_id)])
        return {'output': {'segment_id': str(segment.id)}}

    @staticmethod
    def _handle_remove_from_segment(execution, node):
        from apps.segments.services import SegmentService

        segment = WorkflowExecutionService._segment_for(execution, node)
        SegmentService.remove_contacts_from_segment(
            segment, [str(execution.contact_id)]
        )
        return {'output': {'segment_id': str(segment.id), 'removed': True}}

    # ── Sequences ───────────────────────────────────────────────────────────

    @staticmethod
    def _sequence_for(execution, node):
        from apps.sequences.models import EmailSequence

        sequence_id = (node.config or {}).get('sequence_id')
        if not sequence_id:
            raise ValueError('No sequence chosen.')

        sequence = EmailSequence.objects.filter(
            id=sequence_id, organization_id=execution.workflow.organization_id,
        ).first()
        if not sequence:
            raise ValueError('That sequence is not in this account.')
        return sequence

    @staticmethod
    def _handle_enroll_sequence(execution, node):
        """Hand the contact to a drip sequence."""
        from apps.sequences.services import SequenceEnrollmentService

        sequence = WorkflowExecutionService._sequence_for(execution, node)
        enrollment = SequenceEnrollmentService.enroll_contact(
            sequence, execution.contact,
        )
        return {
            'output': {
                'sequence_id': str(sequence.id),
                # None when they were already enrolled, which the sequence
                # service decides and is not an error here.
                'enrollment_id': str(enrollment.id) if enrollment else None,
            }
        }

    @staticmethod
    def _handle_remove_sequence(execution, node):
        from apps.sequences.models import SequenceEnrollment
        from apps.sequences.services import SequenceEnrollmentService

        sequence = WorkflowExecutionService._sequence_for(execution, node)
        stopped = 0
        for enrollment in SequenceEnrollment.objects.filter(
            sequence=sequence, contact=execution.contact,
            status__in=('active', 'paused'),
        ):
            SequenceEnrollmentService.cancel_enrollment(enrollment)
            stopped += 1
        return {'output': {'sequence_id': str(sequence.id), 'stopped': stopped}}

    # ── Other workflows ─────────────────────────────────────────────────────

    @staticmethod
    def _other_workflow_for(execution, node):
        workflow_id = (node.config or {}).get('workflow_id')
        if not workflow_id:
            raise ValueError('No workflow chosen.')
        if str(workflow_id) == str(execution.workflow_id):
            # Entering yourself is a loop that the re-entry rules would
            # usually stop, but saying so is better than relying on that.
            raise ValueError('A workflow cannot start itself.')

        other = Workflow.objects.filter(
            id=workflow_id, organization_id=execution.workflow.organization_id,
        ).first()
        if not other:
            raise ValueError('That workflow is not in this account.')
        return other

    @staticmethod
    def _handle_enroll_workflow(execution, node):
        """
        Start the contact in another workflow.

        The other workflow's own entry rules still apply, so this cannot be
        used to push someone past a re-entry limit or an entry segment.
        """
        other = WorkflowExecutionService._other_workflow_for(execution, node)
        started = WorkflowExecutionService.start_execution(
            other, execution.contact,
            trigger_data={'from_workflow_id': str(execution.workflow_id)},
        )
        return {
            'output': {
                'workflow_id': str(other.id),
                'started': bool(started),
            }
        }

    @staticmethod
    def _handle_remove_from_workflow(execution, node):
        """Cancel the contact's run of another workflow."""
        other = WorkflowExecutionService._other_workflow_for(execution, node)
        runs = WorkflowExecution.objects.filter(
            workflow=other, contact=execution.contact,
            status__in=('active', 'waiting'),
        )
        cancelled = 0
        for run in runs:
            run.status = 'cancelled'
            run.completed_at = timezone.now()
            run.current_node = None
            run.save(update_fields=[
                'status', 'completed_at', 'current_node', 'updated_at',
            ])
            cancelled += 1
        if cancelled:
            Workflow.objects.filter(id=other.id).update(
                contacts_active=Greatest(F('contacts_active') - cancelled, 0)
            )
        return {'output': {'workflow_id': str(other.id), 'cancelled': cancelled}}

    # ── CRM ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _handle_create_deal(execution, node):
        """Open a deal for the contact."""
        from apps.crm.models import Pipeline, Stage
        from apps.crm.services import DealService

        config = node.config or {}
        organization_id = execution.workflow.organization_id
        pipeline = Pipeline.objects.filter(
            id=config.get('pipeline_id'), organization_id=organization_id,
        ).first()
        if not pipeline:
            raise ValueError('That pipeline is not in this account.')

        stage = None
        if config.get('stage_id'):
            stage = Stage.objects.filter(
                id=config['stage_id'], pipeline=pipeline,
            ).first()
        stage = stage or pipeline.stages.order_by('position').first()
        if not stage:
            raise ValueError(f'Pipeline "{pipeline.name}" has no stages.')

        contact = execution.contact
        title = WorkflowExecutionService._replace_merge_tags(
            config.get('title') or '', contact
        ).strip()
        if not title:
            title = (
                f"{contact.first_name} {contact.last_name}".strip()
                or contact.email
            )

        try:
            value = float(config.get('value') or 0)
        except (TypeError, ValueError):
            value = 0

        deal = DealService.create_deal(
            organization=execution.workflow.organization,
            data={
                'pipeline': pipeline,
                'stage': stage,
                'title': title,
                'value': value,
                'contact_ids': [str(contact.id)],
            },
        )
        return {'output': {'deal_id': str(deal.id)}}

    @staticmethod
    def _handle_create_task(execution, node):
        """Give someone on the team something to do about this contact."""
        from django.contrib.auth import get_user_model
        from apps.crm.services import CRMTaskService

        User = get_user_model()
        config = node.config or {}
        organization_id = execution.workflow.organization_id
        contact = execution.contact

        title = WorkflowExecutionService._replace_merge_tags(
            config.get('title') or '', contact
        ).strip()
        if not title:
            raise ValueError('The task has no title.')

        assignee = None
        if config.get('assigned_to'):
            assignee = User.objects.filter(
                id=config['assigned_to'], organization_id=organization_id,
            ).first()

        try:
            due_in_days = int(config.get('due_in_days', 1))
        except (TypeError, ValueError):
            due_in_days = 1

        data = {
            'title': title,
            'description': WorkflowExecutionService._replace_merge_tags(
                config.get('description') or '', contact
            ),
            'contact': contact,
            'priority': (
                config.get('priority')
                if config.get('priority') in ('low', 'medium', 'high', 'urgent')
                else 'medium'
            ),
            'due_date': timezone.now() + timedelta(days=due_in_days),
        }
        if assignee:
            data['assigned_to'] = assignee

        task = CRMTaskService.create_task(
            organization=execution.workflow.organization, data=data,
        )
        return {'output': {'task_id': str(task.id)}}

    # ── Telling a human ─────────────────────────────────────────────────────

    @staticmethod
    def _handle_notify_team(execution, node):
        """
        Email someone internally about this contact.

        Goes through the transactional path, not the marketing one: this is
        mail to a colleague, so it must not be suppressed by the contact's
        marketing preferences or counted against the sending quota as a
        campaign.
        """
        from django.contrib.auth import get_user_model
        from apps.core.mail import send_transactional_email

        User = get_user_model()
        config = node.config or {}
        organization = execution.workflow.organization
        contact = execution.contact

        recipient = (config.get('email') or '').strip()
        if config.get('user_id'):
            user = User.objects.filter(
                id=config['user_id'], organization_id=organization.id,
            ).first()
            if not user:
                raise ValueError('That team member is not in this account.')
            recipient = user.email
        if not recipient:
            raise ValueError('Nobody to notify: choose a team member or an address.')

        subject = WorkflowExecutionService._replace_merge_tags(
            config.get('subject') or f'Workflow: {execution.workflow.name}', contact
        )
        message = WorkflowExecutionService._replace_merge_tags(
            config.get('message') or '', contact
        )

        result = send_transactional_email(
            subject=subject,
            template='workflows/email/team_notification',
            context={
                'subject': subject,
                'message': message,
                'contact_email': contact.email,
                'contact_name': f'{contact.first_name} {contact.last_name}'.strip(),
                'contact_url': (
                    f'{settings.FRONTEND_URL.rstrip("/")}/contacts/{contact.id}'
                ),
                'workflow_name': execution.workflow.name,
                'organization_name': organization.name,
            },
            to_email=recipient,
            organization=organization,
            # Replies go to the colleague who was notified, not to the lead.
            reply_to='',
        )
        if not result.ok:
            # Surfaced rather than swallowed: a notification nobody received
            # is the kind of silent failure that makes people distrust the
            # whole workflow.
            raise RuntimeError(f'Could not notify {recipient}: {result.error}')
        return {'output': {'notified': recipient}}

    @staticmethod
    def _advance_to_next_node(execution, current_node, result):
        """Find and move to the next node in the workflow."""
        branch = result.get('branch', 'default')

        if current_node.node_type in catalog.TERMINAL_TYPES:
            WorkflowExecutionService._complete_execution(execution)
            return

        edges = WorkflowEdge.objects.filter(
            workflow=execution.workflow, source_node=current_node,
        )
        # A node that offers one path takes it; anything that branches has to
        # be matched. Asked of the catalogue rather than of is_condition,
        # because Wait Until is an action with two ways out.
        if len(catalog.branches_for(current_node.node_type)) > 1 or branch != 'default':
            edge = (
                edges.filter(edge_type=branch).first()
                # A switch names its paths in source_handle, so there is no
                # edge_type to match against.
                or edges.filter(source_handle=branch).first()
            )
        else:
            edge = edges.first()

        if not edge:
            # No more nodes, complete the execution
            WorkflowExecutionService._complete_execution(execution)
            return

        # Move to next node
        execution.current_node = edge.target_node
        execution.save(update_fields=['current_node', 'updated_at'])

        # Queue next node execution
        WorkflowExecutionService._queue_node_execution(execution)

    @staticmethod
    def _complete_execution(execution):
        """Mark the execution as completed."""
        execution.status = 'completed'
        execution.completed_at = timezone.now()
        execution.current_node = None
        execution.save()

        # Update workflow stats
        Workflow.objects.filter(id=execution.workflow_id).update(
            contacts_active=Greatest(F('contacts_active') - 1, 0),
            contacts_completed=F('contacts_completed') + 1,
        )

        logger.info(f"Workflow execution {execution.id} completed")

    @staticmethod
    def resume_waiting_execution(execution):
        """Resume an execution that was waiting."""
        execution.status = 'active'
        execution.resume_at = None
        execution.save(update_fields=['status', 'resume_at', 'updated_at'])

        # Advance to next node (the wait node is complete)
        current_node = execution.current_node
        if current_node:
            WorkflowExecutionService._advance_to_next_node(
                execution,
                current_node,
                {'output': {}}
            )


class WorkflowTriggerService:
    """Service class for handling workflow triggers."""

    @staticmethod
    def trigger_form_submission(form, contact, submission):
        """Trigger workflows when a form is submitted."""
        if not contact:
            return

        workflows = WorkflowTriggerService._matching_workflows(
            form.organization, WorkflowNode.TRIGGER_FORM_SUBMISSION,
            form_id=form.id,
        )

        for workflow in workflows:
            WorkflowExecutionService.start_execution(
                workflow=workflow,
                contact=contact,
                trigger_data={
                    'type': 'form_submission',
                    'form_id': str(form.id),
                    'form_name': form.name,
                    'submission_id': str(submission.id),
                }
            )

    @staticmethod
    def trigger_tag_added(contact, tag):
        """Trigger workflows when a tag is added to a contact."""
        # Find active workflows with tag added trigger
        workflows = Workflow.objects.filter(
            organization=contact.organization,
            status='active',
            nodes__node_type=WorkflowNode.TRIGGER_TAG_ADDED,
            nodes__config__tag_id=str(tag.id),
        ).distinct()

        for workflow in workflows:
            WorkflowExecutionService.start_execution(
                workflow=workflow,
                contact=contact,
                trigger_data={
                    'type': 'tag_added',
                    'tag_id': str(tag.id),
                    'tag_name': tag.name,
                }
            )

    @staticmethod
    def trigger_tag_removed(contact, tag):
        """Trigger workflows when a tag is removed from a contact."""
        # Find active workflows with tag removed trigger
        workflows = Workflow.objects.filter(
            organization=contact.organization,
            status='active',
            nodes__node_type=WorkflowNode.TRIGGER_TAG_REMOVED,
            nodes__config__tag_id=str(tag.id),
        ).distinct()

        for workflow in workflows:
            WorkflowExecutionService.start_execution(
                workflow=workflow,
                contact=contact,
                trigger_data={
                    'type': 'tag_removed',
                    'tag_id': str(tag.id),
                    'tag_name': tag.name,
                }
            )

    @staticmethod
    def trigger_contact_created(contact):
        """Trigger workflows when a new contact is created."""
        # Find active workflows with contact created trigger
        workflows = Workflow.objects.filter(
            organization=contact.organization,
            status='active',
            nodes__node_type=WorkflowNode.TRIGGER_CONTACT_CREATED,
        ).distinct()

        for workflow in workflows:
            WorkflowExecutionService.start_execution(
                workflow=workflow,
                contact=contact,
                trigger_data={
                    'type': 'contact_created',
                    'contact_id': str(contact.id),
                }
            )

    @staticmethod
    def trigger_email_opened(campaign_recipient):
        """Trigger workflows when an email is opened."""
        contact = campaign_recipient.contact
        if not contact:
            return

        # Find active workflows with email opened trigger
        workflows = Workflow.objects.filter(
            organization=contact.organization,
            status='active',
            nodes__node_type=WorkflowNode.TRIGGER_EMAIL_OPENED,
        ).distinct()

        for workflow in workflows:
            WorkflowExecutionService.start_execution(
                workflow=workflow,
                contact=contact,
                trigger_data={
                    'type': 'email_opened',
                    'campaign_id': str(campaign_recipient.campaign_id),
                }
            )

    @staticmethod
    def trigger_email_clicked(campaign_recipient, link_url=None):
        """Trigger workflows when an email link is clicked."""
        contact = campaign_recipient.contact
        if not contact:
            return

        # Find active workflows with email clicked trigger
        workflows = Workflow.objects.filter(
            organization=contact.organization,
            status='active',
            nodes__node_type=WorkflowNode.TRIGGER_EMAIL_CLICKED,
        ).distinct()

        for workflow in workflows:
            WorkflowExecutionService.start_execution(
                workflow=workflow,
                contact=contact,
                trigger_data={
                    'type': 'email_clicked',
                    'campaign_id': str(campaign_recipient.campaign_id),
                    'link_url': link_url,
                }
            )

    @staticmethod
    def trigger_popup_interaction(popup, contact, node_type, extra=None):
        """
        Start workflows waiting on a pop-up being shown or clicked.

        One method for both, because the two differ only in the node type and
        splitting them would be two copies of the same query.

        Only fires for a visitor we can name. A workflow acts on a contact,
        and most people who see a pop-up are nobody yet.
        """
        if contact is None:
            return

        workflows = Workflow.objects.filter(
            organization=contact.organization,
            status='active',
            nodes__node_type=node_type,
        ).filter(
            Q(nodes__config__popup_id=str(popup.id))
            | Q(nodes__config__popup_id__isnull=True)
            | Q(nodes__config__popup_id='')
        ).distinct()

        for workflow in workflows:
            WorkflowExecutionService.start_execution(
                workflow=workflow,
                contact=contact,
                trigger_data={
                    'type': node_type.replace('trigger_', ''),
                    'popup_id': str(popup.id),
                    'popup_name': popup.name,
                    **(extra or {}),
                },
            )

    @staticmethod
    def _matching_workflows(organization, node_type, **config_match):
        """
        Active workflows whose trigger of this type accepts these values.

        A blank trigger config means "any", which the obvious filter
        (`nodes__config__form_id=x`) silently excludes -- a form trigger left
        on "any form" would never fire, which is how the catalogue's own
        "leave empty for any" promise gets quietly broken. A key that is
        absent, null or empty therefore matches everything.
        """
        constraint = Q(nodes__node_type=node_type)
        for key, value in config_match.items():
            wildcard = (
                Q(**{f'nodes__config__{key}': None})
                | Q(**{f'nodes__config__{key}': ''})
                | ~Q(nodes__config__has_key=key)
            )
            constraint &= (
                wildcard if value is None
                else Q(**{f'nodes__config__{key}': str(value)}) | wildcard
            )
        return Workflow.objects.filter(
            constraint, organization=organization, status='active',
        ).distinct()

    @staticmethod
    def _fire(workflows, contact, trigger_data):
        """Start each of these workflows for this contact."""
        started = 0
        for workflow in workflows:
            if WorkflowExecutionService.start_execution(
                workflow=workflow, contact=contact, trigger_data=trigger_data,
            ):
                started += 1
        return started

    # ── Contact ─────────────────────────────────────────────────────────────

    @staticmethod
    def trigger_contact_field_changed(contact, field, old_value, new_value):
        """A field on the contact was given a new value."""
        workflows = WorkflowTriggerService._matching_workflows(
            contact.organization, WorkflowNode.TRIGGER_CONTACT_FIELD_CHANGED,
            field=field,
        )
        # The to_value filter cannot go in the query: it is per node, and a
        # node wanting a particular value must not be fired by a different one.
        fired = 0
        for workflow in workflows:
            wanted = {
                (node.config or {}).get('to_value', '')
                for node in workflow.nodes.filter(
                    node_type=WorkflowNode.TRIGGER_CONTACT_FIELD_CHANGED,
                )
                if (node.config or {}).get('field', '') in ('', field)
            }
            if wanted and not any(
                not w or str(w).lower() == str(new_value).lower() for w in wanted
            ):
                continue
            fired += WorkflowTriggerService._fire(
                [workflow], contact,
                {
                    'type': 'contact_field_changed', 'field': field,
                    'old_value': str(old_value), 'new_value': str(new_value),
                },
            )
        return fired

    @staticmethod
    def trigger_email_unsubscribed(contact):
        """The contact opted out."""
        return WorkflowTriggerService._fire(
            WorkflowTriggerService._matching_workflows(
                contact.organization, WorkflowNode.TRIGGER_EMAIL_UNSUBSCRIBED,
            ),
            contact, {'type': 'email_unsubscribed'},
        )

    @staticmethod
    def trigger_email_bounced(campaign_recipient, bounce_type='hard'):
        """Mail to the contact bounced."""
        contact = campaign_recipient.contact
        if not contact:
            return 0

        organization = campaign_recipient.campaign.organization
        workflows = WorkflowTriggerService._matching_workflows(
            organization, WorkflowNode.TRIGGER_EMAIL_BOUNCED,
        )
        # 'any' is the default and must also match a node that names a type.
        wanted = [
            workflow for workflow in workflows
            if any(
                (node.config or {}).get('bounce_type', 'any') in ('any', '', bounce_type)
                for node in workflow.nodes.filter(
                    node_type=WorkflowNode.TRIGGER_EMAIL_BOUNCED,
                )
            )
        ]
        return WorkflowTriggerService._fire(
            wanted, contact,
            {
                'type': 'email_bounced', 'bounce_type': bounce_type,
                'campaign_id': str(campaign_recipient.campaign_id),
            },
        )

    # ── Website ─────────────────────────────────────────────────────────────

    @staticmethod
    def trigger_page_visited(organization, contact, path):
        """
        A known contact viewed a page.

        Called from the tracking collector, which only knows a visitor id
        until that visitor has been tied to a contact -- so this fires for
        people who have identified themselves, never for anonymous traffic.
        """
        if not contact:
            return 0

        from apps.tracking.models import TrackedEvent

        fired = 0
        for workflow in WorkflowTriggerService._matching_workflows(
            organization, WorkflowNode.TRIGGER_PAGE_VISITED,
        ):
            for node in workflow.nodes.filter(
                node_type=WorkflowNode.TRIGGER_PAGE_VISITED,
            ):
                config = node.config or {}
                pattern = (config.get('path') or '').strip()
                if not pattern:
                    continue
                if pattern.endswith('*'):
                    if not path.startswith(pattern.rstrip('*')):
                        continue
                elif path != pattern:
                    continue

                try:
                    needed = max(1, int(config.get('times', 1)))
                except (TypeError, ValueError):
                    needed = 1
                if needed > 1:
                    seen = TrackedEvent.objects.filter(
                        organization=organization, contact=contact,
                        event_type=TrackedEvent.EVENT_PAGEVIEW,
                        path=path,
                    ).count()
                    if seen < needed:
                        continue

                fired += WorkflowTriggerService._fire(
                    [workflow], contact,
                    {'type': 'page_visited', 'path': path},
                )
                break
        return fired

    # ── Segments ────────────────────────────────────────────────────────────

    @staticmethod
    def seed_segment_watch(workflow):
        """
        Record who is in the watched segments now, so only later changes fire.

        Called when a workflow is activated. Without it, switching on a
        workflow triggered by "entered segment" would read every existing
        member as a new arrival and mail the lot.
        """
        from apps.segments.evaluator import SegmentEvaluator
        from apps.segments.models import Segment

        from .models import WorkflowSegmentWatch

        watched = workflow.nodes.filter(node_type__in=(
            WorkflowNode.TRIGGER_SEGMENT_ENTERED,
            WorkflowNode.TRIGGER_SEGMENT_LEFT,
        ))
        for node in watched:
            segment_id = (node.config or {}).get('segment_id')
            segment = Segment.objects.filter(
                id=segment_id, organization_id=workflow.organization_id,
            ).first()
            if not segment:
                continue

            WorkflowSegmentWatch.objects.filter(node=node).delete()
            contact_ids = SegmentEvaluator.get_segment_contacts(
                segment, workflow.organization,
            ).values_list('id', flat=True)
            WorkflowSegmentWatch.objects.bulk_create(
                [
                    WorkflowSegmentWatch(node=node, contact_id=contact_id)
                    for contact_id in contact_ids
                ],
                batch_size=1000, ignore_conflicts=True,
            )
            logger.info(
                'Seeded segment watch for node %s with %d contact(s)',
                node.id, len(contact_ids),
            )

    @staticmethod
    def sweep_segment_triggers():
        """
        Fire entered/left for every watching node, then update the baseline.

        Polled rather than signalled because a dynamic segment has no event to
        hook: a contact can start matching because a field changed, because a
        tag was applied, or because a date passed and nothing happened at all.
        """
        from apps.segments.evaluator import SegmentEvaluator
        from apps.segments.models import Segment

        from .models import WorkflowSegmentWatch

        nodes = WorkflowNode.objects.filter(
            node_type__in=(
                WorkflowNode.TRIGGER_SEGMENT_ENTERED,
                WorkflowNode.TRIGGER_SEGMENT_LEFT,
            ),
            workflow__status='active',
            workflow__deleted_at__isnull=True,
        ).select_related('workflow')

        fired = 0
        for node in nodes:
            segment = Segment.objects.filter(
                id=(node.config or {}).get('segment_id'),
                organization_id=node.workflow.organization_id,
            ).first()
            if not segment:
                continue

            now_in = set(
                SegmentEvaluator.get_segment_contacts(
                    segment, node.workflow.organization,
                ).values_list('id', flat=True)
            )
            was_in = set(
                WorkflowSegmentWatch.objects
                .filter(node=node).values_list('contact_id', flat=True)
            )

            if node.node_type == WorkflowNode.TRIGGER_SEGMENT_ENTERED:
                changed = now_in - was_in
                kind = 'segment_entered'
            else:
                changed = was_in - now_in
                kind = 'segment_left'

            if changed:
                for contact in Contact.objects.filter(id__in=changed):
                    fired += WorkflowTriggerService._fire(
                        [node.workflow], contact,
                        {
                            'type': kind, 'segment_id': str(segment.id),
                            'segment_name': segment.name,
                        },
                    )

            # Move the baseline on even when nothing fired, so a contact who
            # leaves and rejoins is seen as rejoining.
            WorkflowSegmentWatch.objects.filter(node=node).delete()
            WorkflowSegmentWatch.objects.bulk_create(
                [WorkflowSegmentWatch(node=node, contact_id=cid) for cid in now_in],
                batch_size=1000, ignore_conflicts=True,
            )
        return fired

    # ── CRM ─────────────────────────────────────────────────────────────────

    @staticmethod
    def trigger_deal_closed(deal, won):
        """A deal was marked won or lost."""
        node_type = (
            WorkflowNode.TRIGGER_DEAL_WON if won
            else WorkflowNode.TRIGGER_DEAL_LOST
        )
        contact = WorkflowTriggerService._deal_contact(deal)
        if not contact:
            return 0

        return WorkflowTriggerService._fire(
            WorkflowTriggerService._matching_workflows(deal.organization, node_type),
            contact,
            {
                'type': 'deal_won' if won else 'deal_lost',
                'deal_id': str(deal.id), 'deal_title': deal.title,
                'deal_value': str(deal.value or 0),
            },
        )

    @staticmethod
    def _deal_contact(deal):
        """The contact a deal is about: its primary, else any linked one."""
        link = (
            deal.deal_contacts.filter(role='primary').select_related('contact').first()
            or deal.deal_contacts.select_related('contact').first()
        )
        return link.contact if link else None

    @staticmethod
    def trigger_task_completed(task):
        """A sales task on a contact was marked done."""
        if not task.contact_id:
            return 0

        return WorkflowTriggerService._fire(
            WorkflowTriggerService._matching_workflows(
                task.organization, WorkflowNode.TRIGGER_TASK_COMPLETED,
            ),
            task.contact,
            {'type': 'task_completed', 'task_id': str(task.id), 'title': task.title},
        )

    # ── Sequences ───────────────────────────────────────────────────────────

    @staticmethod
    def trigger_sequence_completed(enrollment):
        """A contact reached the end of a sequence."""
        sequence = enrollment.sequence
        return WorkflowTriggerService._fire(
            WorkflowTriggerService._matching_workflows(
                sequence.organization, WorkflowNode.TRIGGER_SEQUENCE_COMPLETED,
                sequence_id=sequence.id,
            ),
            enrollment.contact,
            {
                'type': 'sequence_completed', 'sequence_id': str(sequence.id),
                'sequence_name': sequence.name,
            },
        )

    @staticmethod
    def trigger_lead_score_threshold(contact, old_score: int, new_score: int):
        """
        Fire workflows whose trigger_lead_score_threshold node is crossed by
        the old_score → new_score transition.
        """
        if old_score == new_score:
            return

        workflows = Workflow.objects.filter(
            organization=contact.organization,
            status='active',
            nodes__node_type=WorkflowNode.TRIGGER_LEAD_SCORE_THRESHOLD,
        ).distinct().prefetch_related('nodes')

        for workflow in workflows:
            for node in workflow.nodes.filter(
                node_type=WorkflowNode.TRIGGER_LEAD_SCORE_THRESHOLD
            ):
                config = node.config or {}
                try:
                    threshold = int(config.get('threshold_value', 0))
                except (TypeError, ValueError):
                    continue
                direction = config.get('direction', 'above')

                crossed = False
                if direction == 'above' and old_score < threshold <= new_score:
                    crossed = True
                elif direction == 'below' and old_score > threshold >= new_score:
                    crossed = True
                elif direction == 'equals' and new_score == threshold:
                    crossed = True

                if crossed:
                    WorkflowExecutionService.start_execution(
                        workflow=workflow,
                        contact=contact,
                        trigger_data={
                            'type': 'lead_score_threshold',
                            'old_score': old_score,
                            'new_score': new_score,
                            'threshold': threshold,
                            'direction': direction,
                        }
                    )

    @staticmethod
    def process_date_triggers():
        """
        Process date-based triggers.
        Should be called daily by a scheduled task.
        """
        today = timezone.now().date()

        # Find all active workflows with date field triggers
        workflows = Workflow.objects.filter(
            status='active',
            nodes__node_type=WorkflowNode.TRIGGER_DATE_FIELD,
        ).distinct()

        for workflow in workflows:
            trigger_nodes = workflow.nodes.filter(
                node_type=WorkflowNode.TRIGGER_DATE_FIELD
            )

            for node in trigger_nodes:
                config = node.config or {}
                field_name = config.get('field_name')
                offset_days = config.get('offset_days', 0)

                if not field_name:
                    continue

                # Calculate target date
                target_date = today - timedelta(days=offset_days)

                # Find contacts matching the date
                contacts = Contact.objects.filter(
                    organization=workflow.organization,
                    is_subscribed=True,
                )

                # Check custom fields for date match
                for contact in contacts:
                    if hasattr(contact, field_name):
                        contact_date = getattr(contact, field_name)
                    else:
                        contact_date = contact.custom_fields.get(field_name)

                    if contact_date:
                        try:
                            if hasattr(contact_date, 'date'):
                                contact_date = contact_date.date()
                            elif isinstance(contact_date, str):
                                from datetime import datetime
                                contact_date = datetime.strptime(contact_date, '%Y-%m-%d').date()

                            if contact_date == target_date:
                                WorkflowExecutionService.start_execution(
                                    workflow=workflow,
                                    contact=contact,
                                    trigger_data={
                                        'type': 'date_field',
                                        'field_name': field_name,
                                        'date': str(target_date),
                                    }
                                )
                        except (ValueError, AttributeError):
                            continue

    @staticmethod
    def trigger_deal_stage_changed(deal, from_stage, to_stage):
        """Trigger workflows when a deal moves to a new stage."""
        contact = deal.primary_contact
        if not contact:
            return

        workflows = Workflow.objects.filter(
            organization=deal.organization,
            status='active',
            nodes__node_type=WorkflowNode.TRIGGER_DEAL_STAGE_CHANGED,
        ).distinct()

        for workflow in workflows:
            trigger_node = workflow.nodes.filter(
                node_type=WorkflowNode.TRIGGER_DEAL_STAGE_CHANGED
            ).first()
            if trigger_node:
                cfg = trigger_node.config or {}
                to_filter = cfg.get('to_stage_id')
                from_filter = cfg.get('from_stage_id')
                if to_filter and str(to_stage.id) != str(to_filter):
                    continue
                if from_filter and from_stage and str(from_stage.id) != str(from_filter):
                    continue

            WorkflowExecutionService.start_execution(
                workflow=workflow,
                contact=contact,
                trigger_data={
                    'type': 'deal_stage_changed',
                    'deal_id': str(deal.id),
                    'deal_title': deal.title,
                    'from_stage_id': str(from_stage.id) if from_stage else None,
                    'from_stage_name': from_stage.name if from_stage else None,
                    'to_stage_id': str(to_stage.id),
                    'to_stage_name': to_stage.name,
                }
            )

    @staticmethod
    def trigger_deal_created(deal):
        """Trigger workflows when a new deal is created."""
        contact = deal.primary_contact
        if not contact:
            return

        workflows = Workflow.objects.filter(
            organization=deal.organization,
            status='active',
            nodes__node_type=WorkflowNode.TRIGGER_DEAL_CREATED,
        ).distinct()

        for workflow in workflows:
            trigger_node = workflow.nodes.filter(
                node_type=WorkflowNode.TRIGGER_DEAL_CREATED
            ).first()
            if trigger_node:
                cfg = trigger_node.config or {}
                pipeline_filter = cfg.get('pipeline_id')
                if pipeline_filter and str(deal.pipeline_id) != str(pipeline_filter):
                    continue

            WorkflowExecutionService.start_execution(
                workflow=workflow,
                contact=contact,
                trigger_data={
                    'type': 'deal_created',
                    'deal_id': str(deal.id),
                    'deal_title': deal.title,
                    'pipeline_id': str(deal.pipeline_id),
                    'stage_id': str(deal.stage_id),
                    'value': float(deal.value),
                }
            )
