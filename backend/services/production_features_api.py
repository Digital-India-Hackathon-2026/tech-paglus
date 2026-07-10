from __future__ import annotations

from models.schemas import CropRecommendation, FarmRequest, LocationData, RiskScores


SCHEME_RULES = [
    {
        "name": "PM-KISAN",
        "reason": "Income-support reminder for eligible landholding farmer families.",
        "action": "Keep Aadhaar, bank account, land record and e-KYC ready.",
    },
    {
        "name": "PMFBY Crop Insurance",
        "reason": "Weather-risk protection is important when flood, drought, heat or wind risk is medium/high.",
        "action": "Check enrolment window for the selected crop and season before sowing.",
    },
    {
        "name": "Soil Health Card",
        "reason": "Soil report values can reduce unnecessary fertilizer cost.",
        "action": "Use pH, NPK and organic carbon values before buying fertilizer.",
    },
]


CROP_INPUTS = {
    "cotton": [("Bt Cotton Hybrid", "certified seed"), ("NPK 20:20:0:13", "basal fertilizer"), ("Neem oil", "pest prevention")],
    "chilli": [("Teja/Byadgi chilli seed", "certified seed"), ("Calcium nitrate", "split fertilizer"), ("Yellow sticky traps", "pest monitoring")],
    "paddy": [("MTU/BPT paddy seed", "certified seed"), ("Zinc sulphate", "micronutrient"), ("Trichoderma", "seed treatment")],
    "maize": [("DHM/HQPM maize hybrid", "certified seed"), ("NPK 15:15:15", "basal fertilizer"), ("Fall armyworm lure", "pest monitoring")],
    "groundnut": [("Kadiri/Dharani groundnut seed", "certified seed"), ("Gypsum", "flowering support"), ("Rhizobium culture", "biofertilizer")],
    "turmeric": [("Pragati turmeric rhizome", "planting material"), ("Neem cake", "soil health"), ("Trichoderma", "rhizome treatment")],
}


def build_production_feature_bundle(
    farm: FarmRequest,
    location: LocationData,
    risk: RiskScores,
    best_crop: CropRecommendation | None,
) -> tuple[list[str], list[dict], list[dict], list[str]]:
    crop = (best_crop.crop if best_crop else farm.crop or "crop").lower()
    pest_alerts = _pest_disease_alerts(crop, risk)
    schemes = _scheme_matches(farm, risk)
    marketplace = _marketplace_items(crop, location)
    alerts = _alert_plan(farm, location, risk, best_crop, pest_alerts)
    return pest_alerts, schemes, marketplace, alerts


def _pest_disease_alerts(crop: str, risk: RiskScores) -> list[str]:
    alerts: list[str] = []
    if risk.flood >= 55:
        alerts.append("High moisture can increase fungal disease risk; avoid spraying before rain and improve drainage.")
    if risk.heat >= 60:
        alerts.append("Heat stress can increase sucking-pest pressure; inspect leaves in early morning.")
    if risk.drought >= 60:
        alerts.append("Dry stress can reduce plant immunity; prioritize irrigation and mulching where possible.")

    crop_specific = {
        "cotton": "Cotton watch: monitor for pink bollworm and sucking pests during humid or hot spells.",
        "chilli": "Chilli watch: check for thrips, mites and leaf curl symptoms after hot dry days.",
        "paddy": "Paddy watch: blast and sheath blight risk rises with standing moisture and cloudy weather.",
        "maize": "Maize watch: inspect whorl leaves for fall armyworm damage after rainfall breaks.",
        "groundnut": "Groundnut watch: watch for leaf spot after humid weather and avoid water stagnation.",
        "turmeric": "Turmeric watch: rhizome rot risk rises in poorly drained fields.",
    }
    alerts.append(crop_specific.get(crop, "Scout the field twice a week and report unusual leaf spots, wilting or pest damage."))
    return alerts


def _scheme_matches(farm: FarmRequest, risk: RiskScores) -> list[dict]:
    matches = []
    for scheme in SCHEME_RULES:
        priority = "High" if scheme["name"].startswith("PMFBY") and risk.overall >= 40 else "Normal"
        if scheme["name"] == "PM-KISAN" and farm.farm_area_acres and farm.farm_area_acres <= 5:
            priority = "High"
        matches.append({**scheme, "priority": priority})
    return matches


def _marketplace_items(crop: str, location: LocationData) -> list[dict]:
    items = CROP_INPUTS.get(crop, CROP_INPUTS["cotton"])
    return [
        {
            "item": item,
            "category": category,
            "nearby_search": f"{item} near {location.name}",
            "note": "Buy only certified/labelled input and verify expiry or lot number.",
        }
        for item, category in items
    ]


def _alert_plan(
    farm: FarmRequest,
    location: LocationData,
    risk: RiskScores,
    best_crop: CropRecommendation | None,
    pest_alerts: list[str],
) -> list[str]:
    crop = best_crop.crop if best_crop else farm.crop.title()
    alerts = [
        f"{location.name}: {crop} advisory ready. Weather risk is {risk.level} ({risk.overall}/100).",
        f"Top action: {pest_alerts[0]}",
    ]
    if best_crop:
        alerts.append(
            f"Expected profit is about Rs {best_crop.expected_profit_per_acre:,}/acre; confirm mandi price before selling."
        )
    if risk.flood >= 60:
        alerts.append("Drain excess water and postpone fertilizer or pesticide spraying until rainfall reduces.")
    if risk.drought >= 60:
        alerts.append("Use mulching and critical-stage irrigation to protect the crop from drought stress.")
    return alerts
