"""
Django email backend that sends through Postal's HTTP API.

This exists so that nothing in the campaign or sequence send path has to
change. Those paths already resolve a per-organization connection through
EmailConfigService.get_connection() and then call msg.send() once per
recipient, which Django turns into connection.send_messages([msg]) — exactly
Postal's "one API call per recipient" rule (mailstack/INTEGRATION.md §2).

The HTTP API is used rather than Postal's SMTP listener because it returns a
per-recipient id and token immediately, and because Postal's SMTP listener has
TLS off by default (INTEGRATION.md §7).
"""
import logging

from django.core.mail.backends.base import BaseEmailBackend

from .postal_client import PostalError, html_to_text, send_message

logger = logging.getLogger(__name__)

# Headers the campaign task already sets, used to tag messages so Postal echoes
# the campaign back on every webhook.
_TAG_HEADERS = ('X-Campaign-ID', 'X-Sequence-ID')


class PostalEmailBackend(BaseEmailBackend):
    """
    Sends each message through POST /api/v1/send/message.

    After send_messages() the caller can read `message.postal_status`
    ({'postal_id', 'token', 'message_id'}) off each message it passed in, the
    same way Anymail exposes `message.anymail_status`. CampaignRecipient stores
    postal_id and token, which are the only reliable key for matching webhooks.
    """

    def __init__(self, api_key=None, base_url=None, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.api_key = api_key
        self.base_url = base_url

    # No persistent connection to manage: each message is its own HTTPS call.
    def open(self):
        return False

    def close(self):
        return None

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent = 0
        for message in email_messages:
            try:
                if self._send(message):
                    sent += 1
            except PostalError:
                if not self.fail_silently:
                    raise
            except Exception:
                if not self.fail_silently:
                    raise
                logger.exception('Unexpected error sending a message through Postal')
        return sent

    # ------------------------------------------------------------------ internal
    def _send(self, message):
        recipients = self._recipients(message)
        if not recipients:
            return False

        html, text = self._bodies(message)
        headers = dict(getattr(message, 'extra_headers', None) or {})
        reply_to = ', '.join(message.reply_to) if getattr(message, 'reply_to', None) else None
        tag = self._tag(message, headers)

        results = []
        for address in recipients:
            results.append(send_message(
                api_key=self.api_key,
                to=address,
                from_=message.from_email,
                subject=message.subject,
                html=html,
                text=text,
                reply_to=reply_to,
                tag=tag,
                headers=headers,
                attachments=self._attachments(message),
                base_url=self.base_url,
            ))

        # Expose the result for the caller to persist. postal_status is the
        # single-recipient case, which is every campaign and sequence send.
        message.postal_statuses = results
        message.postal_status = results[0] if results else None
        return True

    @staticmethod
    def _recipients(message):
        """
        One address per API call.

        Postal accepts several addresses in `to`, but that would show every
        recipient the others and give them a shared unsubscribe link, so cc and
        bcc are expanded into individual sends rather than passed through.
        """
        seen, addresses = set(), []
        for address in list(message.to or []) + list(message.cc or []) + list(message.bcc or []):
            if address and address not in seen:
                seen.add(address)
                addresses.append(address)
        return addresses

    @staticmethod
    def _bodies(message):
        """
        Pull the HTML and text parts out of either message shape in use here:
        EmailMessage with content_subtype='html' (campaigns), or
        EmailMultiAlternatives with an empty body and an HTML alternative
        (sequences).
        """
        html, text = '', ''
        if getattr(message, 'content_subtype', 'plain') == 'html':
            html = message.body or ''
        else:
            text = message.body or ''

        for content, mimetype in getattr(message, 'alternatives', None) or []:
            if mimetype == 'text/html':
                html = content

        # Postal wants both parts. Campaign mail is HTML-only, so derive text.
        if html and not text:
            text = html_to_text(html)
        return html, text

    @staticmethod
    def _tag(message, headers):
        """
        The Postal `tag`, echoed back on every webhook for this message.

        An explicit `message.postal_tag` wins; otherwise it comes from the
        campaign/sequence header the sending task already sets.
        """
        explicit = getattr(message, 'postal_tag', None)
        if explicit:
            return str(explicit)
        for header in _TAG_HEADERS:
            if headers.get(header):
                return str(headers[header])
        return None

    @staticmethod
    def _attachments(message):
        """Convert Django attachments to Postal's {name, content_type, data} form."""
        import base64

        payload = []
        for attachment in getattr(message, 'attachments', None) or []:
            # Django stores either (filename, content, mimetype) or a MIMEBase.
            if not isinstance(attachment, (tuple, list)) or len(attachment) != 3:
                continue
            name, content, mimetype = attachment
            if isinstance(content, str):
                content = content.encode('utf-8')
            payload.append({
                'name': name,
                'content_type': mimetype or 'application/octet-stream',
                'data': base64.b64encode(content).decode('ascii'),
            })
        return payload
