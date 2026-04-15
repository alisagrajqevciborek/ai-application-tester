"""Lightweight views for non-app routes (e.g. service root)."""

from django.http import JsonResponse


def api_service_root(_request):
    """Avoid bare 404 when someone opens the API host without a path."""
    return JsonResponse(
        {
            "service": "ai-application-tester",
            "status": "ok",
            "health": "/api/auth/health",
            "hint": "API routes are under /api/auth/, /api/applications/, /api/reports/, and /admin/.",
        }
    )
