from __future__ import annotations

import logging
from decimal import Decimal

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.orders.models import Order

logger = logging.getLogger(__name__)


class NotificationService:
    """Push real-time events to admin WebSocket subscribers."""

    ADMIN_GROUP = "notifications"

    @staticmethod
    def push_order_created(order: Order) -> None:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.warning("Channel layer unavailable — skipping order notification.")
            return

        first_item = order.items.select_related("variant__product").first()
        payload = {
            "event": "order.created",
            "order_id": str(order.id),
            "tracking_number": order.tracking_number,
            "full_name": order.full_name,
            "phone_number": order.phone_number,
            "city": order.city,
            "total_amount": str(order.total_amount.quantize(Decimal("0.01"))),
            "payment_method": order.payment_method,
            "status": order.status,
            "created_at": order.created_at.isoformat(),
            "product_title": first_item.product_title if first_item else "",
            "variant_color": first_item.variant_color if first_item else "",
        }

        try:
            async_to_sync(channel_layer.group_send)(
                NotificationService.ADMIN_GROUP,
                {
                    "type": "notification.message",
                    "data": payload,
                },
            )
        except Exception:
            logger.exception(
                "Failed to push order notification for %s",
                order.tracking_number,
            )
