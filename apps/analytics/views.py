"""
Admin-only analytics views.
"""
import logging
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache

from apps.chat.models import ChatSession, Message
from .models import DailyUsageSnapshot
from .serializers import DailyUsageSnapshotSerializer

logger = logging.getLogger(__name__)


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class SystemOverviewView(APIView):
    """GET /api/v1/analytics/overview/ — real-time system snapshot."""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        cache_key = "analytics:overview"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        data = {
            "period": {
                "last_24h": {
                    "messages": Message.objects.filter(created_at__gte=last_24h).count(),
                    "sessions": ChatSession.objects.filter(created_at__gte=last_24h).count(),
                    "tokens": Message.objects.filter(created_at__gte=last_24h).aggregate(t=Sum("total_tokens"))["t"] or 0,
                },
                "last_7d": {
                    "messages": Message.objects.filter(created_at__gte=last_7d).count(),
                    "sessions": ChatSession.objects.filter(created_at__gte=last_7d).count(),
                    "tokens": Message.objects.filter(created_at__gte=last_7d).aggregate(t=Sum("total_tokens"))["t"] or 0,
                },
            },
            "totals": {
                "messages": Message.objects.count(),
                "sessions": ChatSession.objects.count(),
                "tokens": Message.objects.aggregate(t=Sum("total_tokens"))["t"] or 0,
            },
            "errors": {
                "failed_messages_24h": Message.objects.filter(
                    created_at__gte=last_24h, status=Message.STATUS_FAILED
                ).count(),
            },
        }

        cache.set(cache_key, data, 120)  # 2-minute cache
        return Response(data)


class UserStatsView(APIView):
    """GET /api/v1/analytics/users/ — top users by usage."""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        top_users = (
            User.objects
            .annotate(session_count=Count("chat_sessions"))
            .order_by("-tokens_used_this_month")[:20]
        )
        data = [
            {
                "user_id": str(u.id),
                "email": u.email,
                "tier": u.tier,
                "tokens_this_month": u.tokens_used_this_month,
                "session_count": u.session_count,
            }
            for u in top_users
        ]
        return Response(data)


class DailySnapshotsView(generics.ListAPIView):
    """GET /api/v1/analytics/snapshots/ — daily snapshot history."""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    serializer_class = DailyUsageSnapshotSerializer

    def get_queryset(self):
        days = int(self.request.query_params.get("days", 30))
        cutoff = timezone.now().date() - timedelta(days=days)
        return DailyUsageSnapshot.objects.filter(date__gte=cutoff)
