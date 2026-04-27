"""
Celery tasks for AI processing and background operations.
"""
import logging
import time
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="ai_processing",
    name="apps.chat.tasks.process_ai_response",
)
def process_ai_response(self, session_id: str, user_message_id: str, assistant_message_id: str):
    """
    Core task: fetch conversation history, call AI, write response back.
    Runs in the 'ai_processing' queue with retry support.
    """
    from .models import Message, ChatSession
    from .services import ChatService
    from utils.ai_client import AIClient

    start_time = time.time()
    logger.info(
        "process_ai_response started | session=%s task=%s",
        session_id, self.request.id,
    )

    try:
        session = ChatSession.objects.select_related("user").get(id=session_id)
        assistant_message = Message.objects.get(id=assistant_message_id)

        # Mark as processing
        assistant_message.status = Message.STATUS_PROCESSING
        assistant_message.save(update_fields=["status"])

        # Build conversation history
        history = ChatService.get_conversation_history(session)

        # Call AI
        client = AIClient()
        system_prompt = session.system_prompt or settings.AI_SYSTEM_PROMPT
        result = client.chat(history=history, system_prompt=system_prompt)

        # Persist response
        processing_time_ms = int((time.time() - start_time) * 1000)
        ChatService.complete_assistant_message(
            message=assistant_message,
            content=result["content"],
            model_name=result["model"],
            prompt_tokens=result["usage"]["prompt_tokens"],
            completion_tokens=result["usage"]["completion_tokens"],
            finish_reason=result["finish_reason"],
            processing_time_ms=processing_time_ms,
        )

        logger.info(
            "AI response completed | session=%s tokens=%d time=%dms",
            session_id, result["usage"]["total_tokens"], processing_time_ms,
        )

        # Trigger summarisation if session is getting long
        msg_count = session.messages.filter(status=Message.STATUS_COMPLETED).count()
        if msg_count > 0 and msg_count % 30 == 0:
            summarize_conversation.apply_async(
                args=[str(session_id)],
                countdown=10,
                queue="background",
            )

        return {
            "status": "completed",
            "session_id": session_id,
            "tokens_used": result["usage"]["total_tokens"],
        }

    except SoftTimeLimitExceeded:
        logger.error("Soft time limit exceeded for session %s", session_id)
        if "assistant_message" in dir():
            ChatService.fail_assistant_message(assistant_message, "Request timed out. Please try again.")
        raise

    except Exception as exc:
        logger.exception("Error processing AI response for session %s", session_id)
        try:
            if "assistant_message" in dir():
                from .services import ChatService as CS
                CS.fail_assistant_message(assistant_message, str(exc))
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 5)


@shared_task(
    bind=True,
    max_retries=2,
    queue="background",
    name="apps.chat.tasks.summarize_conversation",
)
def summarize_conversation(self, session_id: str):
    """
    Generate an AI summary of a conversation and store it.
    """
    from .models import ChatSession, Message, ConversationSummary
    from utils.ai_client import AIClient

    logger.info("Summarising session %s", session_id)

    try:
        session = ChatSession.objects.get(id=session_id)
        messages = list(
            Message.objects.filter(
                session=session,
                status=Message.STATUS_COMPLETED,
                role__in=[Message.ROLE_USER, Message.ROLE_ASSISTANT],
            ).order_by("created_at")
        )

        if len(messages) < 4:
            return {"status": "skipped", "reason": "too_few_messages"}

        transcript = "\n".join(
            f"{m.role.upper()}: {m.content}" for m in messages
        )

        prompt = (
            f"Summarise the following conversation in 2-3 sentences and extract the key topics as a JSON list.\n\n"
            f"Conversation:\n{transcript[:6000]}\n\n"
            f"Respond ONLY in JSON: {{\"summary\": \"...\", \"key_topics\": [...]}}"
        )

        client = AIClient()
        result = client.chat(
            history=[{"role": "user", "content": prompt}],
            system_prompt="You are a conversation summariser. Output only JSON.",
            max_tokens=512,
        )

        import json
        try:
            parsed = json.loads(result["content"])
        except json.JSONDecodeError:
            parsed = {"summary": result["content"], "key_topics": []}

        ConversationSummary.objects.update_or_create(
            session=session,
            defaults={
                "summary_text": parsed.get("summary", ""),
                "key_topics": parsed.get("key_topics", []),
                "messages_summarized": len(messages),
                "tokens_used": result["usage"]["total_tokens"],
            },
        )

        logger.info("Summary created for session %s", session_id)
        return {"status": "completed", "session_id": session_id}

    except Exception as exc:
        logger.exception("Error summarising session %s", session_id)
        raise self.retry(exc=exc, countdown=60)


@shared_task(queue="background", name="apps.chat.tasks.summarize_old_conversations")
def summarize_old_conversations():
    """
    Periodic task: summarise active sessions with many messages but no summary.
    """
    from .models import ChatSession
    from django.db.models import Count

    cutoff = timezone.now() - timedelta(hours=2)
    sessions = (
        ChatSession.objects
        .annotate(msg_count=Count("messages"))
        .filter(
            status=ChatSession.STATUS_ACTIVE,
            msg_count__gte=20,
            summary__isnull=True,
            last_message_at__lt=cutoff,
        )[:20]
    )

    for session in sessions:
        summarize_conversation.apply_async(args=[str(session.id)], queue="background")

    logger.info("Queued summarisation for %d sessions", len(list(sessions)))


@shared_task(queue="background", name="apps.chat.tasks.cleanup_expired_sessions")
def cleanup_expired_sessions():
    """
    Mark sessions older than 90 days with no activity as archived.
    """
    from .models import ChatSession
    cutoff = timezone.now() - timedelta(days=90)
    count = ChatSession.objects.filter(
        status=ChatSession.STATUS_ACTIVE,
        last_message_at__lt=cutoff,
    ).update(status=ChatSession.STATUS_ARCHIVED)
    logger.info("Archived %d expired sessions", count)


@shared_task(queue="background", name="apps.chat.tasks.warm_cache")
def warm_cache():
    """
    Pre-warm cache for the most active recent sessions.
    """
    from .models import ChatSession
    from .services import ChatService

    recent_sessions = ChatSession.objects.filter(
        status=ChatSession.STATUS_ACTIVE,
        last_message_at__gte=timezone.now() - timedelta(hours=1),
    ).select_related("user")[:50]

    warmed = 0
    for session in recent_sessions:
        try:
            ChatService.get_conversation_history(session)
            warmed += 1
        except Exception as e:
            logger.debug("Cache warm failed for session %s: %s", session.id, e)

    logger.info("Cache warmed for %d sessions", warmed)
