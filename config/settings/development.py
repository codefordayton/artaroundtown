import dj_database_url
from .base import *

DEBUG = True

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600,
    )
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Plain static storage locally: the WhiteNoise manifest only exists after
# collectstatic, and the test runner (DEBUG=False) would otherwise fail on
# every {% static %} tag for a file not yet in it.
STORAGES = {
    **STORAGES,
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
