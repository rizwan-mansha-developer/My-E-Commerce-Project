from __future__ import annotations

from django.urls import path

from apps.accounts.views import (
    AdminBootstrapSignupView,
    AdminBootstrapStatusView,
    AdminLoginView,
    AdminPasswordResetView,
    FacebookLoginView,
    GoogleLoginView,
)

urlpatterns = [
    path("admin-login/", AdminLoginView.as_view(), name="admin-login"),
    path(
        "admin-password-reset/",
        AdminPasswordResetView.as_view(),
        name="admin-password-reset",
    ),
    path(
        "admin-bootstrap/",
        AdminBootstrapStatusView.as_view(),
        name="admin-bootstrap-status",
    ),
    path(
        "admin-bootstrap/signup/",
        AdminBootstrapSignupView.as_view(),
        name="admin-bootstrap-signup",
    ),
    path("google/", GoogleLoginView.as_view(), name="google-login"),
    path("facebook/", FacebookLoginView.as_view(), name="facebook-login"),
]
