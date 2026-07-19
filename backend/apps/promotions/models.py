from __future__ import annotations

import secrets
import string
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class DiscountType(models.TextChoices):
    PERCENT = "PERCENT", "Percent"
    FIXED = "FIXED", "Fixed amount (PKR)"


class DiscountCodeKind(models.TextChoices):
    LOYALTY_NEXT_BUY = "LOYALTY_NEXT_BUY", "Next-buy loyalty"
    REFERRAL_FRIEND = "REFERRAL_FRIEND", "Referral friend offer"
    REFERRAL_REWARD = "REFERRAL_REWARD", "Referral reward"
    MANUAL = "MANUAL", "Manual / promo code"
    SEASONAL = "SEASONAL", "Seasonal campaign code"


class SeasonalCampaign(models.Model):
    """Time-boxed storewide (or scoped) seasonal sale."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, db_index=True)
    description = models.TextField(blank=True)
    badge_label = models.CharField(
        max_length=40,
        default="Seasonal sale",
        help_text="Short badge on storefront (e.g. Summer Sale).",
    )
    banner_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Homepage / checkout promo line.",
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENT,
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Percent (e.g. 15) or fixed PKR amount.",
    )
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    applies_sitewide = models.BooleanField(
        default=True,
        help_text="When true, discount applies to the full cart subtotal.",
    )
    categories = models.ManyToManyField(
        "catalog.Category",
        blank=True,
        related_name="seasonal_campaigns",
    )
    products = models.ManyToManyField(
        "catalog.Product",
        blank=True,
        related_name="seasonal_campaigns",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at"]
        indexes = [
            models.Index(fields=["is_active", "starts_at", "ends_at"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(self.name) or "campaign"
            self.slug = f"{base}-{secrets.token_hex(2)}"
        super().save(*args, **kwargs)

    @property
    def is_live(self) -> bool:
        now = timezone.now()
        return bool(
            self.is_active and self.starts_at <= now <= self.ends_at
        )


class DiscountCode(models.Model):
    """Redeemable cart discount — loyalty, referral, or manual promo."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, unique=True, db_index=True)
    kind = models.CharField(
        max_length=32,
        choices=DiscountCodeKind.choices,
        default=DiscountCodeKind.MANUAL,
        db_index=True,
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENT,
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="owned_discount_codes",
    )
    owner_phone = models.CharField(max_length=11, blank=True, db_index=True)
    referrer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referral_friend_codes",
        help_text="For friend codes: the customer who shared the referral.",
    )
    source_order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_discount_codes",
    )
    campaign = models.ForeignKey(
        SeasonalCampaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="codes",
    )
    max_uses = models.PositiveIntegerField(
        default=1,
        help_text="Total redemptions allowed (referral friend codes may be higher).",
    )
    times_used = models.PositiveIntegerField(default=0)
    min_order_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    is_active = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["kind", "is_active"]),
            models.Index(fields=["owner_user", "kind"]),
            models.Index(fields=["owner_phone", "kind"]),
        ]

    def __str__(self) -> str:
        return self.code

    @property
    def is_redeemable(self) -> bool:
        if not self.is_active:
            return False
        if self.times_used >= self.max_uses:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class ReferralProfile(models.Model):
    """Per-user shareable referral code."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_profile",
    )
    code = models.CharField(max_length=24, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.code} ({self.user_id})"

    @staticmethod
    def generate_code(prefix: str = "DRLNG") -> str:
        alphabet = string.ascii_uppercase + string.digits
        suffix = "".join(secrets.choice(alphabet) for _ in range(6))
        return f"{prefix}-{suffix}"


class RewardsSettings(models.Model):
    """Singleton store rewards configuration (pk=1)."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    next_buy_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(Decimal("90.00"))],
    )
    next_buy_expires_days = models.PositiveIntegerField(default=90)
    referral_friend_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("5.00"),
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(Decimal("90.00"))],
    )
    referral_reward_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(Decimal("90.00"))],
    )
    referral_reward_expires_days = models.PositiveIntegerField(default=90)
    issue_loyalty_on_confirmed = models.BooleanField(
        default=True,
        help_text="Issue next-buy codes when an order is Confirmed.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rewards settings"
        verbose_name_plural = "Rewards settings"

    def __str__(self) -> str:
        return "Rewards settings"

    def save(self, *args, **kwargs) -> None:
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> RewardsSettings:
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
