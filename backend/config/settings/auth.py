from __future__ import annotations

import os
from datetime import timedelta

from django.conf import settings

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_COOKIE": "darling-access-token",
    "JWT_AUTH_REFRESH_COOKIE": "darling-refresh-token",
    "JWT_AUTH_HTTPONLY": True,
    "JWT_AUTH_SECURE": not settings.DEBUG,
    "JWT_AUTH_SAMESITE": "Lax",
    "SESSION_LOGIN": False,
    "USER_DETAILS_SERIALIZER": "apps.accounts.serializers.UserSerializer",
}

ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_QUERY_EMAIL = True

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    },
    "facebook": {
        "APP": {
            "client_id": os.environ.get("FACEBOOK_APP_ID", ""),
            "secret": os.environ.get("FACEBOOK_APP_SECRET", ""),
        },
    },
}
