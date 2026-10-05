"""
Custom SMTP email backend that bypasses SSL certificate hostname verification.

Namecheap shared hosting issues SSL certs for the physical server hostname
(e.g. server123.web-hosting.com), not the customer domain (mail.soha.systems),
so Python's default ssl.create_default_context() rejects the connection.

This backend pre-populates the `ssl_context` cached_property with an
unverified context so the parent class uses it transparently.

Safe for development / shared-hosting environments.
Do NOT use this if you control the server and can install a proper certificate.
"""
import ssl

from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPBackend


class UnverifiedSSLEmailBackend(DjangoSMTPBackend):
    """SMTP backend that skips SSL certificate/hostname verification."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate the cached_property so the parent open() uses our context
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.__dict__["ssl_context"] = ctx
