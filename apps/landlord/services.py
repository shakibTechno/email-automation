"""
Cross-tenant aggregation for the landlord console.

Two rules shape everything here:

* **List views read cached columns; detail views compute live.** Per-tenant
  deliverability comes from `PostalTenant`, refreshed hourly by the
  `sync-postal-tenants` Beat task. Computing it per row instead would run
  `guardrails.measure()` once per tenant, and that query joins through
  `Campaign` because `CampaignRecipient` has no organization FK and no index on
  `sent_at` — N unindexed joins per page load.
* **Aggregates over every tenant are cached.** Cheap with one customer,
  expensive with a thousand, and the operator does not need the platform totals
  to be second-accurate.
"""
import logging
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.accounts.models import Organization, User
from apps.billing.models import Subscription
from apps.campaigns.models import Campaign, CampaignRecipient
from apps.contacts.models import Contact
from apps.email_config.models import EmailConfiguration, PostalTenant, SendingDomain
from apps.landing_pages.models import LandingDomain

logger = logging.getLogger(__name__)

OVERVIEW_CACHE_KEY = 'landlord:overview:v1'
OVERVIEW_CACHE_TTL = 300


class PlatformOverviewService:
    """Platform-wide totals and trends."""

    @staticmethod
    def get_overview(days=30, use_cache=True):
        key = f'{OVERVIEW_CACHE_KEY}:{days}'
        if use_cache:
            cached = cache.get(key)
            if cached is not None:
                return cached

        now = timezone.now()
        since = now - timedelta(days=days)

        tenants = Organization.objects.all()
        tenant_counts = tenants.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            suspended=Count('id', filter=Q(is_active=False)),
            new_in_period=Count('id', filter=Q(created_at__gte=since)),
        )

        recipients = CampaignRecipient.objects.filter(sent_at__gte=since)
        email_counts = recipients.aggregate(
            sent=Count('id'),
            delivered=Count('id', filter=CampaignRecipient.delivered_filter()),
            bounced=Count('id', filter=CampaignRecipient.bounced_filter()),
        )

        sent = email_counts['sent'] or 0
        bounced = email_counts['bounced'] or 0

        data = {
            'period_days': days,
            'tenants': tenant_counts,
            'users': User.objects.filter(is_staff=False).count(),
            'contacts': Contact.objects.count(),
            'campaigns_sent': Campaign.objects.filter(
                status='sent', sent_at__gte=since
            ).count(),
            'emails': {
                **email_counts,
                'bounce_rate': round(bounced / sent * 100, 2) if sent else 0.0,
            },
            'signups_by_day': PlatformOverviewService._signups_by_day(since, now),
            'generated_at': now.isoformat(),
        }

        cache.set(key, data, OVERVIEW_CACHE_TTL)
        return data

    @staticmethod
    def _signups_by_day(since, now):
        """A dense series — days with no signups must appear as zero, not be absent."""
        rows = (
            Organization.objects
            .filter(created_at__gte=since)
            .values_list('created_at', flat=True)
        )
        counts = {}
        for created in rows:
            counts[created.date().isoformat()] = counts.get(created.date().isoformat(), 0) + 1

        series, day = [], since.date()
        while day <= now.date():
            key = day.isoformat()
            series.append({'date': key, 'count': counts.get(key, 0)})
            day += timedelta(days=1)
        return series


class TenantService:
    """The tenant list and one tenant's detail."""

    @staticmethod
    def base_queryset():
        """
        All tenants with everything the list column set needs, pre-joined.

        select_related pulls the one-to-ones; the annotations replace what would
        otherwise be a count query per row.
        """
        # Counted with subqueries rather than Count() over joins. Two joined
        # counts in one statement cross-join their tables — an organization
        # with 5 users and 10,000 contacts materialises 50,000 rows for the
        # database to deduplicate, repeated for every tenant on the page. The
        # subqueries each aggregate independently.
        user_count = Subquery(
            User.objects.filter(organization=OuterRef('pk'))
            .order_by().values('organization')
            .annotate(n=Count('id')).values('n')[:1],
            output_field=IntegerField(),
        )
        contact_count = Subquery(
            Contact.objects.filter(organization=OuterRef('pk'))
            .order_by().values('organization')
            .annotate(n=Count('id')).values('n')[:1],
            output_field=IntegerField(),
        )

        # Same subquery shape, for the same reason. Split verified from
        # total because "connected but not working" is the state an
        # operator is asked about, and a single count hides it.
        domain_count = Subquery(
            LandingDomain.objects.filter(organization=OuterRef('pk'))
            .order_by().values('organization')
            .annotate(n=Count('id')).values('n')[:1],
            output_field=IntegerField(),
        )
        unverified_domain_count = Subquery(
            LandingDomain.objects
            .filter(organization=OuterRef('pk'))
            .exclude(status=LandingDomain.STATUS_VERIFIED)
            .order_by().values('organization')
            .annotate(n=Count('id')).values('n')[:1],
            output_field=IntegerField(),
        )

        return (
            Organization.all_objects
            .select_related('subscription__plan', 'postal_tenant', 'email_config')
            .annotate(
                user_count=Coalesce(user_count, Value(0)),
                contact_count=Coalesce(contact_count, Value(0)),
                domain_count=Coalesce(domain_count, Value(0)),
                unverified_domain_count=Coalesce(unverified_domain_count, Value(0)),
            )
            .order_by('-created_at')
        )

    @staticmethod
    def serialize_row(org):
        """One tenant as the list sees it — cached metrics only, no live queries."""
        subscription = getattr(org, 'subscription', None)
        tenant = getattr(org, 'postal_tenant', None)
        config = getattr(org, 'email_config', None)

        return {
            'id': str(org.id),
            'name': org.name,
            'slug': org.slug,
            'plan': org.plan,
            'is_active': org.is_active,
            'suspended_at': org.suspended_at.isoformat() if org.suspended_at else None,
            'suspension_reason': org.suspension_reason,
            'sending_paused': bool(config and config.sending_paused_due_to_threshold),
            'sending_pause_reason': config.sending_pause_reason if config else '',
            'users': org.user_count,
            'contacts': org.contact_count,
            'emails_used': subscription.emails_sent_this_month if subscription else 0,
            'emails_limit': subscription.plan.max_emails_per_month if subscription else 0,
            'subscription_status': subscription.status if subscription else None,
            # From PostalTenant's hourly sync, not computed per row.
            'bounce_rate_30d': float(tenant.bounce_rate_30d) if tenant else None,
            'queued': tenant.queued if tenant else 0,
            'held': tenant.held if tenant else 0,
            'mail_status': tenant.status if tenant else None,
            'landing_domains': org.domain_count,
            'landing_domains_unverified': org.unverified_domain_count,
            'created_at': org.created_at.isoformat(),
        }

    @staticmethod
    def get_detail(org):
        """One tenant in full. Live deliverability is affordable for a single row."""
        from apps.email_config import guardrails

        subscription = Subscription.objects.select_related('plan').filter(
            organization=org
        ).first()
        tenant = PostalTenant.objects.filter(organization=org).first()
        config = EmailConfiguration.objects.filter(organization=org).first()

        return {
            **TenantService.serialize_row(
                TenantService.base_queryset().get(pk=org.pk)
            ),
            'email': org.email,
            'deliverability': guardrails.measure(org),
            'thresholds': {
                'bounce_pct': float(config.bounce_threshold_pct) if config else None,
                'complaint_pct': float(config.complaint_threshold_pct) if config else None,
            },
            'from_identity': {
                'name': config.from_name if config else '',
                'email': config.from_email if config else '',
            } if config else None,
            'mail_server': {
                'external_id': tenant.external_id,
                'status': tenant.status,
                'suspension_reason': tenant.suspension_reason,
                'send_limit_per_hour': tenant.send_limit_per_hour,
                'sent_last_hour': tenant.sent_last_hour,
                'last_synced_at': tenant.last_synced_at.isoformat() if tenant.last_synced_at else None,
            } if tenant else None,
            # Landing-page domains, which are not the same thing as the
            # sending domains below — a customer may well use
            # mail.brand.com and go.brand.com for different jobs, and
            # "my domain is broken" could mean either.
            'landing_domains_detail': [
                {
                    'domain': d.domain,
                    'status': d.status,
                    'is_primary': d.is_primary,
                    'last_check_error': d.last_check_error,
                    'verified_at': d.verified_at.isoformat() if d.verified_at else None,
                    'last_seen_at': d.last_seen_at.isoformat() if d.last_seen_at else None,
                }
                for d in LandingDomain.objects.filter(organization=org).order_by('-is_primary', 'domain')
            ],
            'domains': [
                {
                    'domain': d.domain,
                    'status': d.status,
                    'sending_enabled': d.sending_enabled,
                    'verified_at': d.verified_at.isoformat() if d.verified_at else None,
                }
                for d in SendingDomain.objects.filter(organization=org).order_by('domain')
            ],
            'billing': {
                'plan': subscription.plan.plan_type,
                'status': subscription.status,
                'interval': subscription.interval,
                'trial_end': subscription.trial_end.isoformat() if subscription.trial_end else None,
                'current_period_end': (
                    subscription.current_period_end.isoformat()
                    if subscription.current_period_end else None
                ),
                'price': float(subscription.plan.price),
            } if subscription else None,
            # Deliberately not 'users': the row above already uses that key for
            # the count, and shadowing a number with a list is how a field ends
            # up meaning two things depending on which endpoint served it.
            'members': [
                {
                    'id': str(u.id),
                    'email': u.email,
                    'full_name': u.full_name,
                    'role': u.role,
                    'is_active': u.is_active,
                    'last_login': u.last_login.isoformat() if u.last_login else None,
                }
                for u in User.objects.filter(organization=org).order_by('-created_at')
            ],
            'recent_campaigns': [
                {
                    'id': str(c.id),
                    'name': c.name,
                    'status': c.status,
                    'recipient_count': c.recipient_count,
                    'sent_at': c.sent_at.isoformat() if c.sent_at else None,
                }
                for c in Campaign.objects.filter(organization=org).order_by('-created_at')[:10]
            ],
        }


class DeliverabilityService:
    """
    Who is putting the shared sending IP at risk.

    Every tenant sends through one Postal server on one address, so this is the
    view that cannot be assembled from any single tenant's dashboard.
    """

    @staticmethod
    def get_risk_board():
        rows = []
        for tenant in PostalTenant.objects.select_related(
            'organization', 'organization__email_config'
        ):
            org = tenant.organization
            config = getattr(org, 'email_config', None)
            bounce_limit = float(config.bounce_threshold_pct) if config else 5.0
            bounce_rate = float(tenant.bounce_rate_30d)

            # Unverified domains are a soft signal: a tenant adding domains it
            # cannot prove it owns is worth a look, even before it sends.
            unverified = SendingDomain.objects.filter(
                organization=org, sending_enabled=False
            ).count()

            rows.append({
                'organization_id': str(org.id),
                'organization_name': org.name,
                'plan': org.plan,
                'is_active': org.is_active,
                'mail_status': tenant.status,
                'suspension_reason': tenant.suspension_reason,
                'bounce_rate_30d': bounce_rate,
                'bounce_threshold': bounce_limit,
                'over_threshold': bounce_rate > bounce_limit,
                'sending_paused': bool(config and config.sending_paused_due_to_threshold),
                'sent_last_hour': tenant.sent_last_hour,
                'queued': tenant.queued,
                # Held mail does not move again without intervention — a
                # non-zero count is a tenant quietly failing to deliver.
                'held': tenant.held,
                'unverified_domains': unverified,
                'last_synced_at': tenant.last_synced_at.isoformat() if tenant.last_synced_at else None,
                'risk_score': DeliverabilityService._risk_score(
                    bounce_rate, bounce_limit, tenant.held, tenant.status
                ),
            })

        rows.sort(key=lambda r: r['risk_score'], reverse=True)
        return rows

    @staticmethod
    def _risk_score(bounce_rate, bounce_limit, held, mail_status):
        """
        A blunt ordering for the board, not a measurement.

        Its only job is to put the tenant most likely to damage the shared IP at
        the top. Exact values are meaningless; the ranking is the point.
        """
        score = 0.0
        if bounce_limit and bounce_rate > bounce_limit:
            score += 100 + (bounce_rate - bounce_limit) * 10
        else:
            score += bounce_rate
        if held:
            score += min(held, 50)
        if mail_status == PostalTenant.STATUS_SUSPENDED:
            score += 25
        return round(score, 2)


class RevenueService:
    """Subscription and plan state across all tenants."""

    @staticmethod
    def get_revenue():
        now = timezone.now()
        subscriptions = Subscription.objects.select_related('plan', 'organization')

        by_plan, mrr = {}, 0.0
        for sub in subscriptions:
            plan_type = sub.plan.plan_type
            bucket = by_plan.setdefault(
                plan_type, {'plan': plan_type, 'count': 0, 'mrr': 0.0}
            )
            bucket['count'] += 1
            # Normalise annual subscriptions to a monthly figure, or a yearly
            # price counted whole overstates MRR twelvefold.
            #
            # Plan.monthly_equivalent keys off the *plan's* interval, and only
            # monthly plan rows are seeded — an annual subscription points at a
            # monthly row carrying an annual_price — so it would return the
            # monthly price here. The division is done against the subscription's
            # own interval instead.
            if sub.interval == 'year' and sub.plan.annual_price:
                monthly = float(sub.plan.annual_price) / 12
            else:
                monthly = float(sub.plan.price)
            if sub.status in ('active', 'trialing'):
                bucket['mrr'] += monthly
                mrr += monthly

        trials_ending = [
            {
                'organization_id': str(s.organization.id),
                'organization_name': s.organization.name,
                'trial_end': s.trial_end.isoformat(),
                'days_left': max(0, (s.trial_end - now).days),
            }
            for s in subscriptions.filter(
                status='trialing',
                trial_end__gte=now,
                trial_end__lte=now + timedelta(days=7),
            ).order_by('trial_end')
        ]

        at_risk = [
            {
                'organization_id': str(s.organization.id),
                'organization_name': s.organization.name,
                'status': s.status,
                'plan': s.plan.plan_type,
            }
            for s in subscriptions.filter(status__in=('past_due', 'incomplete'))
        ]

        near_quota = [
            {
                'organization_id': str(s.organization.id),
                'organization_name': s.organization.name,
                'used': s.emails_sent_this_month,
                'limit': s.plan.max_emails_per_month,
                'percent': s.emails_usage_percent,
            }
            for s in subscriptions
            if s.plan.max_emails_per_month and s.emails_usage_percent >= 80
        ]

        return {
            'mrr': round(mrr, 2),
            'by_plan': sorted(by_plan.values(), key=lambda b: b['mrr'], reverse=True),
            'paying_tenants': subscriptions.filter(
                status='active'
            ).exclude(plan__plan_type='free').count(),
            'trials_ending': trials_ending,
            'at_risk': at_risk,
            'near_quota': sorted(near_quota, key=lambda r: r['percent'], reverse=True),
        }


class SuspensionService:
    """
    Two independent levels of stop.

    Sending suspension stops mail but leaves the tenant able to log in, see
    their data and fix their billing. Account suspension additionally refuses
    login and the API. Both are reversible in one call, because a suspension
    applied in error must cost nothing to undo.
    """

    @staticmethod
    def suspend_sending(organization, reason, actor=None):
        from apps.email_config.provisioning import PostalProvisioningService
        from apps.email_config.services import EmailConfigService

        config = EmailConfigService.get_or_create(organization)
        config.sending_paused_due_to_threshold = True
        config.sending_pause_reason = reason
        config.sending_paused_at = timezone.now()
        config.save(update_fields=[
            'sending_paused_due_to_threshold', 'sending_pause_reason',
            'sending_paused_at', 'updated_at',
        ])

        # Also stop it at the mail server, or queued mail keeps going out even
        # though the platform believes sending is paused.
        tenant = PostalProvisioningService.get_tenant(organization)
        if tenant and tenant.postal_tenant_id and not tenant.is_suspended:
            try:
                PostalProvisioningService.suspend(tenant, reason)
            except Exception:
                logger.exception(
                    'Paused sending for org %s but could not suspend its mail server',
                    organization.id,
                )

        SuspensionService._log(organization, actor, 'sending_suspended', reason)
        return config

    @staticmethod
    def resume_sending(organization, actor=None):
        from apps.email_config.provisioning import PostalProvisioningService
        from apps.email_config.services import EmailConfigService

        config = EmailConfigService.get_or_create(organization)
        config.sending_paused_due_to_threshold = False
        config.sending_pause_reason = ''
        config.sending_paused_at = None
        config.save(update_fields=[
            'sending_paused_due_to_threshold', 'sending_pause_reason',
            'sending_paused_at', 'updated_at',
        ])

        tenant = PostalProvisioningService.get_tenant(organization)
        if tenant and tenant.postal_tenant_id and tenant.is_suspended:
            try:
                PostalProvisioningService.unsuspend(tenant)
            except Exception:
                logger.exception(
                    'Resumed sending for org %s but could not unsuspend its mail server',
                    organization.id,
                )

        SuspensionService._log(organization, actor, 'sending_resumed', '')
        return config

    @staticmethod
    def suspend_account(organization, reason, actor=None):
        """Account suspension implies sending suspension."""
        organization.is_active = False
        organization.suspended_at = timezone.now()
        organization.suspension_reason = reason
        organization.save(update_fields=[
            'is_active', 'suspended_at', 'suspension_reason', 'updated_at',
        ])
        SuspensionService.suspend_sending(organization, reason, actor=actor)
        SuspensionService._log(organization, actor, 'account_suspended', reason)
        return organization

    @staticmethod
    def restore_account(organization, actor=None, resume_sending=True):
        """
        Restore access. Sending is resumed too unless asked otherwise — a tenant
        suspended for a deliverability problem may need its access back while
        its mail stays stopped.
        """
        organization.is_active = True
        organization.suspended_at = None
        organization.suspension_reason = ''
        organization.save(update_fields=[
            'is_active', 'suspended_at', 'suspension_reason', 'updated_at',
        ])
        if resume_sending:
            SuspensionService.resume_sending(organization, actor=actor)
        SuspensionService._log(organization, actor, 'account_restored', '')
        return organization

    @staticmethod
    def _log(organization, actor, action, reason):
        """Suspension is consequential and contested; record who did it."""
        try:
            from apps.accounts.models import ActivityLog
            ActivityLog.objects.create(
                organization=organization,
                user=actor if actor and actor.is_authenticated else None,
                action=action,
                target_email=getattr(actor, 'email', '') or '',
                details={'reason': reason} if reason else {},
            )
        except Exception:
            logger.exception('Could not write an activity log entry for %s', action)
