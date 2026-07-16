from __future__ import annotations

from django.urls import path

from apps.accounts.views import AdminLoginView, FacebookLoginView, GoogleLoginView

urlpatterns = [
    path("admin-login/", AdminLoginView.as_view(), name="admin-login"),
    path("google/", GoogleLoginView.as_view(), name="google-login"),
    path("facebook/", FacebookLoginView.as_view(), name="facebook-login"),
]
