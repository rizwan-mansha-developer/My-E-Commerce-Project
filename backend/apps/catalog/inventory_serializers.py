from __future__ import annotations

from rest_framework import serializers

from apps.catalog.models import ProductVariant


class InventoryAdminSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source="product.id", read_only=True)
    product_title = serializers.CharField(source="product.title", read_only=True)
    product_slug = serializers.SlugField(source="product.slug", read_only=True)
    effective_price = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "product_id",
            "product_title",
            "product_slug",
            "color",
            "sku",
            "effective_price",
            "quantity_in_stock",
            "safety_threshold",
            "is_low_stock",
            "is_active",
            "updated_at",
        )

    def get_effective_price(self, obj: ProductVariant) -> str:
        return str(obj.effective_price)

    def get_is_low_stock(self, obj: ProductVariant) -> bool:
        return obj.quantity_in_stock <= obj.safety_threshold


class InventoryUpdateSerializer(serializers.Serializer):
    quantity_in_stock = serializers.IntegerField(min_value=0, required=False)
    safety_threshold = serializers.IntegerField(min_value=0, required=False)

    def validate(self, attrs: dict) -> dict:
        if not attrs:
            raise serializers.ValidationError("Provide at least one field to update.")
        return attrs
