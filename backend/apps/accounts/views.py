from __future__ import annotations

from datetime import timedelta

from allauth.account.forms import default_token_generator
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.app_settings import api_settings as rest_auth_settings
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from apps.accounts.serializers import (
    AdminBootstrapSignupSerializer,
    AdminLoginSerializer,
    AdminPasswordResetSerializer,
    UserSerializer,
    frontend_password_reset_url,
)

User = get_user_model()

# Access stays short; refresh cookie length is what “remember me” controls.
REMEMBER_REFRESH_LIFETIME = timedelta(days=30)
SESSION_REFRESH_LIFETIME = timedelta(hours=12)


def _admin_auth_response(user, *, remember_me: bool = True) -> Response:
    refresh = RefreshToken.for_user(user)
    refresh_lifetime = (
        REMEMBER_REFRESH_LIFETIME if remember_me else SESSION_REFRESH_LIFETIME
    )
    refresh.set_exp(lifetime=refresh_lifetime)

    access = refresh.access_token
    access_lifetime = jwt_settings.ACCESS_TOKEN_LIFETIME
    access.set_exp(lifetime=access_lifetime)

    now = timezone.now()
    response = Response(
        {
            "user": UserSerializer(user).data,
            "remember_me": remember_me,
        },
        status=status.HTTP_200_OK,
    )
    _set_auth_cookies(
        response,
        access_token=str(access),
        refresh_token=str(refresh),
        access_expires=now + access_lifetime,
        refresh_expires=now + refresh_lifetime,
    )
    return response


class GoogleLoginView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter


class FacebookLoginView(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter


def _set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    access_expires,
    refresh_expires,
) -> None:
    cookie_secure = rest_auth_settings.JWT_AUTH_SECURE
    cookie_httponly = rest_auth_settings.JWT_AUTH_HTTPONLY
    cookie_samesite = rest_auth_settings.JWT_AUTH_SAMESITE
    cookie_domain = rest_auth_settings.JWT_AUTH_COOKIE_DOMAIN

    access_name = rest_auth_settings.JWT_AUTH_COOKIE
    refresh_name = rest_auth_settings.JWT_AUTH_REFRESH_COOKIE
    refresh_path = rest_auth_settings.JWT_AUTH_REFRESH_COOKIE_PATH

    if access_name:
        response.set_cookie(
            access_name,
            access_token,
            expires=access_expires,
            secure=cookie_secure,
            httponly=cookie_httponly,
            samesite=cookie_samesite,
            domain=cookie_domain,
        )

    if refresh_name:
        response.set_cookie(
            refresh_name,
            refresh_token,
            expires=refresh_expires,
            secure=cookie_secure,
            httponly=cookie_httponly,
            samesite=cookie_samesite,
            path=refresh_path,
            domain=cookie_domain,
        )


@extend_schema(
    tags=["Auth"],
    summary="Superuser admin login",
    request=AdminLoginSerializer,
    responses={200: UserSerializer},
)
class AdminLoginView(APIView):
    """Email/password login for the admin panel — superusers only."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = AdminLoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        remember_me = bool(serializer.validated_data.get("remember_me"))
        return _admin_auth_response(user, remember_me=remember_me)


@extend_schema(
    tags=["Auth"],
    summary="Whether the first super admin still needs to be created",
    responses={200: {"type": "object", "properties": {"needs_bootstrap": {"type": "boolean"}}}},
)
class AdminBootstrapStatusView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        needs_bootstrap = not User.objects.filter(is_superuser=True).exists()
        return Response({"needs_bootstrap": needs_bootstrap})


@extend_schema(
    tags=["Auth"],
    summary="Create the first super admin (only when none exist)",
    request=AdminBootstrapSignupSerializer,
    responses={201: UserSerializer},
)
class AdminBootstrapSignupView(APIView):
    """One-time bootstrap signup for an empty Neon / auth_user table."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = AdminBootstrapSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        response = _admin_auth_response(user, remember_me=True)
        response.status_code = status.HTTP_201_CREATED
        return response


@extend_schema(
    tags=["Auth"],
    summary="Admin forgot password",
    request=AdminPasswordResetSerializer,
)
class AdminPasswordResetView(APIView):
    """Send a password reset link for an existing super admin."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = AdminPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        requested_email = serializer.validated_data["email"]
        # Prefer the address the admin typed; fall back to stored User.email.
        delivery_email = requested_email or (user.email or user.get_username())

        # Keep email/username aligned when login was stored only on username.
        if not user.email or user.email.lower() != requested_email:
            user.email = requested_email
            user.save(update_fields=["email"])

        token = default_token_generator.make_token(user)
        reset_url = frontend_password_reset_url(request, user, token)

        subject = "Reset your Darling admin password"
        message = (
            "You requested a password reset for the Darling admin panel.\n\n"
            f"Open this link to set a new password:\n{reset_url}\n\n"
            "If you did not request this, you can ignore this email."
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[delivery_email],
            fail_silently=False,
        )

        payload: dict = {
            "detail": "Password reset link sent. Check your email.",
        }
        # No real inbox in local console-email mode — expose the link in DEBUG.
        if settings.DEBUG:
            payload["reset_url"] = reset_url
            payload["detail"] = (
                "Password reset link generated. "
                "Locally, use the link below (also printed in the Django console)."
            )
        return Response(payload, status=status.HTTP_200_OK)
