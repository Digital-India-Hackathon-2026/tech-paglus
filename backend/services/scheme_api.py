from typing import Any

def match_government_schemes(
    farmer_name: str,
    location_name: str,
    state: str | None,
    crop: str,
    season: str,
    land_size: float | None,
    irrigation_available: bool,
    has_soil_report: bool
) -> list[dict[str, Any]]:
    """
    Evaluates farmer parameters and returns matched government scheme recommendations.
    """
    matches = []
    state = state or "Telangana"
    land = land_size or 2.0
    crop_lower = crop.lower()
    
    # 1. PM-KISAN
    if land <= 5.0:
        matches.append({
            "name": "PM-KISAN Samman Nidhi",
            "priority": "High",
            "reason": f"Eligible small farmer ({land} acres). Provides Rs 6,000 yearly income support directly to bank accounts.",
            "action": "Ensure Aadhaar is linked to your bank account and check e-KYC status on PM-KISAN portal."
        })
    else:
        matches.append({
            "name": "PM-KISAN Samman Nidhi",
            "priority": "Medium",
            "reason": f"Eligible medium landholder ({land} acres). Limits apply to specific institutional landowners.",
            "action": "Submit land records (Pattadar Passbook) at local Meeseva/CSC center."
        })
        
    # 2. PMFBY (Crop Insurance)
    insurance_reason = ""
    premium = "2.0%"
    if crop_lower in ("chilli", "turmeric"):
        premium = "5.0% (Commercial Crop)"
        insurance_reason = f"High-value crop {crop.title()} requires premium cover. PMFBY cushions against weather risks."
    elif season.lower() == "kharif":
        premium = "2.0% (Kharif Food Crop)"
        insurance_reason = f"Monsoon risk is high for Kharif {crop.title()}; insurance protects against rain delay or flood."
    else:
        premium = "1.5% (Rabi Crop)"
        insurance_reason = f"Winter Rabi crop {crop.title()} insurance protects against unseasonal frost and hail."
        
    matches.append({
        "name": f"PM Fasal Bima Yojana (PMFBY)",
        "priority": "High",
        "reason": f"{insurance_reason} Premium is {premium}.",
        "action": f"Apply before the cutoff date (usually July 31 for Kharif) through your bank or online crop insurance portal."
    })
    
    # 3. Micro-Irrigation Subsidy (PMKSY)
    if not irrigation_available or crop_lower in ("chilli", "cotton", "turmeric"):
        matches.append({
            "name": f"PMKSY Micro-Irrigation Subsidy",
            "priority": "High",
            "reason": f"Drip/Sprinkler systems are critical for {crop.title()}. Small and marginal farmers in {state} are eligible for 80% to 90% subsidy.",
            "action": f"Register on the state horticulture portal (e.g. TSMIP in Telangana or APMIP in AP) with land passbook and survey details."
        })
        
    # 4. Soil Health Card Subsidy
    if not has_soil_report:
        matches.append({
            "name": "National Soil Health Card Scheme",
            "priority": "High",
            "reason": "You have not uploaded a soil report. Soil testing is subsidized/free at village level blocks every 2 years.",
            "action": "Contact the nearest Rythu Vedika or Agriculture Extension Officer (AEO) to collect soil samples from your field."
        })
    else:
        matches.append({
            "name": "SHC Micronutrient Subsidy",
            "priority": "Medium",
            "reason": "Based on your uploaded Soil Health Card, you can claim 50% subsidy on soil correction inputs like Lime, Gypsum, or Zinc Sulphate.",
            "action": "Present your Soil Health Card at local primary agricultural cooperative societies (PACS) or government fertilizer depots."
        })
        
    # 5. State Specific Direct Benefit Transfers (DBT)
    if state.lower() == "telangana":
        matches.append({
            "name": "Rythu Bandhu / Rythu Bharosa",
            "priority": "High",
            "reason": f"Matched state {state} landholder. Provides cash incentive per acre for inputs.",
            "action": "Submit updated passbook details and check coordinates registration status."
        })
    elif state.lower() == "andhra pradesh":
        matches.append({
            "name": "YSR Rythu Bharosa",
            "priority": "High",
            "reason": f"Matched state {state} landholder. Provides Rs 13,500 annual investment support.",
            "action": "Ensure name appears in the village beneficiary display list at Rythu Bharosa Kendram (RBK)."
        })
        
    return matches
