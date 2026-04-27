from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "username", "tier", "is_active", "is_staff", "date_joined"]
    list_filter = ["tier", "is_active", "is_staff"]
    search_fields = ["email", "username", "first_name", "last_name"]
    ordering = ["-date_joined"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Subscription", {"fields": ("tier", "daily_message_limit", "monthly_token_limit", "tokens_used_this_month")}),
        ("API Access", {"fields": ("api_key", "api_key_created_at")}),
    )
    readonly_fields = ["api_key_created_at", "date_joined", "last_seen"]
