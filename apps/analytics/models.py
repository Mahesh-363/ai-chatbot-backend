"""
Analytics models: daily snapshot, usage stats.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class DailyUsageSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(unique=True, db_index=True)
    total_messages = models.IntegerField(default=0)
    total_sessions = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    new_users = models.IntegerField(default=0)
    avg_session_length = models.FloatField(default=0.0)
    error_rate = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "daily_usage_snapshots"
        ordering = ["-date"]

    def __str__(self):
        return f"Snapshot {self.date}"
