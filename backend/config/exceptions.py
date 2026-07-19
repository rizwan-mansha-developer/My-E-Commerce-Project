from __future__ import annotations

from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler


class InsufficientStockError(APIException):
    status_code = 400
    default_detail = "Insufficient stock for one or more items."
    default_code = "insufficient_stock"


def _first_error_message(data: object) -> str:
    if isinstance(data, list) and data:
        return str(data[0])
    if isinstance(data, dict):
        if "non_field_errors" in data:
            return _first_error_message(data["non_field_errors"])
        if "detail" in data:
            return _first_error_message(data["detail"])
        for key, value in data.items():
            message = _first_error_message(value)
            if key in ("non_field_errors", "detail"):
                return message
            return f"{key}: {message}"
    return str(data)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        detail = _first_error_message(response.data)
        code = getattr(exc, "default_code", "error")
        if isinstance(exc, ValidationError):
            code = "invalid_request"
        response.data = {"detail": detail, "code": code}
    return response
