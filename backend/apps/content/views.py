from __future__ import annotations

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSuperUser
from apps.content.models import Article, ArticleStatus
from apps.content.serializers import ArticleAdminSerializer, ArticlePublicSerializer


class ArticleListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Content"], summary="List published & coming-soon articles")
    def get(self, request: Request) -> Response:
        articles = Article.objects.filter(
            status__in=[ArticleStatus.PUBLISHED, ArticleStatus.COMING_SOON]
        )
        return Response(
            {
                "results": ArticlePublicSerializer(articles, many=True).data,
                "count": articles.count(),
            }
        )


class ArticleDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Content"], summary="Article detail")
    def get(self, request: Request, slug: str) -> Response:
        article = Article.objects.filter(
            slug=slug,
            status__in=[ArticleStatus.PUBLISHED, ArticleStatus.COMING_SOON],
        ).first()
        if article is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ArticlePublicSerializer(article).data)


@extend_schema_view(
    get=extend_schema(tags=["Admin"], summary="List articles (admin)"),
    post=extend_schema(tags=["Admin"], summary="Create article"),
)
class ArticleAdminListView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request: Request) -> Response:
        articles = Article.objects.all()
        return Response(
            {
                "results": ArticleAdminSerializer(articles, many=True).data,
                "count": articles.count(),
            }
        )

    def post(self, request: Request) -> Response:
        serializer = ArticleAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        article = serializer.save()
        return Response(
            ArticleAdminSerializer(article).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(tags=["Admin"], summary="Get article"),
    patch=extend_schema(tags=["Admin"], summary="Update article"),
    delete=extend_schema(tags=["Admin"], summary="Delete article"),
)
class ArticleAdminDetailView(APIView):
    permission_classes = [IsSuperUser]

    def _get(self, article_id: str) -> Article | None:
        return Article.objects.filter(id=article_id).first()

    def get(self, request: Request, article_id: str) -> Response:
        article = self._get(article_id)
        if article is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ArticleAdminSerializer(article).data)

    def patch(self, request: Request, article_id: str) -> Response:
        article = self._get(article_id)
        if article is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ArticleAdminSerializer(article, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        article = serializer.save()
        return Response(ArticleAdminSerializer(article).data)

    def delete(self, request: Request, article_id: str) -> Response:
        article = self._get(article_id)
        if article is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
