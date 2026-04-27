"""
Custom User model with API key support.
"""
import uuid
import secrets
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    username = models.CharField(max_length=150, unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(null=True, blank=True)

    # Subscription / usage tier
    TIER_FREE = "free"
    TIER_PRO = "pro"
    TIER_ENTERPRISE = "enterprise"
    TIER_CHOICES = [
        (TIER_FREE, "Free"),
        (TIER_PRO, "Pro"),
        (TIER_ENTERPRISE, "Enterprise"),
    ]
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default=TIER_FREE)
    daily_message_limit = models.IntegerField(default=50)
    monthly_token_limit = models.IntegerField(default=100_000)
    tokens_used_this_month = models.IntegerField(default=0)

    # API key for programmatic access
    api_key = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    api_key_created_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["email", "is_active"]),
            models.Index(fields=["api_key"]),
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    def generate_api_key(self):
        self.api_key = secrets.token_urlsafe(48)
        self.api_key_created_at = timezone.now()
        self.save(update_fields=["api_key", "api_key_created_at"])
        return self.api_key

    def revoke_api_key(self):
        self.api_key = None
        self.api_key_created_at = None
        self.save(update_fields=["api_key", "api_key_created_at"])
