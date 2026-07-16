from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from decimal import Decimal
from urllib.parse import urlencode

from gateways.base import InitiatePaymentResult, WebhookVerificationResult


class JazzCashGateway:
    gateway_name = "JAZZCASH"

    def __init__(self) -> None:
        self.merchant_id = os.environ.get("JAZZCASH_MERCHANT_ID", "")
        self.password = os.environ.get("JAZZCASH_PASSWORD", "")
        self.integrity_salt = os.environ.get("JAZZCASH_INTEGRITY_SALT", "")
        self.return_url = os.environ.get(
            "JAZZCASH_RETURN_URL",
            "http://localhost:3000/checkout/success",
        )
        self.checkout_url = os.environ.get(
            "JAZZCASH_CHECKOUT_URL",
            "https://sandbox.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform",
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
        external_reference = f"JC-{tracking_number}-{uuid.uuid4().hex[:8]}"

        if self.sandbox or not self.merchant_id:
            site_url = os.environ.get(
                "FRONTEND_URL", "http://localhost:3000"
            )
            return InitiatePaymentResult(
                redirect_url=(
                    f"{site_url}/checkout/success"
                    f"?tracking={tracking_number}"
                    f"&gateway=jazzcash&sandbox=1"
                ),
                external_reference=external_reference,
            )

        amount_paisa = str(int(amount * 100))
        fields = {
            "pp_Amount": amount_paisa,
            "pp_BillReference": tracking_number,
            "pp_Description": f"Darling order {tracking_number}",
            "pp_MerchantID": self.merchant_id,
            "pp_Password": self.password,
            "pp_ReturnURL": self.return_url,
            "pp_TxnRefNo": external_reference,
            "pp_TxnDateTime": "",
            "pp_TxnExpiryDateTime": "",
            "pp_Version": "1.1",
            "ppmpf_1": phone_number,
        }
        secure_hash = self._compute_hash(fields)
        fields["pp_SecureHash"] = secure_hash
        redirect_url = f"{self.checkout_url}?{urlencode(fields)}"
        return InitiatePaymentResult(
            redirect_url=redirect_url,
            external_reference=external_reference,
        )

    def verify_webhook(self, payload: dict[str, object]) -> WebhookVerificationResult:
        response_code = str(payload.get("pp_ResponseCode", ""))
        tracking_number = str(payload.get("pp_BillReference", ""))
        txn_ref = str(payload.get("pp_TxnRefNo", ""))
        event_id = txn_ref or str(payload.get("pp_TxnDateTime", uuid.uuid4().hex))

        return WebhookVerificationResult(
            event_id=event_id,
            order_reference=tracking_number,
            success=response_code in {"000", "121", "200"},
            external_reference=txn_ref,
        )

    def _compute_hash(self, fields: dict[str, str]) -> str:
        sorted_values = "".join(
            str(fields[key])
            for key in sorted(fields.keys())
            if key.startswith("pp_") and key != "pp_SecureHash"
        )
        message = f"{self.integrity_salt}&{sorted_values}"
        return hmac.new(
            self.integrity_salt.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
