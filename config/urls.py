"""
Root URL configuration.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from utils.views import HealthCheckView, APIRootView

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Health check
    path("health/", HealthCheckView.as_view(), name="health-check"),

    # API root
    path("api/", APIRootView.as_view(), name="api-root"),

    # Auth
    path("api/v1/auth/", include("apps.accounts.urls")),

    # Chat
    path("api/v1/chat/", include("apps.chat.urls")),

    # Analytics (admin only)
    path("api/v1/analytics/", include("apps.analytics.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
