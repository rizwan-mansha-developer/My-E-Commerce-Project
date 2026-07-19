from __future__ import annotations

from rest_framework import serializers

from apps.catalog.validators import validate_pakistan_mobile
from apps.orders.models import Order, PaymentMethod


class OrderLineSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=10)


class CheckoutBaseSerializer(serializers.Serializer):
    """Shared customer + payment fields for express and cart checkout."""

    full_name = serializers.CharField(min_length=2, max_length=255, trim_whitespace=True)
    phone_number = serializers.CharField(min_length=11, max_length=11, trim_whitespace=True)
    shipping_address = serializers.CharField(
        min_length=5,
        max_length=500,
        trim_whitespace=True,
    )
    city = serializers.CharField(min_length=2, max_length=100, trim_whitespace=True)
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices,
        default=PaymentMethod.COD,
    )
    cod_confirmed = serializers.BooleanField(default=False)
    discount_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=32,
        trim_whitespace=True,
        default="",
    )

    def validate_phone_number(self, value: str) -> str:
        validate_pakistan_mobile(value)
        return value

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        payment_method = attrs.get("payment_method", PaymentMethod.COD)
        cod_confirmed = attrs.get("cod_confirmed", False)

        # Launch: COD only. Online methods stay in the schema for Phase 4.
        if payment_method != PaymentMethod.COD:
            raise serializers.ValidationError(
                {
                    "payment_method": (
                        "Online payments are coming soon. "
                        "Please pay with Cash on Delivery."
                    )
                },
                code="cod_only_launch",
            )

        if payment_method == PaymentMethod.COD and not cod_confirmed:
            raise serializers.ValidationError(
                {"cod_confirmed": "Confirm Cash on Delivery to place your order."},
                code="cod_required",
            )

        return attrs


class ExpressCheckoutSerializer(CheckoutBaseSerializer):
    """Minimal one-screen checkout — COD at launch."""

    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=10, default=1)


class CartCheckoutSerializer(CheckoutBaseSerializer):
    """Full cart checkout — one order, multiple line items, COD at launch."""

    items = OrderLineSerializer(many=True, allow_empty=False)

    def validate_items(self, value: list[dict[str, object]]) -> list[dict[str, object]]:
        if len(value) > 20:
            raise serializers.ValidationError("Too many items in one order.")
        return value


class ExpressOrderResponseSerializer(serializers.ModelSerializer):
    redirect_url = serializers.CharField(required=False, allow_blank=True)
    payment_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "tracking_number",
            "subtotal_amount",
            "discount_amount",
            "discount_code",
            "total_amount",
            "payment_method",
            "status",
            "created_at",
            "redirect_url",
            "payment_id",
        )
