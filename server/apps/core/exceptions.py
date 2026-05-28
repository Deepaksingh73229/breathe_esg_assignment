"""
Custom exception handling for the Breathe ESG API.

Wraps all DRF errors in a consistent envelope so the React frontend
can handle errors predictably without checking response structure per-endpoint.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging
import traceback


def custom_exception_handler(exc, context):
    """
    Global exception handler that normalises all DRF errors.

    Success response is whatever the view returns.
    Error response format:
    {
        "error": {
            "code": "validation_error",
            "message": "...",
            "details": { ... },
            "status_code": 400
        }
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            "error": {
                "code": getattr(exc, "default_code", "api_error"),
                "message": str(exc),
                "details": response.data,
                "status_code": response.status_code,
            }
        }
    else:
        # Unhandled 500-level exceptions: log full traceback for debugging
        logger = logging.getLogger("django.request")
        try:
            request = context.get("request")
            path = getattr(request, "path", "<unknown>")
        except Exception:
            path = "<unknown>"

        tb = traceback.format_exc()
        logger.error(
            "Unhandled exception processing request %s: %s\n%s",
            path,
            str(exc),
            tb,
        )

        response = Response(
            {
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred.",
                    "details": {},
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response