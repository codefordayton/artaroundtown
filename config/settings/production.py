from decouple import config
from .base import *

DEBUG = False

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Railway terminates TLS at the edge; the app only ever sees HTTP internally.
# Enabling SSL redirect would cause Railway's health checker (plain HTTP) to
# get a 301 and never see a 200.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

EMAIL_BACKEND = 'anymail.backends.brevo.EmailBackend'
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@artaroundtowndayton.org')
ANYMAIL = {
    'BREVO_API_KEY': config('BREVO_API_KEY', default=''),
}
