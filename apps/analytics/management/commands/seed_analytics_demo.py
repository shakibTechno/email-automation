"""
Management command to seed realistic demo analytics data.

Usage:
    python manage.py seed_analytics_demo
    python manage.py seed_analytics_demo --days 90
    python manage.py seed_analytics_demo --email admin@example.com
    python manage.py seed_analytics_demo --clear
"""
import random
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

User = get_user_model()

CAMPAIGN_SUBJECTS = [
    ("Summer Sale — Up to 50% Off Everything", "Summer Promo 2024"),
    ("Your Weekly Newsletter is Here 📰", "Weekly Newsletter #42"),
    ("New Product Launch: Introducing Pro Plan", "Pro Plan Launch"),
    ("Don't miss our webinar this Thursday", "Webinar Invite - Growth Tactics"),
    ("Action required: Your trial ends soon", "Trial Expiry Reminder"),
    ("How to grow your email list by 10x", "Email Growth Guide"),
    ("Case Study: How Acme doubled their open rates", "Case Study Email"),
    ("We'd love your feedback 🙏", "Customer Feedback Survey"),
    ("Exclusive early access — just for you", "Early Access Announcement"),
    ("Monthly digest: Top articles & resources", "Monthly Digest"),
]

FAKE_CONTACTS = [
    ("Alice", "Johnson", "alice.johnson@techcorp.io", "manual", "high", 82),
    ("Bob", "Smith", "bob.smith@acmeinc.com", "import", "medium", 45),
    ("Carol", "Williams", "carol@startupxyz.com", "form", "high", 91),
    ("David", "Brown", "david@globalmedia.net", "manual", "low", 18),
    ("Emily", "Davis", "emily@brightfuture.co", "api", "medium", 60),
    ("Frank", "Miller", "frank@digitalhub.io", "integration", "high", 77),
    ("Grace", "Wilson", "grace@innovatech.com", "form", "medium", 52),
    ("Henry", "Moore", "henry@cloudnine.io", "import", "low", 25),
    ("Ivy", "Taylor", "ivy@nextstep.co", "manual", "high", 88),
    ("Jack", "Anderson", "jack@bluewavetech.com", "api", "medium", 43),
    ("Karen", "Thomas", "karen@peakperform.net", "form", "low", 12),
    ("Leo", "Jackson", "leo@rocketlaunch.io", "integration", "high", 95),
    ("Maria", "White", "maria@greenleaf.co", "manual", "medium", 58),
    ("Nathan", "Harris", "nathan@datastream.com", "import", "low", 30),
    ("Olivia", "Martin", "olivia@sparkdigital.io", "form", "high", 79),
    ("Paul", "Garcia", "paul@visionaryinc.com", "api", "medium", 47),
    ("Quinn", "Martinez", "quinn@agileworks.net", "manual", "low", 22),
    ("Rachel", "Robinson", "rachel@sunrisemedia.co", "form", "high", 83),
    ("Steve", "Clark", "steve@alphalogistics.com", "import", "medium", 55),
    ("Tina", "Lewis", "tina@cubecreative.io", "integration", "low", 15),
    ("Uma", "Walker", "uma@futurestack.io", "form", "high", 87),
    ("Victor", "Hall", "victor@nexgenio.com", "manual", "medium", 64),
    ("Wendy", "Allen", "wendy@clearpath.co", "api", "low", 10),
    ("Xander", "Young", "xander@prismtech.io", "import", "high", 76),
    ("Yara", "King", "yara@bloomsales.com", "form", "medium", 41),
    ("Zach", "Wright", "zach@apexgrowth.io", "manual", "high", 92),
    ("Amy", "Scott", "amy@lightspeed.co", "integration", "medium", 53),
    ("Ben", "Torres", "ben@orbitlabs.io", "api", "low", 8),
    ("Chloe", "Nguyen", "chloe@sunbeam.co", "form", "high", 85),
    ("Derek", "Hill", "derek@stormcloud.io", "manual", "medium", 38),
    ("Elena", "Adams", "elena@pixelcraft.co", "import", "high", 90),
    ("Felix", "Baker", "felix@northwave.io", "form", "medium", 49),
    ("Gina", "Gonzalez", "gina@boldmoves.co", "api", "low", 19),
    ("Hugo", "Nelson", "hugo@swiftrise.io", "manual", "high", 78),
    ("Iris", "Carter", "iris@clearskies.co", "integration", "medium", 62),
    ("Joel", "Mitchell", "joel@crescendo.io", "form", "low", 27),
    ("Kate", "Perez", "kate@luminex.co", "api", "high", 84),
    ("Liam", "Roberts", "liam@terrashift.io", "manual", "medium", 46),
    ("Mia", "Turner", "mia@vividmark.co", "import", "low", 14),
    ("Noah", "Phillips", "noah@cloudvault.io", "form", "high", 89),
    ("Olivia", "Campbell", "olivia.c@gridlines.co", "api", "medium", 57),
    ("Peter", "Parker", "peter@skyforge.io", "manual", "low", 23),
    ("Rita", "Evans", "rita@swiftloop.co", "integration", "high", 80),
    ("Sam", "Edwards", "sam@trailhead.io", "form", "medium", 44),
    ("Tara", "Collins", "tara@leafnode.co", "api", "low", 16),
    ("Ulysses", "Stewart", "ulysses@borealis.io", "manual", "high", 93),
    ("Vera", "Sanchez", "vera@windchime.co", "import", "medium", 50),
    ("Will", "Morris", "will@springcycle.io", "form", "low", 21),
    ("Xenia", "Rogers", "xenia@flashpoint.co", "api", "high", 75),
    ("Yasmine", "Reed", "yasmine@solarsail.io", "manual", "medium", 40),
]

DEVICE_UAS = [
    ("Desktop", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120"),
    ("Desktop", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605"),
    ("Desktop", "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/121.0"),
    ("Mobile", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile/15E148"),
    ("Mobile", "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Mobile Chrome/120"),
    ("Mobile", "Mozilla/5.0 (Linux; Android 13; Samsung SM-S918B) Mobile Chrome/119"),
    ("Tablet", "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"),
    ("Tablet", "Mozilla/5.0 (Linux; Android 13; SM-T870) AppleWebKit/537.36 Mobile Chrome/119"),
]

REFERRERS = [
    "https://www.google.com/search?q=email+marketing",
    "https://twitter.com/",
    "https://www.linkedin.com/feed/",
    "https://www.facebook.com/",
    "https://newsletter.example.com/",
    "https://blog.techcrunch.com/",
    "",  # Direct
    "",  # Direct
    "",  # Direct
]


class Command(BaseCommand):
    help = "Seed realistic demo analytics data for development/testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            help="Email of org owner to seed data for (defaults to first superuser)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Number of days of historical data to create (default: 90)",
        )
        parser.add_argument(
            "--campaigns",
            type=int,
            default=8,
            help="Number of demo campaigns to create (default: 8)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear previously seeded demo data before creating new data",
        )

    def handle(self, *args, **options):
        from apps.accounts.models import Organization
        from apps.campaigns.models import Campaign, CampaignRecipient
        from apps.contacts.models import Contact
        from apps.forms.models import Form, FormSubmission
        from apps.landing_pages.models import LandingPage, PageView

        # ── Find target user / org ────────────────────────────────────────────
        email = options.get("email")
        if email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise CommandError(f"No user found with email: {email}")
        else:
            user = User.objects.filter(is_superuser=True).order_by("date_joined").first()
            if not user:
                user = User.objects.order_by("date_joined").first()
            if not user:
                raise CommandError(
                    "No users found. Create a user first or pass --email."
                )

        organization = getattr(user, "organization", None)
        if organization is None:
            # User may have been created via createsuperuser without an org
            from apps.accounts.models import Organization
            organization = Organization.objects.first()
        if organization is None:
            raise CommandError(
                "No organizations found. Register through the app first or pass --email of "
                "a user who belongs to an organization."
            )

        self.stdout.write(f"Seeding analytics data for org: {organization.name} ({user.email})")

        days = options["days"]
        num_campaigns = min(options["campaigns"], len(CAMPAIGN_SUBJECTS))
        now = timezone.now()

        # ── Clear mode ────────────────────────────────────────────────────────
        if options["clear"]:
            demo_prefix = "[DEMO]"
            deleted_campaigns = Campaign.all_objects.filter(
                organization=organization,
                name__startswith=demo_prefix,
            ).count()
            Campaign.all_objects.filter(
                organization=organization, name__startswith=demo_prefix
            ).delete()
            self.stdout.write(f"  Cleared {deleted_campaigns} demo campaigns")

            org_page_ids = LandingPage.objects.filter(
                organization=organization
            ).values_list('id', flat=True)
            deleted_views = PageView.objects.filter(
                landing_page_id__in=org_page_ids,
                user_agent__startswith="[DEMO]",
            ).count()
            PageView.objects.filter(
                landing_page_id__in=org_page_ids,
                user_agent__startswith="[DEMO]",
            ).delete()
            self.stdout.write(f"  Cleared {deleted_views} demo page views")

        # ── Ensure contacts exist ─────────────────────────────────────────────
        self.stdout.write("Creating/updating demo contacts...")
        contacts = []
        for i, (first, last, email_addr, source, eng, score) in enumerate(FAKE_CONTACTS):
            # Spread creation over the last `days` days
            days_ago = random.randint(0, days)
            created_at = now - timedelta(days=days_ago)

            contact, _ = Contact.objects.update_or_create(
                organization=organization,
                email=email_addr,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "source": source,
                    "engagement_level": eng,
                    "lead_score": score,
                    "is_subscribed": random.random() > 0.08,  # 92% subscribed
                },
            )
            # Override created_at for realistic spread
            Contact.objects.filter(pk=contact.pk).update(created_at=created_at)
            contact.refresh_from_db()
            contacts.append(contact)

        self.stdout.write(self.style.SUCCESS(f"  {len(contacts)} contacts ready"))

        # ── Create sent campaigns with recipients ─────────────────────────────
        self.stdout.write(f"Creating {num_campaigns} demo campaigns...")
        campaign_names = random.sample(CAMPAIGN_SUBJECTS, num_campaigns)

        created_campaigns = []
        for i, (subject, name) in enumerate(campaign_names):
            # Space campaigns across the date range
            days_ago = int((i / num_campaigns) * days) + random.randint(1, 5)
            sent_dt = now - timedelta(days=days_ago)

            campaign = Campaign.objects.create(
                organization=organization,
                name=f"[DEMO] {name}",
                subject=subject,
                sender_name=organization.name,
                sender_email=user.email,
                status="sent",
                sent_at=sent_dt,
                completed_at=sent_dt + timedelta(minutes=random.randint(5, 60)),
                created_by=user,
            )

            # Create recipient records — sample 30-100 contacts
            sample_contacts = random.sample(contacts, min(random.randint(30, 70), len(contacts)))
            recipient_count = len(sample_contacts)

            # Realistic distribution:
            # ~95% delivered, ~22% opened, ~4% clicked, ~1.5% bounced
            n_bounced = max(1, int(recipient_count * random.uniform(0.01, 0.025)))
            n_opened = int((recipient_count - n_bounced) * random.uniform(0.18, 0.30))
            n_clicked = int(n_opened * random.uniform(0.15, 0.30))
            n_delivered = recipient_count - n_bounced - n_opened - n_clicked

            recipients_to_create = []
            statuses = (
                ["bounced"] * n_bounced
                + ["opened"] * n_opened
                + ["clicked"] * n_clicked
                + ["delivered"] * max(0, n_delivered)
            )
            # Pad with 'sent' if needed
            while len(statuses) < recipient_count:
                statuses.append("sent")
            random.shuffle(statuses)

            for contact, rec_status in zip(sample_contacts, statuses):
                opened_at = None
                clicked_at = None
                bounced_at = None
                recipient_sent_at = sent_dt + timedelta(seconds=random.randint(0, 300))

                if rec_status == "opened":
                    opened_at = sent_dt + timedelta(hours=random.uniform(0.5, 48))
                elif rec_status == "clicked":
                    opened_at = sent_dt + timedelta(hours=random.uniform(0.5, 24))
                    clicked_at = opened_at + timedelta(minutes=random.randint(1, 30))
                elif rec_status == "bounced":
                    bounced_at = sent_dt + timedelta(minutes=random.randint(1, 10))
                    recipient_sent_at = bounced_at

                recipients_to_create.append(
                    CampaignRecipient(
                        campaign=campaign,
                        contact=contact,
                        email=contact.email,
                        status=rec_status,
                        sent_at=recipient_sent_at,
                        opened_at=opened_at,
                        clicked_at=clicked_at,
                        bounced_at=bounced_at,
                    )
                )

            CampaignRecipient.objects.bulk_create(recipients_to_create, ignore_conflicts=True)

            # Update campaign recipient count
            Campaign.objects.filter(pk=campaign.pk).update(recipient_count=recipient_count)

            created_campaigns.append(campaign)
            self.stdout.write(
                f"  Campaign '{name}': {recipient_count} recipients, "
                f"{n_opened} opened, {n_clicked} clicked, {n_bounced} bounced"
            )

        self.stdout.write(self.style.SUCCESS(f"  {len(created_campaigns)} campaigns created"))

        # ── Create form submissions ───────────────────────────────────────────
        forms = Form.objects.filter(organization=organization, deleted_at__isnull=True)
        if forms.exists():
            self.stdout.write("Creating demo form submissions...")
            total_submissions = 0
            for form in forms[:5]:  # up to 5 forms
                num_subs = random.randint(15, 40)
                sample = random.choices(contacts, k=num_subs)
                subs_to_create = []
                for contact in sample:
                    days_ago = random.randint(0, days)
                    sub_dt = now - timedelta(days=days_ago)
                    subs_to_create.append(
                        FormSubmission(
                            form=form,
                            contact=contact,
                            data=[
                                {"field": "email", "value": contact.email},
                                {"field": "first_name", "value": contact.first_name},
                                {"field": "last_name", "value": contact.last_name},
                            ],
                        )
                    )
                FormSubmission.objects.bulk_create(subs_to_create)
                # Override created_at
                for i, sub in enumerate(
                    FormSubmission.objects.filter(form=form).order_by("-created_at")[:num_subs]
                ):
                    days_ago = random.randint(0, days)
                    FormSubmission.objects.filter(pk=sub.pk).update(
                        created_at=now - timedelta(days=days_ago)
                    )
                total_submissions += len(subs_to_create)
            self.stdout.write(self.style.SUCCESS(f"  {total_submissions} form submissions created"))
        else:
            self.stdout.write(self.style.WARNING("  No forms found — skipping form submissions"))

        # ── Create page views ─────────────────────────────────────────────────
        pages = LandingPage.objects.filter(
            organization=organization, deleted_at__isnull=True, status="published"
        )
        if pages.exists():
            self.stdout.write("Creating demo page views...")
            total_views = 0
            for page in pages[:5]:  # up to 5 pages
                num_views = random.randint(80, 300)
                views_to_create = []
                session_ids_used = set()
                for _ in range(num_views):
                    days_ago = random.randint(0, days)
                    view_dt = now - timedelta(
                        days=days_ago,
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59),
                    )
                    device_ua = random.choice(DEVICE_UAS)[1]
                    referrer = random.choice(REFERRERS)
                    session_id = str(uuid.uuid4())
                    is_unique = session_id not in session_ids_used
                    session_ids_used.add(session_id)

                    views_to_create.append(
                        PageView(
                            landing_page=page,
                            user_agent=device_ua,
                            referrer=referrer,
                            is_unique=is_unique,
                            session_id=session_id,
                        )
                    )
                PageView.objects.bulk_create(views_to_create)
                # Override created_at for time distribution
                for view in PageView.objects.filter(landing_page=page).order_by("-created_at")[:num_views]:
                    days_ago = random.randint(0, days)
                    PageView.objects.filter(pk=view.pk).update(
                        created_at=now - timedelta(
                            days=days_ago,
                            hours=random.randint(0, 23),
                            minutes=random.randint(0, 59),
                        )
                    )
                # Update the landing page aggregate counters
                actual_views = PageView.objects.filter(landing_page=page).count()
                actual_unique = PageView.objects.filter(landing_page=page, is_unique=True).count()
                LandingPage.objects.filter(pk=page.pk).update(
                    view_count=actual_views,
                    conversion_count=int(actual_unique * random.uniform(0.02, 0.08)),
                )
                total_views += len(views_to_create)
            self.stdout.write(self.style.SUCCESS(f"  {total_views} page views created"))
        else:
            self.stdout.write(
                self.style.WARNING("  No published landing pages found — skipping page views")
            )

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo analytics data seeded successfully!"))
        self.stdout.write(
            f"  Org: {organization.name}\n"
            f"  Contacts: {len(contacts)}\n"
            f"  Campaigns: {len(created_campaigns)}\n"
            f"  Data range: last {days} days\n"
        )
        self.stdout.write(
            "  Visit http://localhost:5173/analytics to see charts with real data."
        )
