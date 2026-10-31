from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponsePermanentRedirect
from django.templatetags.static import static as static_url


def favicon(request):
    # Browsers and link-preview bots ask for /favicon.ico regardless of <link> tags.
    # Resolved per request so the hashed static URL isn't needed at import time.
    return HttpResponsePermanentRedirect(static_url('img/favicon.ico'))


urlpatterns = [
    path('favicon.ico', favicon),
    path('admin/', admin.site.urls),
    path('api/', include('apps.events.urls_api')),
    path('', include('apps.events.urls')),
    path('', include('apps.venues.urls')),
    path('', include('apps.users.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
