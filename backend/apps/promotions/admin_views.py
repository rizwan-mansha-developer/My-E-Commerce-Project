from __future__ import annotations

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSuperUser
from apps.promotions.models import (
    DiscountCode,
    ReferralProfile,
    RewardsSettings,
    SeasonalCampaign,
)
from apps.promotions.serializers import (
    DiscountCodeAdminSerializer,
    ReferralProfileAdminSerializer,
    RewardsSettingsAdminSerializer,
    SeasonalCampaignAdminSerializer,
)


@extend_schema_view(
    get=extend_schema(tags=["Admin"], summary="List seasonal campaigns"),
    post=extend_schema(tags=["Admin"], summary="Create seasonal campaign"),
)
class CampaignAdminListView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request: Request) -> Response:
        campaigns = SeasonalCampaign.objects.all()
        return Response(
            {
                "results": SeasonalCampaignAdminSerializer(campaigns, many=True).data,
                "count": campaigns.count(),
            }
        )

    def post(self, request: Request) -> Response:
        serializer = SeasonalCampaignAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = serializer.save()
        return Response(
            SeasonalCampaignAdminSerializer(campaign).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(tags=["Admin"], summary="Get seasonal campaign"),
    patch=extend_schema(tags=["Admin"], summary="Update seasonal campaign"),
    delete=extend_schema(tags=["Admin"], summary="Delete seasonal campaign"),
)
class CampaignAdminDetailView(APIView):
    permission_classes = [IsSuperUser]

    def _get(self, campaign_id: str) -> SeasonalCampaign | None:
        return SeasonalCampaign.objects.filter(id=campaign_id).first()

    def get(self, request: Request, campaign_id: str) -> Response:
        campaign = self._get(campaign_id)
        if campaign is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(SeasonalCampaignAdminSerializer(campaign).data)

    def patch(self, request: Request, campaign_id: str) -> Response:
        campaign = self._get(campaign_id)
        if campaign is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SeasonalCampaignAdminSerializer(
            campaign, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        campaign = serializer.save()
        return Response(SeasonalCampaignAdminSerializer(campaign).data)

    def delete(self, request: Request, campaign_id: str) -> Response:
        campaign = self._get(campaign_id)
        if campaign is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        campaign.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(tags=["Admin"], summary="List discount codes"),
    post=extend_schema(tags=["Admin"], summary="Create discount code"),
)
class DiscountCodeAdminListView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request: Request) -> Response:
        qs = DiscountCode.objects.select_related(
            "owner_user",
            "referrer_user",
            "source_order",
        ).all()
        kind = request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        active = request.query_params.get("is_active")
        if active in {"true", "false"}:
            qs = qs.filter(is_active=active == "true")
        total = qs.count()
        codes = qs[:200]
        return Response(
            {
                "results": DiscountCodeAdminSerializer(codes, many=True).data,
                "count": total,
            }
        )

    def post(self, request: Request) -> Response:
        serializer = DiscountCodeAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.save()
        return Response(
            DiscountCodeAdminSerializer(code).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(tags=["Admin"], summary="Get discount code"),
    patch=extend_schema(tags=["Admin"], summary="Update discount code"),
    delete=extend_schema(tags=["Admin"], summary="Delete discount code"),
)
class DiscountCodeAdminDetailView(APIView):
    permission_classes = [IsSuperUser]

    def _get(self, code_id: str) -> DiscountCode | None:
        return (
            DiscountCode.objects.select_related(
                "owner_user",
                "referrer_user",
                "source_order",
            )
            .filter(id=code_id)
            .first()
        )

    def get(self, request: Request, code_id: str) -> Response:
        code = self._get(code_id)
        if code is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DiscountCodeAdminSerializer(code).data)

    def patch(self, request: Request, code_id: str) -> Response:
        code = self._get(code_id)
        if code is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DiscountCodeAdminSerializer(
            code, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        code = serializer.save()
        return Response(DiscountCodeAdminSerializer(code).data)

    def delete(self, request: Request, code_id: str) -> Response:
        code = self._get(code_id)
        if code is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        code.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(tags=["Admin"], summary="List referral profiles"),
)
class ReferralProfileAdminListView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request: Request) -> Response:
        profiles = ReferralProfile.objects.select_related("user").all()[:200]
        return Response(
            {
                "results": ReferralProfileAdminSerializer(profiles, many=True).data,
                "count": ReferralProfile.objects.count(),
            }
        )


@extend_schema_view(
    get=extend_schema(tags=["Admin"], summary="Get rewards settings"),
    put=extend_schema(tags=["Admin"], summary="Update rewards settings"),
    patch=extend_schema(tags=["Admin"], summary="Patch rewards settings"),
)
class RewardsSettingsAdminView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request: Request) -> Response:
        settings = RewardsSettings.load()
        return Response(RewardsSettingsAdminSerializer(settings).data)

    def put(self, request: Request) -> Response:
        return self._upsert(request, partial=False)

    def patch(self, request: Request) -> Response:
        return self._upsert(request, partial=True)

    def _upsert(self, request: Request, *, partial: bool) -> Response:
        settings = RewardsSettings.load()
        serializer = RewardsSettingsAdminSerializer(
            settings, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        settings = serializer.save()
        return Response(RewardsSettingsAdminSerializer(settings).data)
