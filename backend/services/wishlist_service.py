from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from django.contrib.auth.models import AnonymousUser
from django.db import transaction
from django.db.models import QuerySet

from apps.catalog.models import Product, WishlistItem

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser
    from django.http import HttpRequest


@dataclass(frozen=True)
class WishlistOwner:
    user: AbstractBaseUser | None
    session_key: str | None


@dataclass(frozen=True)
class ToggleFavoriteResult:
    favorited: bool
    product_id: UUID
    total_count: int


class WishlistService:
    """Guest and authenticated favorites — one-tap toggle, no account required."""

    @staticmethod
    def resolve_owner(request: HttpRequest) -> WishlistOwner:
        user = request.user
        if user.is_authenticated:
            return WishlistOwner(user=user, session_key=None)

        if not request.session.session_key:
            request.session.create()

        return WishlistOwner(user=None, session_key=request.session.session_key)

    @staticmethod
    def list_items(*, owner: WishlistOwner) -> QuerySet[WishlistItem]:
        return (
            WishlistItem.objects.filter(
                product__is_active=True,
                **WishlistService._owner_filter(owner),
            )
            .select_related("product")
            .order_by("-created_at")
        )

    @staticmethod
    def list_products(*, owner: WishlistOwner) -> list[Product]:
        return [item.product for item in WishlistService.list_items(owner=owner)]

    @staticmethod
    def favorited_product_ids(*, owner: WishlistOwner) -> list[UUID]:
        return list(
            WishlistItem.objects.filter(
                product__is_active=True,
                **WishlistService._owner_filter(owner),
            ).values_list("product_id", flat=True)
        )

    @staticmethod
    def is_favorited(*, owner: WishlistOwner, product_id: UUID) -> bool:
        return WishlistItem.objects.filter(
            product_id=product_id,
            product__is_active=True,
            **WishlistService._owner_filter(owner),
        ).exists()

    @staticmethod
    @transaction.atomic
    def toggle_favorite(*, owner: WishlistOwner, product_id: UUID) -> ToggleFavoriteResult:
        product = Product.objects.filter(id=product_id, is_active=True).first()
        if product is None:
            raise ValueError("Product not found or unavailable.")

        existing = WishlistItem.objects.filter(
            product_id=product_id,
            **WishlistService._owner_filter(owner),
        ).first()

        if existing:
            existing.delete()
            favorited = False
        else:
            WishlistItem.objects.create(
                user=owner.user,
                session_key=owner.session_key,
                product=product,
            )
            favorited = True

        total_count = WishlistItem.objects.filter(
            **WishlistService._owner_filter(owner),
        ).count()

        return ToggleFavoriteResult(
            favorited=favorited,
            product_id=product_id,
            total_count=total_count,
        )

    @staticmethod
    @transaction.atomic
    def merge_session_into_user(
        *,
        session_key: str,
        user: AbstractBaseUser,
    ) -> int:
        """Move guest favorites to an authenticated account on login."""
        if isinstance(user, AnonymousUser) or not user.is_authenticated:
            return 0

        merged = 0
        guest_items = WishlistItem.objects.filter(session_key=session_key).select_related(
            "product"
        )

        for item in guest_items:
            _, created = WishlistItem.objects.get_or_create(
                user=user,
                product=item.product,
            )
            if created:
                merged += 1

        guest_items.delete()
        return merged

    @staticmethod
    def _owner_filter(owner: WishlistOwner) -> dict[str, object]:
        if owner.user is not None:
            return {"user": owner.user}
        if owner.session_key:
            return {"session_key": owner.session_key}
        raise ValueError("Wishlist owner requires an authenticated user or session key.")
