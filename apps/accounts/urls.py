from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from .views import RegisterView, ProfileView, APIKeyView, TokenObtainPairView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", TokenBlacklistView.as_view(), name="token-blacklist"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("api-key/", APIKeyView.as_view(), name="api-key"),
]
