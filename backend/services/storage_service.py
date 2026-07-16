from __future__ import annotations
import uuid
from pathlib import PurePosixPath
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
ALLOWED_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
_EXT_BY_CONTENT_TYPE = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}

class StorageService:
    """Upload product images to S3 (prod) or local MEDIA_ROOT (dev)."""
    @staticmethod
    def upload_product_image(uploaded: UploadedFile) -> str:
        content_type = (uploaded.content_type or "").lower().split(";")[0].strip()
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError(
                "Unsupported image type. Use JPEG, PNG, WebP, or GIF."
            )
        size = getattr(uploaded, "size", None)
        if size is not None and size > MAX_UPLOAD_BYTES:
            raise ValueError("Image must be 5 MB or smaller.")
        ext = _EXT_BY_CONTENT_TYPE[content_type]
        original_name = PurePosixPath(uploaded.name or f"upload.{ext}").stem
        safe_stem = "".join(
            ch if ch.isalnum() or ch in "-_" else "-" for ch in original_name
        )[:40] or "product"
        key = f"products/{safe_stem}-{uuid.uuid4().hex[:12]}.{ext}"
        saved_name = default_storage.save(key, ContentFile(uploaded.read()))
        url = default_storage.url(saved_name)
        # Local FileSystemStorage returns relative /media/... — make absolute for storefront.
        if url.startswith("/"):
            base = getattr(settings, "PUBLIC_MEDIA_BASE_URL", "").rstrip("/")
            if base:
                return f"{base}{url}"
        return url
