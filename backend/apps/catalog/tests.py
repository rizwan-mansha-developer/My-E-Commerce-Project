from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.catalog.models import Product, ProductVariant
from apps.catalog.validators import validate_pakistan_mobile
from apps.orders.models import OrderStatus
from services.inventory_service import InventoryService
from services.order_service import CreateOrderPayload, OrderLineInput, OrderService
from services.tracking import TrackingNumberGenerator


@pytest.fixture
def product(db) -> Product:
    return Product.objects.create(
        title="Silk Slip Dress",
        slug="silk-slip-dress",
        description="Hand-finished seams.",
        base_price=Decimal("12500.00"),
        video_url="https://cdn.darling.pk/videos/silk-slip.mp4",
    )


@pytest.fixture
def variant(db, product: Product) -> ProductVariant:
    return ProductVariant.objects.create(
        product=product,
        color="Dusty Pink",
        sku="DR-SSD-DP",
        quantity_in_stock=10,
        safety_threshold=3,
    )


@pytest.mark.django_db
class TestCatalogModels:
    def test_effective_price_uses_override(
        self, product: Product, variant: ProductVariant
    ):
        variant.price_override = Decimal("11999.00")
        variant.save()
        assert variant.effective_price == Decimal("11999.00")

    def test_effective_price_falls_back_to_base(
        self, product: Product, variant: ProductVariant
    ):
        assert variant.effective_price == product.base_price

    def test_low_stock_flag(self, variant: ProductVariant):
        variant.quantity_in_stock = 3
        assert variant.is_low_stock is True

    def test_sale_fields(self, product: Product):
        assert product.is_on_sale is False
        assert product.discount_percent == 0
        product.compare_at_price = Decimal("4999.00")
        product.base_price = Decimal("1999.00")
        product.save()
        product.refresh_from_db()
        assert product.is_on_sale is True
        assert product.discount_percent == 60


@pytest.mark.django_db
class TestPakistanMobileValidator:
    def test_valid_number(self):
        validate_pakistan_mobile("03001234567")

    def test_invalid_number(self):
        with pytest.raises(ValidationError):
            validate_pakistan_mobile("3001234567")


@pytest.mark.django_db
class TestTrackingNumberGenerator:
    def test_format(self):
        tracking = TrackingNumberGenerator.generate()
        assert tracking.startswith("DRLNG-")
        suffix = tracking.split("-")[-1]
        assert len(suffix) == 4
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for c in suffix)


@pytest.mark.django_db
class TestInventoryService:
    def test_decrement_reduces_stock(self, variant: ProductVariant):
        InventoryService.decrement_stock(variant_id=variant.id, quantity=2)
        variant.refresh_from_db()
        assert variant.quantity_in_stock == 8

    def test_decrement_raises_on_oversell(self, variant: ProductVariant):
        from config.exceptions import InsufficientStockError

        with pytest.raises(InsufficientStockError):
            InventoryService.decrement_stock(variant_id=variant.id, quantity=100)


@pytest.mark.django_db
class TestOrderService:
    def test_create_order_deducts_stock(self, variant: ProductVariant):
        payload = CreateOrderPayload(
            full_name="Ayesha Khan",
            phone_number="03001234567",
            shipping_address="12 Mall Road, Gulberg",
            city="Lahore",
            items=[OrderLineInput(variant_id=variant.id, quantity=2)],
        )
        order = OrderService.create_order(payload=payload)

        variant.refresh_from_db()
        assert order.tracking_number.startswith("DRLNG-")
        assert order.status == OrderStatus.PENDING
        assert order.total_amount == variant.effective_price * 2
        assert variant.quantity_in_stock == 8
        assert order.items.count() == 1

    def test_cancel_restores_stock(self, variant: ProductVariant):
        payload = CreateOrderPayload(
            full_name="Ayesha Khan",
            phone_number="03001234567",
            shipping_address="12 Mall Road, Gulberg",
            city="Lahore",
            items=[OrderLineInput(variant_id=variant.id, quantity=3)],
        )
        order = OrderService.create_order(payload=payload)
        OrderService.transition_status(
            order_id=order.id,
            new_status=OrderStatus.CANCELLED,
        )

        variant.refresh_from_db()
        assert variant.quantity_in_stock == 10
