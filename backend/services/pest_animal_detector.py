"""Backward-compatible wrapper for AgriSarthi Pest Guard.

The old heuristic detector has been replaced by a neural-network-ready pipeline.
The public function name stays the same so main.py and frontend continue working.
"""

from __future__ import annotations

from typing import Any

from services.nn_pest_classifier import classify_pest_image


def analyze_crop_frame(image_bytes: bytes, filename: str = "camera-frame.jpg", crop: str | None = None, mode: str = "rgb") -> dict[str, Any]:
    result = classify_pest_image(image_bytes=image_bytes, crop=crop, mode=mode)
    result["filename"] = filename
    return result
