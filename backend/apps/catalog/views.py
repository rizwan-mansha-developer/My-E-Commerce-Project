from __future__ import annotations
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsSuperUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from dj_rest_auth.jwt_auth import JWTCookieAuthentication
from apps.catalog.models import Category, Product, ProductVariant
from apps.catalog.serializers import (
    CategoryListResponseSerializer,
    ProductDetailSerializer,
    ProductListResponseSerializer,
    WishlistStateSerializer,
    WishlistToggleResponseSerializer,
    WishlistToggleSerializer,
)
from config.schema import ApiErrorSerializer
from services.storage_service import StorageService
from services.wishlist_service import WishlistService

class CategoryListView(APIView):
    """Active storefront collections for nav and section filters."""
    authentication_classes: list = []
    permission_classes: list = []
    @extend_schema(
        tags=["Catalog"],
        operation_id="catalog_category_list",
        summary="List active categories",
        responses={200: CategoryListResponseSerializer},
    )

    def get(self, request: Request) -> Response:
        categories = Category.objects.filter(is_active=True).order_by(
            "sort_order", "name"
        )
        payload = {"results": categories, "count": categories.count()}
        return Response(CategoryListResponseSerializer(payload).data)

class ProductListView(APIView):
    """Active catalog feed for SSR product listing pages."""
    authentication_classes: list = []
    permission_classes: list = []
    @extend_schema(
        tags=["Catalog"],
        operation_id="catalog_product_list",
        summary="List active products",
        description=(
            "Returns active catalog products. Optional filters: "
            "`category` (slug), `top_pick=true`, `bestseller=true`, "
            "`sort=newest|price_asc|price_desc|featured`."
        ),
        responses={200: ProductListResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        products = (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related("gallery_images", "variants")
        )
        category_slug = request.query_params.get("category")
        if category_slug:
            products = products.filter(category__slug=category_slug)
        if request.query_params.get("top_pick") == "true":
            products = products.filter(is_top_pick=True)
        if request.query_params.get("bestseller") == "true":
            products = products.filter(is_bestseller=True)

        sort = request.query_params.get("sort", "newest")
        if sort == "price_asc":
            products = products.order_by("base_price", "-created_at")
        elif sort == "price_desc":
            products = products.order_by("-base_price", "-created_at")
        elif sort == "featured":
            products = products.order_by("featured_sort", "-created_at")
        else:
            products = products.order_by("-created_at")

        serializer = ProductListResponseSerializer(
            {"results": products, "count": products.count()}
        )
        return Response(serializer.data)

class ProductDetailView(APIView):
    """Single product by slug for PDP SSR."""
    authentication_classes: list = []
    permission_classes: list = []
    @extend_schema(
        tags=["Catalog"],
        operation_id="catalog_product_detail",
        summary="Get product by slug",
        description="Full PDP payload including variants, gallery images, and video URL.",
        responses={
            200: ProductDetailSerializer,
            404: ApiErrorSerializer,
        },
    )

    def get(self, request: Request, slug: str) -> Response:
        product = (
            Product.objects.filter(slug=slug, is_active=True)
            .select_related("category")
            .prefetch_related(
                "gallery_images",
                Prefetch(
                    "variants",
                    queryset=ProductVariant.objects.filter(is_active=True),
                ),
            )
            .first()
        )
        if product is None:
            return Response(
                {"detail": "Product not found.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ProductDetailSerializer(product)
        return Response(serializer.data)

class ProductImageUploadView(APIView):
    """Staff-only multipart upload to S3 (or local media in development)."""
    permission_classes = [IsSuperUser]
    parser_classes = [MultiPartParser, FormParser]
    @extend_schema(
        tags=["Admin"],
        summary="Upload product image",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {"file": {"type": "string", "format": "binary"}},
                "required": ["file"],
            }
        },
        responses={
            201: inline_serializer(
                name='ProductImageUploadResponse',
                fields={'url': serializers.URLField()},
            )
        },
    )

    def post(self, request: Request) -> Response:
        uploaded = request.FILES.get("file")
        if uploaded is None:
            return Response(
                {"detail": "Missing file field.", "code": "invalid_request"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            url = StorageService.upload_product_image(uploaded)
        except ValueError as exc:
            return Response(
                {"detail": str(exc), "code": "invalid_request"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"url": url}, status=status.HTTP_201_CREATED)

class WishlistView(APIView):
    """List guest or authenticated favorites (session cookie, no login)."""
    authentication_classes: list = []
    permission_classes: list = []
    @extend_schema(
        tags=["Wishlist"],
        summary="Get wishlist state",
        description=(
            "Returns favorited product IDs and items. "
            "Uses session cookie for guests — send credentials on cross-origin requests."
        ),
        responses={200: WishlistStateSerializer},
    )

    def get(self, request: Request) -> Response:
        owner = WishlistService.resolve_owner(request)
        products = WishlistService.list_products(owner=owner)
        product_ids = WishlistService.favorited_product_ids(owner=owner)
        payload = {
            "product_ids": product_ids,
            "count": len(product_ids),
            "items": products,
        }
        serializer = WishlistStateSerializer(payload)
        return Response(serializer.data)

class WishlistToggleView(APIView):
    """One-tap heart toggle — adds or removes a favorite instantly."""
    authentication_classes: list = []
    permission_classes: list = []
    @extend_schema(
        tags=["Wishlist"],
        summary="Toggle favorite",
        request=WishlistToggleSerializer,
        responses={
            200: WishlistToggleResponseSerializer,
            404: ApiErrorSerializer,
        },
    )

    def post(self, request: Request) -> Response:
        serializer = WishlistToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        owner = WishlistService.resolve_owner(request)
        try:
            result = WishlistService.toggle_favorite(
                owner=owner,
                product_id=serializer.validated_data["product_id"],
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc), "code": "product_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        response = WishlistToggleResponseSerializer(
            {
                "favorited": result.favorited,
                "product_id": result.product_id,
                "total_count": result.total_count,
            }
        )
        return Response(response.data, status=status.HTTP_200_OK)

class WishlistMergeView(APIView):
    """Merge guest session favorites into authenticated account after login."""
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]
    @extend_schema(
        tags=["Wishlist"],
        summary="Merge session wishlist into user account",
        responses={200: WishlistStateSerializer},
    )

    def post(self, request: Request) -> Response:
        session_key = request.session.session_key
        if session_key:
            WishlistService.merge_session_into_user(
                session_key=session_key,
                user=request.user,
            )
        owner = WishlistService.resolve_owner(request)
        products = WishlistService.list_products(owner=owner)
        product_ids = WishlistService.favorited_product_ids(owner=owner)
        payload = {
            "product_ids": product_ids,
            "count": len(product_ids),
            "items": products,
        }
        return Response(WishlistStateSerializer(payload).data)
