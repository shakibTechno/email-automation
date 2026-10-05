"""
Celery tasks for the Workflow Automation app.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_workflow_node(self, execution_id: str):
    """
    Execute the current node in a workflow execution.
    This task is queued when an execution starts or advances.
    """
    from .models import WorkflowExecution
    from .services import WorkflowExecutionService

    try:
        execution = WorkflowExecution.objects.select_related(
            'workflow', 'contact', 'current_node'
        ).get(id=execution_id)
    except WorkflowExecution.DoesNotExist:
        logger.error(f"WorkflowExecution {execution_id} not found")
        return

    try:
        WorkflowExecutionService.execute_node(execution)
        logger.info(f"Executed node for execution {execution_id}")
    except Exception as exc:
        logger.exception(f"Error executing workflow node: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def resume_waiting_executions():
    """
    Resume workflow executions that have finished waiting.
    Should run every minute via Celery Beat.
    """
    from .models import WorkflowExecution
    from .services import WorkflowExecutionService

    now = timezone.now()

    # Find executions ready to resume
    executions = WorkflowExecution.objects.filter(
        status='waiting',
        resume_at__lte=now,
    ).select_related('workflow', 'contact', 'current_node')

    resumed_count = 0
    for execution in executions:
        try:
            WorkflowExecutionService.resume_waiting_execution(execution)
            resumed_count += 1
            logger.info(f"Resumed execution {execution.id}")
        except Exception as exc:
            logger.exception(f"Error resuming execution {execution.id}: {exc}")

    if resumed_count > 0:
        logger.info(f"Resumed {resumed_count} waiting executions")

    return resumed_count


@shared_task
def process_date_triggers():
    """
    Process date-based workflow triggers.
    Should run daily via Celery Beat (e.g., at 00:05).
    """
    from .services import WorkflowTriggerService

    try:
        WorkflowTriggerService.process_date_triggers()
        logger.info("Processed date triggers successfully")
    except Exception as exc:
        logger.exception(f"Error processing date triggers: {exc}")


@shared_task
def start_workflow_execution(workflow_id: str, contact_id: str, trigger_data: dict = None):
    """
    Start a workflow execution for a specific contact.
    Can be called directly or from signals.
    """
    from .models import Workflow
    from .services import WorkflowExecutionService
    from apps.contacts.models import Contact

    try:
        workflow = Workflow.objects.get(id=workflow_id)
        contact = Contact.objects.get(id=contact_id)
    except (Workflow.DoesNotExist, Contact.DoesNotExist) as e:
        logger.error(f"Failed to start execution: {e}")
        return

    execution = WorkflowExecutionService.start_execution(
        workflow=workflow,
        contact=contact,
        trigger_data=trigger_data or {},
    )

    if execution:
        logger.info(f"Started execution {execution.id} for workflow {workflow.name}")
        return str(execution.id)

    return None
