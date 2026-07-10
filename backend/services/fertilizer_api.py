from typing import Any

def calculate_fertilizer_plan(crop: str, soil_type: str, nutrients: dict[str, Any]) -> dict[str, Any]:
    """
    Calculates dynamic basal and top dressing fertilizer dosage based on Soil Health Card.
    Returns:
    - basal: string
    - top_dressing: string
    - organic: string
    - soil_note: string
    - urea_bags: float
    - dap_bags: float
    - mop_bags: float
    """
    crop_lower = crop.lower()
    
    # Defaults
    n = nutrients.get("nitrogen", 280)
    p = nutrients.get("phosphorus", 22)
    k = nutrients.get("potassium", 140)
    ph = nutrients.get("ph", 7.0)
    oc = nutrients.get("organic_carbon", 0.5)
    
    # Standard recommendations per crop (in kg/acre)
    # Target N-P-K requirement
    targets = {
        "cotton": {"n": 60, "p": 30, "k": 30},
        "chilli": {"n": 120, "p": 60, "k": 60},
        "paddy": {"n": 50, "p": 25, "k": 25},
        "maize": {"n": 80, "p": 40, "k": 40},
        "groundnut": {"n": 15, "p": 30, "k": 30}, # Legume fixes nitrogen
        "turmeric": {"n": 60, "p": 50, "k": 90}
    }
    
    req = targets.get(crop_lower, {"n": 50, "p": 25, "k": 25})
    
    # Modify targets based on soil report levels
    # If soil Nitrogen is low, increase Urea target. If high, decrease.
    n_factor = 1.2 if n < 200 else 1.1 if n < 280 else 0.8 if n > 450 else 1.0
    p_factor = 1.25 if p < 15 else 1.1 if p < 22 else 0.75 if p > 40 else 1.0
    k_factor = 1.25 if k < 100 else 1.1 if k < 140 else 0.7 if k > 250 else 1.0
    
    target_n = req["n"] * n_factor
    target_p = req["p"] * p_factor
    target_k = req["k"] * k_factor
    
    # Calculate fertilizer bags:
    # 1. DAP (18% N, 46% P) -> Provides all P.
    dap_needed = target_p / 0.46
    dap_bags = round(dap_needed / 50.0, 1)
    
    # N provided by DAP
    n_from_dap = dap_needed * 0.18
    
    # Remaining N provided by Urea (46% N)
    remaining_n = max(0.0, target_n - n_from_dap)
    urea_needed = remaining_n / 0.46
    urea_bags = round(urea_needed / 45.0, 1)
    
    # Potash (MOP - 60% K)
    mop_needed = target_k / 0.60
    mop_bags = round(mop_needed / 50.0, 1)
    
    # Build text descriptions
    basal = f"Basal Application: Apply {dap_bags * 50:.0f} kg DAP, {mop_bags * 25:.0f} kg MOP, and {urea_bags * 15:.0f} kg Urea at the time of sowing/transplanting."
    top_dressing = f"Top Dressing: Split Urea into 2 doses ({urea_bags * 15:.0f} kg each) at 30 days (tillering/vegetative) and 60 days (flowering). Apply remaining Potash ({mop_bags * 25:.0f} kg) during second Urea split."
    
    organic_parts = ["Apply 5-8 tonnes of well-decomposed Farm Yard Manure (FYM) or compost during land preparation."]
    if oc < 0.4:
        organic_parts.append("Organic carbon is very low. Sowing green manure crops like Dhaincha or Sunnhemp and incorporation at 45 days is highly recommended.")
    organic = " ".join(organic_parts)
    
    notes = []
    if ph < 6.0:
        notes.append("Soil is acidic (pH < 6). Apply 200 kg agricultural lime per acre to neutralize acidity.")
    elif ph > 8.0:
        notes.append("Soil is alkaline (pH > 8). Apply 250 kg agricultural Gypsum per acre to reduce alkalinity.")
        
    if nutrients.get("zinc") is not None and nutrients["zinc"] < 0.6:
        notes.append("Zinc deficiency detected. Apply 10 kg Zinc Sulphate (ZnSO4) per acre during basal dressing.")
    if nutrients.get("iron") is not None and nutrients["iron"] < 4.5:
        notes.append("Iron deficiency detected. Foliar spray 0.5% Ferrous Sulphate (FeSO4) if leaf yellowing occurs.")
        
    soil_note = " ".join(notes) if notes else "Soil pH and micronutrients look balanced. Continue organic composting."
    
    return {
        "basal": basal,
        "top_dressing": top_dressing,
        "organic": organic,
        "soil_note": soil_note,
        "urea_bags": urea_bags,
        "dap_bags": dap_bags,
        "mop_bags": mop_bags
    }
