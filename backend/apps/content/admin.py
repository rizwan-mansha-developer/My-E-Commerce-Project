from django.contrib import admin

from apps.content.models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "sort_order", "published_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("title", "slug", "excerpt")
    prepopulated_fields = {"slug": ("title",)}
