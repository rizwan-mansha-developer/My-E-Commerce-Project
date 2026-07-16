from __future__ import annotations

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from dj_rest_auth.jwt_auth import JWTCookieAuthentication

from apps.orders.models import PaymentMethod
from apps.orders.serializers import (
    CartCheckoutSerializer,
    ExpressCheckoutSerializer,
    ExpressOrderResponseSerializer,
)
from config.exceptions import InsufficientStockError
from config.schema import ApiErrorSerializer
from gateways.registry import is_online_payment_method
from services.order_service import CreateOrderPayload, ExpressCheckoutInput, OrderLineInput, OrderService
from services.payment_service import PaymentService

WebhookResponseSerializer = inline_serializer(
    name="WebhookResponse",
    fields={
        "success": serializers.BooleanField(),
        "message": serializers.CharField(),
    },
)


class ExpressCheckoutView(APIView):
    """Guest-friendly instant COD checkout."""

    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Orders"],
        summary="Express COD checkout",
        description=(
            "Create a guest order in one request. "
            "Launch configuration uses `payment_method: COD` only."
        ),
        request=ExpressCheckoutSerializer,
        responses={
            201: ExpressOrderResponseSerializer,
            400: ApiErrorSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = ExpressCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            user = request.user if request.user.is_authenticated else None
            order = OrderService.create_express_order(
                payload=ExpressCheckoutInput(
                    variant_id=data["variant_id"],
                    full_name=data["full_name"],
                    phone_number=data["phone_number"],
                    shipping_address=data["shipping_address"],
                    city=data["city"],
                    quantity=data["quantity"],
                    payment_method=data["payment_method"],
                    user=user,
                )
            )
        except InsufficientStockError as exc:
            return Response(
                {"detail": str(exc.detail), "code": exc.default_code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc), "code": "checkout_error"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_data = ExpressOrderResponseSerializer(order).data

        if is_online_payment_method(order.payment_method):
            payment = PaymentService.initiate_for_order(order=order)
            response_data["redirect_url"] = payment.redirect_url
            response_data["payment_id"] = str(payment.payment_id)

        return Response(response_data, status=status.HTTP_201_CREATED)


class CartCheckoutView(APIView):
    """Cart checkout — COD only at launch; multi-item order."""

    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Orders"],
        summary="Cart COD checkout",
        description=(
            "Create an order from one or more cart lines. "
            "Launch configuration accepts `payment_method: COD` only; "
            "JazzCash / EasyPaisa / Card remain for Phase 4."
        ),
        request=CartCheckoutSerializer,
        responses={
            201: ExpressOrderResponseSerializer,
            400: ApiErrorSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = CartCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            user = request.user if request.user.is_authenticated else None
            order = OrderService.create_order(
                payload=CreateOrderPayload(
                    full_name=data["full_name"],
                    phone_number=data["phone_number"],
                    shipping_address=data["shipping_address"],
                    city=data["city"],
                    items=[
                        OrderLineInput(
                            variant_id=line["variant_id"],
                            quantity=line["quantity"],
                        )
                        for line in data["items"]
                    ],
                    payment_method=data["payment_method"],
                    user=user,
                )
            )
        except InsufficientStockError as exc:
            return Response(
                {"detail": str(exc.detail), "code": exc.default_code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc), "code": "checkout_error"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_data = ExpressOrderResponseSerializer(order).data

        if is_online_payment_method(order.payment_method):
            payment = PaymentService.initiate_for_order(order=order)
            response_data["redirect_url"] = payment.redirect_url
            response_data["payment_id"] = str(payment.payment_id)

        return Response(response_data, status=status.HTTP_201_CREATED)


class PaymentWebhookView(APIView):
    """Idempotent gateway webhook handler (postponed at launch)."""

    authentication_classes: list = []
    permission_classes: list = []

    gateway_name: str = ""

    @extend_schema(
        tags=["Payments"],
        summary="Payment gateway webhook",
        description="Postponed — not used during COD-only launch.",
        request=inline_serializer(
            name="WebhookPayload",
            fields={"payload": serializers.JSONField()},
        ),
        responses={
            200: WebhookResponseSerializer,
            404: ApiErrorSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        payload = request.data if isinstance(request.data, dict) else {}
        success, message = PaymentService.handle_webhook(
            gateway_name=self.gateway_name,
            payload=payload,
        )

        if message == "order_not_found":
            return Response(
                {"detail": "Order not found.", "code": "order_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"success": success, "message": message},
            status=status.HTTP_200_OK,
        )


class JazzCashWebhookView(PaymentWebhookView):
    gateway_name = PaymentMethod.JAZZCASH


class EasyPaisaWebhookView(PaymentWebhookView):
    gateway_name = PaymentMethod.EASYPAISA


class StripeWebhookView(PaymentWebhookView):
    gateway_name = PaymentMethod.CARD


class SandboxConfirmView(APIView):
    """Confirm sandbox online payments (dev only, postponed)."""

    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        tags=["Payments"],
        summary="Sandbox payment confirm",
        description="Development helper for postponed online payment flow.",
        request=inline_serializer(
            name="SandboxConfirmRequest",
            fields={"tracking_number": serializers.CharField()},
        ),
        responses={
            200: ExpressOrderResponseSerializer,
            404: ApiErrorSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        tracking_number = request.data.get("tracking_number", "")
        if not tracking_number:
            return Response(
                {"detail": "tracking_number is required.", "code": "invalid_request"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order = PaymentService.simulate_sandbox_confirmation(
            tracking_number=str(tracking_number)
        )
        if order is None:
            return Response(
                {"detail": "Order not found or already confirmed.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(ExpressOrderResponseSerializer(order).data)
