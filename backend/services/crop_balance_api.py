from typing import Any

# National and regional demand-supply statistics
CROP_MARKET_DYNAMICS = {
    "cotton": {"national_demand": 85, "national_supply": 80, "oversupply_risk": 20, "trend": "stable"},
    "chilli": {"national_demand": 90, "national_supply": 75, "oversupply_risk": 15, "trend": "rising"},
    "paddy": {"national_demand": 60, "national_supply": 95, "oversupply_risk": 80, "trend": "oversupply risk"},
    "maize": {"national_demand": 80, "national_supply": 78, "oversupply_risk": 25, "trend": "stable"},
    "groundnut": {"national_demand": 85, "national_supply": 72, "oversupply_risk": 10, "trend": "rising"},
    "turmeric": {"national_demand": 82, "national_supply": 70, "oversupply_risk": 30, "trend": "rising"}
}

def get_crop_balance(crop: str, state: str | None) -> dict[str, Any]:
    """
    Returns regional and national demand-supply scores:
    - demand_score: 0-100
    - oversupply_risk_score: 0-100
    - balance_ratio: supply/demand ratio
    - market_message: user-friendly description of supply/demand trends
    """
    crop_lower = crop.lower()
    dynamics = CROP_MARKET_DYNAMICS.get(crop_lower, {"national_demand": 70, "national_supply": 70, "oversupply_risk": 30, "trend": "stable"})
    
    state_lower = (state or "").lower()
    
    # Apply regional shifts
    demand_modifier = 0
    supply_modifier = 0
    
    if state_lower == "telangana":
        if crop_lower == "paddy":
            # Very high supply in Telangana due to Kaleshwaram irrigation projects
            supply_modifier += 15
            demand_modifier -= 5
        elif crop_lower == "chilli":
            demand_modifier += 10
        elif crop_lower == "cotton":
            demand_modifier += 5
    elif state_lower == "andhra pradesh":
        if crop_lower == "chilli":
            # Guntur chilli is world famous and has huge export demand
            demand_modifier += 15
            supply_modifier += 5
        elif crop_lower == "paddy":
            supply_modifier += 10
            
    demand_score = min(100, max(10, dynamics["national_demand"] + demand_modifier))
    supply_score = min(100, max(10, dynamics["national_supply"] + supply_modifier))
    
    balance_ratio = round(supply_score / max(1, demand_score), 2)
    
    # Calculate oversupply risk score
    oversupply_risk = dynamics["oversupply_risk"]
    if balance_ratio > 1.1:
        oversupply_risk = min(100, oversupply_risk + 15)
        market_message = f"{crop.title()} is seeing regional oversupply (Ratio: {balance_ratio}). Mandi prices may remain low or experience pressure."
    elif balance_ratio < 0.9:
        oversupply_risk = max(5, oversupply_risk - 10)
        market_message = f"{crop.title()} is in high demand (Ratio: {balance_ratio}). Expected price realization should be premium."
    else:
        market_message = f"{crop.title()} market is balanced (Ratio: {balance_ratio}). Stable trading conditions predicted."
        
    return {
        "demand_score": demand_score,
        "supply_score": supply_score,
        "oversupply_risk_score": oversupply_risk,
        "balance_ratio": balance_ratio,
        "market_message": market_message,
        "trend": dynamics["trend"]
    }
