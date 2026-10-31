from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-change-in-production')

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Origins allowed to POST (admin login, event submission forms). Must include
# the scheme, e.g. https://artaroundtowndayton.org
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'anymail',
    'apps.users',
    'apps.events',
    'apps.venues',
    'apps.artists',
]

MIDDLEWARE = [
    'config.middleware.HealthCheckMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.events.context_processors.site_meta',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

CORS_ALLOW_ALL_ORIGINS = True

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

ADMIN_EMAIL = config('ADMIN_EMAIL', default='')
ADMINS = [('Art Around Town Admin', ADMIN_EMAIL)] if ADMIN_EMAIL else []
SERVER_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@artaroundtowndayton.org')

# ── Site identity ──────────────────────────────────────────────────
SITE_NAME = 'Art Around Town Dayton'
SITE_TAGLINE = "Dayton's Arts & Culture Calendar"
SITE_DESCRIPTION = (
    "Dayton's arts and culture calendar: gallery openings, concerts, theater, "
    "dance, museums and more across the Miami Valley. Browse what's on, or "
    "submit your own event."
)

# Organizations credited in the masthead and footer, in display order.
# `logo` is a path under static/ (e.g. 'img/partners/dsa.png'); leave it
# None to show the name as text until the logo file is added.
SITE_PARTNERS = [
    {'name': 'Dayton Society of Artists', 'url': 'https://daytondsa.org/', 'logo': 'img/partners/dsa.png'},
    {'name': 'The Collaboratory', 'url': 'https://www.daytoncollaboratory.org', 'logo': 'img/partners/collaboratory.png'},
    # TODO: logo once a PNG/SVG on white or transparent is available (the
    # JPEG supplied was flattened onto black, which hides the wordmark)
    {'name': 'Code for Dayton', 'url': 'https://www.codefordayton.org', 'logo': None},
]

# Social accounts for the footer. Fill in the URLs as the accounts go live;
# entries with an empty url are hidden.
SITE_SOCIAL = [
    {'name': 'Facebook', 'url': 'https://www.facebook.com/groups/artaroundtowndaytonoh'},
    {'name': 'Instagram', 'url': 'https://www.instagram.com/essentialartistsdayton/'},
]

# ── Newsletter (Brevo contact list) ────────────────────────────────
# The signup form appears once BREVO_NEWSLETTER_LIST_ID is set (Brevo →
# Contacts → Lists → the number in the list's URL). Uses the same API key
# as outgoing email.
BREVO_API_KEY = config('BREVO_API_KEY', default='')
BREVO_NEWSLETTER_LIST_ID = config('BREVO_NEWSLETTER_LIST_ID', default=0, cast=int)

# Brevo's hosted signup form (handles confirmation emails and unsubscribe
# itself). When set, signup buttons link here instead of the inline form.
NEWSLETTER_FORM_URL = config(
    'NEWSLETTER_FORM_URL',
    default='https://346e413d.sibforms.com/serve/MUIFABmkF3QZpxbLtWv8f3Tkr-HnYVpXa6VGOiUC9tYaI_0NauCRJkGZIZz3pAdjys0KpitbIx7UgukVV1Lq0wlP2d9Usmu7IbmD4NKJKZfHnqiXorxIm_iI88N7QZZExf2N7Z_1ZZZ130tT94Jx_q2MkFaJpMguPQ4ZG7eTs0qoTpK8d7-HgqlLose7ISE5D5d3S16u94dOBZWHqQ==',
)
