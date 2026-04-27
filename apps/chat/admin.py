from django.contrib import admin
from django.utils.html import format_html
from .models import ChatSession, Message, MessageFeedback, ConversationSummary


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "title", "status", "total_messages", "total_tokens_used", "last_message_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["user__email", "title"]
    readonly_fields = ["id", "created_at", "updated_at", "total_messages", "total_tokens_used"]
    raw_id_fields = ["user"]
    ordering = ["-last_message_at"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "role", "status", "total_tokens", "processing_time_ms", "created_at"]
    list_filter = ["role", "status", "created_at"]
    search_fields = ["content", "session__user__email"]
    readonly_fields = ["id", "created_at", "updated_at", "task_id"]
    ordering = ["-created_at"]

    def content_preview(self, obj):
        return format_html("<span title='{}'>{}</span>", obj.content, obj.content[:80])
    content_preview.short_description = "Content"


@admin.register(ConversationSummary)
class ConversationSummaryAdmin(admin.ModelAdmin):
    list_display = ["session", "messages_summarized", "tokens_used", "created_at"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(MessageFeedback)
class MessageFeedbackAdmin(admin.ModelAdmin):
    list_display = ["message", "user", "rating", "created_at"]
    list_filter = ["rating"]
