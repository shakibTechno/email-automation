"""
Services for the Landing Pages app.
"""
import hashlib
import logging
import re
from datetime import timedelta
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, F, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import LandingPage, LandingPageTemplate, PageView

logger = logging.getLogger(__name__)

# Matches the src of a form embed, which the builder writes as an iframe
# pointing at the public form route. Keying on the `/f/<uuid>` shape rather
# than parsing the document keeps this precise without pulling in an HTML
# parser: that path is ours, and nothing else in a page looks like it.
FORM_EMBED_SRC_RE = re.compile(
    r"""(?P<head>\ssrc=["'])"""
    r"""(?P<origin>https?://[^"'/]+)?"""
    r"""/f/(?P<form_id>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"""
    r"""-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"""
    r"""(?P<query>\?[^"']*)?"""
    r"""(?P<tail>["'])"""
)

# Query parameter carrying the landing page a form was submitted from.
LANDING_PAGE_PARAM = 'lp'


class LandingPageService:
    """Service class for landing page operations."""

    @staticmethod
    @transaction.atomic
    def publish_page(landing_page: LandingPage) -> LandingPage:
        """
        Publish a landing page.

        Args:
            landing_page: The landing page to publish

        Returns:
            Updated landing page
        """
        if not landing_page.html_content and not landing_page.design_json:
            raise ValueError("Cannot publish a page without content.")

        landing_page.status = 'published'
        landing_page.published_at = timezone.now()
        landing_page.save(update_fields=['status', 'published_at', 'updated_at'])

        logger.info(f"Published landing page: {landing_page.id}")
        return landing_page

    @staticmethod
    @transaction.atomic
    def unpublish_page(landing_page: LandingPage) -> LandingPage:
        """
        Unpublish a landing page.

        Args:
            landing_page: The landing page to unpublish

        Returns:
            Updated landing page
        """
        landing_page.status = 'draft'
        landing_page.save(update_fields=['status', 'updated_at'])

        logger.info(f"Unpublished landing page: {landing_page.id}")
        return landing_page

    @staticmethod
    @transaction.atomic
    def duplicate_page(landing_page: LandingPage, user) -> LandingPage:
        """
        Duplicate a landing page.

        Args:
            landing_page: The landing page to duplicate
            user: The user performing the duplication

        Returns:
            New duplicated landing page
        """
        # Generate unique name
        base_name = f"{landing_page.name} (Copy)"
        name = base_name
        counter = 1
        while LandingPage.objects.filter(
            organization=landing_page.organization,
            name=name
        ).exists():
            counter += 1
            name = f"{landing_page.name} (Copy {counter})"

        # Create clone
        clone = LandingPage.objects.create(
            organization=landing_page.organization,
            name=name,
            status='draft',
            html_content=landing_page.html_content,
            design_json=landing_page.design_json,
            css_content=landing_page.css_content,
            seo_title=landing_page.seo_title,
            seo_description=landing_page.seo_description,
            seo_keywords=landing_page.seo_keywords,
            google_analytics_id=landing_page.google_analytics_id,
            facebook_pixel_id=landing_page.facebook_pixel_id,
            custom_head_code=landing_page.custom_head_code,
            custom_body_code=landing_page.custom_body_code,
            form=landing_page.form,
            created_by=user,
        )

        logger.info(f"Duplicated landing page {landing_page.id} to {clone.id}")
        return clone

    @staticmethod
    def _embedded_form_body(landing_page: LandingPage) -> str:
        """
        Return the page body with every embedded form's iframe URL corrected.

        The builder writes the embed with `window.location.origin` baked in, so
        the saved HTML carries whatever origin the page happened to be edited
        from -- in development that freezes the Vite dev server into the stored
        markup. Rewriting at render time means the published page always points
        at the configured frontend, and existing pages are fixed without having
        to touch their saved HTML.

        The same pass tags each embed with the landing page it is served from,
        which is what lets a submission be attributed back here as a conversion.
        """
        frontend_url = settings.FRONTEND_URL.rstrip('/')

        def rewrite(match: 're.Match') -> str:
            query = parse_qs(match.group('query')[1:]) if match.group('query') else {}
            query[LANDING_PAGE_PARAM] = [str(landing_page.id)]
            return (
                f"{match.group('head')}"
                f"{frontend_url}/f/{match.group('form_id')}"
                f"?{urlencode(query, doseq=True)}"
                f"{match.group('tail')}"
            )

        return FORM_EMBED_SRC_RE.sub(rewrite, landing_page.html_content or '')

    @staticmethod
    def record_form_conversion(organization, source_url: str) -> bool:
        """
        Count a form submission as a conversion on the page it came from.

        `source_url` is the address of the page the form was submitted from,
        which for an embedded form is the form route carrying `?lp=<page id>`
        (see `_embedded_form_body`). Scoped to the submitting form's own
        organization so a hand-edited `lp` cannot touch another tenant's page.

        Returns True when a page was credited. Never raises: a conversion that
        cannot be attributed must not cost the visitor their submission.
        """
        if not source_url:
            return False

        try:
            page_ids = parse_qs(urlparse(source_url).query).get(LANDING_PAGE_PARAM)
            if not page_ids:
                return False

            updated = LandingPage.objects.filter(
                id=page_ids[0],
                organization=organization,
            ).update(conversion_count=F('conversion_count') + 1)

            if updated:
                logger.info(
                    f"Recorded landing page conversion: {page_ids[0]}"
                )
            return bool(updated)
        except (ValueError, TypeError, ValidationError) as exc:
            # A malformed or non-UUID `lp` is visitor-supplied data, not a bug.
            logger.debug(f"Could not attribute conversion from {source_url!r}: {exc}")
            return False

    @staticmethod
    def render_page_html(landing_page: LandingPage) -> str:
        """
        Render the complete HTML document for a landing page.

        Args:
            landing_page: The landing page to render

        Returns:
            Complete HTML string
        """
        title = landing_page.seo_title or landing_page.name
        description = landing_page.seo_description or ''
        keywords = landing_page.seo_keywords or ''
        body_html = LandingPageService._embedded_form_body(landing_page)

        # Build favicon tag
        favicon_tag = ''
        if landing_page.favicon:
            favicon_tag = f'<link rel="icon" href="{landing_page.favicon.url}">'

        # Build OG tags
        og_tags = f'''
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{landing_page.public_url}">'''
        if landing_page.og_image:
            og_tags += f'\n    <meta property="og:image" content="{landing_page.og_image.url}">'

        # Build analytics scripts
        analytics_scripts = ''
        if landing_page.google_analytics_id:
            analytics_scripts += f'''
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={landing_page.google_analytics_id}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{landing_page.google_analytics_id}');
    </script>'''

        if landing_page.facebook_pixel_id:
            analytics_scripts += f'''
    <!-- Facebook Pixel -->
    <script>
      !function(f,b,e,v,n,t,s){{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
      n.callMethod.apply(n,arguments):n.queue.push(arguments)}};if(!f._fbq)f._fbq=n;
      n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
      t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}}(window,
      document,'script','https://connect.facebook.net/en_US/fbevents.js');
      fbq('init', '{landing_page.facebook_pixel_id}');
      fbq('track', 'PageView');
    </script>
    <noscript><img height="1" width="1" style="display:none"
      src="https://www.facebook.com/tr?id={landing_page.facebook_pixel_id}&ev=PageView&noscript=1"/>
    </noscript>'''

        # Build the complete HTML document
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{description}">
    <meta name="keywords" content="{keywords}">
    {favicon_tag}
    {og_tags}
    <!-- Tailwind CSS for GrapesJS blocks -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Font Awesome for icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    {analytics_scripts}
    {landing_page.custom_head_code}
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; }}
        /* Smooth scrolling */
        html {{ scroll-behavior: smooth; }}
        /* Ensure images are responsive */
        img {{ max-width: 100%; height: auto; }}
        /* Custom CSS from editor */
        {landing_page.css_content}
    </style>
</head>
<body>
    {body_html}
    {landing_page.custom_body_code}
</body>
</html>'''

        return html


class LandingPageAnalyticsService:
    """Service class for landing page analytics."""

    @staticmethod
    def record_page_view(landing_page: LandingPage, request) -> PageView:
        """
        Record a page view for analytics.

        Args:
            landing_page: The landing page being viewed
            request: The HTTP request object

        Returns:
            Created PageView instance
        """
        # Extract request data
        ip_address = LandingPageAnalyticsService._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        referrer = request.META.get('HTTP_REFERER', '')[:2000]

        # Generate or get session ID
        session_id = LandingPageAnalyticsService._get_or_create_session_id(
            request, landing_page.id
        )

        # Check if this is a unique view (first in this session for this page)
        is_unique = not PageView.objects.filter(
            landing_page=landing_page,
            session_id=session_id
        ).exists()

        # Create page view record
        page_view = PageView.objects.create(
            landing_page=landing_page,
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer,
            session_id=session_id,
            is_unique=is_unique
        )

        # Update cached view count
        if is_unique:
            landing_page.view_count += 1
            landing_page.save(update_fields=['view_count'])

        return page_view

    @staticmethod
    def _get_client_ip(request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    @staticmethod
    def _get_or_create_session_id(request, page_id) -> str:
        """Generate a session ID for tracking unique visitors."""
        # Create a hash based on IP + User Agent + Page ID + Date
        ip = LandingPageAnalyticsService._get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')
        date_str = timezone.now().strftime('%Y-%m-%d')
        raw = f"{ip}:{ua}:{page_id}:{date_str}"
        return hashlib.sha256(raw.encode()).hexdigest()[:64]

    @staticmethod
    def get_page_analytics(landing_page: LandingPage, days: int = 30) -> dict:
        """
        Get analytics data for a landing page.

        Args:
            landing_page: The landing page
            days: Number of days to look back

        Returns:
            Dict with analytics data
        """
        start_date = timezone.now() - timedelta(days=days)

        # Get views by date
        views_by_date = (
            PageView.objects
            .filter(
                landing_page=landing_page,
                created_at__gte=start_date
            )
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                total_views=Count('id'),
                unique_views=Count('id', filter=Q(is_unique=True))
            )
            .order_by('date')
        )

        # Calculate totals
        total_views = sum(v['total_views'] for v in views_by_date)
        unique_views = sum(v['unique_views'] for v in views_by_date)

        # Get conversion count (form submissions on this page)
        conversion_count = landing_page.conversion_count

        # Calculate conversion rate
        conversion_rate = 0
        if unique_views > 0:
            conversion_rate = round((conversion_count / unique_views) * 100, 2)

        return {
            'total_views': total_views,
            'unique_views': unique_views,
            'conversion_count': conversion_count,
            'conversion_rate': conversion_rate,
            'views_by_date': [
                {
                    'date': v['date'].isoformat(),
                    'views': v['total_views'],
                    'unique_views': v['unique_views']
                }
                for v in views_by_date
            ]
        }


class LandingPageTemplateService:
    """Service class for landing page templates."""

    @staticmethod
    @transaction.atomic
    def create_from_template(
        template: LandingPageTemplate,
        organization,
        user,
        name: str,
        slug: str = None
    ) -> LandingPage:
        """
        Create a new landing page from a template.

        Args:
            template: The template to use
            organization: The organization
            user: The user creating the page
            name: Name for the new page
            slug: Optional custom slug

        Returns:
            New LandingPage instance
        """
        landing_page = LandingPage.objects.create(
            organization=organization,
            name=name,
            slug=slug or '',
            status='draft',
            html_content=template.html_content,
            design_json=template.design_json,
            css_content=template.css_content,
            created_by=user,
        )

        # Increment template usage count
        template.usage_count += 1
        template.save(update_fields=['usage_count'])

        logger.info(f"Created landing page {landing_page.id} from template {template.id}")
        return landing_page

    @staticmethod
    @transaction.atomic
    def save_as_template(
        landing_page: LandingPage,
        name: str,
        category: str,
        description: str = ''
    ) -> LandingPageTemplate:
        """
        Save a landing page as a reusable template.

        Args:
            landing_page: The landing page to save as template
            name: Name for the template
            category: Template category
            description: Optional description

        Returns:
            New LandingPageTemplate instance
        """
        template = LandingPageTemplate.objects.create(
            organization=landing_page.organization,
            name=name,
            description=description,
            category=category,
            html_content=landing_page.html_content,
            design_json=landing_page.design_json,
            css_content=landing_page.css_content,
            is_system=False,
            is_active=True,
        )

        logger.info(f"Saved landing page {landing_page.id} as template {template.id}")
        return template
