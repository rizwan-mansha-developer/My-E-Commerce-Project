from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db import transaction

from apps.catalog.models import Product, ProductVariant
from services.order_service import CreateOrderPayload, OrderLineInput, OrderService


@pytest.mark.django_db
class TestOrderNotificationIntegration:
    @pytest.fixture
    def variant(self) -> ProductVariant:
        product = Product.objects.create(
            title="Silk Slip Dress",
            slug="silk-slip-dress",
            base_price=Decimal("12500.00"),
        )
        return ProductVariant.objects.create(
            product=product,
            color="Dusty Pink",
            sku="DR-SSD-DP",
            quantity_in_stock=10,
        )

    def test_create_order_enqueues_notification(self, variant: ProductVariant):
        payload = CreateOrderPayload(
            full_name="Ayesha Khan",
            phone_number="03001234567",
            shipping_address="12 Mall Road",
            city="Lahore",
            items=[OrderLineInput(variant_id=variant.id, quantity=1)],
        )

        with patch(
            "services.notification_service.NotificationService.push_order_created"
        ) as push_mock:
            with patch.object(transaction, "on_commit", side_effect=lambda func: func()):
                order = OrderService.create_order(payload=payload)

        push_mock.assert_called_once()
        notified_order = push_mock.call_args.args[0]
        assert notified_order.tracking_number == order.tracking_number
