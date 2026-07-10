from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def _font(size: int = 18):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except Exception:
        return ImageFont.load_default()


def annotate_image(image: Image.Image, regions: list[dict[str, Any]]) -> tuple[bytes | None, bytes | None]:
    if not regions:
        return None, None
    canvas = image.copy().convert("RGB")
    draw = ImageDraw.Draw(canvas, "RGBA")
    width, height = canvas.size
    font = _font(max(12, min(width, height) // 35))
    best_region = None
    best_score = -1.0

    for index, region in enumerate(regions):
        bbox = region.get("bbox") or []
        if len(bbox) != 4:
            continue
        x, y, w, h = [float(value) for value in bbox]
        x1, y1 = int(max(0, x) * width), int(max(0, y) * height)
        x2, y2 = int(min(1, x + w) * width), int(min(1, y + h) * height)
        if x2 <= x1 or y2 <= y1:
            continue
        confidence = float(region.get("confidence") or 0)
        label = str(region.get("label") or "damaged region")
        polygon = region.get("polygon") or []
        polygon_pixels = [
            (int(max(0.0, min(1.0, float(point[0]))) * width), int(max(0.0, min(1.0, float(point[1]))) * height))
            for point in polygon
            if isinstance(point, (list, tuple)) and len(point) == 2
        ]
        if len(polygon_pixels) >= 3:
            draw.polygon(polygon_pixels, fill=(239, 68, 68, 55), outline=(239, 68, 68, 255))
            draw.line(polygon_pixels + [polygon_pixels[0]], fill=(239, 68, 68, 255), width=max(3, width // 220))
        else:
            draw.rectangle((x1, y1, x2, y2), outline=(239, 68, 68, 255), width=max(3, width // 220))
            draw.rectangle((x1, y1, x2, y2), fill=(239, 68, 68, 35))
        text = f"{label} {confidence * 100:.0f}%"
        text_box = draw.textbbox((x1, y1), text, font=font)
        text_h = max(20, text_box[3] - text_box[1] + 8)
        draw.rectangle((x1, max(0, y1 - text_h), min(width, x1 + text_box[2] - text_box[0] + 10), y1), fill=(127, 29, 29, 230))
        draw.text((x1 + 5, max(0, y1 - text_h + 4)), text, fill="white", font=font)
        score = float(region.get("area_fraction") or 0) * max(confidence, 0.01)
        if score > best_score:
            best_score = score
            best_region = (x1, y1, x2, y2)

    annotated_out = io.BytesIO()
    canvas.save(annotated_out, format="JPEG", quality=91, optimize=True)

    zoom_bytes = None
    if best_region:
        x1, y1, x2, y2 = best_region
        pad_x = max(20, int((x2 - x1) * 0.18))
        pad_y = max(20, int((y2 - y1) * 0.18))
        crop = image.crop((max(0, x1 - pad_x), max(0, y1 - pad_y), min(width, x2 + pad_x), min(height, y2 + pad_y)))
        zoom_out = io.BytesIO()
        crop.convert("RGB").save(zoom_out, format="JPEG", quality=93, optimize=True)
        zoom_bytes = zoom_out.getvalue()
    return annotated_out.getvalue(), zoom_bytes
