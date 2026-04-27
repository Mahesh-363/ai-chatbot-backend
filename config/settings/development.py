from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Show SQL queries in development
LOGGING["loggers"]["django.db.backends"] = {
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
}

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

CORS_ALLOW_ALL_ORIGINS = True
