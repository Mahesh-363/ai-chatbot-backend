"""
Base settings for AI Chatbot project.
"""
import os
from pathlib import Path
from decouple import config, Csv
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me-in-production")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'django_redis',
    'django_extensions',
    'django_celery_beat',   # <-- ADD THIS LINE
    # Local
    'apps.accounts',
    'apps.chat',
    'apps.analytics',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "utils.middleware.RequestLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ── Database ──────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="ai_chatbot"),
        "USER": config("DB_USER", default="chatbot_user"),
        "PASSWORD": config("DB_PASSWORD", default="chatbot_pass"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"connect_timeout": 10},
    }
}

# ── Redis & Cache ─────────────────────────────────────────────────────────────
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "RETRY_ON_TIMEOUT": True,
            "MAX_CONNECTIONS": 1000,
        },
        "KEY_PREFIX": "chatbot",
        "TIMEOUT": 300,
    },
    "rate_limit": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_RATE_LIMIT_URL", default="redis://localhost:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "ratelimit",
        "TIMEOUT": 3600,
    },
    "session": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_SESSION_URL", default="redis://localhost:6379/2"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "session",
        "TIMEOUT": 86400,
    },
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "session"

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/3")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/4")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

CELERY_BEAT_SCHEDULE = {
    "summarize-old-conversations": {
        "task": "apps.chat.tasks.summarize_old_conversations",
        "schedule": 3600.0,
    },
    "cleanup-expired-sessions": {
        "task": "apps.chat.tasks.cleanup_expired_sessions",
        "schedule": 86400.0,
    },
    "generate-analytics-report": {
        "task": "apps.analytics.tasks.generate_daily_report",
        "schedule": 86400.0,
    },
    "warm-cache": {
        "task": "apps.chat.tasks.warm_cache",
        "schedule": 1800.0,
    },
}

# ── DRF ───────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "utils.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "utils.throttling.UserBurstRateThrottle",
        "utils.throttling.UserSustainedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user_burst": "30/minute",
        "user_sustained": "500/day",
        "anon": "10/minute",
        "chat_send": "20/minute",
    },
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "utils.exceptions.custom_exception_handler",
}

# ── JWT ───────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── AI Configuration ──────────────────────────────────────────────────────────
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
OPENAI_MODEL = config("OPENAI_MODEL", default="gpt-4o-mini")
OPENAI_MAX_TOKENS = config("OPENAI_MAX_TOKENS", default=2048, cast=int)
OPENAI_TEMPERATURE = config("OPENAI_TEMPERATURE", default=0.7, cast=float)
OPENAI_TIMEOUT = config("OPENAI_TIMEOUT", default=30, cast=int)
AI_SYSTEM_PROMPT = config(
    "AI_SYSTEM_PROMPT",
    default="You are a helpful, harmless, and honest AI assistant. Provide clear, concise, and accurate responses.",
)
AI_MAX_HISTORY_MESSAGES = config("AI_MAX_HISTORY_MESSAGES", default=20, cast=int)
AI_MAX_CONTEXT_TOKENS = config("AI_MAX_CONTEXT_TOKENS", default=4000, cast=int)

# ── Rate Limiting ─────────────────────────────────────────────────────────────
RATE_LIMIT_CHAT_MESSAGES_PER_MINUTE = config("RATE_LIMIT_CHAT_PER_MIN", default=20, cast=int)
RATE_LIMIT_CHAT_MESSAGES_PER_HOUR = config("RATE_LIMIT_CHAT_PER_HOUR", default=200, cast=int)
RATE_LIMIT_CHAT_MESSAGES_PER_DAY = config("RATE_LIMIT_CHAT_PER_DAY", default=1000, cast=int)

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="http://localhost:3000", cast=Csv())
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept", "accept-encoding", "authorization", "content-type",
    "dnt", "origin", "user-agent", "x-csrftoken", "x-requested-with", "x-session-id",
]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "app.log",
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO"},
        "apps": {"handlers": ["console", "file"], "level": "DEBUG", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "utils": {"handlers": ["console", "file"], "level": "DEBUG", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
