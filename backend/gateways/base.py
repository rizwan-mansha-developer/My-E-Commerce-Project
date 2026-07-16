from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class InitiatePaymentResult:
    redirect_url: str
    external_reference: str


@dataclass(frozen=True)
class WebhookVerificationResult:
    event_id: str
    order_reference: str
    success: bool
    external_reference: str = ""


class PaymentGateway(Protocol):
    gateway_name: str

    def initiate_payment(
        self,
        *,
        order_id: str,
        tracking_number: str,
        amount: Decimal,
        phone_number: str,
        idempotency_key: str,
    ) -> InitiatePaymentResult: ...

    def verify_webhook(self, payload: dict[str, object]) -> WebhookVerificationResult: ...
