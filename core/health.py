import logging

from django.conf import settings
from django.db import connection
from django.db.utils import DatabaseError

logger = logging.getLogger("core.health")


def base_health_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "service": "deep-workflow",
        "environment": settings.DEPLOYMENT_ENV,
    }
    if settings.DEPLOYMENT_URL:
        payload["url"] = settings.DEPLOYMENT_URL
    if settings.DEPLOYMENT_GIT_SHA:
        payload["version"] = settings.DEPLOYMENT_GIT_SHA[:12]
    return payload


def check_database() -> str:
    connection.ensure_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return "ok"


def liveness_payload() -> dict[str, object]:
    return {
        **base_health_payload(),
        "status": "ok",
    }


def readiness_payload() -> tuple[dict[str, object], int]:
    payload = base_health_payload()
    try:
        database_status = check_database()
    except DatabaseError:
        logger.warning("Health readiness check failed.", exc_info=True)
        return {
            **payload,
            "status": "error",
            "checks": {"database": "error"},
        }, 503
    return {
        **payload,
        "status": "ok",
        "checks": {"database": database_status},
    }, 200
