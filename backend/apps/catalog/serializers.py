from __future__ import annotations
from decimal import Decimal
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from apps.catalog.models import Category, Product, ProductImage, ProductVariant

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "sort_order",
            "show_in_nav",
            "accent",
            "hero_title",
            "hero_subtitle",
            "hero_images",
        )

class CategoryListResponseSerializer(serializers.Serializer):
    results = CategorySerializer(many=True)
    count = serializers.IntegerField()

class WishlistToggleSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()

class WishlistProductSerializer(serializers.ModelSerializer):
    price_display = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "title",
            "slug",
            "base_price",
            "compare_at_price",
            "price_display",
            "is_on_sale",
            "discount_percent",
            "primary_image",
            "image_urls",
            "video_url",
        )

    def get_price_display(self, obj: Product) -> str:
        return str(obj.base_price.quantize(Decimal("0.01")))

    def get_primary_image(self, obj: Product) -> str | None:
        gallery = obj.gallery_images.order_by("sort_order").first()
        if gallery:
            return gallery.url
        if obj.image_urls:
            return obj.image_urls[0]
        return None

class WishlistStateSerializer(serializers.Serializer):
    product_ids = serializers.ListField(child=serializers.UUIDField())
    count = serializers.IntegerField()
    items = WishlistProductSerializer(many=True)

class WishlistToggleResponseSerializer(serializers.Serializer):
    favorited = serializers.BooleanField()
    product_id = serializers.UUIDField()
    total_count = serializers.IntegerField()

class ProductVariantSerializer(serializers.ModelSerializer):
    effective_price = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "color",
            "sku",
            "effective_price",
            "in_stock",
            "is_low_stock",
        )
    def get_effective_price(self, obj: ProductVariant) -> str:
        return str(obj.effective_price.quantize(Decimal("0.01")))
    def get_in_stock(self, obj: ProductVariant) -> bool:
        return obj.quantity_in_stock > 0
    def get_is_low_stock(self, obj: ProductVariant) -> bool:
        return obj.is_low_stock

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("url", "alt_text", "sort_order")

class ProductListSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    price_display = serializers.SerializerMethodField()
    category_slug = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "title",
            "slug",
            "base_price",
            "compare_at_price",
            "price_display",
            "is_on_sale",
            "discount_percent",
            "primary_image",
            "video_url",
            "category_slug",
            "category_name",
            "is_top_pick",
            "is_bestseller",
            "featured_sort",
        )
    def get_primary_image(self, obj: Product) -> str | None:
        gallery = obj.gallery_images.order_by("sort_order").first()
        if gallery:
            return gallery.url
        if obj.image_urls:
            return obj.image_urls[0]
        return None
    def get_price_display(self, obj: Product) -> str:
        return str(obj.base_price.quantize(Decimal("0.01")))
    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_category_slug(self, obj: Product) -> str | None:
        return obj.category.slug if obj.category_id else None
    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_category_name(self, obj: Product) -> str | None:
        return obj.category.name if obj.category_id else None

class ProductListResponseSerializer(serializers.Serializer):
    results = ProductListSerializer(many=True)
    count = serializers.IntegerField()

class ProductDetailSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    variants = ProductVariantSerializer(many=True, read_only=True)
    price_display = serializers.SerializerMethodField()
    category_slug = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "base_price",
            "compare_at_price",
            "price_display",
            "is_on_sale",
            "discount_percent",
            "video_url",
            "images",
            "variants",
            "category_slug",
            "category_name",
            "is_top_pick",
            "is_bestseller",
        )
    @extend_schema_field(ProductImageSerializer(many=True))
    def get_images(self, obj: Product) -> list[dict[str, object]]:
        gallery = [
            {"url": image.url, "alt_text": image.alt_text, "sort_order": image.sort_order}
            for image in obj.gallery_images.order_by("sort_order")
        ]
        if gallery:
            return gallery
        return [
            {"url": url, "alt_text": obj.title, "sort_order": index}
            for index, url in enumerate(obj.image_urls)
        ]
    def get_price_display(self, obj: Product) -> str:
        return str(obj.base_price.quantize(Decimal("0.01")))
    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_category_slug(self, obj: Product) -> str | None:
        return obj.category.slug if obj.category_id else None
    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_category_name(self, obj: Product) -> str | None:
        return obj.category.name if obj.category_id else None
