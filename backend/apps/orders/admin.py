from django.contrib import admin

from apps.orders.models import Order, OrderItem, PaymentTransaction, PaymentWebhookEvent


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "product_title",
        "variant_color",
        "sku",
        "unit_price",
        "quantity",
        "line_total",
    )
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "tracking_number",
        "full_name",
        "phone_number",
        "city",
        "total_amount",
        "payment_method",
        "status",
        "created_at",
    )
    list_filter = ("status", "payment_method", "city", "created_at")
    search_fields = ("tracking_number", "full_name", "phone_number")
    readonly_fields = ("tracking_number", "created_at", "updated_at")
    inlines = (OrderItemInline,)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "gateway",
        "status",
        "amount",
        "external_reference",
        "created_at",
    )
    list_filter = ("gateway", "status")
    search_fields = ("order__tracking_number", "external_reference", "idempotency_key")
    readonly_fields = ("idempotency_key", "created_at", "updated_at")


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("gateway", "idempotency_key", "processed_at")
    list_filter = ("gateway",)
    search_fields = ("idempotency_key",)
    readonly_fields = ("processed_at",)
