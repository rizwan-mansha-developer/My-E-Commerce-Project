from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.catalog.models import ProductVariant
from apps.catalog.validators import validate_pakistan_mobile


class PaymentMethod(models.TextChoices):
    COD = "COD", "Cash on Delivery"
    JAZZCASH = "JAZZCASH", "JazzCash"
    EASYPAISA = "EASYPAISA", "EasyPaisa"
    CARD = "CARD", "Card (Stripe)"


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"
    CONFIRMED = "CONFIRMED", "Confirmed"
    DISPATCHED = "DISPATCHED", "Dispatched"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"


class Order(models.Model):
    """Customer order with secure DRLNG tracking ID and COD workflow."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tracking_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        editable=False,
        help_text="Format: DRLNG-{YEAR}-{A-Z0-9}{4}",
    )
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(
        max_length=11,
        validators=[validate_pakistan_mobile],
        db_index=True,
    )
    shipping_address = models.TextField()
    city = models.CharField(max_length=100, db_index=True)
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.COD,
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["phone_number", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.tracking_number} — {self.full_name}"


class OrderItem(models.Model):
    """Line item snapshot at time of purchase."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    product_title = models.CharField(max_length=255)
    variant_color = models.CharField(max_length=100)
    sku = models.CharField(max_length=64, db_index=True)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["sku"]),
        ]

    def __str__(self) -> str:
        return f"{self.quantity}× {self.product_title} ({self.variant_color})"


class PaymentTransactionStatus(models.TextChoices):
    INITIATED = "INITIATED", "Initiated"
    PENDING = "PENDING", "Pending"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class PaymentTransaction(models.Model):
    """Gateway payment attempt linked to an order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payment_transactions",
    )
    gateway = models.CharField(max_length=20, choices=PaymentMethod.choices, db_index=True)
    idempotency_key = models.CharField(max_length=128, unique=True, db_index=True)
    external_reference = models.CharField(max_length=128, blank=True, db_index=True)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentTransactionStatus.choices,
        default=PaymentTransactionStatus.INITIATED,
        db_index=True,
    )
    redirect_url = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["gateway", "status"]),
            models.Index(fields=["order", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.gateway} — {self.order.tracking_number} ({self.status})"


class PaymentWebhookEvent(models.Model):
    """Idempotent record of processed gateway webhook events."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.CharField(max_length=255, unique=True, db_index=True)
    gateway = models.CharField(max_length=20, choices=PaymentMethod.choices)
    payload = models.JSONField(default=dict)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-processed_at"]

    def __str__(self) -> str:
        return f"{self.gateway} webhook {self.idempotency_key}"
