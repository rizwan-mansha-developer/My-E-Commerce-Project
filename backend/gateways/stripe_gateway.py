from __future__ import annotations

import os
import uuid
from decimal import Decimal

from gateways.base import InitiatePaymentResult, WebhookVerificationResult


class StripeGateway:
    gateway_name = "CARD"

    def __init__(self) -> None:
        self.secret_key = os.environ.get("STRIPE_SECRET_KEY", "")
        self.success_url = os.environ.get(
            "STRIPE_SUCCESS_URL",
            "http://localhost:3000/checkout/success",
        )
        self.sandbox = os.environ.get("PAYMENT_SANDBOX", "true").lower() in (
            "true",
            "1",
            "yes",
        )

    def initiate_payment(
        self,
        *,
        order_id: str,
        tracking_number: str,
        amount: Decimal,
        phone_number: str,
        idempotency_key: str,
    ) -> InitiatePaymentResult:
        external_reference = f"ST-{tracking_number}-{uuid.uuid4().hex[:8]}"

        if self.sandbox or not self.secret_key:
            site_url = os.environ.get(
                "FRONTEND_URL", "http://localhost:3000"
            )
            return InitiatePaymentResult(
                redirect_url=(
                    f"{site_url}/checkout/success"
                    f"?tracking={tracking_number}"
                    f"&gateway=stripe&sandbox=1"
                ),
                external_reference=external_reference,
            )

        try:
            import stripe  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "Stripe SDK not installed. Add stripe to requirements for card payments."
            ) from exc

        stripe.api_key = self.secret_key
        session = stripe.checkout.Session.create(
            mode="payment",
            success_url=f"{self.success_url}?tracking={tracking_number}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{self.success_url.replace('/success', '/cancel')}?tracking={tracking_number}",
            line_items=[
                {
                    "price_data": {
                        "currency": "pkr",
                        "product_data": {"name": f"Darling {tracking_number}"},
                        "unit_amount": int(amount * 100),
                    },
                    "quantity": 1,
                }
            ],
            metadata={"order_id": order_id, "tracking_number": tracking_number},
        )
        return InitiatePaymentResult(
            redirect_url=session.url or self.success_url,
            external_reference=session.id,
        )

    def verify_webhook(self, payload: dict[str, object]) -> WebhookVerificationResult:
        event_id = str(payload.get("id", uuid.uuid4().hex))
        event_type = str(payload.get("type", ""))
        data = payload.get("data", {})
        object_data = data.get("object", {}) if isinstance(data, dict) else {}
        metadata = (
            object_data.get("metadata", {})
            if isinstance(object_data, dict)
            else {}
        )
        tracking_number = str(
            metadata.get("tracking_number", payload.get("tracking_number", ""))
        )

        return WebhookVerificationResult(
            event_id=event_id,
            order_reference=tracking_number,
            success=event_type == "checkout.session.completed",
            external_reference=str(
                object_data.get("id", "") if isinstance(object_data, dict) else ""
            ),
        )
