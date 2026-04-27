"""
Chat serializers.
"""
from rest_framework import serializers
from .models import ChatSession, Message, MessageFeedback, ConversationSummary


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id", "role", "content", "status", "model_name",
            "prompt_tokens", "completion_tokens", "total_tokens",
            "processing_time_ms", "finish_reason", "created_at",
        ]
        read_only_fields = [
            "id", "role", "status", "model_name", "prompt_tokens",
            "completion_tokens", "total_tokens", "processing_time_ms",
            "finish_reason", "created_at",
        ]


class SendMessageSerializer(serializers.Serializer):
    """Incoming message from user."""
    content = serializers.CharField(
        min_length=1,
        max_length=10_000,
        trim_whitespace=True,
    )
    session_id = serializers.UUIDField(required=False, allow_null=True)
    stream = serializers.BooleanField(default=False)


class ChatSessionSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            "id", "title", "status", "model_name", "total_messages",
            "total_tokens_used", "last_message_at", "created_at",
            "message_count", "last_message_preview",
        ]
        read_only_fields = ["id", "total_messages", "total_tokens_used", "created_at"]

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_last_message_preview(self, obj):
        last = obj.messages.filter(role=Message.ROLE_ASSISTANT).last()
        if last:
            return last.content[:120] + ("..." if len(last.content) > 120 else "")
        return None


class ChatSessionDetailSerializer(ChatSessionSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta(ChatSessionSerializer.Meta):
        fields = ChatSessionSerializer.Meta.fields + ["messages", "summary", "system_prompt"]

    def get_summary(self, obj):
        try:
            return obj.summary.summary_text
        except ConversationSummary.DoesNotExist:
            return None


class MessageFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageFeedback
        fields = ["id", "rating", "comment", "created_at"]
        read_only_fields = ["id", "created_at"]


class ConversationSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationSummary
        fields = ["summary_text", "key_topics", "messages_summarized", "created_at", "updated_at"]
