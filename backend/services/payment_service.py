from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from apps.orders.models import (
    Order,
    OrderStatus,
    PaymentMethod,
    PaymentTransaction,
    PaymentTransactionStatus,
    PaymentWebhookEvent,
)
from gateways.registry import get_gateway, is_online_payment_method
from services.notification_service import NotificationService
from services.order_service import OrderService


@dataclass(frozen=True)
class InitiatePaymentOutput:
    payment_id: uuid.UUID
    redirect_url: str
    external_reference: str


class PaymentService:
    """Online payment initiation and idempotent webhook processing."""

    @staticmethod
    @transaction.atomic
    def initiate_for_order(*, order: Order) -> InitiatePaymentOutput:
        if not is_online_payment_method(order.payment_method):
            raise ValueError("Order does not use an online payment method.")

        idempotency_key = f"pay-{order.id}-{uuid.uuid4().hex[:12]}"
        gateway = get_gateway(order.payment_method)

        result = gateway.initiate_payment(
            order_id=str(order.id),
            tracking_number=order.tracking_number,
            amount=order.total_amount,
            phone_number=order.phone_number,
            idempotency_key=idempotency_key,
        )

        payment = PaymentTransaction.objects.create(
            order=order,
            gateway=order.payment_method,
            idempotency_key=idempotency_key,
            external_reference=result.external_reference,
            amount=order.total_amount,
            status=PaymentTransactionStatus.PENDING,
            redirect_url=result.redirect_url,
        )

        return InitiatePaymentOutput(
            payment_id=payment.id,
            redirect_url=result.redirect_url,
            external_reference=result.external_reference,
        )

    @staticmethod
    @transaction.atomic
    def handle_webhook(
        *,
        gateway_name: str,
        payload: dict[str, object],
    ) -> tuple[bool, str]:
        gateway = get_gateway(gateway_name)
        verification = gateway.verify_webhook(payload)
        idempotency_key = f"{gateway_name}:{verification.event_id}"

        if PaymentWebhookEvent.objects.filter(idempotency_key=idempotency_key).exists():
            return True, "already_processed"

        PaymentWebhookEvent.objects.create(
            idempotency_key=idempotency_key,
            gateway=gateway_name,
            payload=payload,
        )

        order = Order.objects.filter(
            tracking_number=verification.order_reference
        ).first()

        if order is None and verification.external_reference:
            payment_match = (
                PaymentTransaction.objects.filter(
                    external_reference=verification.external_reference
                )
                .select_related("order")
                .first()
            )
            if payment_match:
                order = payment_match.order

        if order is None:
            return False, "order_not_found"

        payment = (
            PaymentTransaction.objects.filter(order=order)
            .order_by("-created_at")
            .first()
        )

        if verification.success:
            if payment:
                payment.status = PaymentTransactionStatus.COMPLETED
                payment.external_reference = (
                    verification.external_reference or payment.external_reference
                )
                payment.save(update_fields=["status", "external_reference", "updated_at"])

            if order.status == OrderStatus.PENDING_PAYMENT:
                OrderService.transition_status(
                    order_id=order.id,
                    new_status=OrderStatus.CONFIRMED,
                )
                transaction.on_commit(
                    lambda order_id=order.id: NotificationService.push_order_created(
                        Order.objects.prefetch_related("items").get(id=order_id)
                    )
                )
            return True, "payment_confirmed"

        if payment:
            payment.status = PaymentTransactionStatus.FAILED
            payment.save(update_fields=["status", "updated_at"])

        return False, "payment_failed"

    @staticmethod
    def simulate_sandbox_confirmation(*, tracking_number: str) -> Order | None:
        """Dev helper: confirm a sandbox online payment from the success page."""
        order = Order.objects.filter(
            tracking_number=tracking_number,
            status=OrderStatus.PENDING_PAYMENT,
            payment_method__in=[
                PaymentMethod.JAZZCASH,
                PaymentMethod.EASYPAISA,
                PaymentMethod.CARD,
            ],
        ).first()

        if order is None:
            return None

        payload = {
            "pp_ResponseCode": "000",
            "pp_BillReference": tracking_number,
            "pp_TxnRefNo": f"sandbox-{uuid.uuid4().hex[:8]}",
            "status": "PAID",
            "type": "checkout.session.completed",
            "tracking_number": tracking_number,
        }
        PaymentService.handle_webhook(gateway_name=order.payment_method, payload=payload)
        order.refresh_from_db()
        return order
