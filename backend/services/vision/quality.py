from __future__ import annotations

from dataclasses import asdict, dataclass

from PIL import Image, ImageFilter, ImageStat

from .config import settings


@dataclass
class QualityReport:
    suitable: bool
    width: int
    height: int
    brightness: float
    contrast: float
    blur_score: float
    issues: list[str]
    capture_guidance: list[str]
    plant_visibility: str = "not_verified"
    affected_area_clarity: str = "unknown"

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_image_quality(image: Image.Image) -> QualityReport:
    width, height = image.size
    gray = image.convert("L")
    stat = ImageStat.Stat(gray)
    brightness = float(stat.mean[0])
    contrast = float(stat.stddev[0])
    # Variance of a Laplacian response is a deterministic focus estimate.
    # It is not a diagnosis and is intentionally configurable per deployment.
    laplacian = gray.filter(
        ImageFilter.Kernel((3, 3), (0, 1, 0, 1, -4, 1, 0, 1, 0), scale=1, offset=128)
    )
    blur_score = float(ImageStat.Stat(laplacian).var[0])

    issues: list[str] = []
    guidance: list[str] = []

    if width < settings.min_width or height < settings.min_height:
        issues.append("resolution_too_low")
        guidance.append(
            f"Move closer or use a higher camera resolution. Minimum recommended size is "
            f"{settings.min_width}×{settings.min_height} pixels."
        )
    if brightness < settings.low_light_threshold:
        issues.append("too_dark")
        guidance.append("Retake the photo in daylight or use a steady light without strong shadows.")
    if brightness > settings.bright_threshold:
        issues.append("overexposed")
        guidance.append("Avoid direct flash or harsh sunlight; keep the affected area evenly lit.")
    if blur_score < settings.blur_threshold:
        issues.append("blurry")
        guidance.append("Hold the phone steady, tap to focus, and keep the affected area close to the camera.")
    if contrast < 12:
        issues.append("low_contrast")
        guidance.append("Use a plain background and capture the symptom from a clearer angle.")

    critical = {"resolution_too_low", "too_dark", "overexposed", "blurry"}
    clarity = "clear" if not critical.intersection(issues) else "insufficient"
    return QualityReport(
        suitable=not bool(critical.intersection(issues)),
        width=width,
        height=height,
        brightness=round(brightness, 2),
        contrast=round(contrast, 2),
        blur_score=round(blur_score, 2),
        issues=issues,
        capture_guidance=guidance,
        affected_area_clarity=clarity,
    )
