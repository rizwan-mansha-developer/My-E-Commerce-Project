from __future__ import annotations
from decimal import Decimal
from rest_framework import serializers
from apps.catalog.models import Category, Product, ProductImage, ProductVariant

class ProductVariantWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "color",
            "sku",
            "price_override",
            "quantity_in_stock",
            "safety_threshold",
            "is_active",
        )
        read_only_fields = ("id",)

class ProductImageWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "url", "alt_text", "sort_order")
        read_only_fields = ("id",)

class ProductAdminSerializer(serializers.ModelSerializer):
    variants = ProductVariantWriteSerializer(many=True, read_only=True)
    gallery_images = ProductImageWriteSerializer(many=True, read_only=True)
    primary_image = serializers.SerializerMethodField()
    total_stock = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()
    category_id = serializers.UUIDField(
        source="category.id", allow_null=True, read_only=True
    )
    category_slug = serializers.CharField(
        source="category.slug", allow_null=True, read_only=True
    )
    category_name = serializers.CharField(
        source="category.name", allow_null=True, read_only=True
    )
    class Meta:
        model = Product
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "base_price",
            "compare_at_price",
            "video_url",
            "image_urls",
            "is_active",
            "category_id",
            "category_slug",
            "category_name",
            "is_top_pick",
            "is_bestseller",
            "featured_sort",
            "primary_image",
            "total_stock",
            "in_stock",
            "stock_status",
            "variants",
            "gallery_images",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "category_id",
            "category_slug",
            "category_name",
            "primary_image",
            "total_stock",
            "in_stock",
            "stock_status",
            "created_at",
            "updated_at",
        )
    def get_primary_image(self, obj: Product) -> str | None:
        from apps.catalog.serializers import ordered_product_image_urls

        urls = ordered_product_image_urls(obj)
        return urls[0] if urls else None
    def get_total_stock(self, obj: Product) -> int:
        return sum(
            variant.quantity_in_stock
            for variant in obj.variants.filter(is_active=True)
        )
    def get_in_stock(self, obj: Product) -> bool:
        return any(
            variant.quantity_in_stock > 0
            for variant in obj.variants.filter(is_active=True)
        )
    def get_stock_status(self, obj: Product) -> str:
        if not obj.is_active:
            return "inactive"
        variants = list(obj.variants.filter(is_active=True))
        if not variants or all(v.quantity_in_stock == 0 for v in variants):
            return "out_of_stock"
        if any(v.quantity_in_stock <= v.safety_threshold for v in variants):
            return "low_stock"
        return "in_stock"

class ProductAdminWriteSerializer(serializers.ModelSerializer):
    variants = ProductVariantWriteSerializer(many=True, required=False)
    gallery_images = ProductImageWriteSerializer(many=True, required=False)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.all_objects.all(),
        source="category",
        allow_null=True,
        required=False,
    )
    class Meta:
        model = Product
        fields = (
            "title",
            "slug",
            "description",
            "base_price",
            "compare_at_price",
            "video_url",
            "image_urls",
            "is_active",
            "category_id",
            "is_top_pick",
            "is_bestseller",
            "featured_sort",
            "variants",
            "gallery_images",
        )
    def create(self, validated_data: dict) -> Product:
        variants_data = validated_data.pop("variants", [])
        images_data = validated_data.pop("gallery_images", [])
        product = Product.objects.create(**validated_data)
        self._sync_variants(product, variants_data)
        self._sync_images(product, images_data)
        return product
    def update(self, instance: Product, validated_data: dict) -> Product:
        variants_data = validated_data.pop("variants", None)
        images_data = validated_data.pop("gallery_images", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if variants_data is not None:
            ProductVariant.all_objects.filter(product=instance).delete()
            self._sync_variants(instance, variants_data)
        if images_data is not None:
            instance.gallery_images.all().delete()
            self._sync_images(instance, images_data)
        return instance
    def _sync_variants(
        self, product: Product, variants_data: list[dict]
    ) -> None:
        for item in variants_data:
            ProductVariant.objects.create(product=product, **item)
    def _sync_images(self, product: Product, images_data: list[dict]) -> None:
        for item in images_data[:10]:
            ProductImage.objects.create(product=product, **item)

    def validate_image_urls(self, value: list) -> list:
        cleaned = [str(url).strip() for url in value if str(url).strip()]
        if len(cleaned) > 10:
            raise serializers.ValidationError("Maximum 10 product images allowed.")
        if not cleaned:
            raise serializers.ValidationError("Add at least one product image.")
        return cleaned

    def validate_gallery_images(self, value: list) -> list:
        if len(value) > 10:
            raise serializers.ValidationError("Maximum 10 product images allowed.")
        return value

    def validate_base_price(self, value: Decimal) -> Decimal:
        if value < 0:
            raise serializers.ValidationError("Base price must be non-negative.")
        return value

    def validate_compare_at_price(self, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Compare-at price must be non-negative."
            )
        return value

    def validate(self, attrs: dict) -> dict:
        base_price = attrs.get("base_price")
        if base_price is None and self.instance is not None:
            base_price = self.instance.base_price
        compare_at = attrs.get("compare_at_price", serializers.empty)
        if compare_at is serializers.empty:
            compare_at = (
                self.instance.compare_at_price if self.instance is not None else None
            )
        if (
            compare_at is not None
            and base_price is not None
            and compare_at <= base_price
        ):
            raise serializers.ValidationError(
                {
                    "compare_at_price": (
                        "Was/compare-at price must be higher than the now price."
                    )
                }
            )
        return attrs
