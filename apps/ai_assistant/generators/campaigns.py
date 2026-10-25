"""
Campaign generation.

A Campaign holds the subject, the preheader and a link to an EmailTemplate —
the body lives in the template. So one description produces both: the email
itself, and the draft campaign it will be sent from.

Audience and send time stay manual. Those are the decisions with consequences,
and the point is a draft that is ready for them, not a campaign that sends
itself.
"""
import logging

from django.db import transaction

from apps.ai_assistant.generators import email_templates
from apps.campaigns.models import Campaign

logger = logging.getLogger(__name__)

# A campaign is an email plus a name to find it by, so the schema is the email
# schema with one more field.
SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['name', 'subject', 'preheader', 'blocks'],
    'properties': {
        **email_templates.SCHEMA['properties'],
        'name': {
            'type': 'string',
            'description': 'Internal campaign name, 2-5 words. Not shown to recipients.',
        },
    },
}

SYSTEM_PROMPT = email_templates.SYSTEM_PROMPT + """

The `name` is how the campaign is found in a list later — short and factual \
("Q3 webinar invite"), not a subject line.\
"""


def build_user_prompt(*, prompt: str, audience: str = '') -> str:
    parts = [f'Write an email campaign about:\n\n{prompt.strip()}']
    if audience.strip():
        parts.append(f'It is going to: {audience.strip()}')
    return '\n\n'.join(parts)


validate = email_templates.validate


@transaction.atomic
def create(job, payload: dict) -> Campaign:
    # The template carries the body; the campaign carries the envelope.
    template = email_templates.create(job, payload)

    campaign = Campaign.objects.create(
        organization=job.organization,
        name=(payload.get('name') or job.prompt)[:255].strip() or 'Untitled campaign',
        status='draft',
        template=template,
        subject=(payload.get('subject') or '')[:255],
        preheader_text=(payload.get('preheader') or '')[:255],
        created_by=job.created_by,
    )

    # The job's own FK is set by the service from `kind`, which is `campaign`;
    # recording the template too means the generated email is reachable from
    # the job without going through the campaign.
    job.email_template = template

    logger.info(f'Generated campaign {campaign.id} with template {template.id}')
    return campaign
