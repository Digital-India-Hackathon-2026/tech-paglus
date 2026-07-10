from __future__ import annotations

import re
from io import BytesIO
from typing import Any

from pypdf import PdfReader

from models.schemas import SoilReportAnalysis


NUTRIENT_PATTERNS = {
    "ph": [r"\bpH\b[^0-9]{0,16}([0-9]+(?:\.[0-9]+)?)"],
    "nitrogen": [r"\b(?:nitrogen|available\s+n|n)\b[^0-9]{0,24}([0-9]+(?:\.[0-9]+)?)"],
    "phosphorus": [r"\b(?:phosphorus|phosphate|available\s+p|p2o5|p)\b[^0-9]{0,24}([0-9]+(?:\.[0-9]+)?)"],
    "potassium": [r"\b(?:potassium|potash|available\s+k|k2o|k)\b[^0-9]{0,24}([0-9]+(?:\.[0-9]+)?)"],
    "organic_carbon": [r"\b(?:organic\s+carbon|oc)\b[^0-9]{0,24}([0-9]+(?:\.[0-9]+)?)"],
    "ec": [r"\b(?:ec|electrical\s+conductivity)\b[^0-9]{0,24}([0-9]+(?:\.[0-9]+)?)"],
}


def extract_soil_report_text(filename: str, content: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1", errors="ignore")


def analyze_soil_report(filename: str, content: bytes) -> SoilReportAnalysis:
    text = extract_soil_report_text(filename, content)
    normalized = re.sub(r"\s+", " ", text).strip()
    lower_text = normalized.lower()
    nutrients = _extract_nutrients(normalized)
    soil_type = _infer_soil_type(lower_text, nutrients)
    issues = _build_issues(nutrients)
    recommendations = _build_recommendations(nutrients, soil_type)

    confidence = 35
    confidence += min(45, len(nutrients) * 8)
    confidence += 12 if soil_type != "loamy" else 0
    confidence += 8 if len(normalized) > 120 else 0

    return SoilReportAnalysis(
        file_name=filename,
        extracted_text_preview=normalized[:700],
        inferred_soil_type=soil_type,
        confidence=min(confidence, 96),
        nutrients=nutrients,
        detected_issues=issues,
        recommendations=recommendations,
    )


def _extract_nutrients(text: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, patterns in NUTRIENT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            try:
                values[key] = float(match.group(1))
                break
            except ValueError:
                continue
    return values


def _infer_soil_type(text: str, nutrients: dict[str, Any]) -> str:
    direct_matches = {
        "black": ["black soil", "black cotton", "regur"],
        "red": ["red soil", "red sandy"],
        "sandy": ["sandy soil", "sand soil", "light soil"],
        "loamy": ["loamy soil", "clay loam", "sandy loam"],
    }
    for soil, hints in direct_matches.items():
        if any(hint in text for hint in hints):
            return soil

    ph = nutrients.get("ph")
    organic_carbon = nutrients.get("organic_carbon")
    ec = nutrients.get("ec")
    if ec and ec > 2:
        return "sandy"
    if ph and ph >= 7.5 and organic_carbon and organic_carbon >= 0.6:
        return "black"
    if ph and ph < 6.5:
        return "red"
    return "loamy"


def _build_issues(nutrients: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    ph = nutrients.get("ph")
    nitrogen = nutrients.get("nitrogen")
    phosphorus = nutrients.get("phosphorus")
    potassium = nutrients.get("potassium")
    organic_carbon = nutrients.get("organic_carbon")
    ec = nutrients.get("ec")

    if ph is not None and ph < 6.2:
        issues.append("Soil appears acidic; lime correction may be needed after local agronomist confirmation.")
    if ph is not None and ph > 7.8:
        issues.append("Soil appears alkaline; avoid unnecessary liming and improve organic matter.")
    if nitrogen is not None and nitrogen < 280:
        issues.append("Available nitrogen looks low.")
    if phosphorus is not None and phosphorus < 22:
        issues.append("Available phosphorus looks low.")
    if potassium is not None and potassium < 140:
        issues.append("Available potassium looks low.")
    if organic_carbon is not None and organic_carbon < 0.5:
        issues.append("Organic carbon looks low; soil structure and nutrient retention may suffer.")
    if ec is not None and ec > 2:
        issues.append("Electrical conductivity is high; salinity stress is possible.")
    if not issues:
        issues.append("No major nutrient warning was detected from the readable report values.")
    return issues


def _build_recommendations(nutrients: dict[str, Any], soil_type: str) -> list[str]:
    recommendations = [
        f"Use {soil_type} as the starting soil type in the advisory form.",
        "Verify final fertilizer dosage with the local agriculture officer because PDF formats vary by state.",
    ]
    if nutrients.get("nitrogen", 9999) < 280:
        recommendations.append("Prefer split nitrogen application instead of one heavy dose.")
    if nutrients.get("organic_carbon", 9999) < 0.5:
        recommendations.append("Add FYM, compost, green manure, or crop residue to improve organic carbon.")
    if nutrients.get("phosphorus", 9999) < 22:
        recommendations.append("Include phosphorus in the basal dose based on the crop selected.")
    if nutrients.get("potassium", 9999) < 140:
        recommendations.append("Add potash support, especially for cotton, chilli, turmeric, and paddy.")
    return recommendations
