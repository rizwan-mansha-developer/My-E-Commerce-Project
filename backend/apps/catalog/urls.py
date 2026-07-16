"""Catalog API routes."""

from __future__ import annotations

from django.urls import path

from apps.catalog.admin_views import (
    InventoryAdminDetailView,
    InventoryAdminListView,
    ProductAdminDetailView,
    ProductAdminListView,
    ProductAdminSlugDetailView,
)
from apps.catalog.views import (
    CategoryListView,
    ProductDetailView,
    ProductImageUploadView,
    ProductListView,
    WishlistMergeView,
    WishlistToggleView,
    WishlistView,
)

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
    path("wishlist/", WishlistView.as_view(), name="wishlist-list"),
    path("wishlist/toggle/", WishlistToggleView.as_view(), name="wishlist-toggle"),
    path("wishlist/merge/", WishlistMergeView.as_view(), name="wishlist-merge"),
    path("admin/products/", ProductAdminListView.as_view(), name="admin-product-list"),
    path(
        "admin/products/upload/",
        ProductImageUploadView.as_view(),
        name="admin-product-image-upload",
    ),
    path(
        "admin/products/by-slug/<slug:slug>/",
        ProductAdminSlugDetailView.as_view(),
        name="admin-product-slug-detail",
    ),
    path(
        "admin/products/<uuid:product_id>/",
        ProductAdminDetailView.as_view(),
        name="admin-product-detail",
    ),
    path("admin/inventory/", InventoryAdminListView.as_view(), name="admin-inventory-list"),
    path(
        "admin/inventory/<uuid:variant_id>/",
        InventoryAdminDetailView.as_view(),
        name="admin-inventory-detail",
    ),
]
