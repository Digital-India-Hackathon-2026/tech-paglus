import re
from io import BytesIO
from typing import Any
# pyrefly: ignore [missing-import]
from pypdf import PdfReader

def extract_pdf_text(content: bytes) -> str:
    """Helper to extract text from raw PDF bytes."""
    try:
        reader = PdfReader(BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text
    except Exception as exc:
        raise ValueError(f"Failed to read PDF: {exc}")

def parse_farmer_document_text(text: str) -> dict[str, Any]:
    """
    Parses a string of text extracted from a farmer document (Soil Report or Land Passbook).
    Extracts farmer info, regional details, soil values, and coordinates using robust regex.
    """
    normalized = re.sub(r"\s+", " ", text).strip()
    lower_text = normalized.lower()
    
    extracted: dict[str, Any] = {}
    evidence: dict[str, str] = {}
    
    # Define regex helper
    def search_field(keys: list[str], pattern: str, clean_fn=None):
        for key in keys:
            # Match label followed by optional separators and then target
            regex = rf"\b{re.escape(key)}\b\s*[:\-=]?\s*{pattern}"
            match = re.search(regex, lower_text)
            if match:
                val = match.group(1).strip()
                if clean_fn:
                    val = clean_fn(val)
                return val, f"Found pattern around '{key}'"
        return None, None

    # Farmer Name
    name, ev = search_field(["farmer name", "pattadar name", "name of farmer", "applicant name", "name"], r"([a-z][a-z .]{2,40})")
    if name:
        extracted["farmer_name"] = name.title()
        evidence["farmer_name"] = ev
        
    # Location Hierarchy
    village, ev = search_field(["village", "village name", "gram panchayat"], r"([a-z][a-z .]{2,30})")
    if village:
        extracted["village"] = village.title()
        evidence["village"] = ev
        
    mandal, ev = search_field(["mandal", "taluk", "tehsil", "block"], r"([a-z][a-z .]{2,30})")
    if mandal:
        extracted["mandal"] = mandal.title()
        evidence["mandal"] = ev
        
    district, ev = search_field(["district", "dist"], r"([a-z][a-z .]{2,30})")
    if district:
        extracted["district"] = district.title()
        evidence["district"] = ev

    state, ev = search_field(["state"], r"([a-z][a-z .]{2,30})")
    if state:
        extracted["state"] = state.title()
        evidence["state"] = ev
        
    # Combines location text
    parts = []
    for item in ("village", "mandal", "district", "state"):
        if item in extracted:
            parts.append(extracted[item])
    if parts:
        extracted["location"] = ", ".join(parts)
        evidence["location"] = "Synthesized from parsed address components"
        
    # Survey Number
    survey_no, ev = search_field(["survey no", "survey number", "sy no", "khata no", "khata number", "plot no"], r"([0-9a-z\-/]+)")
    if survey_no:
        extracted["survey_number"] = survey_no
        evidence["survey_number"] = ev
        
    # Farm Area in Acres
    def clean_float(val):
        try:
            return float(val)
        except ValueError:
            return None
            
    area, ev = search_field(["farm area", "land area", "area", "extent", "farm size"], r"([0-9]+(?:\.[0-9]+)?)\s*(?:acres|acre|ac|hec|ha)", clean_float)
    if area:
        extracted["farm_area_acres"] = area
        evidence["farm_area_acres"] = ev
        
    # Coordinates
    lat_lon_pattern = r"(?:lat|latitude)\s*[:=]?\s*(-?\d{1,2}\.\d+)\s*[, ]+\s*(?:lon|longitude)\s*[:=]?\s*(-?\d{2,3}\.\d+)"
    match = re.search(lat_lon_pattern, lower_text)
    if match:
        extracted["latitude"] = float(match.group(1))
        extracted["longitude"] = float(match.group(2))
        evidence["latitude"] = "Found coordinates label in text"
        evidence["longitude"] = "Found coordinates label in text"
    else:
        # Check raw coordinate formats
        match_raw = re.search(r"(\d{1,2}\.\d{4,6})\s*[n]?\s*,\s*(\d{2,3}\.\d{4,6})\s*[e]?", lower_text)
        if match_raw:
            lat = float(match_raw.group(1))
            lon = float(match_raw.group(2))
            if 6 <= lat <= 38 and 68 <= lon <= 98: # India boundaries
                extracted["latitude"] = lat
                extracted["longitude"] = lon
                evidence["latitude"] = "Extracted coordinate-like sequence"
                evidence["longitude"] = "Extracted coordinate-like sequence"
                
    # Nutrients / Soil parameters
    nutrients = {}
    for nutrient, keys in [
        ("ph", ["ph", "soil ph", "reaction"]),
        ("nitrogen", ["nitrogen", "available n", "n"]),
        ("phosphorus", ["phosphorus", "available p", "phosphate", "p2o5", "p"]),
        ("potassium", ["potassium", "available k", "potash", "k2o", "k"]),
        ("organic_carbon", ["organic carbon", "oc", "carbon"]),
        ("ec", ["ec", "electrical conductivity"]),
        ("zinc", ["zinc", "zn"]),
        ("sulphur", ["sulphur", "s"]),
        ("iron", ["iron", "fe"])
    ]:
        for k in keys:
            pattern = rf"\b{re.escape(k)}\b[^0-9]{{0,25}}([0-9]+(?:\.[0-9]+)?)\s*(?:mg/kg|ppm|kg/ha|%)?"
            match = re.search(pattern, lower_text)
            if match:
                try:
                    val = float(match.group(1))
                    nutrients[nutrient] = val
                    evidence[nutrient] = f"Parsed value {val} from pattern key '{k}'"
                    break
                except ValueError:
                    continue
                    
    if nutrients:
        extracted["nutrients"] = nutrients
        
    # Irrigation source
    irr, ev = search_field(["irrigation source", "water source", "irrigation", "source of water"], r"(borewell|canal|drip|sprinkler|rainfed|tank|well)")
    if irr:
        extracted["irrigation_source"] = irr
        extracted["irrigation_available"] = irr != "rainfed"
        evidence["irrigation_available"] = ev
        
    # Crop / Season if available
    crop, ev = search_field(["crop", "commodity", "sowing crop"], r"(cotton|chilli|chili|paddy|rice|maize|corn|groundnut|turmeric)")
    if crop:
        # Normalize chilli/rice
        if crop == "chili": crop = "chilli"
        if crop == "rice": crop = "paddy"
        if crop == "corn": crop = "maize"
        extracted["crop"] = crop
        evidence["crop"] = ev
        
    season, ev = search_field(["season", "sowing season"], r"(kharif|rabi|summer|zaid)")
    if season:
        if season == "zaid": season = "summer"
        extracted["season"] = season
        evidence["season"] = ev
        
    # Confidence Score Estimation
    confidence = 10
    if "farmer_name" in extracted: confidence += 15
    if "location" in extracted: confidence += 15
    if "survey_number" in extracted: confidence += 10
    if "farm_area_acres" in extracted: confidence += 10
    if "latitude" in extracted: confidence += 15
    if nutrients: confidence += min(25, len(nutrients) * 5)
    
    extracted["confidence"] = min(98, confidence)
    extracted["evidence"] = evidence
    
    return extracted
