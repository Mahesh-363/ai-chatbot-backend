from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "username", "first_name", "last_name", "password", "password_confirm"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    tier_display = serializers.CharField(source="get_tier_display", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "first_name", "last_name", "full_name",
            "tier", "tier_display", "daily_message_limit", "monthly_token_limit",
            "tokens_used_this_month", "date_joined", "last_seen",
        ]
        read_only_fields = [
            "id", "email", "tier", "daily_message_limit", "monthly_token_limit",
            "tokens_used_this_month", "date_joined", "last_seen",
        ]


class APIKeySerializer(serializers.Serializer):
    api_key = serializers.CharField(read_only=True)
    api_key_created_at = serializers.DateTimeField(read_only=True)
