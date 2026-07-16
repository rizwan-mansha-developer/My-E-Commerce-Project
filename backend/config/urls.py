from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.utils import extend_schema, inline_serializer
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response


HealthResponseSerializer = inline_serializer(
    name="HealthResponse",
    fields={
        "status": serializers.CharField(),
        "service": serializers.CharField(),
    },
)


@extend_schema(
    tags=["Health"],
    summary="Health check",
    responses={200: HealthResponseSerializer},
)
@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok", "service": "darling-api"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health_check, name="health-check"),
    path("api/v1/catalog/", include("apps.catalog.urls")),
    path("api/v1/orders/", include("apps.orders.urls")),
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if settings.DEBUG and not getattr(settings, "USE_S3", False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

