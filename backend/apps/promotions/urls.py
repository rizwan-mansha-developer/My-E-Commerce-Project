from __future__ import annotations

from django.urls import path

from apps.promotions.admin_views import (
    CampaignAdminDetailView,
    CampaignAdminListView,
    DiscountCodeAdminDetailView,
    DiscountCodeAdminListView,
    ReferralProfileAdminListView,
    RewardsSettingsAdminView,
)
from apps.promotions.views import ActiveCampaignView, BuyerRewardsView, DiscountQuoteView

urlpatterns = [
    path("campaigns/active/", ActiveCampaignView.as_view(), name="active-campaign"),
    path("quote/", DiscountQuoteView.as_view(), name="discount-quote"),
    path("rewards/", BuyerRewardsView.as_view(), name="buyer-rewards"),
    path("admin/campaigns/", CampaignAdminListView.as_view(), name="admin-campaigns"),
    path(
        "admin/campaigns/<uuid:campaign_id>/",
        CampaignAdminDetailView.as_view(),
        name="admin-campaign-detail",
    ),
    path("admin/codes/", DiscountCodeAdminListView.as_view(), name="admin-codes"),
    path(
        "admin/codes/<uuid:code_id>/",
        DiscountCodeAdminDetailView.as_view(),
        name="admin-code-detail",
    ),
    path(
        "admin/referral-profiles/",
        ReferralProfileAdminListView.as_view(),
        name="admin-referral-profiles",
    ),
    path(
        "admin/rewards-settings/",
        RewardsSettingsAdminView.as_view(),
        name="admin-rewards-settings",
    ),
]
