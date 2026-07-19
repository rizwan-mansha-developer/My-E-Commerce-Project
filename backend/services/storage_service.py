from __future__ import annotations

import uuid
from pathlib import PurePosixPath

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile

ALLOWED_IMAGE_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)
ALLOWED_VIDEO_TYPES = frozenset(
    {
        "video/mp4",
        "video/webm",
        "video/quicktime",
    }
)
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_VIDEO_BYTES = 40 * 1024 * 1024  # 40 MB
_EXT_BY_CONTENT_TYPE = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "video/mp4": "mp4",
    "video/webm": "webm",
    "video/quicktime": "mov",
}


class StorageService:
    """Upload product media to S3 (prod) or local MEDIA_ROOT (dev)."""

    @staticmethod
    def absolutize_media_url(url: str | None) -> str | None:
        """Prefix PUBLIC_MEDIA_BASE_URL onto relative /media/... paths."""
        if not url:
            return None
        value = url.strip()
        if not value:
            return None
        if value.startswith("http://") or value.startswith("https://"):
            return value
        if value.startswith("/"):
            base = getattr(settings, "PUBLIC_MEDIA_BASE_URL", "").rstrip("/")
            return f"{base}{value}" if base else value
        if value.startswith("media/") or value.startswith("products/"):
            path = value if value.startswith("media/") else f"media/{value}"
            base = getattr(settings, "PUBLIC_MEDIA_BASE_URL", "").rstrip("/")
            return f"{base}/{path}" if base else f"/{path}"
        return value

    @staticmethod
    def _save_upload(
        uploaded: UploadedFile,
        *,
        folder: str,
        allowed_types: frozenset[str],
        max_bytes: int,
        unsupported_message: str,
        too_large_message: str,
    ) -> str:
        content_type = (uploaded.content_type or "").lower().split(";")[0].strip()
        if content_type not in allowed_types:
            raise ValueError(unsupported_message)
        size = getattr(uploaded, "size", None)
        if size is not None and size > max_bytes:
            raise ValueError(too_large_message)
        ext = _EXT_BY_CONTENT_TYPE[content_type]
        original_name = PurePosixPath(uploaded.name or f"upload.{ext}").stem
        safe_stem = (
            "".join(
                ch if ch.isalnum() or ch in "-_" else "-" for ch in original_name
            )[:40]
            or "product"
        )
        key = f"{folder}/{safe_stem}-{uuid.uuid4().hex[:12]}.{ext}"
        saved_name = default_storage.save(key, ContentFile(uploaded.read()))
        url = default_storage.url(saved_name)
        return StorageService.absolutize_media_url(url) or url

    @staticmethod
    def upload_product_image(uploaded: UploadedFile) -> str:
        return StorageService._save_upload(
            uploaded,
            folder="products",
            allowed_types=ALLOWED_IMAGE_TYPES,
            max_bytes=MAX_IMAGE_BYTES,
            unsupported_message="Unsupported image type. Use JPEG, PNG, WebP, or GIF.",
            too_large_message="Image must be 5 MB or smaller.",
        )

    @staticmethod
    def upload_product_video(uploaded: UploadedFile) -> str:
        return StorageService._save_upload(
            uploaded,
            folder="products/videos",
            allowed_types=ALLOWED_VIDEO_TYPES,
            max_bytes=MAX_VIDEO_BYTES,
            unsupported_message="Unsupported video type. Use MP4 or WebM.",
            too_large_message="Video must be 40 MB or smaller.",
        )

    @staticmethod
    def upload_product_media(uploaded: UploadedFile) -> str:
        content_type = (uploaded.content_type or "").lower().split(";")[0].strip()
        if content_type in ALLOWED_VIDEO_TYPES:
            return StorageService.upload_product_video(uploaded)
        return StorageService.upload_product_image(uploaded)
