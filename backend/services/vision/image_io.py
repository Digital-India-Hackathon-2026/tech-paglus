from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

from .config import settings

try:  # Optional HEIC/HEIF support.
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIF_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    HEIF_AVAILABLE = False


class VisionImageError(ValueError):
    pass


@dataclass
class DecodedImage:
    image: Image.Image
    detected_format: str
    mime_type: str
    sha256: str
    original_size: int


MIME_BY_FORMAT = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "HEIF": "image/heif",
    "HEIC": "image/heic",
}


def read_limited(stream: BinaryIO, limit: int | None = None) -> bytes:
    limit = limit or settings.max_upload_bytes
    data = stream.read(limit + 1)
    if len(data) > limit:
        raise VisionImageError(f"Image is larger than the {settings.max_upload_mb} MB limit.")
    if not data:
        raise VisionImageError("The uploaded image is empty.")
    return data


def decode_image(data: bytes) -> DecodedImage:
    if len(data) > settings.max_upload_bytes:
        raise VisionImageError(f"Image is larger than the {settings.max_upload_mb} MB limit.")
    try:
        with Image.open(io.BytesIO(data)) as opened:
            detected_format = (opened.format or "").upper()
            if opened.width * opened.height > settings.max_pixels:
                raise VisionImageError(
                    f"Image dimensions are too large. Maximum allowed pixel count is {settings.max_pixels:,}."
                )
            if detected_format not in MIME_BY_FORMAT:
                raise VisionImageError("Unsupported image content. Use JPEG, PNG, WEBP, HEIC or HEIF.")
            if detected_format in {"HEIC", "HEIF"} and not HEIF_AVAILABLE:
                raise VisionImageError(
                    "HEIC/HEIF support is not installed. Install pillow-heif or convert the image to JPEG."
                )
            opened.verify()
        with Image.open(io.BytesIO(data)) as opened:
            oriented = ImageOps.exif_transpose(opened)
            rgb = oriented.convert("RGB")
    except VisionImageError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise VisionImageError("The file is not a valid or readable image.") from exc

    return DecodedImage(
        image=rgb,
        detected_format=detected_format,
        mime_type=MIME_BY_FORMAT[detected_format],
        sha256=hashlib.sha256(data).hexdigest(),
        original_size=len(data),
    )


def sanitized_jpeg_bytes(image: Image.Image, max_edge: int = 2200, quality: int = 90) -> bytes:
    clean = image.copy()
    clean.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    clean.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()


def safe_original_name(filename: str | None) -> str:
    name = Path(filename or "crop-image.jpg").name
    allowed = "".join(ch for ch in name if ch.isalnum() or ch in {"-", "_", ".", " "}).strip()
    return allowed[:120] or "crop-image.jpg"
