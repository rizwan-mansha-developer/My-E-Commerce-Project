from __future__ import annotations

from datetime import timedelta

from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.app_settings import api_settings as rest_auth_settings
from dj_rest_auth.registration.views import SocialLoginView
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from apps.accounts.serializers import AdminLoginSerializer, UserSerializer

# Access stays short; refresh cookie length is what “remember me” controls.
REMEMBER_REFRESH_LIFETIME = timedelta(days=30)
SESSION_REFRESH_LIFETIME = timedelta(hours=12)


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
