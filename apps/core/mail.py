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
import re
from collections import namedtuple
from html import unescape

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
    from_platform=False,
    sender_name='',
):
    """
    Render and send one message. Returns MailResult(ok, error).

    `from_platform` marks account mail — an invitation, a password reset, an
    email verification. It is about the platform and links to the platform, so
    it goes out on the platform's own domain rather than the organization's:
    tying it to a tenant's sending reputation is wrong, and an organization
    that has not verified a domain yet could not send it at all, which is
    precisely when an invitation goes out.

    Never raises. Every caller is a request handler whose primary job is not
    sending mail: an invitation row must still be created when the email fails,
    or the admin is left with no invitation *and* no link to share. The return
    value is how the caller tells the user the truth.
    """
    html_body = render_to_string(f'{template}.html', context)
    text_body = _html_to_text(html_body)

    identity = None
    if from_platform:
        identity = _platform_identity(sender_name)
    if identity is None:
        # No shared sender configured yet. The organization's own identity is
        # worse for account mail but far better than not sending it.
        identity = _resolve_identity(organization)
    if identity is not None and identity.unavailable:
        logger.error(
            'Transactional email %r to %s not sent: %s',
            template, to_email, identity.unavailable,
        )
        return MailResult(False, identity.unavailable)

    if identity is None:
        from_header = settings.DEFAULT_FROM_EMAIL
        connection, reply_to_list = None, ([reply_to] if reply_to else None)
    else:
        from_header, reply_to_list = identity.sender(
            name=sender_name, reply_to=reply_to or '',
        )
        connection = identity.connection

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_header,
        to=[to_email],
        reply_to=reply_to_list,
        connection=connection,
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


def _platform_identity(sender_name):
    """The platform's own sender, or None when none is configured."""
    from apps.email_config.services import EmailConfigService

    try:
        return EmailConfigService.platform_identity(display_name=sender_name)
    except Exception:
        logger.warning(
            'Could not build the platform sending identity; '
            "falling back to the organization's.", exc_info=True,
        )
        return None


def _resolve_identity(organization):
    """
    The organization's sending identity, or None for platform-level mail.

    None means there is no organization to resolve against -- a password reset
    before sign-in, say -- and Django's own default backend handles it.
    """
    if organization is None:
        return None

    from apps.email_config.services import EmailConfigService

    try:
        return EmailConfigService.resolve(organization)
    except Exception:
        logger.warning(
            'Could not resolve a sending identity for org %s; using the '
            'platform default.', organization.id, exc_info=True,
        )
        return None


def _html_to_text(html):
    """
    Derive the plain-text part from the HTML.

    Generated rather than kept as a second template, so the two cannot drift
    apart â€” a plain-text part that contradicts the HTML is worse than one that
    is merely plainer.

    <head> is dropped first. Without it the <title> comes through and the
    subject line appears twice at the top of the message, which is how this was
    noticed: by reading the rendered text part rather than trusting it.
    """
    body = html
    if '<body' in body:
        body = body.split('<body', 1)[1].split('>', 1)[-1]
    if '</body>' in body:
        body = body.split('</body>', 1)[0]

    # Block-level tags become blank lines so sentences do not run together.
    for tag in ('</p>', '</tr>', '</div>', '</h1>', '</h2>'):
        body = body.replace(tag, tag + '\n\n')
    for br in ('<br>', '<br/>', '<br />'):
        body = body.replace(br, '\n')

    text = unescape(strip_tags(body))
    # Collapse the whitespace that table markup leaves behind, without
    # collapsing the paragraph breaks just inserted.
    collapsed = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.splitlines()]
    out = []
    for line in collapsed:
        if line or (out and out[-1]):
            out.append(line)
    return '\n'.join(out).strip()
