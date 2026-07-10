from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from models.schemas import DocumentIntakeAnalysis, InferredFarmProfile, SoilReportAnalysis
from services.soil_report_api import analyze_soil_report, extract_soil_report_text
from services.pdf_parser import parse_farmer_document_text

@dataclass
class ParsedFile:
    filename: str
    text: str
    document_type: str

def analyze_farmer_documents(files: list[tuple[str, bytes]]) -> DocumentIntakeAnalysis:
    parsed_files = [_parse_file(filename, content) for filename, content in files]
    combined_text = "\n".join(item.text for item in parsed_files)
    normalized = re.sub(r"\s+", " ", combined_text).strip()
    
    # Extract details using pdf_parser
    parsed_details = parse_farmer_document_text(combined_text)
    
    # Process soil report if any Soil document is classification-matched or has nutrients
    soil_report = _best_soil_report(files, parsed_files)
    
    # Build inferred profile
    profile_data = {
        "farmer_name": parsed_details.get("farmer_name"),
        "location": parsed_details.get("location"),
        "crop": parsed_details.get("crop"),
        "soil_type": parsed_details.get("soil_type") or (soil_report.inferred_soil_type if soil_report else None),
        "season": parsed_details.get("season"),
        "land_type": parsed_details.get("land_type") or ("normal" if "location" in parsed_details else None),
        "irrigation_available": parsed_details.get("irrigation_available"),
        "farm_area_acres": parsed_details.get("farm_area_acres"),
        "budget_per_acre": parsed_details.get("budget_per_acre"),
        "preferred_language": parsed_details.get("preferred_language") or "English",
    }
    
    # Check for missing values
    missing_fields = [
        field
        for field in ("location", "soil_type", "crop", "season")
        if not profile_data.get(field)
    ]
    if profile_data.get("irrigation_available") is None:
        missing_fields.append("irrigation_available")
        
    evidence = parsed_details.get("evidence", {})
    confidence = parsed_details.get("confidence", 30)
    
    inferred_profile = InferredFarmProfile(
        farmer_name=profile_data["farmer_name"],
        location=profile_data["location"],
        crop=profile_data["crop"],
        soil_type=profile_data["soil_type"],
        season=profile_data["season"],
        land_type=profile_data["land_type"] or "normal",
        irrigation_available=profile_data["irrigation_available"] if profile_data["irrigation_available"] is not None else True,
        farm_area_acres=profile_data["farm_area_acres"],
        budget_per_acre=profile_data["budget_per_acre"],
        preferred_language=profile_data["preferred_language"],
        confidence=confidence,
        missing_fields=missing_fields,
        evidence=evidence,
    )
    
    return DocumentIntakeAnalysis(
        file_names=[item.filename for item in parsed_files],
        document_types=[item.document_type for item in parsed_files],
        extracted_text_preview=normalized[:900],
        soil_report=soil_report,
        inferred_profile=inferred_profile,
        farmer_ready_summary=_summary(inferred_profile, soil_report),
        warnings=_warnings(parsed_files, normalized, soil_report),
        next_questions=_next_questions(missing_fields),
    )

def _parse_file(filename: str, content: bytes) -> ParsedFile:
    text = extract_soil_report_text(filename, content)
    document_type = _classify_document(filename, text)
    return ParsedFile(filename=filename, text=text, document_type=document_type)

def _classify_document(filename: str, text: str) -> str:
    haystack = f"{filename} {text}".lower()
    if any(word in haystack for word in ("soil health", "soil test", "ph", "organic carbon", "nitrogen", "potassium", "phosphorus", "npk")):
        return "Soil Health Card / Soil Test"
    if any(word in haystack for word in ("pattadar", "passbook", "khata", "survey no", "ror", "1-b", "land record", "pass book")):
        return "Land Record / Farmer Passbook"
    if any(word in haystack for word in ("crop", "sowing", "acre", "irrigation", "cultivation")):
        return "Crop / Farm Detail Document"
    return "Readable Farm Document"

def _best_soil_report(files: list[tuple[str, bytes]], parsed_files: list[ParsedFile]) -> SoilReportAnalysis | None:
    candidates = [
        (filename, content)
        for filename, content in files
        if any(item.filename == filename and "Soil" in item.document_type for item in parsed_files)
    ]
    if not candidates and files:
        candidates = [files[0]]

    best: SoilReportAnalysis | None = None
    for filename, content in candidates:
        try:
            current = analyze_soil_report(filename, content)
        except Exception:
            continue
        if best is None or current.confidence > best.confidence:
            best = current
    return best

def _summary(profile: InferredFarmProfile, soil_report: SoilReportAnalysis | None) -> list[str]:
    summary = []
    if profile.farmer_name:
        summary.append(f"Farmer Name: {profile.farmer_name}")
    if profile.location:
        summary.append(f"Farm Location: {profile.location}")
    if profile.soil_type:
        summary.append(f"Inferred Soil Type: {profile.soil_type}")
    if profile.farm_area_acres:
        summary.append(f"Farm Size: {profile.farm_area_acres} Acres")
    if profile.crop:
        summary.append(f"Planned Crop: {profile.crop.title()}")
    if soil_report and soil_report.nutrients:
        nut_str = ", ".join(f"{k.upper()}: {v}" for k, v in soil_report.nutrients.items())
        summary.append(f"Nutrient Levels -> {nut_str}")
    if not summary:
        summary.append("Document processed, but no major farm parameters could be extracted.")
    return summary

def _warnings(parsed_files: list[ParsedFile], text: str, soil_report: SoilReportAnalysis | None) -> list[str]:
    warnings = []
    if not text.strip():
        warnings.append("The document text appears empty. Scanned PDFs may require high-contrast scan.")
    if soil_report is None:
        warnings.append("No Soil Health Card detected. Specific fertilizer split advices will be estimated.")
    if len(parsed_files) == 1:
        warnings.append("Add both Land Passbook and Soil Card for complete profile verification.")
    return warnings

def _next_questions(missing_fields: list[str]) -> list[str]:
    prompts = {
        "location": "Please tell me your farm location (Village, Mandal, District).",
        "soil_type": "What is the soil type? (e.g. Red, Black cotton, Loamy, Sandy).",
        "crop": "Which crop are you looking to sow?",
        "season": "Confirm the current crop season (Kharif, Rabi, Summer).",
        "irrigation_available": "Do you have access to borewell/canal irrigation?",
    }
    return [prompts[field] for field in missing_fields if field in prompts]
