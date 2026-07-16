from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from django.db import transaction
from django.db.models import F

from apps.catalog.models import ProductVariant
from config.exceptions import InsufficientStockError


@dataclass(frozen=True)
class StockAdjustment:
    variant_id: UUID
    quantity: int


class InventoryService:
    """Race-safe stock mutations with row-level locking."""

    @staticmethod
    @transaction.atomic
    def decrement_stock(*, variant_id: UUID, quantity: int) -> ProductVariant:
        if quantity < 1:
            raise ValueError("Quantity must be at least 1.")

        variant = (
            ProductVariant.objects.select_for_update()
            .select_related("product")
            .get(id=variant_id, is_active=True)
        )

        if variant.quantity_in_stock < quantity:
            raise InsufficientStockError(
                detail=(
                    f"Insufficient stock for SKU {variant.sku}. "
                    f"Requested {quantity}, available {variant.quantity_in_stock}."
                )
            )

        ProductVariant.objects.filter(pk=variant.pk).update(
            quantity_in_stock=F("quantity_in_stock") - quantity,
        )
        variant.refresh_from_db(fields=["quantity_in_stock", "updated_at"])
        return variant

    @staticmethod
    @transaction.atomic
    def decrement_bulk(adjustments: Sequence[StockAdjustment]) -> list[ProductVariant]:
        updated: list[ProductVariant] = []
        for adjustment in adjustments:
            updated.append(
                InventoryService.decrement_stock(
                    variant_id=adjustment.variant_id,
                    quantity=adjustment.quantity,
                )
            )
        return updated

    @staticmethod
    @transaction.atomic
    def restore_stock(*, variant_id: UUID, quantity: int) -> ProductVariant:
        """Return stock on cancellation — mirrors decrement with row lock."""
        if quantity < 1:
            raise ValueError("Quantity must be at least 1.")

        variant = ProductVariant.objects.select_for_update().get(
            id=variant_id,
            is_active=True,
        )
        ProductVariant.objects.filter(pk=variant.pk).update(
            quantity_in_stock=F("quantity_in_stock") + quantity,
        )
        variant.refresh_from_db(fields=["quantity_in_stock", "updated_at"])
        return variant

    @staticmethod
    def get_available_quantity(*, variant_id: UUID) -> int:
        return (
            ProductVariant.objects.filter(id=variant_id, is_active=True)
            .values_list("quantity_in_stock", flat=True)
            .first()
            or 0
        )

    @staticmethod
    def is_low_stock(variant: ProductVariant) -> bool:
        return variant.quantity_in_stock <= variant.safety_threshold

    @staticmethod
    @transaction.atomic
    def set_stock(
        *,
        variant_id: UUID,
        quantity_in_stock: int | None = None,
        safety_threshold: int | None = None,
    ) -> ProductVariant:
        variant = (
            ProductVariant.all_objects.select_for_update()
            .select_related("product")
            .get(id=variant_id)
        )

        update_fields = ["updated_at"]
        if quantity_in_stock is not None:
            variant.quantity_in_stock = quantity_in_stock
            update_fields.append("quantity_in_stock")
        if safety_threshold is not None:
            variant.safety_threshold = safety_threshold
            update_fields.append("safety_threshold")

        if len(update_fields) == 1:
            raise ValueError("No stock fields provided.")

        variant.save(update_fields=update_fields)
        return variant

    @staticmethod
    def resolve_line_total(*, variant: ProductVariant, quantity: int) -> Decimal:
        return variant.effective_price * quantity
