import dj_database_url
from decouple import config
from .base import *

DEBUG = True

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600,
    )
}

# ── Media storage ──────────────────────────────────────────────────
# S3-compatible object storage (DigitalOcean Spaces, Backblaze B2, AWS S3).
# DO Spaces endpoint looks like https://nyc3.digitaloceanspaces.com and the
# bucket is the Space name. Set S3_CUSTOM_DOMAIN to a CDN domain if you use
# the Spaces CDN (e.g. mybucket.nyc3.digitaloceanspaces.com).
USE_S3_STORAGE = config('USE_S3_STORAGE', default=False, cast=bool)

if USE_S3_STORAGE:
    _s3_custom_domain = config('S3_CUSTOM_DOMAIN', default='')
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {
                'access_key': config('S3_ACCESS_KEY_ID'),
                'secret_key': config('S3_SECRET_ACCESS_KEY'),
                'bucket_name': config('S3_BUCKET_NAME'),
                'endpoint_url': config('S3_ENDPOINT_URL'),
                'region_name': config('S3_REGION', default=''),
                'location': 'media',
                'default_acl': 'public-read',
                'querystring_auth': False,
                'file_overwrite': False,
                'custom_domain': _s3_custom_domain or None,
            },
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }
    MEDIA_URL = (
        f'https://{_s3_custom_domain}/media/'
        if _s3_custom_domain else
        f"{config('S3_ENDPOINT_URL')}/{config('S3_BUCKET_NAME')}/media/"
    )
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
