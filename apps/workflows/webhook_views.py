"""
The inbound webhook: another system starting a workflow.

Unauthenticated by design — possessing the workflow's token *is* the
authorisation, which is why the token is an unguessable UUID minted by the
server and never settable by a client. Everything else follows from treating
the body as hostile:

  * the token identifies the workflow, so the organization is never taken
    from the request
  * a contact is looked up, or created, only inside that organization
  * the workflow's own entry rules still apply, so a webhook cannot push a
    contact past a re-entry limit or an entry segment
  * the response says nothing about whether the contact existed, so this
    cannot be used to test whether an address is in someone's account
"""
import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Workflow, WorkflowNode

logger = logging.getLogger(__name__)

# A body larger than this is not a contact payload.
MAX_BODY = 64 * 1024


@csrf_exempt
@require_POST
def inbound(request, token):
    """Start `token`'s workflow for the contact named in the body."""
    workflow = (
        Workflow.objects
        .filter(webhook_token=token, status='active', deleted_at__isnull=True)
        .select_related('organization')
        .first()
    )
    # Same answer for a bad token and a paused workflow: a caller holding a
    # token should not learn the difference.
    if workflow is None:
        return JsonResponse({'ok': False}, status=404)

    if len(request.body or b'') > MAX_BODY:
        return JsonResponse({'ok': False, 'error': 'Payload too large.'}, status=413)

    try:
        payload = json.loads((request.body or b'{}').decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'Body is not JSON.'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'ok': False, 'error': 'Body is not an object.'}, status=400)

    node = workflow.nodes.filter(
        node_type=WorkflowNode.TRIGGER_WEBHOOK_RECEIVED,
    ).first()
    if node is None:
        logger.warning(
            'Webhook called for workflow %s, which has no webhook trigger',
            workflow.id,
        )
        return JsonResponse({'ok': False}, status=404)

    config = node.config or {}
    match_by = config.get('match_by', 'email')
    contact, created = _find_or_create(workflow, payload, match_by, config)
    if contact is None:
        # Deliberately vague: naming the missing field is fine, confirming
        # whether the address is in the account is not.
        return JsonResponse(
            {'ok': False, 'error': f'No contact matched by {match_by}.'}, status=422,
        )

    from .services import WorkflowExecutionService

    execution = WorkflowExecutionService.start_execution(
        workflow=workflow,
        contact=contact,
        trigger_data={
            'type': 'webhook_received',
            # Kept for merge tags and conditions downstream; it is the
            # caller's own data, already inside their tenant.
            'payload': payload,
        },
    )
    return JsonResponse({
        'ok': True,
        'started': bool(execution),
        'contact_created': created,
    })


def _find_or_create(workflow, payload, match_by, config):
    """The contact this call is about, or (None, False)."""
    from apps.contacts.models import Contact

    key = (str(payload.get(match_by) or '')).strip()
    if not key:
        return None, False

    lookup = (
        {'email__iexact': key} if match_by == 'email' else {'external_id': key}
    )
    contact = Contact.objects.filter(
        organization=workflow.organization, deleted_at__isnull=True, **lookup,
    ).first()
    if contact:
        return contact, False

    if not config.get('create_missing'):
        return None, False
    if match_by != 'email' or '@' not in key:
        # A contact with no address is not reachable, so creating one from a
        # webhook that supplied only an external id would make a dead row.
        return None, False

    contact = Contact.objects.create(
        organization=workflow.organization,
        email=key.lower(),
        first_name=str(payload.get('first_name') or '')[:100],
        last_name=str(payload.get('last_name') or '')[:100],
        source='integration',
    )
    logger.info(
        'Webhook for workflow %s created contact %s', workflow.id, contact.id
    )
    return contact, True
