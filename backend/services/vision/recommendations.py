from __future__ import annotations

import json
from typing import Any

from .config import settings


GENERAL_CAPTURE_ACTIONS = [
    "Isolate the visibly affected produce or plant material when practical and avoid moving it between fields.",
    "Photograph the full plant plus close-ups of both sides of affected leaves before applying any treatment.",
    "Clean cutting tools and hands after handling affected plants.",
]

LOW_COST_BY_CAUSE = {
    "fungal": [
        "Remove severely infected tissue when agronomically appropriate and dispose of it away from the crop.",
        "Improve airflow and avoid wetting foliage late in the day.",
        "Use only locally registered Trichoderma or other biological products after confirming crop compatibility on the label.",
    ],
    "bacterial": [
        "Avoid working in the crop while leaves are wet and disinfect pruning tools between plants.",
        "Remove badly affected plant material and reduce splash irrigation where possible.",
    ],
    "viral": [
        "Remove heavily symptomatic plants when recommended locally and control confirmed insect vectors with integrated pest management.",
        "Use clean planting material and control weed hosts around the field.",
    ],
    "pest-related": [
        "Scout leaf undersides and nearby plants to confirm the pest and life stage.",
        "Use sticky or pheromone traps only for the target pest and crop.",
        "Use manual removal or biological control where infestation is localized.",
    ],
    "nutrient-related": [
        "Confirm the suspected deficiency with a recent Soil Health Card or laboratory test before applying nutrients.",
        "Use compost, farmyard manure, or vermicompost as a soil-health input where suitable for the crop.",
    ],
    "environmental": [
        "Check irrigation, drainage, heat, wind, sunscald, and recent chemical exposure before treating as an infection.",
        "Reduce plant stress and monitor new growth for recovery.",
    ],
    "healthy": [
        "No treatment is indicated from the supported image evidence. Continue routine scouting and good crop hygiene.",
        "Recheck the plant after weather changes or if new symptoms appear.",
    ],
    "unknown": [
        "Do not apply a pesticide based only on this image. Collect clearer images and seek an agriculture expert diagnosis.",
    ],
}

CROP_PREVENTION = {
    "rice": ["Avoid excessive nitrogen and maintain field sanitation after harvest."],
    "paddy": ["Avoid excessive nitrogen and maintain field sanitation after harvest."],
    "cotton": ["Scout squares, flowers, bolls, and leaf undersides twice weekly during high-risk stages."],
    "tomato": ["Stake plants where appropriate, remove infected debris, and avoid overhead irrigation late in the day."],
    "chilli": ["Use clean seedlings, remove weed hosts, and monitor thrips and mites with suitable traps."],
    "maize": ["Inspect whorls and tassels regularly and destroy crop residues that shelter borers."],
    "potato": ["Use healthy seed tubers, avoid waterlogging, and remove volunteer plants after harvest."],
}


def _load_kb() -> dict[str, Any]:
    if not settings.treatment_kb_path.exists():
        return {"records": []}
    try:
        return json.loads(settings.treatment_kb_path.read_text(encoding="utf-8"))
    except Exception:
        return {"records": []}


def _verified_commercial_options(
    crop: str,
    diagnosis: str,
    location: str,
    harvest_stage: str,
) -> list[dict[str, Any]]:
    location_lower = (location or "").lower()
    matches: list[dict[str, Any]] = []
    for record in _load_kb().get("records", []):
        if record.get("verification_status") != "verified":
            if not settings.allow_unverified_commercial_treatments:
                continue
        if record.get("regulatory_status") != "registered_unrestricted":
            continue
        if record.get("crop_compatible") is not True or record.get("active", True) is not True:
            continue
        crops = [str(item).lower() for item in record.get("crops", [])]
        diagnoses = [str(item).lower() for item in record.get("diagnoses", [])]
        regions = [str(item).lower() for item in record.get("regions", [])]
        stages = [str(item).lower() for item in record.get("harvest_stages", [])]
        if crops and crop.lower() not in crops:
            continue
        if diagnoses and diagnosis.lower() not in diagnoses:
            continue
        if regions and not any(region in location_lower for region in regions):
            continue
        if stages and harvest_stage.lower() not in stages:
            continue
        matches.append(
            {
                "type": "commercial",
                "title": record.get("active_ingredient", "Registered treatment"),
                "active_ingredient": record.get("active_ingredient"),
                "product_category": record.get("product_category"),
                "detail": record.get("general_application_method", "Follow the verified product label."),
                "cost_category": record.get("cost_category", "unknown"),
                "safety_precautions": record.get("safety_precautions", []),
                "re_entry_interval": record.get("re_entry_interval"),
                "pre_harvest_interval": record.get("pre_harvest_interval"),
                "suitable_for": record.get("harvest_stages", []),
                "regulatory_status": record.get("regulatory_status"),
                "verification_status": record.get("verification_status"),
                "source": record.get("source"),
            }
        )
    return matches


def build_recommendations(
    *,
    crop: str,
    cause_category: str,
    diagnosis: str,
    severity: str,
    growth_stage: str,
    harvest_stage: str,
    location: str,
    preference: str,
    budget: str,
    previous_treatment: str,
    weather: dict[str, Any] | None,
    soil_report: dict[str, Any] | None,
    reliable_diagnosis: bool,
) -> dict[str, Any]:
    cause = cause_category if cause_category in LOW_COST_BY_CAUSE else "unknown"
    natural = [
        {
            "type": "natural",
            "title": "Low-cost immediate action",
            "detail": detail,
            "cost_category": "low",
            "verification_status": "general_ipm_guidance",
        }
        for detail in GENERAL_CAPTURE_ACTIONS[:2] + LOW_COST_BY_CAUSE[cause]
    ]
    if previous_treatment.strip():
        natural.append({
            "type": "safety",
            "title": "Previous treatment check",
            "detail": "Do not repeat or mix a previous treatment until its active ingredient, application date, label interval, and crop compatibility are reviewed.",
            "cost_category": "low",
            "verification_status": "general_safety_guidance",
        })

    for detail in CROP_PREVENTION.get((crop or "").lower(), []):
        natural.append(
            {
                "type": "prevention",
                "title": f"{crop.title()} prevention",
                "detail": detail,
                "cost_category": "low",
                "verification_status": "general_crop_guidance",
            }
        )

    commercial: list[dict[str, Any]] = []
    commercial_warning = None
    if reliable_diagnosis and cause != "healthy":
        commercial = _verified_commercial_options(crop, diagnosis, location, harvest_stage)
    if cause == "healthy":
        commercial_warning = "No pesticide or corrective fertilizer is recommended for an apparently healthy image."
    elif not commercial:
        commercial_warning = (
            "No verified crop-, diagnosis-, stage-, and region-compatible chemical record is configured. "
            "Confirm the active ingredient, dosage, re-entry interval, and pre-harvest interval with the "
            "product label or a local agriculture officer."
        )

    weather_warnings: list[str] = []
    analysis = (weather or {}).get("analysis", {}) if isinstance(weather, dict) else {}
    if analysis.get("total_precipitation_72h", 0) > 2:
        weather_warnings.append("Rain is possible; avoid spraying before rainfall and follow the product label.")
    if analysis.get("safe_spraying_hours_next_24h") == 0 and weather:
        weather_warnings.append("No clearly safe spray window was identified in the next 24 hours.")
    if analysis.get("pest_humidity_index") == "High":
        weather_warnings.append("High humidity may increase disease pressure; improve airflow and scouting.")

    if cause == "healthy":
        nutrient_note = "Do not apply extra fertilizer unless a soil or tissue test confirms a deficiency."
    elif cause != "nutrient-related" and soil_report:
        nutrient_note = (
            "The soil report is available, but fertilizer is not being presented as a cure for this diagnosis. "
            "Use it only to correct a separately confirmed nutrient deficiency."
        )
    elif cause == "nutrient-related" and not soil_report:
        nutrient_note = "Obtain a Soil Health Card or laboratory test before applying corrective fertilizer."
    else:
        nutrient_note = None

    selected = natural + commercial
    preference_key = (preference or "integrated").lower()
    if preference_key == "natural":
        selected = natural
    elif preference_key == "artificial":
        selected = commercial
    elif preference_key == "cheapest":
        selected = [item for item in natural + commercial if item.get("cost_category") == "low"] or natural[:3]
    elif preference_key == "fastest":
        selected = (commercial[:2] if commercial else natural[:3])

    return {
        "preference": preference_key,
        "budget": budget,
        "previous_treatment_considered": bool(previous_treatment.strip()),
        "natural": natural,
        "commercial": commercial,
        "selected": selected,
        "all": natural + commercial,
        "commercial_warning": commercial_warning,
        "weather_warnings": weather_warnings,
        "nutrient_note": nutrient_note,
        "severity_context": f"Advice was filtered for {severity} image-based severity and {growth_stage} growth stage.",
    }
