from __future__ import annotations

import secrets
import string
from datetime import datetime

from django.apps import apps


class TrackingNumberGenerator:
    """Generates unique customer-facing IDs: DRLNG-{YEAR}-{A-Z0-9}{4}."""

    PREFIX = "DRLNG"
    SUFFIX_ALPHABET = string.ascii_uppercase + string.digits
    SUFFIX_LENGTH = 4
    MAX_ATTEMPTS = 50

    @classmethod
    def generate(cls) -> str:
        year = datetime.now().year
        order_model = apps.get_model("orders", "Order")

        for _ in range(cls.MAX_ATTEMPTS):
            suffix = "".join(
                secrets.choice(cls.SUFFIX_ALPHABET) for _ in range(cls.SUFFIX_LENGTH)
            )
            tracking_number = f"{cls.PREFIX}-{year}-{suffix}"
            if not order_model.objects.filter(tracking_number=tracking_number).exists():
                return tracking_number

        raise RuntimeError("Unable to generate a unique tracking number.")
