"""
Celery configuration for AI Chatbot.
"""
import os
from celery import Celery
from celery.signals import task_failure, task_success, worker_ready
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("ai_chatbot")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# ── Queue routing ─────────────────────────────────────────────────────────────
app.conf.task_queues = {
    "default": {"exchange": "default", "routing_key": "default"},
    "ai_processing": {"exchange": "ai_processing", "routing_key": "ai_processing"},
    "background": {"exchange": "background", "routing_key": "background"},
    "analytics": {"exchange": "analytics", "routing_key": "analytics"},
}

app.conf.task_routes = {
    "apps.chat.tasks.process_ai_response": {"queue": "ai_processing"},
    "apps.chat.tasks.summarize_conversation": {"queue": "background"},
    "apps.chat.tasks.summarize_old_conversations": {"queue": "background"},
    "apps.chat.tasks.cleanup_expired_sessions": {"queue": "background"},
    "apps.analytics.tasks.*": {"queue": "analytics"},
}

app.conf.task_default_queue = "default"
app.conf.task_default_exchange = "default"
app.conf.task_default_routing_key = "default"


@task_failure.connect
def handle_task_failure(task_id, exception, args, kwargs, traceback, einfo, **kw):
    logger.error(
        "Celery task failed",
        extra={
            "task_id": task_id,
            "exception": str(exception),
            "args": args,
            "kwargs": kwargs,
        },
    )


@task_success.connect
def handle_task_success(sender, result, **kwargs):
    logger.debug("Task %s completed successfully", sender.name)


@worker_ready.connect
def handle_worker_ready(**kwargs):
    logger.info("Celery worker ready and accepting tasks")


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    logger.debug("Request: %r", self.request)
