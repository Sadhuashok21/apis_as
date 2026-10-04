from urllib.parse import urlparse
from django.conf import settings
from django.http import HttpResponse


class FrontendCorsMiddleware:
    """Allow the configured Vite origins and local dev servers to call the JSON API."""
    """Allow configured Vite origins, subdomains, and local dev servers to call the JSON API."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin", "")
        allowed = getattr(settings, "FRONTEND_ALLOWED_ORIGINS", ())
        is_allowed = origin in allowed or (
            origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:")
        )
        is_allowed = False

        if origin:
            if origin in allowed or origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:"):
                is_allowed = True
            else:
                try:
                    parsed = urlparse(origin)
                    if parsed.scheme == "https":
                        hostname = parsed.hostname or ""
                        if (
                            hostname == "asentracoresolutions.com"
                            or hostname.endswith(".asentracoresolutions.com")
                            or hostname == "ascentracoresolutions.com"
                            or hostname.endswith(".ascentracoresolutions.com")
                        ):
                            is_allowed = True
                except Exception:
                    pass

        if request.method == "OPTIONS" and is_allowed:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if is_allowed and origin:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = "GET, POST, PATCH, PUT, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, X-CSRFToken, X-Requested-With, Idempotency-Key"
            response["Access-Control-Allow-Credentials"] = "true"
            response["Vary"] = "Origin"
        return response
