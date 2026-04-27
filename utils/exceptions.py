import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            "error": True,
            "status_code": response.status_code,
            "detail": response.data,
        }
        response.data = error_data
        return response

    # Unhandled exception
    logger.exception("Unhandled exception in view %s", context.get("view"))
    return Response(
        {"error": True, "status_code": 500, "detail": "An unexpected error occurred."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
