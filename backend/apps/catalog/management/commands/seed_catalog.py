from __future__ import annotations
from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.catalog.models import Category, Product, ProductImage, ProductVariant

class Command(BaseCommand):
    help = "Seed demo catalog categories and products for storefront development."

    def handle(self, *args, **options) -> None:
        categories_data = [
            {
                "name": "New In",
                "slug": "new-in",
                "description": "Just landed styles for the season.",
                "sort_order": 1,
                "accent": False,
                "hero_title": "Basics",
                "hero_subtitle": "Hot summer ft. ready to wear collection",
                "hero_images": [
                    "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=800&q=80",
                    "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=800&q=80",
                    "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=800&q=80",
                ],
            },
            {
                "name": "Ready to Wear",
                "slug": "rtw",
                "description": "Complete looks ready for everyday luxury.",
                "sort_order": 2,
                "accent": False,
                "hero_title": "Monochrome Edit",
                "hero_subtitle": "Timeless silhouettes in black & white",
                "hero_images": [
                    "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=600&auto=format&fit=crop&q=60",
                    "https://images.unsplash.com/photo-1682745230951-8a5aa9a474a0?q=80&w=687&auto=format&fit=crop",
                    "https://images.unsplash.com/photo-1590874103328-eac38a683ce7?w=600&auto=format&fit=crop&q=60",
                ],
            },
            {
                "name": "Fabrics",
                "slug": "fabrics",
                "description": "Premium cloth and soft suiting textiles.",
                "sort_order": 3,
                "accent": False,
                "hero_title": "Signature",
                "hero_subtitle": "Embroidered pieces crafted with care",
                "hero_images": [
                    "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&q=80",
                    "https://images.unsplash.com/photo-1581044777550-4cfa60707c03?w=800&q=80",
                    "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=800&q=80",
                ],
            },
            {
                "name": "Sale",
                "slug": "sale",
                "description": "Limited-time reductions on signature pieces.",
                "sort_order": 4,
                "accent": True,
                "hero_title": "",
                "hero_subtitle": "",
                "hero_images": [],
            },
            {
                "name": "Now Happening",
                "slug": "happening",
                "description": "Campaigns and editorial drops happening now.",
                "sort_order": 5,
                "accent": False,
                "hero_title": "",
                "hero_subtitle": "",
                "hero_images": [],
            },
        ]
        categories: dict[str, Category] = {}
        for item in categories_data:
            category, _ = Category.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "name": item["name"],
                    "description": item["description"],
                    "sort_order": item["sort_order"],
                    "show_in_nav": True,
                    "accent": item["accent"],
                    "hero_title": item["hero_title"],
                    "hero_subtitle": item["hero_subtitle"],
                    "hero_images": item["hero_images"],
                    "is_active": True,
                },
            )
            categories[item["slug"]] = category
        products = [
            {
                "title": "Silk Slip Dress",
                "slug": "silk-slip-dress",
                "category": "new-in",
                "is_top_pick": True,
                "is_bestseller": True,
                "featured_sort": 1,
                "description": (
                    "Bias-cut silk with hand-finished seams. A fluid silhouette "
                    "designed for evening ease and all-day grace."
                ),
                "base_price": Decimal("12500.00"),
                "compare_at_price": Decimal("18900.00"),
                "video_url": "https://cdn.coverr.co/videos/coverr-woman-in-a-silk-dress-1576/1080p.mp4",
                "images": [
                    "https://images.unsplash.com/photo-1595777457583-95e059d581bb?w=800&q=80",
                    "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=800&q=80",
                ],
                "variants": [
                    ("Dusty Pink", "DR-SSD-DP", 12),
                    ("Champagne", "DR-SSD-CH", 8),
                ],
            },
            {
                "title": "Cashmere Wrap Coat",
                "slug": "cashmere-wrap-coat",
                "category": "rtw",
                "is_top_pick": True,
                "is_bestseller": True,
                "featured_sort": 2,
                "description": (
                    "Double-faced cashmere with a relaxed wrap closure. "
                    "Crafted for Lahore winters and layered luxury."
                ),
                "base_price": Decimal("28900.00"),
                "compare_at_price": None,
                "video_url": "https://cdn.coverr.co/videos/coverr-fashion-model-posing-1574/1080p.mp4",
                "images": [
                    "https://images.unsplash.com/photo-1738653926836-9f11034d7d0e?q=80&w=735&auto=format&fit=crop",
                    "https://images.unsplash.com/photo-1738653926597-6923cde1b38b?w=600&auto=format&fit=crop&q=60",
                ],
                "variants": [
                    ("Stone", "DR-CWC-ST", 6),
                    ("Ivory", "DR-CWC-IV", 4),
                ],
            },
            {
                "title": "Pearl Embroidered Blouse",
                "slug": "pearl-embroidered-blouse",
                "category": "fabrics",
                "is_top_pick": True,
                "is_bestseller": False,
                "featured_sort": 3,
                "description": (
                    "Fine cotton voile with hand-applied pearl embroidery. "
                    "Each motif takes forty minutes to complete."
                ),
                "base_price": Decimal("8900.00"),
                "compare_at_price": Decimal("12900.00"),
                "video_url": "",
                "images": [
                    "https://images.unsplash.com/photo-1600857062241-98e5dba7f214?w=600&auto=format&fit=crop&q=60",
                    "https://images.unsplash.com/photo-1600857125164-499a823272b4?w=600&auto=format&fit=crop&q=60",
                ],
                "variants": [
                    ("Pearl White", "DR-PEB-PW", 15),
                    ("Blush", "DR-PEB-BL", 10),
                ],
            },
            {
                "title": "Linen Wide-Leg Trousers",
                "slug": "linen-wide-leg-trousers",
                "category": "sale",
                "is_top_pick": False,
                "is_bestseller": True,
                "featured_sort": 4,
                "description": (
                    "Belgian linen with a high waist and fluid wide leg. "
                    "Breathable tailoring for premium everyday wear."
                ),
                "base_price": Decimal("1999.00"),
                "compare_at_price": Decimal("4999.00"),
                "video_url": "",
                "images": [
                    "https://images.unsplash.com/photo-1594633313593-bab3825d0caf?w=800&q=80",
                ],
                "variants": [
                    ("Natural", "DR-LWT-NA", 20),
                    ("Olive", "DR-LWT-OL", 14),
                ],
            },
        ]
        created_count = 0
        for item in products:
            product, created = Product.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "title": item["title"],
                    "description": item["description"],
                    "base_price": item["base_price"],
                    "compare_at_price": item.get("compare_at_price"),
                    "video_url": item["video_url"],
                    "image_urls": item["images"],
                    "category": categories[item["category"]],
                    "is_top_pick": item["is_top_pick"],
                    "is_bestseller": item["is_bestseller"],
                    "featured_sort": item["featured_sort"],
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
            ProductImage.objects.filter(product=product).delete()
            for index, url in enumerate(item["images"]):
                ProductImage.objects.create(
                    product=product,
                    url=url,
                    alt_text=item["title"],
                    sort_order=index,
                )
            for color, sku, stock in item["variants"]:
                ProductVariant.objects.update_or_create(
                    sku=sku,
                    defaults={
                        "product": product,
                        "color": color,
                        "quantity_in_stock": stock,
                        "safety_threshold": 3,
                        "is_active": True,
                    },
                )
        self.stdout.write(
            self.style.SUCCESS(
                f"Catalog seeded: {len(categories_data)} categories, "
                f"{len(products)} products ({created_count} new)."
            )
        )
