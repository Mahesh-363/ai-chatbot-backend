from django.contrib import admin
from .models import DailyUsageSnapshot

@admin.register(DailyUsageSnapshot)
class DailyUsageSnapshotAdmin(admin.ModelAdmin):
    list_display = ["date", "total_messages", "total_sessions", "total_tokens", "active_users", "error_rate"]
    ordering = ["-date"]
    readonly_fields = ["created_at"]
