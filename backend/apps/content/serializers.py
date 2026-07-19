from __future__ import annotations

from rest_framework import serializers

from apps.content.models import Article, ArticleStatus


class ArticlePublicSerializer(serializers.ModelSerializer):
    is_coming_soon = serializers.BooleanField(read_only=True)

    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "body",
            "cover_image_url",
            "status",
            "published_at",
            "is_coming_soon",
        )

    def to_representation(self, instance: Article) -> dict:
        data = super().to_representation(instance)
        # Coming soon / draft teasers hide full body on public list/detail.
        if instance.status != ArticleStatus.PUBLISHED:
            data["body"] = ""
        return data


class ArticleAdminSerializer(serializers.ModelSerializer):
    is_coming_soon = serializers.BooleanField(read_only=True)

    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "body",
            "cover_image_url",
            "status",
            "published_at",
            "sort_order",
            "is_coming_soon",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "is_coming_soon")
