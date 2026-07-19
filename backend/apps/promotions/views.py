from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from dj_rest_auth.jwt_auth import JWTCookieAuthentication

from apps.promotions.serializers import (
    BuyerRewardsSerializer,
    DiscountQuoteResponseSerializer,
    DiscountQuoteSerializer,
    SeasonalCampaignPublicSerializer,
)
from config.schema import ApiErrorSerializer
from services.order_service import OrderService
from services.promotion_service import PromotionService, QuoteLine


class ActiveCampaignView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Promotions"],
        summary="Active seasonal campaign",
        responses={200: SeasonalCampaignPublicSerializer},
    )
    def get(self, request: Request) -> Response:
        campaign = PromotionService.get_active_campaign()
        if campaign is None:
            return Response({"campaign": None})
        return Response(
            {"campaign": SeasonalCampaignPublicSerializer(campaign).data}
        )


class DiscountQuoteView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Promotions"],
        summary="Preview cart discounts",
        request=DiscountQuoteSerializer,
        responses={200: DiscountQuoteResponseSerializer, 400: ApiErrorSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = DiscountQuoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        items = [
            QuoteLine(variant_id=line["variant_id"], quantity=line["quantity"])
            for line in data["items"]
        ]
        try:
            variants = OrderService.load_variants(items)
            applied = PromotionService.quote(
                items=items,
                variants=variants,
                discount_code=data.get("discount_code") or None,
                user=request.user if request.user.is_authenticated else None,
                phone=data.get("phone_number") or None,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc), "code": "discount_error"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "subtotal": applied.subtotal,
                "seasonal_discount": applied.seasonal_amount,
                "code_discount": applied.code_amount,
                "total_discount": applied.total_discount,
                "total": applied.total_amount,
                "discount_code": applied.discount_code_str,
                "label": applied.label,
                "campaign": (
                    SeasonalCampaignPublicSerializer(applied.campaign).data
                    if applied.campaign
                    else None
                ),
            }
        )


class BuyerRewardsView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Promotions"],
        summary="Buyer referral code and rewards",
        responses={200: BuyerRewardsSerializer},
    )
    def get(self, request: Request) -> Response:
        payload = PromotionService.list_user_rewards(user=request.user)
        return Response(payload)
