from __future__ import annotations

from rest_framework import serializers

from apps.orders.models import Order, OrderItem, OrderStatus


class OrderItemAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_title",
            "variant_color",
            "sku",
            "unit_price",
            "quantity",
            "line_total",
        )


class OrderAdminSerializer(serializers.ModelSerializer):
    items = OrderItemAdminSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "tracking_number",
            "full_name",
            "phone_number",
            "shipping_address",
            "city",
            "total_amount",
            "payment_method",
            "status",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatus.choices)
