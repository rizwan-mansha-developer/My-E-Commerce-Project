from __future__ import annotations

import secrets
import uuid

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class ArticleStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    COMING_SOON = "COMING_SOON", "Coming soon"
    PUBLISHED = "PUBLISHED", "Published"


class Article(models.Model):
    """Editorial / journal post — supports Coming soon teaser state."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    excerpt = models.CharField(max_length=300, blank=True)
    body = models.TextField(
        blank=True,
        help_text="Full article body. Optional while Coming soon.",
    )
    cover_image_url = models.URLField(max_length=500, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ArticleStatus.choices,
        default=ArticleStatus.COMING_SOON,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "sort_order"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(self.title) or "article"
            self.slug = f"{base}-{secrets.token_hex(2)}"
        if self.status == ArticleStatus.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_coming_soon(self) -> bool:
        return self.status == ArticleStatus.COMING_SOON
