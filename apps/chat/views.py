"""
Chat API views.
"""
import logging
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.core.cache import caches

from .models import ChatSession, Message, MessageFeedback
from .serializers import (
    ChatSessionSerializer, ChatSessionDetailSerializer,
    SendMessageSerializer, MessageSerializer,
    MessageFeedbackSerializer, ConversationSummarySerializer,
)
from .services import ChatService
from .tasks import process_ai_response, summarize_conversation
from utils.rate_limiter import RateLimiter
from utils.throttling import ChatMessageThrottle
from utils.pagination import StandardResultsPagination

logger = logging.getLogger(__name__)


class ChatSessionListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/chat/sessions/        → list user's sessions
    POST /api/v1/chat/sessions/        → create a new session
    """
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        return (
            ChatSession.objects
            .filter(user=self.request.user, status=ChatSession.STATUS_ACTIVE)
            .prefetch_related("messages")
            .order_by("-last_message_at", "-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ChatSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/chat/sessions/<id>/  → session with messages
    PATCH  /api/v1/chat/sessions/<id>/  → update title / system_prompt
    DELETE /api/v1/chat/sessions/<id>/  → archive session
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ChatSessionDetailSerializer
        return ChatSessionSerializer

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        session = self.get_object()
        ChatService.archive_session(request.user, str(session.id))
        return Response({"message": "Session archived."}, status=status.HTTP_200_OK)


class SendMessageView(APIView):
    """
    POST /api/v1/chat/messages/send/

    Accepts a user message, creates a placeholder assistant message,
    dispatches the Celery task, and returns the task ID for polling.
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ChatMessageThrottle]

    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user

        # ── Rate limiting ─────────────────────────────────────────────────────
        rate_limiter = RateLimiter(user=user)
        allowed, retry_after = rate_limiter.check()
        if not allowed:
            return Response(
                {"error": "Rate limit exceeded.", "retry_after_seconds": retry_after},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # ── Get / create session ──────────────────────────────────────────────
        session = ChatService.get_or_create_session(
            user=user, session_id=data.get("session_id")
        )

        # Auto-title from first message
        if session.total_messages == 0:
            ChatService.auto_title_session(session, data["content"])

        # ── Persist user message ──────────────────────────────────────────────
        user_message = ChatService.create_user_message(session, data["content"])

        # ── Dispatch Celery task ──────────────────────────────────────────────
        task = process_ai_response.apply_async(
            args=[str(session.id), str(user_message.id), "placeholder"],
            queue="ai_processing",
        )

        # Create placeholder with real task ID now
        assistant_placeholder = ChatService.create_assistant_placeholder(session, task.id)

        # Re-dispatch with correct assistant message ID
        task.revoke()
        task = process_ai_response.apply_async(
            args=[str(session.id), str(user_message.id), str(assistant_placeholder.id)],
            queue="ai_processing",
        )
        assistant_placeholder.task_id = task.id
        assistant_placeholder.save(update_fields=["task_id"])

        logger.info(
            "Message sent | user=%s session=%s task=%s",
            user.id, session.id, task.id,
        )

        return Response(
            {
                "session_id": str(session.id),
                "user_message_id": str(user_message.id),
                "assistant_message_id": str(assistant_placeholder.id),
                "task_id": task.id,
                "status": "processing",
                "message": "Your message is being processed.",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class MessageStatusView(APIView):
    """
    GET /api/v1/chat/messages/<id>/status/

    Poll for the processing status of an assistant message.
    Returns the full message content once completed.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, message_id):
        message = get_object_or_404(
            Message,
            id=message_id,
            session__user=request.user,
            role=Message.ROLE_ASSISTANT,
        )

        if message.status == Message.STATUS_COMPLETED:
            return Response({
                "status": "completed",
                "message": MessageSerializer(message).data,
            })
        elif message.status == Message.STATUS_FAILED:
            return Response({
                "status": "failed",
                "error": message.content or "Processing failed.",
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                "status": message.status,
                "message": "Still processing...",
            })


class SessionMessagesView(generics.ListAPIView):
    """
    GET /api/v1/chat/sessions/<session_id>/messages/

    Paginated message history for a session.
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        session_id = self.kwargs["session_id"]
        return Message.objects.filter(
            session__id=session_id,
            session__user=self.request.user,
        ).order_by("created_at")


class MessageFeedbackView(generics.CreateAPIView):
    """
    POST /api/v1/chat/messages/<message_id>/feedback/
    """
    serializer_class = MessageFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        message = get_object_or_404(
            Message,
            id=self.kwargs["message_id"],
            session__user=self.request.user,
            role=Message.ROLE_ASSISTANT,
        )
        serializer.save(message=message, user=self.request.user)


class SummariseSessionView(APIView):
    """
    POST /api/v1/chat/sessions/<session_id>/summarise/

    Manually trigger background summarisation.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        task = summarize_conversation.apply_async(
            args=[str(session.id)], queue="background"
        )
        return Response(
            {"task_id": task.id, "message": "Summarisation queued."},
            status=status.HTTP_202_ACCEPTED,
        )


class SessionSummaryView(generics.RetrieveAPIView):
    """
    GET /api/v1/chat/sessions/<session_id>/summary/
    """
    serializer_class = ConversationSummarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        session = get_object_or_404(ChatSession, id=self.kwargs["session_id"], user=self.request.user)
        return get_object_or_404(session.__class__.objects.get(pk=session.pk).summary.__class__, session=session)

    def retrieve(self, request, *args, **kwargs):
        session = get_object_or_404(ChatSession, id=self.kwargs["session_id"], user=request.user)
        try:
            summary = session.summary
            return Response(ConversationSummarySerializer(summary).data)
        except Exception:
            return Response({"message": "No summary available yet."}, status=status.HTTP_404_NOT_FOUND)
