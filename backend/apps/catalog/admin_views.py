from __future__ import annotations

from django.db import models
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from apps.accounts.permissions import IsSuperUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.admin_serializers import (
    ProductAdminSerializer,
    ProductAdminWriteSerializer,
)
from apps.catalog.inventory_serializers import (
    InventoryAdminSerializer,
    InventoryUpdateSerializer,
)
from apps.catalog.models import Product, ProductVariant
from services.inventory_service import InventoryService


@extend_schema_view(
    get=extend_schema(tags=["Admin"], summary="List all products (staff)"),
    post=extend_schema(tags=["Admin"], summary="Create product (staff)"),
)
class ProductAdminListView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request: Request) -> Response:
        products = (
            Product.all_objects.select_related("category")
            .prefetch_related("variants", "gallery_images")
            .annotate(
                total_stock=models.Sum(
                    "variants__quantity_in_stock",
                    filter=models.Q(variants__is_active=True),
                )
            )
            .order_by("-created_at")
        )

        status_filter = request.query_params.get("status")
        if status_filter == "active":
            products = products.filter(is_active=True)
        elif status_filter == "inactive":
            products = products.filter(is_active=False)
        elif status_filter == "out_of_stock":
            products = products.filter(is_active=True).filter(
                models.Q(total_stock=0) | models.Q(total_stock__isnull=True)
            )
        elif status_filter == "low_stock":
            low_stock_variants = ProductVariant.objects.filter(
                product_id=models.OuterRef("pk"),
                is_active=True,
                quantity_in_stock__gt=0,
                quantity_in_stock__lte=models.F("safety_threshold"),
            )
            products = products.filter(is_active=True).filter(
                models.Exists(low_stock_variants)
            )

        q = (request.query_params.get("q") or "").strip()
        if q:
            products = products.filter(
                models.Q(title__icontains=q)
                | models.Q(slug__icontains=q)
                | models.Q(variants__sku__icontains=q)
            ).distinct()

        serializer = ProductAdminSerializer(products, many=True)
        return Response({"results": serializer.data, "count": products.count()})

    def post(self, request: Request) -> Response:
        serializer = ProductAdminWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(
            ProductAdminSerializer(product).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(tags=["Admin"], summary="Get product by slug (staff)"),
    put=extend_schema(tags=["Admin"], summary="Update product by slug (staff)"),
    patch=extend_schema(tags=["Admin"], summary="Partial update product by slug"),
    delete=extend_schema(tags=["Admin"], summary="Soft-delete product by slug"),
)
class ProductAdminDetailView(APIView):
    """Admin product detail keyed by slug — same shape as public /products/{slug}/."""

    permission_classes = [IsSuperUser]

    def _get_product(self, slug: str) -> Product | None:
        return (
            Product.all_objects.filter(slug=slug)
            .select_related("category")
            .prefetch_related("variants", "gallery_images")
            .first()
        )

    def get(self, request: Request, slug: str) -> Response:
        product = self._get_product(slug)
        if product is None:
            return Response(
                {"detail": "Product not found.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ProductAdminSerializer(product).data)

    def put(self, request: Request, slug: str) -> Response:
        return self._update(request, slug, partial=False)

    def patch(self, request: Request, slug: str) -> Response:
        return self._update(request, slug, partial=True)

    def delete(self, request: Request, slug: str) -> Response:
        product = self._get_product(slug)
        if product is None:
            return Response(
                {"detail": "Product not found.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        product.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _update(self, request: Request, slug: str, *, partial: bool) -> Response:
        product = self._get_product(slug)
        if product is None:
            return Response(
                {"detail": "Product not found.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ProductAdminWriteSerializer(
            product, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(ProductAdminSerializer(product).data)


@extend_schema_view(
    get=extend_schema(tags=["Admin"], summary="List inventory / variants (staff)"),
)
class InventoryAdminListView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request: Request) -> Response:
        low_stock_only = request.query_params.get("low_stock") == "true"
        variants = (
            ProductVariant.all_objects.select_related("product")
            .order_by("product__title", "color")
        )

        if low_stock_only:
            variants = variants.filter(
                quantity_in_stock__lte=models.F("safety_threshold"),
            )

        serializer = InventoryAdminSerializer(variants, many=True)
        return Response({"results": serializer.data, "count": variants.count()})


@extend_schema_view(
    patch=extend_schema(tags=["Admin"], summary="Update variant stock (staff)"),
)
class InventoryAdminDetailView(APIView):
    permission_classes = [IsSuperUser]

    def patch(self, request: Request, variant_id: str) -> Response:
        variant = (
            ProductVariant.all_objects.filter(id=variant_id)
            .select_related("product")
            .first()
        )
        if variant is None:
            return Response(
                {"detail": "Variant not found.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = InventoryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            variant = InventoryService.set_stock(
                variant_id=variant.id,
                quantity_in_stock=serializer.validated_data.get("quantity_in_stock"),
                safety_threshold=serializer.validated_data.get("safety_threshold"),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc), "code": "invalid_request"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        variant = ProductVariant.all_objects.select_related("product").get(id=variant.id)
        return Response(InventoryAdminSerializer(variant).data)
