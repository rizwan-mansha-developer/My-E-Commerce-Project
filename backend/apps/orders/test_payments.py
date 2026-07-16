from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db import transaction

from apps.catalog.models import Product, ProductVariant
from apps.orders.models import OrderStatus, PaymentMethod, PaymentWebhookEvent
from services.order_service import ExpressCheckoutInput, OrderService
from services.payment_service import PaymentService


@pytest.mark.django_db
class TestOnlinePayments:
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

    def test_jazzcash_checkout_returns_redirect(self, variant: ProductVariant):
        order = OrderService.create_express_order(
            payload=ExpressCheckoutInput(
                variant_id=variant.id,
                full_name="Ayesha Khan",
                phone_number="03001234567",
                shipping_address="12 Mall Road",
                city="Lahore",
                payment_method=PaymentMethod.JAZZCASH,
            )
        )
        assert order.status == OrderStatus.PENDING_PAYMENT

        payment = PaymentService.initiate_for_order(order=order)
        assert payment.redirect_url
        assert "sandbox=1" in payment.redirect_url or "jazzcash" in payment.redirect_url

    def test_webhook_idempotency(self, variant: ProductVariant):
        order = OrderService.create_express_order(
            payload=ExpressCheckoutInput(
                variant_id=variant.id,
                full_name="Ayesha Khan",
                phone_number="03001234567",
                shipping_address="12 Mall Road",
                city="Lahore",
                payment_method=PaymentMethod.JAZZCASH,
            )
        )

        payload = {
            "pp_ResponseCode": "000",
            "pp_BillReference": order.tracking_number,
            "pp_TxnRefNo": "txn-12345",
        }

        with patch.object(transaction, "on_commit", side_effect=lambda func: func()):
            ok1, _ = PaymentService.handle_webhook(
                gateway_name=PaymentMethod.JAZZCASH,
                payload=payload,
            )
            ok2, msg2 = PaymentService.handle_webhook(
                gateway_name=PaymentMethod.JAZZCASH,
                payload=payload,
            )

        assert ok1 is True
        assert msg2 == "already_processed"
        assert PaymentWebhookEvent.objects.count() == 1

        order.refresh_from_db()
        assert order.status == OrderStatus.CONFIRMED
