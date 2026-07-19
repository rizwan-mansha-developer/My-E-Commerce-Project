from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from django.db import transaction

from apps.catalog.models import ProductVariant
from apps.orders.models import Order, OrderItem, OrderStatus, PaymentMethod
from services.inventory_service import InventoryService, StockAdjustment
from services.notification_service import NotificationService
from services.promotion_service import PromotionService
from services.tracking import TrackingNumberGenerator


@dataclass(frozen=True)
class OrderLineInput:
    variant_id: UUID
    quantity: int


@dataclass(frozen=True)
class CreateOrderPayload:
    full_name: str
    phone_number: str
    shipping_address: str
    city: str
    items: Sequence[OrderLineInput]
    payment_method: str = PaymentMethod.COD
    user: object | None = None
    discount_code: str | None = None


@dataclass(frozen=True)
class ExpressCheckoutInput:
    """Minimal single-screen checkout — COD or online wallet/card."""

    variant_id: UUID
    full_name: str
    phone_number: str
    shipping_address: str
    city: str
    quantity: int = 1
    payment_method: str = PaymentMethod.COD
    user: object | None = None
    discount_code: str | None = None


class OrderService:
    """Order creation and status lifecycle mutations."""

    ALLOWED_TRANSITIONS: dict[str, set[str]] = {
        OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
        OrderStatus.PENDING_PAYMENT: {
            OrderStatus.CONFIRMED,
            OrderStatus.CANCELLED,
        },
        OrderStatus.CONFIRMED: {OrderStatus.DISPATCHED, OrderStatus.CANCELLED},
        OrderStatus.DISPATCHED: {OrderStatus.DELIVERED, OrderStatus.CANCELLED},
        OrderStatus.DELIVERED: set(),
        OrderStatus.CANCELLED: set(),
    }

    @staticmethod
    @transaction.atomic
    def create_order(*, payload: CreateOrderPayload) -> Order:
        if not payload.items:
            raise ValueError("At least one order line is required.")

        variants = OrderService.load_variants(payload.items)
        from services.promotion_service import QuoteLine

        applied = PromotionService.quote(
            items=[
                QuoteLine(variant_id=line.variant_id, quantity=line.quantity)
                for line in payload.items
            ],
            variants=variants,
            discount_code=payload.discount_code,
            user=payload.user,
            phone=payload.phone_number,
        )
        PromotionService.consume_code(applied.discount_code)

        initial_status = (
            OrderStatus.PENDING_PAYMENT
            if payload.payment_method != PaymentMethod.COD
            else OrderStatus.PENDING
        )

        order = Order.objects.create(
            tracking_number=TrackingNumberGenerator.generate(),
            full_name=payload.full_name.strip(),
            phone_number=payload.phone_number.strip(),
            shipping_address=payload.shipping_address.strip(),
            city=payload.city.strip(),
            subtotal_amount=applied.subtotal,
            discount_amount=applied.total_discount,
            discount_code=applied.discount_code_str,
            campaign=applied.campaign,
            referrer_user=applied.referrer_user,
            total_amount=applied.total_amount,
            payment_method=payload.payment_method,
            status=initial_status,
            user=payload.user if getattr(payload.user, "is_authenticated", False) else None,
        )

        line_items: list[OrderItem] = []
        stock_adjustments: list[StockAdjustment] = []

        for line in payload.items:
            variant = variants[line.variant_id]
            unit_price = variant.effective_price
            line_total = unit_price * line.quantity

            line_items.append(
                OrderItem(
                    order=order,
                    variant=variant,
                    product_title=variant.product.title,
                    variant_color=variant.color,
                    sku=variant.sku,
                    unit_price=unit_price,
                    quantity=line.quantity,
                    line_total=line_total,
                )
            )
            stock_adjustments.append(
                StockAdjustment(variant_id=variant.id, quantity=line.quantity)
            )

        OrderItem.objects.bulk_create(line_items)
        InventoryService.decrement_bulk(stock_adjustments)
        # Referral rewards are issued when the order is Confirmed/Delivered
        # (see transition_status) so cancelled pending orders never grant them.

        if payload.payment_method == PaymentMethod.COD:
            transaction.on_commit(
                lambda order_id=order.id: NotificationService.push_order_created(
                    Order.objects.prefetch_related("items").get(id=order_id)
                )
            )

        return order

    @staticmethod
    @transaction.atomic
    def create_express_order(*, payload: ExpressCheckoutInput) -> Order:
        """One-tap guest checkout — delegates to create_order with a single line."""
        return OrderService.create_order(
            payload=CreateOrderPayload(
                full_name=payload.full_name,
                phone_number=payload.phone_number,
                shipping_address=payload.shipping_address,
                city=payload.city,
                items=[
                    OrderLineInput(
                        variant_id=payload.variant_id,
                        quantity=payload.quantity,
                    )
                ],
                payment_method=payload.payment_method,
                user=payload.user,
                discount_code=payload.discount_code,
            )
        )

    @staticmethod
    @transaction.atomic
    def transition_status(*, order_id: UUID, new_status: str) -> Order:
        order = Order.objects.select_for_update().get(id=order_id)
        allowed = OrderService.ALLOWED_TRANSITIONS.get(order.status, set())

        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition order {order.tracking_number} "
                f"from {order.status} to {new_status}."
            )

        if (
            new_status == OrderStatus.CANCELLED
            and order.status != OrderStatus.CANCELLED
        ):
            OrderService._restore_order_stock(order)

        order.status = new_status
        order.save(update_fields=["status", "updated_at"])

        if new_status in {OrderStatus.CONFIRMED, OrderStatus.DELIVERED}:
            PromotionService.issue_loyalty_for_order(order)
            if order.referrer_user_id:
                PromotionService.issue_referral_reward(
                    referrer=order.referrer_user,
                    source_order=order,
                )

        return order

    @staticmethod
    def load_variants(
        items: Sequence[OrderLineInput] | Sequence[object],
    ) -> dict[UUID, ProductVariant]:
        variant_ids = [item.variant_id for item in items]  # type: ignore[attr-defined]
        variants = {
            variant.id: variant
            for variant in ProductVariant.objects.select_related("product").filter(
                id__in=variant_ids,
                is_active=True,
                product__is_active=True,
            )
        }

        missing = set(variant_ids) - set(variants.keys())
        if missing:
            raise ValueError(f"Unknown or inactive variant(s): {missing}")

        return variants

    @staticmethod
    def _calculate_total(
        items: Sequence[OrderLineInput],
        variants: dict[UUID, ProductVariant],
    ) -> Decimal:
        total = Decimal("0.00")
        for line in items:
            variant = variants[line.variant_id]
            total += variant.effective_price * line.quantity
        return total

    @staticmethod
    def _restore_order_stock(order: Order) -> None:
        for item in order.items.select_related("variant"):
            InventoryService.restore_stock(
                variant_id=item.variant_id,
                quantity=item.quantity,
            )
