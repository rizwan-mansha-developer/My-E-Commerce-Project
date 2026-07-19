from django.contrib import admin

from apps.promotions.models import (
    DiscountCode,
    ReferralProfile,
    RewardsSettings,
    SeasonalCampaign,
)


@admin.register(SeasonalCampaign)
class SeasonalCampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "badge_label",
        "discount_type",
        "discount_value",
        "starts_at",
        "ends_at",
        "is_active",
    )
    list_filter = ("is_active", "discount_type")
    search_fields = ("name", "slug", "badge_label")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("categories", "products")


@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "kind",
        "discount_type",
        "discount_value",
        "times_used",
        "max_uses",
        "is_active",
        "expires_at",
    )
    list_filter = ("kind", "is_active", "discount_type")
    search_fields = ("code", "owner_phone")


@admin.register(ReferralProfile)
class ReferralProfileAdmin(admin.ModelAdmin):
    list_display = ("code", "user", "created_at")
    search_fields = ("code", "user__email", "user__username")


@admin.register(RewardsSettings)
class RewardsSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "next_buy_percent",
        "referral_friend_percent",
        "referral_reward_percent",
        "updated_at",
    )

    def has_add_permission(self, request) -> bool:
        return not RewardsSettings.objects.exists()

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
