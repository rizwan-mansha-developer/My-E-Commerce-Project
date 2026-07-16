from __future__ import annotations

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from apps.accounts.permissions import IsSuperUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.admin_serializers import (
    OrderAdminSerializer,
    OrderStatusUpdateSerializer,
)
from apps.orders.models import Order
from services.order_service import OrderService


@extend_schema_view(
    get=extend_schema(tags=["Admin"], summary="List all orders (staff)"),
)
class OrderAdminListView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get("status")
        queryset = Order.objects.prefetch_related("items").order_by("-created_at")

        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())

        serializer = OrderAdminSerializer(queryset, many=True)
        return Response({"results": serializer.data, "count": queryset.count()})


@extend_schema_view(
    get=extend_schema(tags=["Admin"], summary="Get order (staff)"),
    patch=extend_schema(tags=["Admin"], summary="Update order status (staff)"),
)
class OrderAdminDetailView(APIView):
    permission_classes = [IsSuperUser]

    def _get_order(self, order_id: str) -> Order | None:
        return (
            Order.objects.filter(id=order_id)
            .prefetch_related("items")
            .first()
        )

    def get(self, request: Request, order_id: str) -> Response:
        order = self._get_order(order_id)
        if order is None:
            return Response(
                {"detail": "Order not found.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(OrderAdminSerializer(order).data)

    def patch(self, request: Request, order_id: str) -> Response:
        order = self._get_order(order_id)
        if order is None:
            return Response(
                {"detail": "Order not found.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = OrderService.transition_status(
                order_id=order.id,
                new_status=serializer.validated_data["status"],
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc), "code": "invalid_transition"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order = self._get_order(str(order.id))
        return Response(OrderAdminSerializer(order).data)


@extend_schema(tags=["Admin"], summary="Dashboard overview stats (staff)")
class AdminOverviewView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request: Request) -> Response:
        from django.db.models import F
        from django.utils import timezone

        today = timezone.now().date()
        pending_statuses = [OrderStatus.PENDING, OrderStatus.PENDING_PAYMENT]

        return Response(
            {
                "orders_total": Order.objects.count(),
                "orders_today": Order.objects.filter(created_at__date=today).count(),
                "orders_pending": Order.objects.filter(status__in=pending_statuses).count(),
                "products_active": Product.objects.count(),
                "products_total": Product.all_objects.count(),
                "variants_low_stock": ProductVariant.all_objects.filter(
                    is_active=True,
                    quantity_in_stock__lte=F("safety_threshold"),
                ).count(),
                "variants_total": ProductVariant.all_objects.filter(is_active=True).count(),
            }
        )
