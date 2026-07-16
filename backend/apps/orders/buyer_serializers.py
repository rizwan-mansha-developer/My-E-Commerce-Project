from __future__ import annotations

from rest_framework import serializers

from apps.orders.models import Order, OrderItem, OrderStatus


class BuyerOrderItemSerializer(serializers.ModelSerializer):
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


class BuyerOrderSerializer(serializers.ModelSerializer):
    items = BuyerOrderItemSerializer(many=True, read_only=True)

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


class OrderTrackRequestSerializer(serializers.Serializer):
    tracking_number = serializers.CharField(max_length=20)
    phone_number = serializers.CharField(max_length=11)


class BuyerDashboardSummarySerializer(serializers.Serializer):
    order_count = serializers.IntegerField()
    wishlist_count = serializers.IntegerField()
    total_spent = serializers.CharField()
    delivered_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    recent_orders = BuyerOrderSerializer(many=True)
