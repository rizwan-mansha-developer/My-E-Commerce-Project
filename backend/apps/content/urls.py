from __future__ import annotations

from django.urls import path

from apps.content.views import (
    ArticleAdminDetailView,
    ArticleAdminListView,
    ArticleDetailView,
    ArticleListView,
)

urlpatterns = [
    path("articles/", ArticleListView.as_view(), name="article-list"),
    path("articles/<slug:slug>/", ArticleDetailView.as_view(), name="article-detail"),
    path("admin/articles/", ArticleAdminListView.as_view(), name="admin-article-list"),
    path(
        "admin/articles/<uuid:article_id>/",
        ArticleAdminDetailView.as_view(),
        name="admin-article-detail",
    ),
]
