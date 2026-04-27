import logging
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model
from .serializers import UserRegistrationSerializer, UserProfileSerializer, APIKeySerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("New user registered: %s", user.email)
        return Response(
            {"message": "Account created successfully.", "user_id": str(user.id)},
            status=status.HTTP_201_CREATED,
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class APIKeyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = APIKeySerializer(request.user)
        return Response(serializer.data)

    def post(self, request):
        key = request.user.generate_api_key()
        logger.info("API key generated for user: %s", request.user.email)
        return Response({"api_key": key, "message": "Store this key securely — it won't be shown again."})

    def delete(self, request):
        request.user.revoke_api_key()
        return Response({"message": "API key revoked."}, status=status.HTTP_200_OK)
