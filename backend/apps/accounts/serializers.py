from __future__ import annotations

import os

from allauth.account.utils import user_pk_to_url_str
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from dj_rest_auth.serializers import PasswordResetSerializer
from rest_framework import serializers

User = get_user_model()


def frontend_password_reset_url(request, user, temp_key: str) -> str:
    """Build a Next.js reset link instead of Django's default confirm URL."""
    base = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    uid = user_pk_to_url_str(user)
    return f"{base}/admin/reset-password/{uid}/{temp_key}"


def find_active_user_by_login(email: str):
    """Match Django User.email or username (either may hold the login email)."""
    return (
        User.objects.filter(is_active=True)
        .filter(Q(email__iexact=email) | Q(username__iexact=email))
        .order_by("-is_superuser")
        .first()
    )


class DarlingPasswordResetSerializer(PasswordResetSerializer):
    """Password reset emails point at the Darling admin frontend."""

    def get_email_options(self) -> dict:
        return {"url_generator": frontend_password_reset_url}


class AdminPasswordResetSerializer(serializers.Serializer):
    """Admin forgot-password: require an existing superuser email."""

    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate(self, attrs: dict) -> dict:
        email = attrs["email"]
        user = find_active_user_by_login(email)
        if user is None:
            raise serializers.ValidationError(
                {"email": "No account exists with this email."}
            )
        if not user.is_superuser:
            raise serializers.ValidationError(
                {"email": "No super admin account exists with this email."}
            )
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_superuser",
        )
        read_only_fields = fields


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    remember_me = serializers.BooleanField(default=False, required=False)

    def validate(self, attrs: dict) -> dict:
        email = attrs["email"].strip().lower()
        password = attrs["password"]
        request = self.context.get("request")

        user = find_active_user_by_login(email)
        if user is not None:
            authenticated = authenticate(
                request=request,
                username=user.get_username(),
                password=password,
            )
        else:
            authenticated = authenticate(
                request=request,
                username=email,
                password=password,
            )

        if authenticated is None or not authenticated.is_active:
            raise serializers.ValidationError("Invalid email or password.")

        if not authenticated.is_superuser:
            raise serializers.ValidationError(
                "Only super admins can access the admin panel."
            )

        attrs["user"] = authenticated
        return attrs


class AdminBootstrapSignupSerializer(serializers.Serializer):
    """Create the first superuser only when none exist yet."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    password_confirm = serializers.CharField(
        write_only=True, min_length=8, trim_whitespace=False
    )
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate(self, attrs: dict) -> dict:
        if User.objects.filter(is_superuser=True).exists():
            raise serializers.ValidationError(
                "A super admin already exists. Use sign in instead."
            )

        email = attrs["email"].strip().lower()
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": "This email is already in use."})

        if User.objects.filter(username__iexact=email).exists():
            raise serializers.ValidationError({"email": "This email is already in use."})

        attrs["email"] = email
        return attrs

    def create(self, validated_data: dict) -> User:
        from allauth.account.models import EmailAddress

        email = validated_data["email"]
        user = User.objects.create_superuser(
            username=email,
            email=email,
            password=validated_data["password"],
            first_name=(validated_data.get("first_name") or "").strip(),
        )
        EmailAddress.objects.update_or_create(
            user=user,
            email=email,
            defaults={"primary": True, "verified": True},
        )
        return user
