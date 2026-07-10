from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if not value:
        return default.resolve()
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path.resolve()


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class VisionSettings:
    model_dir: Path = _path_from_env("VISION_MODEL_DIR", BACKEND_ROOT / "model_artifacts")
    registry_path: Path = _path_from_env("VISION_MODEL_REGISTRY", BACKEND_ROOT / "model_registry.json")
    storage_dir: Path = _path_from_env("VISION_STORAGE_DIR", BACKEND_ROOT / "storage" / "vision")
    database_path: Path = _path_from_env("VISION_DATABASE_PATH", BACKEND_ROOT / "vision.db")
    treatment_kb_path: Path = _path_from_env(
        "VISION_TREATMENT_KB", BACKEND_ROOT / "knowledge_base" / "treatments.json"
    )
    dataset_candidate_dir: Path = _path_from_env(
        "VISION_DATASET_CANDIDATE_DIR", BACKEND_ROOT / "storage" / "dataset_candidates"
    )
    max_upload_mb: int = int(os.getenv("VISION_MAX_UPLOAD_MB", "12"))
    max_images_per_session: int = int(os.getenv("VISION_MAX_IMAGES_PER_SESSION", "8"))
    request_timeout_seconds: int = int(os.getenv("VISION_REQUEST_TIMEOUT_SECONDS", "90"))
    rate_limit_per_minute: int = int(os.getenv("VISION_RATE_LIMIT_PER_MINUTE", "20"))
    retention_hours_without_consent: int = int(os.getenv("VISION_TEMP_RETENTION_HOURS", "24"))
    retention_days_with_consent: int = int(os.getenv("VISION_CONSENT_RETENTION_DAYS", "30"))
    disease_threshold: float = float(os.getenv("VISION_DISEASE_THRESHOLD", "0.55"))
    pest_threshold: float = float(os.getenv("VISION_PEST_THRESHOLD", "0.40"))
    crop_threshold: float = float(os.getenv("VISION_CROP_THRESHOLD", "0.60"))
    low_confidence_threshold: float = float(os.getenv("VISION_LOW_CONFIDENCE_THRESHOLD", "0.45"))
    min_width: int = int(os.getenv("VISION_MIN_WIDTH", "320"))
    max_pixels: int = int(os.getenv("VISION_MAX_PIXELS", "40000000"))
    min_height: int = int(os.getenv("VISION_MIN_HEIGHT", "320"))
    blur_threshold: float = float(os.getenv("VISION_BLUR_THRESHOLD", "80"))
    low_light_threshold: float = float(os.getenv("VISION_LOW_LIGHT_THRESHOLD", "35"))
    bright_threshold: float = float(os.getenv("VISION_BRIGHT_THRESHOLD", "235"))
    enable_weather_context: bool = _bool_env("VISION_ENABLE_WEATHER_CONTEXT", True)
    allow_unverified_commercial_treatments: bool = _bool_env(
        "VISION_ALLOW_UNVERIFIED_COMMERCIAL_TREATMENTS", False
    )
    inference_device: str = os.getenv("VISION_INFERENCE_DEVICE", "auto").strip().lower()

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = VisionSettings()
