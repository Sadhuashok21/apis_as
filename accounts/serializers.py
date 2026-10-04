from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import ClientApplication, UserProfile, UserSession


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    phone_number = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    email_verified = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "user_id",
            "email",
            "name",
            "lastname",
            "username",
            "profile",
            "user_type",
            "status",
            "created_at",
            "phone_number",
            "bio",
            "email_verified",
        ]
        read_only_fields = ["user_id", "email", "username", "user_type", "status", "created_at"]

    def get_phone_number(self, obj):
        profile = getattr(obj, "accounts_profile", None)
        return profile.phone_number if profile else ""

    def get_bio(self, obj):
        profile = getattr(obj, "accounts_profile", None)
        return profile.bio if profile else ""

    def get_email_verified(self, obj):
        profile = getattr(obj, "accounts_profile", None)
        return profile.email_verified if profile else False


class SignupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50, required=True)
    lastname = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=6, required=True)
    username = serializers.CharField(max_length=50, required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=25, required=False, allow_blank=True, default="")
    platform = serializers.CharField(max_length=20, required=False, default="web")
    platform_name = serializers.CharField(max_length=50, required=False, default="ascentracore")
    type = serializers.CharField(max_length=20, required=False, default="user")

    def validate_email(self, value):
        norm = value.strip().lower()
        if User.objects.filter(email__iexact=norm).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return norm

    def validate_username(self, value):
        if not value:
            return ""
        norm = value.strip()
        if User.objects.filter(username__iexact=norm).exists():
            raise serializers.ValidationError("This username is already taken.")
        return norm


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    client_id = serializers.CharField(required=False, allow_blank=True, default="")


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=6)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=6)


class UpdateProfileSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    lastname = serializers.CharField(max_length=50, required=False, allow_blank=True)
    profile = serializers.CharField(max_length=500, required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=25, required=False, allow_blank=True)
    bio = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class ClientApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientApplication
        fields = ["client_id", "name", "description", "logo_url", "is_enabled", "created_at"]


class UserSessionSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = [
            "session_id",
            "client_name",
            "ip_address",
            "user_agent",
            "created_at",
            "last_active_at",
            "expires_at",
            "is_revoked",
            "is_current",
        ]

    def get_client_name(self, obj):
        return obj.client_app.name if obj.client_app else "Central Accounts Portal"

    def get_is_current(self, obj):
        req_session_id = getattr(self.context.get("request"), "auth_session_id", None)
        return obj.session_id == req_session_id


class OAuthAuthorizeSerializer(serializers.Serializer):
    client_id = serializers.CharField(required=True)
    redirect_uri = serializers.CharField(required=True)
    code_challenge = serializers.CharField(required=True)
    code_challenge_method = serializers.CharField(required=False, allow_blank=True, default="S256")
    state = serializers.CharField(required=False, allow_blank=True, default="")
    scope = serializers.CharField(required=False, allow_blank=True, default="openid profile email")
    nonce = serializers.CharField(required=False, allow_blank=True, default="")


class OAuthTokenSerializer(serializers.Serializer):
    client_id = serializers.CharField(required=True)
    code = serializers.CharField(required=True)
    code_verifier = serializers.CharField(required=True)
    redirect_uri = serializers.CharField(required=True)

