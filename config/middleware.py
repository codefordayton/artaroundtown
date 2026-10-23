from django.http import JsonResponse


class HealthCheckMiddleware:
    """Answer /health/ before host validation runs.

    Platform health checkers (DigitalOcean App Platform, load balancers)
    hit the container directly with whatever Host header they like. Short-
    circuiting here means we never have to whitelist their hostnames in
    ALLOWED_HOSTS. Must be first in MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/health/':
            return JsonResponse({'status': 'ok'})
        return self.get_response(request)
