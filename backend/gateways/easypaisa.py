from __future__ import annotations

import os
import uuid
from decimal import Decimal
from urllib.parse import urlencode

from gateways.base import InitiatePaymentResult, WebhookVerificationResult


class EasyPaisaGateway:
    gateway_name = "EASYPAISA"

    def __init__(self) -> None:
        self.store_id = os.environ.get("EASYPAISA_STORE_ID", "")
        self.hash_key = os.environ.get("EASYPAISA_HASH_KEY", "")
        self.return_url = os.environ.get(
            "EASYPAISA_RETURN_URL",
            "http://localhost:3000/checkout/success",
        )
        self.checkout_url = os.environ.get(
            "EASYPAISA_CHECKOUT_URL",
            "https://easypay.easypaisa.com.pk/easypay/Index.jsf",
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
        external_reference = f"EP-{tracking_number}-{uuid.uuid4().hex[:8]}"

        if self.sandbox or not self.store_id:
            site_url = os.environ.get(
                "FRONTEND_URL", "http://localhost:3000"
            )
            return InitiatePaymentResult(
                redirect_url=(
                    f"{site_url}/checkout/success"
                    f"?tracking={tracking_number}"
                    f"&gateway=easypaisa&sandbox=1"
                ),
                external_reference=external_reference,
            )

        params = {
            "storeId": self.store_id,
            "amount": str(amount),
            "orderRefNum": external_reference,
            "postBackURL": self.return_url,
            "mobileNum": phone_number,
            "emailAddr": "",
        }
        redirect_url = f"{self.checkout_url}?{urlencode(params)}"
        return InitiatePaymentResult(
            redirect_url=redirect_url,
            external_reference=external_reference,
        )

    def verify_webhook(self, payload: dict[str, object]) -> WebhookVerificationResult:
        status = str(payload.get("status", "")).upper()
        order_ref = str(payload.get("orderRefNum", payload.get("orderId", "")))
        event_id = str(payload.get("transactionId", order_ref or uuid.uuid4().hex))

        tracking_number = str(payload.get("pp_BillReference", ""))
        if not tracking_number and order_ref.startswith("EP-"):
            parts = order_ref.split("-")
            if len(parts) >= 3:
                tracking_number = "-".join(parts[1:-1])

        return WebhookVerificationResult(
            event_id=event_id,
            order_reference=tracking_number,
            success=status in {"PAID", "SUCCESS", "COMPLETED"},
            external_reference=order_ref,
        )
