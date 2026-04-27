"""
Core chat business logic: session management, AI call, history building.
"""
import logging
import time
from typing import Optional
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction

from .models import ChatSession, Message, ConversationSummary

logger = logging.getLogger(__name__)


class ChatService:
    """Orchestrates chat operations: session creation, history fetch, AI dispatch."""

    HISTORY_CACHE_TTL = 300  # 5 minutes

    # ── Session management ────────────────────────────────────────────────────

    @staticmethod
    def get_or_create_session(user, session_id: Optional[str] = None) -> ChatSession:
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, user=user, status=ChatSession.STATUS_ACTIVE)
                return session
            except ChatSession.DoesNotExist:
                logger.warning("Session %s not found for user %s", session_id, user.id)

        return ChatSession.objects.create(user=user)

    @staticmethod
    def archive_session(user, session_id: str) -> ChatSession:
        session = ChatSession.objects.get(id=session_id, user=user)
        session.status = ChatSession.STATUS_ARCHIVED
        session.save(update_fields=["status", "updated_at"])
        # Bust cache
        cache_key = f"session_history:{session_id}"
        cache.delete(cache_key)
        return session

    # ── Message creation ──────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def create_user_message(session: ChatSession, content: str) -> Message:
        message = Message.objects.create(
            session=session,
            role=Message.ROLE_USER,
            content=content,
            status=Message.STATUS_COMPLETED,
        )
        ChatSession.objects.filter(pk=session.pk).update(
            total_messages=ChatSession.objects.filter(pk=session.pk).values("total_messages")[0]["total_messages"] + 1,
            last_message_at=timezone.now(),
        )
        # Invalidate history cache
        cache.delete(f"session_history:{session.id}")
        return message

    @staticmethod
    @transaction.atomic
    def create_assistant_placeholder(session: ChatSession, task_id: str) -> Message:
        return Message.objects.create(
            session=session,
            role=Message.ROLE_ASSISTANT,
            content="",
            status=Message.STATUS_PENDING,
            task_id=task_id,
        )

    @staticmethod
    @transaction.atomic
    def complete_assistant_message(
        message: Message,
        content: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        finish_reason: str,
        processing_time_ms: int,
    ) -> Message:
        message.content = content
        message.status = Message.STATUS_COMPLETED
        message.model_name = model_name
        message.prompt_tokens = prompt_tokens
        message.completion_tokens = completion_tokens
        message.total_tokens = prompt_tokens + completion_tokens
        message.finish_reason = finish_reason
        message.processing_time_ms = processing_time_ms
        message.save()

        # Update session token count
        ChatSession.objects.filter(pk=message.session_id).update(
            total_tokens_used=ChatSession.objects.filter(pk=message.session_id).values("total_tokens_used")[0]["total_tokens_used"] + message.total_tokens,
            total_messages=ChatSession.objects.filter(pk=message.session_id).values("total_messages")[0]["total_messages"] + 1,
        )

        # Update user monthly tokens
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.filter(pk=message.session.user_id).update(
            tokens_used_this_month=User.objects.filter(pk=message.session.user_id).values("tokens_used_this_month")[0]["tokens_used_this_month"] + message.total_tokens
        )

        # Invalidate cache
        cache.delete(f"session_history:{message.session_id}")
        return message

    @staticmethod
    def fail_assistant_message(message: Message, error: str) -> Message:
        message.content = f"I encountered an error: {error}"
        message.status = Message.STATUS_FAILED
        message.save(update_fields=["content", "status", "updated_at"])
        return message

    # ── History building ──────────────────────────────────────────────────────

    @classmethod
    def get_conversation_history(cls, session: ChatSession) -> list[dict]:
        """
        Returns recent messages formatted for the OpenAI API.
        Uses Redis cache to avoid repeated DB hits.
        """
        cache_key = f"session_history:{session.id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        max_messages = settings.AI_MAX_HISTORY_MESSAGES
        messages = (
            Message.objects
            .filter(
                session=session,
                status=Message.STATUS_COMPLETED,
                role__in=[Message.ROLE_USER, Message.ROLE_ASSISTANT],
            )
            .order_by("-created_at")[:max_messages]
        )
        # Reverse so oldest first
        history = [{"role": m.role, "content": m.content} for m in reversed(list(messages))]

        cache.set(cache_key, history, cls.HISTORY_CACHE_TTL)
        return history

    # ── Auto-title ────────────────────────────────────────────────────────────

    @staticmethod
    def auto_title_session(session: ChatSession, first_user_message: str):
        """Set a title from the first user message if not set."""
        if session.title == "New Conversation":
            title = first_user_message[:60].strip()
            if len(first_user_message) > 60:
                title += "..."
            ChatSession.objects.filter(pk=session.pk).update(title=title)
