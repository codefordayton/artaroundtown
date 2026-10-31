from django.conf import settings
from django.templatetags.static import static


def site_meta(request):
    """Site-wide identity used by base.html (title, link previews, partner
    credits). Views can override the per-page keys (page_title,
    meta_description, og_image, og_type) in their own context."""
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_TAGLINE': settings.SITE_TAGLINE,
        'SITE_DESCRIPTION': settings.SITE_DESCRIPTION,
        'SITE_PARTNERS': settings.SITE_PARTNERS,
        'SITE_SOCIAL': [s for s in settings.SITE_SOCIAL if s.get('url')],
        'NEWSLETTER_ENABLED': bool(settings.NEWSLETTER_FORM_URL or settings.BREVO_NEWSLETTER_LIST_ID),
        'NEWSLETTER_FORM_URL': settings.NEWSLETTER_FORM_URL,
        # Social scrapers need an absolute image URL
        'default_og_image': request.build_absolute_uri(static('img/og-default.png')),
    }
