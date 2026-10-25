"""
Keeping the domain lookup cache honest.

`domains.resolve_domain` is cached for five minutes because it runs on every
request to a connected domain. That is fine for traffic and wrong for changes:
a domain that was just disconnected, or whose organization was just suspended,
would keep serving for up to five minutes. These handlers close that window.
"""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .domains import forget_domain
from .models import LandingDomain


@receiver(post_save, sender=LandingDomain)
def forget_saved_domain(sender, instance, **kwargs):
    forget_domain(instance.domain)


@receiver(post_delete, sender=LandingDomain)
def forget_deleted_domain(sender, instance, **kwargs):
    forget_domain(instance.domain)


@receiver(post_save, sender='accounts.Organization')
def forget_domains_for_organization(sender, instance, **kwargs):
    """
    Suspending an organization must stop its domains serving immediately.

    The cached row carries the organization's active state, so without this a
    suspended tenant's pages stay up until the entry expires.
    """
    for domain in LandingDomain.objects.filter(
        organization_id=instance.pk
    ).values_list('domain', flat=True):
        forget_domain(domain)
