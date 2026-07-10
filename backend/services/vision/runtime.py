from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from PIL import Image

from models.schemas import LocationData
from services.weather_api import get_weather_forecast

from .adapters import BaseAdapter, build_adapter
from .config import settings
from .database import expiry_for_consent, init_vision_db, save_analysis
from .image_io import DecodedImage, decode_image, safe_original_name, sanitized_jpeg_bytes
from .quality import evaluate_image_quality
from .recommendations import build_recommendations
from .registry import ModelRecord, load_registry
from .render import annotate_image
from .storage import cleanup_expired, save_bytes


logger = logging.getLogger("agrisarthi.vision")

CAUSE_PREFIXES = {
    "fungal": "fungal",
    "bacterial": "bacterial",
    "viral": "viral",
    "pest": "pest-related",
    "insect": "pest-related",
    "nutrient": "nutrient-related",
    "deficiency": "nutrient-related",
    "environmental": "environmental",
    "physical": "environmental",
    "postharvest": "environmental",
    "post_harvest": "environmental",
}


def _humanize(label: str) -> str:
    return label.replace("__", " - ").replace("_", " ").strip().title()


def _is_healthy_label(label: str) -> bool:
    normalized = label.lower().replace("-", "_").replace(" ", "_")
    tokens = {token for token in normalized.replace("__", "_").split("_") if token}
    return bool(tokens & {"healthy", "normal", "unaffected"})


def _cause_for_label(label: str) -> str:
    lower = label.lower()
    for prefix, category in CAUSE_PREFIXES.items():
        if lower.startswith(prefix + "__") or prefix in lower.split("_")[:2]:
            return category
    return "unknown"


def _severity_from_percentage(value: float | None, method: str = "segmented_pixels_divided_by_image_pixels") -> dict[str, Any]:
    if value is None:
        return {
            "level": "unknown",
            "affected_percentage": None,
            "method": "unavailable_without_segmentation",
            "disclaimer": "Severity needs a compatible segmentation model and is not inferred from classification confidence.",
        }
    if value <= 0.5:
        level = "healthy"
    elif value < 5:
        level = "very_low"
    elif value < 15:
        level = "low"
    elif value < 35:
        level = "moderate"
    elif value < 60:
        level = "high"
    else:
        level = "severe"
    return {
        "level": level,
        "affected_percentage": round(value, 2),
        "method": method,
        "disclaimer": "This is an image-based estimate and may not represent the complete plant or field.",
    }


def _parse_crop_part(label: str) -> dict[str, str]:
    parts = [part.strip() for part in label.split("__")]
    keys = ["crop", "plant_part", "growth_stage", "harvest_stage", "image_scope"]
    parsed = {key: value for key, value in zip(keys, parts) if value}
    return parsed


def _localized_farmer_message(status: str, diagnosis: str, language: str) -> str:
    lang = (language or "en").lower()
    messages = {
        "en": {
            "model_unavailable": "Image quality was checked, but trained crop, disease, pest, and damage-segmentation weights are not installed. No diagnosis has been generated.",
            "needs_better_images": "The images are not clear enough for a reliable analysis. Please retake them using the guidance shown.",
            "uncertain": "The condition could not be identified reliably. Upload more views or contact an agriculture expert.",
            "completed": f"The strongest image evidence is {diagnosis}. Review confidence, severity, and safety warnings before acting.",
        },
        "te": {
            "model_unavailable": "చిత్ర నాణ్యతను పరిశీలించాం, కానీ శిక్షణ పొందిన పంట, వ్యాధి, పురుగు మరియు నష్టం విభజన మోడళ్లు అందుబాటులో లేవు. ఎలాంటి నిర్ధారణ ఇవ్వలేదు.",
            "needs_better_images": "నమ్మదగిన విశ్లేషణకు చిత్రాలు స్పష్టంగా లేవు. చూపిన సూచనల ప్రకారం మళ్లీ ఫోటోలు తీయండి.",
            "uncertain": "ఈ సమస్యను నమ్మదగిన విధంగా గుర్తించలేకపోయాం. మరిన్ని కోణాల నుంచి చిత్రాలు అప్‌లోడ్ చేయండి లేదా వ్యవసాయ నిపుణుడిని సంప్రదించండి.",
            "completed": f"చిత్రంలో బలమైన సూచన {diagnosis}. చర్యకు ముందు నమ్మకం, తీవ్రత మరియు భద్రతా హెచ్చరికలను పరిశీలించండి.",
        },
        "hi": {
            "model_unavailable": "चित्र की गुणवत्ता जाँची गई, लेकिन प्रशिक्षित फसल, रोग, कीट और क्षति-विभाजन मॉडल उपलब्ध नहीं हैं। कोई निदान नहीं बनाया गया।",
            "needs_better_images": "विश्वसनीय विश्लेषण के लिए चित्र पर्याप्त स्पष्ट नहीं हैं। दिए गए निर्देशों के अनुसार फिर से फोटो लें।",
            "uncertain": "स्थिति की विश्वसनीय पहचान नहीं हो सकी। अधिक कोणों से चित्र अपलोड करें या कृषि विशेषज्ञ से संपर्क करें।",
            "completed": f"चित्र में सबसे मजबूत संकेत {diagnosis} है। कार्रवाई से पहले विश्वास, गंभीरता और सुरक्षा चेतावनियाँ देखें।",
        },
    }
    selected = messages.get(lang, messages["en"])
    return selected.get(status, messages["en"]["uncertain"])


def _parse_pest(label: str, confidence: float, bbox: list[float]) -> dict[str, Any]:
    parts = [part for part in label.split("__") if part]
    name = parts[0] if parts else label
    lifecycle = parts[1] if len(parts) > 1 and parts[1] in {"egg", "larva", "nymph", "adult"} else "not_visually_determined"
    damage_index = 2 if lifecycle != "not_visually_determined" else 1
    damage_type = (
        _humanize("__".join(parts[damage_index:]))
        if len(parts) > damage_index
        else "Damage type requires confirmation from the crop-pest knowledge base"
    )
    return {
        "name": _humanize(name),
        "raw_label": label,
        "confidence": round(float(confidence), 4),
        "count": 1,
        "bbox": bbox,
        "crop_part": "not_determined",
        "damage_type": damage_type,
        "lifecycle_stage": lifecycle,
        "directly_visible": True,
        "detection_basis": "object_detection",
    }


@dataclass
class InputImage:
    filename: str
    data: bytes


class VisionRuntime:
    def __init__(self):
        self.registry: dict[str, ModelRecord] = {}
        self.adapters: dict[str, BaseAdapter] = {}
        self.statuses: dict[str, dict[str, Any]] = {}
        self._inference_lock = threading.Lock()
        self.initialized = False

    def initialize(self) -> None:
        settings.model_dir.mkdir(parents=True, exist_ok=True)
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        init_vision_db()
        cleanup_expired()
        self.registry = load_registry()
        self.adapters = {}
        self.statuses = {}
        for key, record in self.registry.items():
            adapter = build_adapter(record)
            status = adapter.load()
            self.adapters[key] = adapter
            self.statuses[key] = {
                **record.public_info(),
                "ready": status.ready,
                "message": status.message,
            }
        self.initialized = True

    def ensure_initialized(self) -> None:
        if not self.initialized:
            self.initialize()

    def model_info(self) -> dict[str, Any]:
        self.ensure_initialized()
        ready_count = sum(1 for item in self.statuses.values() if item.get("ready"))
        return {
            "development_mode": ready_count == 0,
            "ready_models": ready_count,
            "configured_models": len(self.statuses),
            "models": list(self.statuses.values()),
            "registry_file": settings.registry_path.name,
            "model_directory": settings.model_dir.name,
        }

    def _predict(self, key: str, image: Image.Image) -> dict[str, Any]:
        adapter = self.adapters.get(key)
        if not adapter or not adapter.ready:
            return {"ready": False, "predictions": [], "detections": [], "regions": []}
        with self._inference_lock:
            return adapter.predict(image)

    def _weather_context(self, latitude: float | None, longitude: float | None, location: str) -> dict[str, Any] | None:
        if not settings.enable_weather_context or latitude is None or longitude is None:
            return None
        try:
            weather = get_weather_forecast(
                LocationData(name=location or "Farmer field", latitude=latitude, longitude=longitude)
            )
            return weather.data if weather.data else {"message": weather.message}
        except Exception as exc:
            return {"message": f"Weather context unavailable: {exc}"}

    def _analyze_one(
        self,
        analysis_id: str,
        source: InputImage,
        *,
        crop: str,
        plant_part: str,
        growth_stage: str,
        harvest_stage: str,
        consent: bool,
    ) -> dict[str, Any]:
        image_id = str(uuid4())
        decoded: DecodedImage = decode_image(source.data)
        quality = evaluate_image_quality(decoded.image)
        original_name = safe_original_name(source.filename)
        image_result: dict[str, Any] = {
            "image_id": image_id,
            "original_name": original_name,
            "mime_type": decoded.mime_type,
            "sha256": decoded.sha256,
            "quality": quality.to_dict(),
            "crop": crop if crop and crop != "auto" else "unknown",
            "plant_part": plant_part if plant_part and plant_part != "auto" else "unknown",
            "growth_stage": growth_stage if growth_stage and growth_stage != "auto" else "unknown",
            "harvest_stage": harvest_stage if harvest_stage and harvest_stage != "auto" else "unknown",
            "image_scope": "unknown",
            "diseases": [],
            "health_assessment": None,
            "pests": [],
            "damage_regions": [],
            "severity": _severity_from_percentage(None),
            "paths": {},
            "warnings": [],
        }

        sanitized = sanitized_jpeg_bytes(decoded.image)
        save_bytes(analysis_id, f"{image_id}-original.jpg", sanitized)
        image_result["paths"]["original"] = f"{image_id}-original.jpg"
        image_result["urls"] = {
            "original": f"/api/vision/file/{analysis_id}/{image_id}-original.jpg",
            "annotated": None,
            "zoom": None,
        }

        if not quality.suitable:
            image_result["warnings"].append(
                "Image quality is insufficient. No disease or pest diagnosis was attempted."
            )
            return image_result

        crop_output = self._predict("crop_part_classifier", decoded.image)
        crop_predictions = crop_output.get("predictions", [])
        if crop_predictions:
            top_crop = crop_predictions[0]
            if float(top_crop.get("confidence", 0)) >= settings.crop_threshold:
                parsed = _parse_crop_part(str(top_crop.get("label", "")))
                if crop == "auto" or not crop:
                    image_result["crop"] = _humanize(parsed.get("crop", "unknown"))
                if plant_part == "auto" or not plant_part:
                    image_result["plant_part"] = _humanize(parsed.get("plant_part", "unknown"))
                if growth_stage == "auto" or not growth_stage:
                    image_result["growth_stage"] = _humanize(parsed.get("growth_stage", "unknown"))
                if harvest_stage == "auto" or not harvest_stage:
                    image_result["harvest_stage"] = parsed.get("harvest_stage", "unknown")
                image_result["image_scope"] = parsed.get("image_scope", "unknown")
                image_result["quality"]["plant_visibility"] = "model_confirmed"
                image_result["crop_prediction"] = {
                    "label": top_crop.get("label"),
                    "confidence": round(float(top_crop.get("confidence", 0)), 4),
                    "alternatives": crop_predictions[1:3],
                }
            else:
                image_result["quality"]["plant_visibility"] = "low_confidence"
        elif self.statuses.get("crop_part_classifier", {}).get("ready"):
            image_result["quality"]["plant_visibility"] = "not_detected"

        pest_output = self._predict("pest_detector", decoded.image)
        visible_pest_candidates = [
            item for item in pest_output.get("detections", [])
            if float(item.get("confidence", 0)) >= settings.pest_threshold
        ]
        crop_model_ready = bool(self.statuses.get("crop_part_classifier", {}).get("ready"))
        crop_content_confirmed = image_result["quality"].get("plant_visibility") == "model_confirmed"
        if crop_model_ready and not crop_content_confirmed and not visible_pest_candidates:
            image_result["quality"]["suitable"] = False
            image_result["quality"].setdefault("issues", []).append("unsupported_or_unclear_subject")
            image_result["quality"].setdefault("capture_guidance", []).extend([
                "Keep the crop, plant part, harvested produce, or pest as the main subject of the image.",
                "Move closer and avoid unrelated objects or busy backgrounds.",
            ])
            image_result["warnings"].append(
                "No supported crop, plant part, produce, or visible pest was detected confidently. No diagnosis was attempted."
            )
            return image_result

        skip_disease_classifier = crop_model_ready and not crop_content_confirmed and bool(visible_pest_candidates)
        if skip_disease_classifier:
            image_result["warnings"].append(
                "A pest was visible, but crop or plant tissue was not confirmed, so disease classification was skipped."
            )
            disease_output = {"predictions": []}
        else:
            disease_output = self._predict("disease_classifier", decoded.image)
        disease_predictions = disease_output.get("predictions", [])
        for rank, pred in enumerate(disease_predictions[:3], start=1):
            raw_label = str(pred.get("label", "unknown"))
            confidence = float(pred.get("confidence", 0))
            if _is_healthy_label(raw_label):
                assessment = {
                    "label": "Apparently healthy",
                    "raw_label": raw_label,
                    "confidence": round(confidence, 4),
                    "reliable": confidence >= settings.disease_threshold,
                    "disclaimer": "No supported disease was confidently detected in this image; this does not prove the complete plant or field is healthy.",
                }
                current = image_result.get("health_assessment")
                if current is None or confidence > float(current.get("confidence", 0)):
                    image_result["health_assessment"] = assessment
                continue
            alternative = rank > 1 or confidence < settings.disease_threshold
            image_result["diseases"].append(
                {
                    "name": _humanize(raw_label),
                    "raw_label": raw_label,
                    "category": _cause_for_label(raw_label),
                    "confidence": round(confidence, 4),
                    "rank": rank,
                    "alternative": alternative,
                    "reliable": confidence >= settings.disease_threshold,
                }
            )

        if disease_predictions:
            scores = [float(item.get("confidence", 0)) for item in disease_predictions[:2]]
            top_score = scores[0]
            margin = top_score - scores[1] if len(scores) > 1 else top_score
            image_result["uncertainty"] = {
                "top_confidence": round(top_score, 4),
                "top_two_margin": round(margin, 4),
                "out_of_distribution_suspected": top_score < settings.low_confidence_threshold or margin < 0.08,
                "method": "confidence_and_margin_screening_not_a_formal_ood_detector",
            }
        else:
            image_result["uncertainty"] = {
                "top_confidence": None,
                "top_two_margin": None,
                "out_of_distribution_suspected": None,
                "method": "unavailable",
            }

        for detection in pest_output.get("detections", []):
            if float(detection.get("confidence", 0)) < settings.pest_threshold:
                continue
            pest_item = _parse_pest(
                str(detection.get("label", "unknown pest")),
                float(detection.get("confidence", 0)),
                list(detection.get("bbox") or []),
            )
            pest_item["crop_part"] = image_result.get("plant_part", "not_determined")
            image_result["pests"].append(pest_item)

        segment_output = self._predict("damage_segmenter", decoded.image)
        segment_regions = []
        for region in segment_output.get("regions", []):
            segment_regions.append(
                {
                    "label": _humanize(str(region.get("label", "damaged area"))),
                    "raw_label": region.get("label"),
                    "confidence": round(float(region.get("confidence", 0)), 4),
                    "bbox": region.get("bbox"),
                    "polygon": region.get("polygon"),
                    "area_fraction": round(float(region.get("area_fraction", 0)), 6),
                    "method": "instance_or_semantic_segmentation",
                }
            )
        image_result["damage_regions"] = segment_regions

        localization_regions = segment_regions[:]
        if not localization_regions:
            for pest in image_result["pests"]:
                localization_regions.append(
                    {
                        "label": pest["name"],
                        "confidence": pest["confidence"],
                        "bbox": pest["bbox"],
                        "area_fraction": 0,
                        "method": "pest_object_detection",
                    }
                )
        annotated, zoom = annotate_image(decoded.image, localization_regions)
        if annotated:
            save_bytes(analysis_id, f"{image_id}-annotated.jpg", annotated)
            image_result["paths"]["annotated"] = f"{image_id}-annotated.jpg"
            image_result["urls"]["annotated"] = f"/api/vision/file/{analysis_id}/{image_id}-annotated.jpg"
        if zoom:
            save_bytes(analysis_id, f"{image_id}-zoom.jpg", zoom)
            image_result["paths"]["zoom"] = f"{image_id}-zoom.jpg"
            image_result["urls"]["zoom"] = f"/api/vision/file/{analysis_id}/{image_id}-zoom.jpg"

        if segment_regions:
            union_fraction = segment_output.get("union_area_fraction")
            if union_fraction is not None:
                affected = min(100.0, max(0.0, float(union_fraction)) * 100)
                method = "union_of_segmentation_masks_divided_by_image_pixels"
            else:
                affected = min(100.0, sum(float(item["area_fraction"]) for item in segment_regions) * 100)
                method = "sum_of_region_areas_possible_overlap"
            image_result["severity"] = _severity_from_percentage(affected, method=method)

        reliable_diseases = [item for item in image_result["diseases"] if item["reliable"]]
        reliable_healthy = bool((image_result.get("health_assessment") or {}).get("reliable"))
        if not reliable_diseases and not image_result["pests"] and not reliable_healthy:
            image_result["warnings"].append("The condition could not be identified reliably.")
        if image_result["diseases"] and not reliable_diseases:
            image_result["warnings"].append(
                "Disease probabilities are below the configured confidence threshold and are shown only as possibilities."
            )
        return image_result

    def analyze_session(
        self,
        images: list[InputImage],
        *,
        owner_id: str,
        crop: str = "auto",
        plant_part: str = "auto",
        growth_stage: str = "auto",
        harvest_stage: str = "auto",
        location: str = "",
        latitude: float | None = None,
        longitude: float | None = None,
        treatment_preference: str = "integrated",
        budget: str = "low",
        previous_treatment: str = "",
        soil_report: dict[str, Any] | None = None,
        consent: bool = False,
        language: str = "en",
    ) -> dict[str, Any]:
        self.ensure_initialized()
        cleanup_expired()
        if not images:
            raise ValueError("At least one image is required.")
        if len(images) > settings.max_images_per_session:
            raise ValueError(f"Upload no more than {settings.max_images_per_session} images per analysis session.")

        analysis_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        image_results = [
            self._analyze_one(
                analysis_id,
                source,
                crop=crop,
                plant_part=plant_part,
                growth_stage=growth_stage,
                harvest_stage=harvest_stage,
                consent=consent,
            )
            for source in images
        ]

        suitable_images = [item for item in image_results if item["quality"]["suitable"]]
        reliable_diseases = [
            disease
            for image in suitable_images
            for disease in image.get("diseases", [])
            if disease.get("reliable")
        ]
        pests = [pest for image in suitable_images for pest in image.get("pests", [])]
        healthy_assessments = [
            image.get("health_assessment")
            for image in suitable_images
            if (image.get("health_assessment") or {}).get("reliable")
        ]
        severities = [
            image["severity"]["affected_percentage"]
            for image in suitable_images
            if image.get("severity", {}).get("affected_percentage") is not None
        ]
        overall_severity = _severity_from_percentage(max(severities) if severities else None)
        crop_fallback = "unknown" if crop in {"", "auto"} else crop
        part_fallback = "unknown" if plant_part in {"", "auto"} else plant_part
        growth_fallback = "unknown" if growth_stage in {"", "auto"} else growth_stage
        harvest_fallback = "unknown" if harvest_stage in {"", "auto"} else harvest_stage
        detected_crop = next((item.get("crop") for item in suitable_images if item.get("crop") != "unknown"), crop_fallback)
        detected_part = next((item.get("plant_part") for item in suitable_images if item.get("plant_part") != "unknown"), part_fallback)
        detected_growth = next((item.get("growth_stage") for item in suitable_images if item.get("growth_stage") != "unknown"), growth_fallback)
        detected_harvest = next((item.get("harvest_stage") for item in suitable_images if item.get("harvest_stage") != "unknown"), harvest_fallback)

        if not suitable_images:
            status = "needs_better_images"
        elif reliable_diseases or pests or healthy_assessments:
            status = "completed"
        elif any(item.get("diseases") for item in suitable_images):
            status = "uncertain"
        else:
            status = "model_unavailable" if self.model_info()["development_mode"] else "uncertain"

        primary_disease = reliable_diseases[0] if reliable_diseases else None
        primary_pest = pests[0] if pests else None
        primary_healthy = healthy_assessments[0] if healthy_assessments else None
        diagnosis = (
            primary_disease["name"] if primary_disease
            else primary_pest["name"] if primary_pest
            else "apparently healthy" if primary_healthy
            else "unknown"
        )
        diagnosis_key = (
            primary_disease.get("raw_label") if primary_disease
            else primary_pest.get("raw_label") if primary_pest
            else primary_healthy.get("raw_label") if primary_healthy
            else "unknown"
        )
        cause = (
            primary_disease["category"] if primary_disease
            else "pest-related" if primary_pest
            else "healthy" if primary_healthy
            else "unknown"
        )
        weather = self._weather_context(latitude, longitude, location)
        recommendations = build_recommendations(
            crop=str(detected_crop or "unknown"),
            cause_category=cause,
            diagnosis=str(diagnosis_key),
            severity=overall_severity["level"],
            growth_stage=str(detected_growth or "unknown"),
            harvest_stage=str(detected_harvest or "unknown"),
            location=location,
            preference=treatment_preference,
            budget=budget,
            previous_treatment=previous_treatment,
            weather=weather,
            soil_report=soil_report,
            reliable_diagnosis=bool(primary_disease or primary_pest or primary_healthy),
        )

        farmer_message = _localized_farmer_message(status, diagnosis, language)

        result = {
            "ok": True,
            "analysis_id": analysis_id,
            "created_at": created_at,
            "status": status,
            "development_mode": self.model_info()["development_mode"],
            "farmer_message": farmer_message,
            "detected_crop": detected_crop or "unknown",
            "plant_part": detected_part or "unknown",
            "growth_stage": detected_growth or "unknown",
            "harvest_stage": detected_harvest or "unknown",
            "location": location,
            "images": image_results,
            "diseases": reliable_diseases,
            "health_assessment": primary_healthy,
            "pests": pests,
            "pest_summary": [
                {"name": name, "count": sum(1 for item in pests if item.get("name") == name)}
                for name in sorted({item.get("name") for item in pests if item.get("name")})
            ],
            "pest_evidence": {
                "status": "direct_pest_detected" if pests else (
                    "probable_pest_damage_only"
                    if any(item.get("category") == "pest-related" for image in suitable_images for item in image.get("diseases", []))
                    else "none_or_uncertain"
                ),
                "direct_detection_count": len(pests),
                "message": (
                    "One or more pests were directly localized by object detection." if pests
                    else "No pest was directly localized; symptom-only predictions must not be treated as proof of a pest."
                ),
            },
            "severity": overall_severity,
            "possible_alternatives": [
                disease for image in suitable_images for disease in image.get("diseases", []) if not disease.get("reliable")
            ][:5],
            "recommendations": recommendations,
            "weather_context": weather,
            "model_summary": {
                "version": ", ".join(
                    sorted({item.get("version", "unknown") for item in self.statuses.values() if item.get("ready")})
                ) or "no-trained-models-loaded",
                "models": self.statuses,
            },
            "uncertainty": {
                "low_confidence": status in {"uncertain", "model_unavailable"},
                "message": "The condition could not be identified reliably." if status != "completed" else None,
                "additional_images_requested": [
                    "full plant image",
                    "front side of affected leaf",
                    "back side of affected leaf",
                    "stem or fruit close-up",
                    "close-up of any visible pest",
                    "wider field image",
                ],
            },
            "voice_summary": farmer_message,
            "explainability": {
                "heatmap_available": False,
                "method": "not_generated",
                "message": "Heatmaps are optional secondary explanations and are not generated without a compatible explainability adapter. Damage localization relies on detector/segmenter outputs, not Grad-CAM alone.",
            },
            "expert_escalation": {
                "recommended": status in {"uncertain", "needs_better_images", "model_unavailable"},
                "reason": "Low confidence, unsuitable images, or unavailable trained models." if status != "completed" else None,
            },
            "disclaimer": (
                "Image analysis is advisory and is not a replacement for laboratory testing, a registered product label, "
                "or diagnosis by a qualified agriculture expert."
            ),
            "retention": {
                "consent": consent,
                "expires_at": expiry_for_consent(consent),
                "policy": "temporary" if not consent else "consented_retention",
            },
        }
        save_analysis(result, owner_id=owner_id, consent=consent, expires_at=result["retention"]["expires_at"])
        logger.info(
            "vision_analysis_completed analysis_id=%s owner=%s status=%s images=%d consent=%s model_version=%s",
            analysis_id, owner_id[:24], status, len(images), consent, result["model_summary"]["version"],
        )
        return result


_RUNTIME = VisionRuntime()


def initialize_vision_system() -> None:
    _RUNTIME.initialize()


def get_vision_runtime() -> VisionRuntime:
    _RUNTIME.ensure_initialized()
    return _RUNTIME
