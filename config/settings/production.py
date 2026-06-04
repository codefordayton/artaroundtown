import dj_database_url
from decouple import config
from .base import *

DEBUG = False

DATABASES = {
    'default': dj_database_url.config(conn_max_age=600)
}

USE_B2_STORAGE = config('USE_B2_STORAGE', default=False, cast=bool)

if USE_B2_STORAGE:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = config('B2_APP_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('B2_APP_KEY')
    AWS_STORAGE_BUCKET_NAME = config('B2_BUCKET_NAME')
    AWS_S3_ENDPOINT_URL = config('B2_ENDPOINT_URL')
    AWS_S3_FILE_OVERWRITE = False
    MEDIA_URL = f"{config('B2_ENDPOINT_URL')}/{config('B2_BUCKET_NAME')}/"
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Railway terminates TLS at the edge; the app only ever sees HTTP internally.
# Enabling SSL redirect would cause Railway's health checker (plain HTTP) to
# get a 301 and never see a 200.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@artaroundtowndayton.org')
