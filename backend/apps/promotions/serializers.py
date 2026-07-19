from __future__ import annotations

from rest_framework import serializers

from apps.promotions.models import (
    DiscountCode,
    DiscountCodeKind,
    DiscountType,
    ReferralProfile,
    RewardsSettings,
    SeasonalCampaign,
)


class SeasonalCampaignPublicSerializer(serializers.ModelSerializer):
    is_live = serializers.BooleanField(read_only=True)

    class Meta:
        model = SeasonalCampaign
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "badge_label",
            "banner_text",
            "discount_type",
            "discount_value",
            "starts_at",
            "ends_at",
            "is_live",
        )


class QuoteLineSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=10)


class DiscountQuoteSerializer(serializers.Serializer):
    items = QuoteLineSerializer(many=True, allow_empty=False)
    discount_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=32,
        trim_whitespace=True,
    )
    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=11,
        trim_whitespace=True,
    )


class DiscountQuoteResponseSerializer(serializers.Serializer):
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    seasonal_discount = serializers.DecimalField(max_digits=12, decimal_places=2)
    code_discount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_discount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount_code = serializers.CharField(allow_blank=True)
    label = serializers.CharField(allow_blank=True)
    campaign = SeasonalCampaignPublicSerializer(allow_null=True)


class DiscountCodePublicSerializer(serializers.ModelSerializer):
    is_redeemable = serializers.BooleanField(read_only=True)

    class Meta:
        model = DiscountCode
        fields = (
            "code",
            "kind",
            "discount_type",
            "discount_value",
            "times_used",
            "max_uses",
            "expires_at",
            "is_redeemable",
        )


class RewardsSettingsPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardsSettings
        fields = (
            "next_buy_percent",
            "referral_friend_percent",
            "referral_reward_percent",
        )


class BuyerRewardsSerializer(serializers.Serializer):
    referral_code = serializers.CharField()
    settings = RewardsSettingsPublicSerializer()
    codes = DiscountCodePublicSerializer(many=True)


class SeasonalCampaignAdminSerializer(serializers.ModelSerializer):
    category_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
    )
    product_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
    )
    is_live = serializers.BooleanField(read_only=True)
    # Optional on write — SeasonalCampaign.save() auto-generates from name.
    slug = serializers.SlugField(required=False, allow_blank=True, max_length=140)

    class Meta:
        model = SeasonalCampaign
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "badge_label",
            "banner_text",
            "discount_type",
            "discount_value",
            "starts_at",
            "ends_at",
            "is_active",
            "applies_sitewide",
            "category_ids",
            "product_ids",
            "is_live",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "is_live")

    def validate(self, attrs: dict) -> dict:
        discount_type = attrs.get(
            "discount_type",
            getattr(self.instance, "discount_type", DiscountType.PERCENT),
        )
        value = attrs.get(
            "discount_value",
            getattr(self.instance, "discount_value", None),
        )
        if value is not None and discount_type == DiscountType.PERCENT and value > 90:
            raise serializers.ValidationError(
                {"discount_value": "Percent discount cannot exceed 90%."}
            )
        starts = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts and ends and ends <= starts:
            raise serializers.ValidationError(
                {"ends_at": "End must be after start."}
            )
        return attrs

    def create(self, validated_data: dict) -> SeasonalCampaign:
        category_ids = validated_data.pop("category_ids", [])
        product_ids = validated_data.pop("product_ids", [])
        if not validated_data.get("slug"):
            validated_data.pop("slug", None)
        campaign = SeasonalCampaign.objects.create(**validated_data)
        if category_ids:
            campaign.categories.set(category_ids)
        if product_ids:
            campaign.products.set(product_ids)
        return campaign

    def update(self, instance: SeasonalCampaign, validated_data: dict) -> SeasonalCampaign:
        category_ids = validated_data.pop("category_ids", None)
        product_ids = validated_data.pop("product_ids", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if category_ids is not None:
            instance.categories.set(category_ids)
        if product_ids is not None:
            instance.products.set(product_ids)
        return instance


class DiscountCodeAdminSerializer(serializers.ModelSerializer):
    owner_email = serializers.SerializerMethodField()
    is_redeemable = serializers.BooleanField(read_only=True)
    source_order_id = serializers.UUIDField(read_only=True, allow_null=True)
    referrer_email = serializers.SerializerMethodField()

    class Meta:
        model = DiscountCode
        fields = (
            "id",
            "code",
            "kind",
            "discount_type",
            "discount_value",
            "owner_user",
            "owner_email",
            "owner_phone",
            "referrer_user",
            "referrer_email",
            "source_order_id",
            "max_uses",
            "times_used",
            "min_order_amount",
            "is_active",
            "expires_at",
            "is_redeemable",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "times_used",
            "created_at",
            "updated_at",
            "is_redeemable",
            "owner_email",
            "referrer_email",
            "source_order_id",
        )
        extra_kwargs = {
            "code": {"required": False, "allow_blank": True},
            "owner_user": {"required": False, "allow_null": True},
            "referrer_user": {"required": False, "allow_null": True},
            "owner_phone": {"required": False, "allow_blank": True},
            "expires_at": {"required": False, "allow_null": True},
        }

    def get_owner_email(self, obj: DiscountCode) -> str | None:
        user = obj.owner_user
        if user is None:
            return None
        return user.email or user.username or None

    def get_referrer_email(self, obj: DiscountCode) -> str | None:
        user = obj.referrer_user
        if user is None:
            return None
        return user.email or user.username or None

    def validate_code(self, value: str) -> str:
        return value.strip().upper()

    def create(self, validated_data: dict) -> DiscountCode:
        from services.promotion_service import PromotionService

        code = validated_data.get("code") or ""
        if not code:
            kind = validated_data.get("kind", DiscountCodeKind.MANUAL)
            prefix = {
                DiscountCodeKind.LOYALTY_NEXT_BUY: "NEXT",
                DiscountCodeKind.REFERRAL_REWARD: "REF",
                DiscountCodeKind.REFERRAL_FRIEND: "FRIEND",
                DiscountCodeKind.SEASONAL: "SALE",
            }.get(kind, "PROMO")
            validated_data["code"] = PromotionService._new_code(prefix)
        return super().create(validated_data)


class ReferralProfileAdminSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = ReferralProfile
        fields = (
            "id",
            "user_id",
            "user_email",
            "code",
            "created_at",
        )
        read_only_fields = fields

    def get_user_email(self, obj: ReferralProfile) -> str:
        return obj.user.email or obj.user.username or str(obj.user_id)


class RewardsSettingsAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardsSettings
        fields = (
            "next_buy_percent",
            "next_buy_expires_days",
            "referral_friend_percent",
            "referral_reward_percent",
            "referral_reward_expires_days",
            "issue_loyalty_on_confirmed",
            "updated_at",
        )
        read_only_fields = ("updated_at",)
