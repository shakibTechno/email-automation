"""
Transactional email: the messages the platform itself sends to one person.

Distinct from campaign sending, which is batched, tracked, click-wrapped,
counted against a quota and driven by Celery. A transactional message is one
recipient, no tracking, no unsubscribe, and it has to arrive now — an invitation
or a password reset that is queued behind a campaign is a broken feature.

The connection comes from the organization when there is one, through
`EmailConfigService`, so the message arrives from a sending identity the
recipient's provider will accept. Falling back to the platform default is
deliberate but weak: that default is unconfigured in most deployments, which is
precisely why `send` reports whether it worked instead of pretending.
"""
import logging
from collections import namedtuple

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

# `error` is short, already phrased for a person, and safe to store on a row:
# it names the failure class and message, never the rendered body, which for
# these templates contains a live token.
MailResult = namedtuple('MailResult', ['ok', 'error'])


def send_transactional_email(
    *,
    subject,
    template,
    context,
    to_email,
    organization=None,
    reply_to=None,
):
    """
    Render and send one message. Returns MailResult(ok, error).

    Never raises. Every caller is a request handler whose primary job is not
    sending mail: an invitation row must still be created when the email fails,
    or the admin is left with no invitation *and* no link to share. The return
    value is how the caller tells the user the truth.
    """
    html_body = render_to_string(f'{template}.html', context)
    # Generated from the HTML rather than kept as a second template, so the two
    # cannot drift apart — a plain-text part that contradicts the HTML is worse
    # than one that is merely plainer.
    text_body = strip_tags(
        html_body.replace('</p>', '</p>\n\n').replace('<br>', '\n')
    ).strip()

    from_name, from_email = _resolve_sender(organization)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=f'{from_name} <{from_email}>' if from_name else from_email,
        to=[to_email],
        reply_to=[reply_to] if reply_to else None,
        connection=_resolve_connection(organization),
    )
    message.attach_alternative(html_body, 'text/html')

    try:
        sent = message.send(fail_silently=False)
    except Exception as exc:
        # Deliberately not re-raised, and deliberately without the message
        # body: these templates carry invitation and reset tokens, and a
        # traceback with one in it is a credential in the log file.
        logger.error(
            'Transactional email %r to %s failed: %s: %s',
            template, to_email, exc.__class__.__name__, exc,
        )
        return MailResult(False, f'{exc.__class__.__name__}: {exc}'[:500])

    if not sent:
        logger.error('Transactional email %r to %s was not accepted', template, to_email)
        return MailResult(False, 'The mail provider did not accept the message.')

    logger.info('Transactional email %r sent to %s', template, to_email)
    return MailResult(True, '')


def _resolve_sender(organization):
    if organization is None:
        return '', settings.DEFAULT_FROM_EMAIL

    from apps.email_config.services import EmailConfigService

    return EmailConfigService.get_default_from(organization)


def _resolve_connection(organization):
    """
    The organization's own connection, or the platform default.

    `None` lets Django open the default connection, which is also what
    EmailConfigService falls back to.
    """
    if organization is None:
        return None

    from apps.email_config.services import EmailConfigService

    try:
        return EmailConfigService.get_connection(organization)
    except Exception:
        logger.warning(
            'Could not build a connection for org %s; using the platform default.',
            organization.id, exc_info=True,
        )
        return None
