from __future__ import annotations
import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from repositories.base import SoftDeleteModel

class Category(SoftDeleteModel):
    """Storefront collection — New In, RTW, Sale, etc."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True, db_index=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0, db_index=True)
    show_in_nav = models.BooleanField(default=True)
    accent = models.BooleanField(
        default=False,
        help_text="Highlight in nav (e.g. Sale).",
    )
    hero_title = models.CharField(max_length=120, blank=True)
    hero_subtitle = models.CharField(max_length=255, blank=True)
    hero_images = models.JSONField(
        default=list,
        blank=True,
        help_text="Up to 3 image URLs for the homepage hero carousel.",
    )
    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"
        indexes = [
            models.Index(fields=["slug", "is_active"]),
            models.Index(fields=["show_in_nav", "sort_order"]),
        ]
    def __str__(self) -> str:
        return self.name

class Product(SoftDeleteModel):
    """Core catalog product with SEO slug and optional showcase video."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Selling (now) price charged at checkout.",
    )
    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Optional 'was' price for strikethrough sale display.",
    )
    video_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Direct mp4/stream URL for product showcase reel.",
    )
    image_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered gallery URLs (webp/avif preferred).",
    )
    is_top_pick = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Show in homepage Top Picks.",
    )
    is_bestseller = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Show in homepage Bestsellers.",
    )
    featured_sort = models.PositiveSmallIntegerField(
        default=0,
        help_text="Lower numbers appear first in featured sections.",
    )
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug", "is_active"]),
            models.Index(fields=["is_active", "-created_at"]),
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["is_top_pick", "featured_sort"]),
            models.Index(fields=["is_bestseller", "featured_sort"]),
        ]
    def __str__(self) -> str:
        return self.title

    @property
    def is_on_sale(self) -> bool:
        return (
            self.compare_at_price is not None
            and self.compare_at_price > self.base_price
        )

    @property
    def discount_percent(self) -> int:
        if not self.is_on_sale or self.compare_at_price is None:
            return 0
        if self.compare_at_price <= 0:
            return 0
        ratio = (self.compare_at_price - self.base_price) / self.compare_at_price
        return max(0, min(99, int(round(ratio * 100))))

class ProductImage(models.Model):
    """Relational media rows for rich gallery metadata and sort order."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="gallery_images",
    )
    url = models.URLField(max_length=500)
    alt_text = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0, db_index=True)
    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["product", "sort_order"]),
        ]
    def __str__(self) -> str:
        return f"{self.product.title} — image {self.sort_order}"

class ProductVariant(SoftDeleteModel):
    """Sellable SKU with color, optional price override, and inventory counts."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    color = models.CharField(max_length=100, help_text="e.g. Dusty Pink")
    sku = models.CharField(max_length=64, unique=True, db_index=True)
    price_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    quantity_in_stock = models.PositiveIntegerField(default=0)
    safety_threshold = models.PositiveIntegerField(
        default=5,
        help_text="Alert when stock falls to or below this level.",
    )
    class Meta:
        ordering = ["color"]
        indexes = [
            models.Index(fields=["product", "is_active"]),
            models.Index(fields=["sku"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "color"],
                condition=models.Q(is_active=True),
                name="unique_active_color_per_product",
            ),
        ]
    def __str__(self) -> str:
        return f"{self.product.title} — {self.color} ({self.sku})"
    @property
    def effective_price(self) -> Decimal:
        if self.price_override is not None:
            return self.price_override
        return self.product.base_price
    @property
    def is_low_stock(self) -> bool:
        return self.quantity_in_stock <= self.safety_threshold

class WishlistItem(models.Model):
    """Guest or authenticated favorite — no account required (session cookie)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="wishlist_items",
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="wishlist_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "product"]),
            models.Index(fields=["session_key", "product"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                condition=models.Q(user__isnull=False),
                name="unique_wishlist_item_per_user",
            ),
            models.UniqueConstraint(
                fields=["session_key", "product"],
                condition=models.Q(session_key__isnull=False),
                name="unique_wishlist_item_per_session",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(user__isnull=False)
                    | models.Q(session_key__isnull=False)
                ),
                name="wishlist_requires_user_or_session",
            ),
        ]
    def __str__(self) -> str:
        owner = self.user_id or self.session_key
        return f"Wishlist {owner} → {self.product.title}"
