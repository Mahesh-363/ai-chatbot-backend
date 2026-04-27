import logging
import time
import uuid

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = str(uuid.uuid4())[:8]
        request.request_id = request_id
        start = time.time()

        response = self.get_response(request)

        elapsed_ms = int((time.time() - start) * 1000)
        user = getattr(request, "user", None)
        user_id = str(user.id) if user and user.is_authenticated else "anon"

        logger.info(
            "[%s] %s %s %d %dms user=%s",
            request_id, request.method, request.path,
            response.status_code, elapsed_ms, user_id,
        )
        response["X-Request-ID"] = request_id
        return response
