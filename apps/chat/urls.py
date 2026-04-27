from django.urls import path
from .views import (
    ChatSessionListCreateView, ChatSessionDetailView,
    SendMessageView, MessageStatusView, SessionMessagesView,
    MessageFeedbackView, SummariseSessionView, SessionSummaryView,
)

urlpatterns = [
    # Sessions
    path("sessions/", ChatSessionListCreateView.as_view(), name="session-list-create"),
    path("sessions/<uuid:pk>/", ChatSessionDetailView.as_view(), name="session-detail"),
    path("sessions/<uuid:session_id>/messages/", SessionMessagesView.as_view(), name="session-messages"),
    path("sessions/<uuid:session_id>/summarise/", SummariseSessionView.as_view(), name="session-summarise"),
    path("sessions/<uuid:session_id>/summary/", SessionSummaryView.as_view(), name="session-summary"),

    # Messages
    path("messages/send/", SendMessageView.as_view(), name="send-message"),
    path("messages/<uuid:message_id>/status/", MessageStatusView.as_view(), name="message-status"),
    path("messages/<uuid:message_id>/feedback/", MessageFeedbackView.as_view(), name="message-feedback"),
]
