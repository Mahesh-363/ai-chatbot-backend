import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(queue="analytics", name="apps.analytics.tasks.generate_daily_report")
def generate_daily_report():
    from apps.chat.models import Message, ChatSession
    from .models import DailyUsageSnapshot
    from django.db.models import Sum, Count, Avg
    from django.contrib.auth import get_user_model

    User = get_user_model()
    yesterday = (timezone.now() - timedelta(days=1)).date()
    start = timezone.datetime.combine(yesterday, timezone.datetime.min.time()).replace(tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    messages = Message.objects.filter(created_at__range=(start, end))
    sessions = ChatSession.objects.filter(created_at__range=(start, end))
    total_messages = messages.count()
    total_sessions = sessions.count()
    total_tokens = messages.aggregate(t=Sum("total_tokens"))["t"] or 0
    active_users = sessions.values("user").distinct().count()
    new_users = User.objects.filter(date_joined__range=(start, end)).count()
    failed = messages.filter(status=Message.STATUS_FAILED).count()
    error_rate = (failed / total_messages * 100) if total_messages else 0

    DailyUsageSnapshot.objects.update_or_create(
        date=yesterday,
        defaults={
            "total_messages": total_messages,
            "total_sessions": total_sessions,
            "total_tokens": total_tokens,
            "active_users": active_users,
            "new_users": new_users,
            "error_rate": round(error_rate, 2),
        },
    )
    logger.info("Daily report generated for %s", yesterday)
