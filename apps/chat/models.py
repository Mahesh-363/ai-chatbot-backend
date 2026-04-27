"""
Chat models: Session, Message, MessageFeedback, ConversationSummary.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ChatSession(models.Model):
    """
    Represents a conversation thread. One user can have many sessions.
    """
    STATUS_ACTIVE = "active"
    STATUS_ARCHIVED = "archived"
    STATUS_DELETED = "deleted"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_ARCHIVED, "Archived"),
        (STATUS_DELETED, "Deleted"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_sessions")
    title = models.CharField(max_length=255, blank=True, default="New Conversation")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    system_prompt = models.TextField(blank=True, help_text="Optional custom system prompt for this session")
    model_name = models.CharField(max_length=50, blank=True, help_text="AI model used")
    total_messages = models.IntegerField(default=0)
    total_tokens_used = models.IntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "chat_sessions"
        ordering = ["-last_message_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "-last_message_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.title[:40]}"

    def touch(self):
        self.last_message_at = timezone.now()
        self.save(update_fields=["last_message_at", "updated_at"])


class Message(models.Model):
    """
    Individual message in a chat session.
    """
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_SYSTEM = "system"
    ROLE_CHOICES = [
        (ROLE_USER, "User"),
        (ROLE_ASSISTANT, "Assistant"),
        (ROLE_SYSTEM, "System"),
    ]

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_COMPLETED)

    # Token tracking
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)

    # AI model metadata
    model_name = models.CharField(max_length=50, blank=True)
    finish_reason = models.CharField(max_length=50, blank=True)

    # Celery task reference
    task_id = models.CharField(max_length=255, blank=True, db_index=True)

    # Processing time in milliseconds
    processing_time_ms = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "chat_messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["session", "role"]),
            models.Index(fields=["status"]),
            models.Index(fields=["task_id"]),
        ]

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"

    @property
    def is_pending(self):
        return self.status == self.STATUS_PENDING


class MessageFeedback(models.Model):
    """
    Thumbs up/down feedback on assistant messages.
    """
    RATING_POSITIVE = "positive"
    RATING_NEGATIVE = "negative"
    RATING_CHOICES = [(RATING_POSITIVE, "Positive"), (RATING_NEGATIVE, "Negative")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name="feedback")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="message_feedbacks")
    rating = models.CharField(max_length=20, choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "message_feedbacks"

    def __str__(self):
        return f"{self.rating} on message {self.message_id}"


class ConversationSummary(models.Model):
    """
    AI-generated summary of a chat session (background task output).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name="summary")
    summary_text = models.TextField()
    key_topics = models.JSONField(default=list)
    messages_summarized = models.IntegerField(default=0)
    tokens_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversation_summaries"

    def __str__(self):
        return f"Summary for session {self.session_id}"
