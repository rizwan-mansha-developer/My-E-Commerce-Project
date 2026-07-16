from __future__ import annotations

from gateways.base import PaymentGateway
from gateways.easypaisa import EasyPaisaGateway
from gateways.jazzcash import JazzCashGateway
from gateways.stripe_gateway import StripeGateway

_GATEWAYS: dict[str, PaymentGateway] = {
    "JAZZCASH": JazzCashGateway(),
    "EASYPAISA": EasyPaisaGateway(),
    "CARD": StripeGateway(),
}


def get_gateway(gateway_name: str) -> PaymentGateway:
    gateway = _GATEWAYS.get(gateway_name.upper())
    if gateway is None:
        raise ValueError(f"Unsupported payment gateway: {gateway_name}")
    return gateway


def is_online_payment_method(payment_method: str) -> bool:
    return payment_method.upper() in _GATEWAYS
