from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from apps.content.models import Article, ArticleStatus
from apps.promotions.models import (
    DiscountType,
    RewardsSettings,
    SeasonalCampaign,
)


class Command(BaseCommand):
    help = "Seed a sample seasonal campaign and Coming soon articles."

    def handle(self, *args, **options) -> None:
        RewardsSettings.load()
        now = timezone.now()

        campaign, created = SeasonalCampaign.objects.get_or_create(
            slug="summer-edit",
            defaults={
                "name": "Summer Edit",
                "description": "Light layers and festive ready-to-wear.",
                "badge_label": "Summer sale",
                "banner_text": "15% off your bag at checkout — Summer Edit is live.",
                "discount_type": DiscountType.PERCENT,
                "discount_value": 15,
                "starts_at": now - timedelta(days=1),
                "ends_at": now + timedelta(days=30),
                "is_active": True,
                "applies_sitewide": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Exists'}: campaign {campaign.name}"
            )
        )

        samples = [
            {
                "title": "How we finish every Darling bag",
                "excerpt": "A quiet look at stitching, lining, and the last polish.",
                "status": ArticleStatus.COMING_SOON,
                "cover_image_url": (
                    "https://images.unsplash.com/photo-1590874103328-eac38a683ce7?w=1200&q=80"
                ),
            },
            {
                "title": "Eid styling notes",
                "excerpt": "Soft neutrals, one statement bag, and breathable layers.",
                "status": ArticleStatus.COMING_SOON,
                "cover_image_url": (
                    "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=1200&q=80"
                ),
            },
            {
                "title": "Why COD still matters",
                "excerpt": "Trust, touch, and why we launched with cash on delivery.",
                "status": ArticleStatus.PUBLISHED,
                "body": (
                    "Darling launched with Cash on Delivery so you can see your "
                    "piece before you pay. Online wallets are on the way — until "
                    "then, COD keeps checkout simple across Pakistan."
                ),
                "cover_image_url": (
                    "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=1200&q=80"
                ),
            },
        ]

        for index, sample in enumerate(samples):
            slug = slugify(sample["title"])
            article, art_created = Article.objects.get_or_create(
                slug=slug,
                defaults={
                    **sample,
                    "sort_order": index,
                    "published_at": now if sample["status"] == ArticleStatus.PUBLISHED else None,
                },
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"{'Created' if art_created else 'Exists'}: article {article.title}"
                )
            )
