from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import WishlistItem
from apps.orders.buyer_serializers import (
    BuyerDashboardSummarySerializer,
    BuyerOrderSerializer,
    OrderTrackRequestSerializer,
)
from apps.orders.models import Order, OrderStatus
from services.wishlist_service import WishlistService


COMPLETED_STATUSES = {OrderStatus.DELIVERED, OrderStatus.DISPATCHED, OrderStatus.CONFIRMED}


@extend_schema_view(
    get=extend_schema(tags=["Buyer"], summary="List my orders"),
)
class BuyerOrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        orders = (
            Order.objects.filter(user=request.user)
            .prefetch_related("items")
            .order_by("-created_at")
        )
        serializer = BuyerOrderSerializer(orders, many=True)
        return Response({"results": serializer.data, "count": orders.count()})


@extend_schema_view(
    get=extend_schema(tags=["Buyer"], summary="Buyer dashboard summary"),
)
class BuyerDashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        orders = Order.objects.filter(user=request.user).prefetch_related("items")
        recent = orders.order_by("-created_at")[:5]

        spent = (
            orders.filter(status__in=COMPLETED_STATUSES).aggregate(
                total=Sum("total_amount")
            )["total"]
            or Decimal("0.00")
        )

        owner = WishlistService.resolve_owner(request)
        wishlist_count = WishlistService.list_items(owner=owner).count()

        payload = {
            "order_count": orders.count(),
            "wishlist_count": wishlist_count,
            "total_spent": str(spent.quantize(Decimal("0.01"))),
            "delivered_count": orders.filter(status=OrderStatus.DELIVERED).count(),
            "pending_count": orders.filter(
                status__in=[OrderStatus.PENDING, OrderStatus.PENDING_PAYMENT]
            ).count(),
            "recent_orders": BuyerOrderSerializer(recent, many=True).data,
        }
        return Response(BuyerDashboardSummarySerializer(payload).data)


@extend_schema_view(
    post=extend_schema(tags=["Buyer"], summary="Track order by tracking number + phone"),
)
class OrderTrackView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request: Request) -> Response:
        serializer = OrderTrackRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        order = (
            Order.objects.filter(
                tracking_number=data["tracking_number"].strip().upper(),
                phone_number=data["phone_number"].strip(),
            )
            .prefetch_related("items")
            .first()
        )

        if order is None:
            return Response(
                {"detail": "Order not found. Check tracking number and phone.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(BuyerOrderSerializer(order).data)
