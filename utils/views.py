import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import connection
from django.core.cache import cache

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        health = {"status": "healthy", "checks": {}}

        # DB check
        try:
            connection.ensure_connection()
            health["checks"]["database"] = "ok"
        except Exception as e:
            health["checks"]["database"] = f"error: {e}"
            health["status"] = "degraded"

        # Cache check
        try:
            cache.set("_healthcheck", "ok", 5)
            val = cache.get("_healthcheck")
            health["checks"]["redis"] = "ok" if val == "ok" else "error"
        except Exception as e:
            health["checks"]["redis"] = f"error: {e}"
            health["status"] = "degraded"

        status_code = 200 if health["status"] == "healthy" else 503
        return Response(health, status=status_code)


class APIRootView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({
            "name": "AI Chatbot API",
            "version": "1.0.0",
            "endpoints": {
                "auth": "/api/v1/auth/",
                "chat": "/api/v1/chat/",
                "analytics": "/api/v1/analytics/",
                "health": "/health/",
                "admin": "/admin/",
            },
        })
