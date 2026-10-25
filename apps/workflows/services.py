"""
Services for the Workflow Automation app.
"""
import logging
import re
import requests
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import F

from .models import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowTemplate,
)
from apps.contacts.models import Contact, Tag, ContactTag
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
        """Create a new workflow from a template."""
        template_data = template.template_data or {}

        with transaction.atomic():
            workflow = Workflow.objects.create(
                organization=organization,
                name=f"{template.name}",
                description=template.description,
                status='draft',
                canvas_data=template_data.get('canvas', {}),
                created_by=user,
            )

            # Create nodes from template
            node_mapping = {}
            for node_data in template_data.get('nodes', []):
                node = WorkflowNode.objects.create(
                    workflow=workflow,
                    node_type=node_data.get('node_type'),
                    position_x=node_data.get('position_x', 0),
                    position_y=node_data.get('position_y', 0),
                    config=node_data.get('config', {}),
                    label=node_data.get('label', ''),
                )
                # Map template node ID to new node
                old_id = node_data.get('id')
                if old_id:
                    node_mapping[old_id] = node

            # Create edges from template
            for edge_data in template_data.get('edges', []):
                source_id = edge_data.get('source_node_id')
                target_id = edge_data.get('target_node_id')
                source_node = node_mapping.get(source_id)
                target_node = node_mapping.get(target_id)

                if source_node and target_node:
                    WorkflowEdge.objects.create(
                        workflow=workflow,
                        source_node=source_node,
                        target_node=target_node,
                        edge_type=edge_data.get('edge_type', 'default'),
                        source_handle=edge_data.get('source_handle', 'default'),
                        target_handle=edge_data.get('target_handle', 'default'),
                    )

            # Increment template usage
            template.usage_count = F('usage_count') + 1
            template.save(update_fields=['usage_count'])

            return workflow


class WorkflowExecutionService:
    """Service class for workflow execution operations."""

    @staticmethod
    def start_execution(workflow, contact, trigger_data=None):
        """Start a new workflow execution for a contact."""
        # Check if contact already has an active execution for this workflow
        existing = WorkflowExecution.objects.filter(
            workflow=workflow,
            contact=contact,
        ).first()

        if existing:
            logger.info(
                f"Contact {contact.email} already in workflow {workflow.name}, "
                f"status: {existing.status}"
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
                execution.save(update_fields=['status', 'resume_at', 'updated_at'])
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
                    contacts_active=F('contacts_active') - 1
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
    def _handle_send_email(execution, node):
        """Send an email using the configured template."""
        config = node.config or {}
        template_id = config.get('template_id')
        subject_override = config.get('subject')

        if not template_id:
            raise ValueError("Email template not configured")

        template = EmailTemplate.objects.filter(id=template_id).first()
        if not template:
            raise ValueError(f"Email template {template_id} not found")

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
        from_name, from_addr = EmailConfigService.get_default_from(organization)

        msg = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=f'{from_name} <{from_addr}>',
            to=[contact.email],
            connection=EmailConfigService.get_connection(organization),
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

        tag = Tag.objects.filter(id=tag_id).first()
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
        """Update a field on the contact."""
        config = node.config or {}
        field = config.get('field')
        operation = config.get('operation', 'set')
        value = config.get('value')

        if not field:
            raise ValueError("Contact field not configured")

        contact = execution.contact

        if operation == 'set':
            if hasattr(contact, field):
                setattr(contact, field, value)
            else:
                # Custom field
                contact.custom_fields[field] = value
        elif operation == 'increment':
            current = getattr(contact, field, 0) or 0
            setattr(contact, field, current + (int(value) if value else 1))
        elif operation == 'decrement':
            current = getattr(contact, field, 0) or 0
            setattr(contact, field, current - (int(value) if value else 1))
        elif operation == 'append':
            current = getattr(contact, field, '') or ''
            setattr(contact, field, f"{current}{value}")

        contact.save()
        contact.update_activity()

        logger.info(f"Updated contact {contact.email}: {field} = {operation}({value})")

        return {'output': {'field': field, 'operation': operation}}

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
    def _handle_goal(execution, node):
        """Mark the goal as reached."""
        execution.goal_reached = True
        execution.goal_reached_at = timezone.now()
        execution.save(update_fields=['goal_reached', 'goal_reached_at', 'updated_at'])

        # Update workflow stats
        Workflow.objects.filter(id=execution.workflow_id).update(
            contacts_goal_reached=F('contacts_goal_reached') + 1
        )

        logger.info(f"Goal reached for execution {execution.id}")

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

        deal = Deal.objects.filter(id=deal_id).first()
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
            user = User.objects.filter(id=value).first()
            if user:
                deal.assigned_to = user
                deal.save(update_fields=['assigned_to'])
        elif field == 'priority' and value in ('low', 'medium', 'high'):
            deal.priority = value
            deal.save(update_fields=['priority'])

        logger.info(f"Updated deal {deal.title}: {field} = {value}")
        return {'output': {'field': field, 'value': value}}

    @staticmethod
    def _handle_condition(execution, node):
        """Evaluate condition rules and determine which branch to take."""
        config = node.config or {}
        rules = config.get('rules', [])
        logic = config.get('logic', 'all')  # 'all' = AND, 'any' = OR

        contact = execution.contact

        results = []
        for rule in rules:
            result = WorkflowExecutionService._evaluate_rule(rule, contact, execution)
            results.append(result)

        if logic == 'all':
            condition_met = all(results)
        else:  # 'any'
            condition_met = any(results)

        branch = 'true' if condition_met else 'false'

        logger.info(f"Condition evaluated to {branch} for execution {execution.id}")

        return {
            'branch': branch,
            'output': {'condition_met': condition_met, 'branch': branch},
        }

    @staticmethod
    def _evaluate_rule(rule, contact, execution):
        """Evaluate a single condition rule."""
        field = rule.get('field', '')
        operator = rule.get('operator', 'equals')
        value = rule.get('value', '')

        # Get field value from contact
        if field.startswith('custom_'):
            field_name = field[7:]  # Remove 'custom_' prefix
            actual_value = contact.custom_fields.get(field_name, '')
        elif hasattr(contact, field):
            actual_value = getattr(contact, field, '')
        else:
            actual_value = ''

        # Handle tag checks
        if field == 'has_tag':
            has_tag = ContactTag.objects.filter(
                contact=contact,
                tag_id=value,
            ).exists()
            return has_tag if operator == 'equals' else not has_tag

        # Convert to strings for comparison
        actual_str = str(actual_value or '').lower()
        compare_str = str(value or '').lower()

        if operator == 'equals':
            return actual_str == compare_str
        elif operator == 'not_equals':
            return actual_str != compare_str
        elif operator == 'contains':
            return compare_str in actual_str
        elif operator == 'not_contains':
            return compare_str not in actual_str
        elif operator == 'starts_with':
            return actual_str.startswith(compare_str)
        elif operator == 'ends_with':
            return actual_str.endswith(compare_str)
        elif operator == 'is_empty':
            return not actual_str
        elif operator == 'is_not_empty':
            return bool(actual_str)
        elif operator == 'greater_than':
            try:
                return float(actual_value) > float(value)
            except (ValueError, TypeError):
                return False
        elif operator == 'less_than':
            try:
                return float(actual_value) < float(value)
            except (ValueError, TypeError):
                return False

        return False

    @staticmethod
    def _advance_to_next_node(execution, current_node, result):
        """Find and move to the next node in the workflow."""
        branch = result.get('branch', 'default')

        # Find outgoing edge
        if current_node.is_condition:
            # For conditions, match the branch taken
            edge = WorkflowEdge.objects.filter(
                workflow=execution.workflow,
                source_node=current_node,
                edge_type=branch,
            ).first()
        else:
            # For other nodes, use default edge
            edge = WorkflowEdge.objects.filter(
                workflow=execution.workflow,
                source_node=current_node,
            ).first()

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
            contacts_active=F('contacts_active') - 1,
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

        # Find active workflows with form submission trigger
        workflows = Workflow.objects.filter(
            organization=form.organization,
            status='active',
            nodes__node_type=WorkflowNode.TRIGGER_FORM_SUBMISSION,
            nodes__config__form_id=str(form.id),
        ).distinct()

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
