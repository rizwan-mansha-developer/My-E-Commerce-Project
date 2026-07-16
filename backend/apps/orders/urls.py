"""Orders and payment API routes."""

from __future__ import annotations

from django.urls import path

from apps.orders.buyer_views import (
    BuyerDashboardSummaryView,
    BuyerOrderListView,
    OrderTrackView,
)
from apps.orders.admin_views import (
    AdminOverviewView,
    OrderAdminDetailView,
    OrderAdminListView,
)
from apps.orders.views import (
    CartCheckoutView,
    EasyPaisaWebhookView,
    ExpressCheckoutView,
    JazzCashWebhookView,
    SandboxConfirmView,
    StripeWebhookView,
)

urlpatterns = [
    path("express/", ExpressCheckoutView.as_view(), name="express-checkout"),
    path("cart/", CartCheckoutView.as_view(), name="cart-checkout"),
    path("my/", BuyerOrderListView.as_view(), name="buyer-order-list"),
    path("my/summary/", BuyerDashboardSummaryView.as_view(), name="buyer-dashboard-summary"),
    path("track/", OrderTrackView.as_view(), name="order-track"),
    path("admin/overview/", AdminOverviewView.as_view(), name="admin-overview"),
    path("admin/orders/", OrderAdminListView.as_view(), name="admin-order-list"),
    path(
        "admin/orders/<uuid:order_id>/",
        OrderAdminDetailView.as_view(),
        name="admin-order-detail",
    ),
    path(
        "payments/webhooks/jazzcash/",
        JazzCashWebhookView.as_view(),
        name="webhook-jazzcash",
    ),
    path(
        "payments/webhooks/easypaisa/",
        EasyPaisaWebhookView.as_view(),
        name="webhook-easypaisa",
    ),
    path(
        "payments/webhooks/stripe/",
        StripeWebhookView.as_view(),
        name="webhook-stripe",
    ),
    path(
        "payments/sandbox-confirm/",
        SandboxConfirmView.as_view(),
        name="sandbox-confirm",
    ),
]
