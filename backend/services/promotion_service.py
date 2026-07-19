from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import ProductVariant
from apps.orders.models import Order, OrderStatus
from apps.promotions.models import (
    DiscountCode,
    DiscountCodeKind,
    DiscountType,
    ReferralProfile,
    RewardsSettings,
    SeasonalCampaign,
)


TWOPLACES = Decimal("0.01")


@dataclass(frozen=True)
class QuoteLine:
    variant_id: UUID
    quantity: int


@dataclass(frozen=True)
class AppliedDiscount:
    subtotal: Decimal
    seasonal_amount: Decimal
    code_amount: Decimal
    total_discount: Decimal
    total_amount: Decimal
    campaign: SeasonalCampaign | None
    discount_code: DiscountCode | None
    discount_code_str: str
    referrer_user: object | None
    label: str


class PromotionService:
    """Seasonal campaigns, loyalty next-buy codes, and referral rewards."""

    @staticmethod
    def get_active_campaign() -> SeasonalCampaign | None:
        now = timezone.now()
        return (
            SeasonalCampaign.objects.filter(
                is_active=True,
                starts_at__lte=now,
                ends_at__gte=now,
            )
            .order_by("-starts_at")
            .first()
        )

    @staticmethod
    def ensure_referral_profile(*, user) -> ReferralProfile:
        profile = getattr(user, "referral_profile", None)
        if profile is not None:
            return profile
        for _ in range(8):
            code = ReferralProfile.generate_code()
            if not ReferralProfile.objects.filter(code=code).exists():
                return ReferralProfile.objects.create(user=user, code=code)
        raise ValueError("Could not allocate a referral code.")

    @staticmethod
    def calculate_discount_amount(
        *,
        subtotal: Decimal,
        discount_type: str,
        discount_value: Decimal,
    ) -> Decimal:
        if subtotal <= 0:
            return Decimal("0.00")
        if discount_type == DiscountType.PERCENT:
            amount = (subtotal * discount_value / Decimal("100")).quantize(
                TWOPLACES, rounding=ROUND_HALF_UP
            )
        else:
            amount = discount_value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        return min(amount, subtotal)

    @staticmethod
    def _eligible_subtotal_for_campaign(
        *,
        campaign: SeasonalCampaign,
        items: Sequence[QuoteLine],
        variants: dict[UUID, ProductVariant],
        full_subtotal: Decimal,
    ) -> Decimal:
        if campaign.applies_sitewide:
            return full_subtotal

        category_ids = set(campaign.categories.values_list("id", flat=True))
        product_ids = set(campaign.products.values_list("id", flat=True))
        if not category_ids and not product_ids:
            return full_subtotal

        eligible = Decimal("0.00")
        for line in items:
            variant = variants[line.variant_id]
            product = variant.product
            if product.id in product_ids or (
                product.category_id and product.category_id in category_ids
            ):
                eligible += variant.effective_price * line.quantity
        return eligible

    @staticmethod
    def resolve_code(
        *,
        raw_code: str | None,
        user=None,
        phone: str | None = None,
    ) -> DiscountCode | None:
        if not raw_code:
            return None
        code = raw_code.strip().upper()
        if not code:
            return None

        referral = ReferralProfile.objects.filter(code=code).select_related("user").first()
        if referral is not None:
            if user is not None and getattr(user, "is_authenticated", False):
                if referral.user_id == user.id:
                    raise ValueError("You cannot use your own referral code.")
            settings = RewardsSettings.load()
            # Virtual friend offer backed by the referrer's profile.
            return DiscountCode(
                code=referral.code,
                kind=DiscountCodeKind.REFERRAL_FRIEND,
                discount_type=DiscountType.PERCENT,
                discount_value=settings.referral_friend_percent,
                referrer_user=referral.user,
                max_uses=10_000,
                times_used=0,
                is_active=True,
            )

        discount = DiscountCode.objects.filter(code=code).first()
        if discount is None:
            raise ValueError("Discount code not found.")
        if not discount.is_redeemable:
            raise ValueError("This discount code is no longer valid.")

        if discount.kind == DiscountCodeKind.LOYALTY_NEXT_BUY:
            owner_ok = False
            if (
                discount.owner_user_id
                and user is not None
                and getattr(user, "is_authenticated", False)
                and discount.owner_user_id == user.id
            ):
                owner_ok = True
            if phone and discount.owner_phone and discount.owner_phone == phone.strip():
                owner_ok = True
            if not owner_ok:
                raise ValueError("This next-buy discount belongs to another customer.")

        if discount.kind == DiscountCodeKind.REFERRAL_REWARD:
            owner_ok = False
            if (
                discount.owner_user_id
                and user is not None
                and getattr(user, "is_authenticated", False)
                and discount.owner_user_id == user.id
            ):
                owner_ok = True
            if phone and discount.owner_phone and discount.owner_phone == phone.strip():
                owner_ok = True
            if not owner_ok:
                raise ValueError(
                    "This referral reward belongs to another customer. "
                    "Sign in or use the matching phone number."
                )

        return discount

    @staticmethod
    def quote(
        *,
        items: Sequence[QuoteLine],
        variants: dict[UUID, ProductVariant],
        discount_code: str | None = None,
        user=None,
        phone: str | None = None,
    ) -> AppliedDiscount:
        subtotal = Decimal("0.00")
        for line in items:
            subtotal += variants[line.variant_id].effective_price * line.quantity
        subtotal = subtotal.quantize(TWOPLACES)

        campaign = PromotionService.get_active_campaign()
        seasonal_amount = Decimal("0.00")
        if campaign is not None:
            eligible = PromotionService._eligible_subtotal_for_campaign(
                campaign=campaign,
                items=items,
                variants=variants,
                full_subtotal=subtotal,
            )
            seasonal_amount = PromotionService.calculate_discount_amount(
                subtotal=eligible,
                discount_type=campaign.discount_type,
                discount_value=campaign.discount_value,
            )

        after_seasonal = subtotal - seasonal_amount
        code_obj = PromotionService.resolve_code(
            raw_code=discount_code,
            user=user,
            phone=phone,
        )
        code_amount = Decimal("0.00")
        if code_obj is not None:
            if after_seasonal < code_obj.min_order_amount:
                raise ValueError(
                    f"Minimum order of PKR {code_obj.min_order_amount} required for this code."
                )
            code_amount = PromotionService.calculate_discount_amount(
                subtotal=after_seasonal,
                discount_type=code_obj.discount_type,
                discount_value=code_obj.discount_value,
            )

        total_discount = (seasonal_amount + code_amount).quantize(TWOPLACES)
        total_amount = (subtotal - total_discount).quantize(TWOPLACES)
        if total_amount < 0:
            total_amount = Decimal("0.00")

        parts: list[str] = []
        if campaign is not None and seasonal_amount > 0:
            parts.append(campaign.badge_label or campaign.name)
        if code_obj is not None and code_amount > 0:
            parts.append(code_obj.code)
        label = " + ".join(parts) if parts else ""

        # Persistable DiscountCode rows only — virtual referral codes have no pk.
        persistable = (
            code_obj
            if code_obj is not None and getattr(code_obj, "pk", None)
            else None
        )
        referrer = getattr(code_obj, "referrer_user", None) if code_obj else None
        code_str = code_obj.code if code_obj is not None else ""

        return AppliedDiscount(
            subtotal=subtotal,
            seasonal_amount=seasonal_amount,
            code_amount=code_amount,
            total_discount=total_discount,
            total_amount=total_amount,
            campaign=campaign if seasonal_amount > 0 else None,
            discount_code=persistable,
            discount_code_str=code_str,
            referrer_user=referrer,
            label=label,
        )

    @staticmethod
    def _new_code(prefix: str) -> str:
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(12):
            suffix = "".join(secrets.choice(alphabet) for _ in range(6))
            candidate = f"{prefix}-{suffix}"
            if not DiscountCode.objects.filter(code=candidate).exists():
                return candidate
        raise ValueError("Could not allocate discount code.")

    @staticmethod
    @transaction.atomic
    def consume_code(discount: DiscountCode | None) -> None:
        if discount is None or discount.pk is None:
            return
        locked = DiscountCode.objects.select_for_update().get(pk=discount.pk)
        if not locked.is_redeemable:
            raise ValueError("Discount code was just used up.")
        locked.times_used += 1
        locked.save(update_fields=["times_used", "updated_at"])

    @staticmethod
    @transaction.atomic
    def issue_loyalty_for_order(order: Order) -> DiscountCode | None:
        settings = RewardsSettings.load()
        if not settings.issue_loyalty_on_confirmed:
            return None
        if order.status not in {OrderStatus.CONFIRMED, OrderStatus.DELIVERED}:
            return None
        if DiscountCode.objects.filter(
            source_order=order,
            kind=DiscountCodeKind.LOYALTY_NEXT_BUY,
        ).exists():
            return None

        expires = timezone.now() + timedelta(days=settings.next_buy_expires_days)
        return DiscountCode.objects.create(
            code=PromotionService._new_code("NEXT"),
            kind=DiscountCodeKind.LOYALTY_NEXT_BUY,
            discount_type=DiscountType.PERCENT,
            discount_value=settings.next_buy_percent,
            owner_user=order.user,
            owner_phone=order.phone_number,
            source_order=order,
            max_uses=1,
            expires_at=expires,
        )

    @staticmethod
    @transaction.atomic
    def issue_referral_reward(
        *,
        referrer,
        source_order: Order,
    ) -> DiscountCode | None:
        if referrer is None:
            return None
        if DiscountCode.objects.filter(
            source_order=source_order,
            kind=DiscountCodeKind.REFERRAL_REWARD,
        ).exists():
            return None

        settings = RewardsSettings.load()
        expires = timezone.now() + timedelta(days=settings.referral_reward_expires_days)
        return DiscountCode.objects.create(
            code=PromotionService._new_code("REF"),
            kind=DiscountCodeKind.REFERRAL_REWARD,
            discount_type=DiscountType.PERCENT,
            discount_value=settings.referral_reward_percent,
            owner_user=referrer,
            source_order=source_order,
            max_uses=1,
            expires_at=expires,
        )

    @staticmethod
    def list_user_rewards(*, user) -> dict:
        from django.db.models import Q

        profile = PromotionService.ensure_referral_profile(user=user)
        settings = RewardsSettings.load()
        now = timezone.now()
        codes = list(
            DiscountCode.objects.filter(owner_user=user, is_active=True)
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gte=now))
            .order_by("-created_at")[:50]
        )
        return {
            "referral_code": profile.code,
            "settings": {
                "next_buy_percent": str(settings.next_buy_percent),
                "referral_friend_percent": str(settings.referral_friend_percent),
                "referral_reward_percent": str(settings.referral_reward_percent),
            },
            "codes": [
                {
                    "code": c.code,
                    "kind": c.kind,
                    "discount_type": c.discount_type,
                    "discount_value": str(c.discount_value),
                    "times_used": c.times_used,
                    "max_uses": c.max_uses,
                    "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                    "is_redeemable": c.is_redeemable,
                }
                for c in codes
            ],
        }
