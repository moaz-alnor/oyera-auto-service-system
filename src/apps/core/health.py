"""Operational health-check endpoints."""

import logging

from django.db import connection
from django.db.utils import DatabaseError
from django.http import HttpRequest, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


def _database_is_ready() -> bool:
    """Return whether the primary database accepts a simple query."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
    except DatabaseError:
        logger.warning("Database readiness check failed.")
        return False

    return result == (1,)


@never_cache
@require_GET
def liveness(request: HttpRequest) -> JsonResponse:
    """Confirm that the OYERA web process is running."""
    return JsonResponse(
        {
            "status": "ok",
            "service": "oyera",
            "check": "liveness",
        }
    )


@never_cache
@require_GET
def readiness(request: HttpRequest) -> JsonResponse:
    """Confirm that OYERA can serve database-backed requests."""
    if not _database_is_ready():
        return JsonResponse(
            {
                "status": "unavailable",
                "service": "oyera",
                "checks": {
                    "database": "unavailable",
                },
            },
            status=503,
        )

    return JsonResponse(
        {
            "status": "ok",
            "service": "oyera",
            "checks": {
                "database": "ok",
            },
        }
    )
