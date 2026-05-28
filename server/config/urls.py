"""
Root URL configuration for Breathe ESG.

All API endpoints are versioned under /api/v1/ for future compatibility.
Auth endpoints live at /api/v1/auth/ so the React frontend can obtain tokens.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

# Simple health check/root view
def health_check(request):
    return JsonResponse({"status": "healthy", "message": "Breathe ESG API is live"})

# ── Third-party auth views ──────────────────────────────────────────────────
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    # Root & Health
    path("", health_check),
    path("health/", health_check),

    # Django admin
    path("admin/", admin.site.urls),

    path("api/v1/", include([
        # Token login: POST {"username": ..., "password": ...} → {"token": ...}
        path("auth/login/", obtain_auth_token, name="api-token-auth"),

        # Business API routes
        path("organizations/", include("apps.organizations.urls")),
        path("facilities/", include("apps.facilities.urls")),
        path("factors/", include("apps.factors.urls")),
        path("ingestion/", include("apps.ingestion.urls")),
        path("activities/", include("apps.activities.urls")),
        path("audit/", include("apps.audit.urls")),
        path("dashboard/", include("apps.dashboard.urls")),
    ])),
]

# Serve uploaded raw files in development (gunicorn/nginx handles this in prod)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)