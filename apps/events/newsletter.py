"""Add a subscriber to the Brevo newsletter list.

Brevo's contacts API: POST /v3/contacts with the list id. A 201 is a new
contact, a 204 means the contact already existed and was updated (we send
updateEnabled so re-subscribing is harmless).
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

BREVO_CONTACTS_URL = 'https://api.brevo.com/v3/contacts'


class NewsletterError(Exception):
    pass


def subscribe(email, name=''):
    if not settings.BREVO_NEWSLETTER_LIST_ID:
        raise NewsletterError('Newsletter signup is not configured.')
    if not settings.BREVO_API_KEY:
        if settings.DEBUG:
            logger.info('DEBUG: would subscribe %s (%s) to Brevo list %s',
                        email, name, settings.BREVO_NEWSLETTER_LIST_ID)
            return
        raise NewsletterError('Newsletter signup is not configured.')

    payload = {
        'email': email,
        'listIds': [settings.BREVO_NEWSLETTER_LIST_ID],
        'updateEnabled': True,
    }
    if name:
        first, _, last = name.strip().partition(' ')
        payload['attributes'] = {'FIRSTNAME': first, 'LASTNAME': last}

    try:
        resp = requests.post(
            BREVO_CONTACTS_URL,
            json=payload,
            headers={'api-key': settings.BREVO_API_KEY, 'accept': 'application/json'},
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.warning('Brevo unreachable: %s', exc)
        raise NewsletterError('Could not reach the newsletter service. Please try again later.')

    if resp.status_code in (201, 204):
        return
    logger.warning('Brevo rejected signup for %s: %s %s', email, resp.status_code, resp.text[:300])
    raise NewsletterError('Could not complete the signup. Please check the address and try again.')
