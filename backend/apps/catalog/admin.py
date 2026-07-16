from django.contrib import admin
from apps.catalog.models import Category, Product, ProductImage, ProductVariant, WishlistItem

@admin.register(Category)

class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "sort_order",
        "show_in_nav",
        "accent",
        "is_active",
    )
    list_filter = ("is_active", "show_in_nav", "accent")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("sort_order", "name")

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    ordering = ("sort_order",)

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = (
        "color",
        "sku",
        "price_override",
        "quantity_in_stock",
        "safety_threshold",
        "is_active",
    )

@admin.register(Product)

class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "category",
        "base_price",
        "compare_at_price",
        "is_top_pick",
        "is_bestseller",
        "is_active",
        "created_at",
    )
    list_filter = (
        "is_active",
        "is_top_pick",
        "is_bestseller",
        "category",
        "created_at",
    )
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    inlines = (ProductVariantInline, ProductImageInline)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("category",)

@admin.register(ProductVariant)

class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "product",
        "color",
        "quantity_in_stock",
        "safety_threshold",
        "is_active",
    )
    list_filter = ("is_active", "product")
    search_fields = ("sku", "color", "product__title")

@admin.register(WishlistItem)

class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "session_key", "created_at")
    list_filter = ("created_at",)
    search_fields = ("product__title", "session_key", "user__username")
