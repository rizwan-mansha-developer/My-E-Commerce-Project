from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from django.test import Client

from apps.catalog.models import Product, ProductVariant, WishlistItem
from services.wishlist_service import WishlistService


@pytest.mark.django_db
class TestWishlistService:
    @pytest.fixture
    def product(self) -> Product:
        return Product.objects.create(
            title="Silk Slip Dress",
            slug="silk-slip-dress",
            base_price=Decimal("12500.00"),
        )

    def test_guest_toggle_add_and_remove(self, product: Product):
        client = Client()
        session = client.session
        session.save()

        request = client.request().wsgi_request
        request.session = session
        owner = WishlistService.resolve_owner(request)

        add_result = WishlistService.toggle_favorite(
            owner=owner,
            product_id=product.id,
        )
        assert add_result.favorited is True
        assert add_result.total_count == 1
        assert WishlistItem.objects.filter(session_key=session.session_key).count() == 1

        remove_result = WishlistService.toggle_favorite(
            owner=owner,
            product_id=product.id,
        )
        assert remove_result.favorited is False
        assert remove_result.total_count == 0

    def test_favorited_product_ids(self, product: Product):
        client = Client()
        session = client.session
        session.save()

        request = client.request().wsgi_request
        request.session = session
        owner = WishlistService.resolve_owner(request)

        WishlistService.toggle_favorite(owner=owner, product_id=product.id)
        ids = WishlistService.favorited_product_ids(owner=owner)
        assert ids == [product.id]


@pytest.mark.django_db
class TestWishlistApi:
    @pytest.fixture
    def product(self) -> Product:
        return Product.objects.create(
            title="Silk Slip Dress",
            slug="silk-slip-dress",
            base_price=Decimal("12500.00"),
        )

    def test_toggle_without_login(self, product: Product):
        client = Client()
        response = client.post(
            "/api/v1/catalog/wishlist/toggle/",
            data={"product_id": str(product.id)},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["favorited"] is True
        assert response.json()["total_count"] == 1

        list_response = client.get("/api/v1/catalog/wishlist/")
        assert list_response.status_code == 200
        assert str(product.id) in {
            str(product_id) for product_id in list_response.json()["product_ids"]
        }


@pytest.mark.django_db
class TestExpressCheckoutApi:
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
            quantity_in_stock=5,
        )

    def test_guest_express_checkout(self, variant: ProductVariant):
        client = Client()
        response = client.post(
            "/api/v1/orders/express/",
            data={
                "variant_id": str(variant.id),
                "full_name": "Ayesha Khan",
                "phone_number": "03001234567",
                "shipping_address": "12 Mall Road",
                "city": "Lahore",
                "cod_confirmed": True,
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["tracking_number"].startswith("DRLNG-")
        assert body["payment_method"] == "COD"

    def test_rejects_unchecked_cod(self, variant: ProductVariant):
        client = Client()
        response = client.post(
            "/api/v1/orders/express/",
            data={
                "variant_id": str(variant.id),
                "full_name": "Ayesha Khan",
                "phone_number": "03001234567",
                "shipping_address": "12 Mall Road",
                "city": "Lahore",
                "cod_confirmed": False,
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_rejects_unknown_variant(self):
        client = Client()
        response = client.post(
            "/api/v1/orders/express/",
            data={
                "variant_id": str(uuid4()),
                "full_name": "Ayesha Khan",
                "phone_number": "03001234567",
                "shipping_address": "12 Mall Road",
                "city": "Lahore",
                "cod_confirmed": True,
            },
            content_type="application/json",
        )
        assert response.status_code == 400
