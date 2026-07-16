from __future__ import annotations

import re

from django.core.exceptions import ValidationError

PAKISTAN_MOBILE_PATTERN = re.compile(r"^03\d{9}$")


def validate_pakistan_mobile(value: str) -> None:
    """Validate Pakistani mobile numbers in 03XXXXXXXXX format."""
    if not PAKISTAN_MOBILE_PATTERN.match(value):
        raise ValidationError(
            "Enter a valid Pakistani mobile number (e.g. 03001234567).",
            code="invalid_pk_mobile",
        )
