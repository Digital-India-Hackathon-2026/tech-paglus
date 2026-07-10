from typing import Any
from services.crop_balance_api import get_crop_balance, CROP_MARKET_DYNAMICS

def get_demand_supply_projection(location_name: str, state: str | None) -> dict[str, Any]:
    """
    Returns an aggregated projection of crop demand/supply for FPO planning dashboards.
    Useful for warning groups of farmers if they are all planting the same crops.
    """
    state = state or "India"
    
    crops_projection = []
    oversupply_alerts = []
    
    for crop in CROP_MARKET_DYNAMICS.keys():
        balance = get_crop_balance(crop, state)
        crops_projection.append({
            "crop": crop.title(),
            "demand_score": balance["demand_score"],
            "supply_score": balance["supply_score"],
            "balance_ratio": balance["balance_ratio"],
            "trend": balance["trend"]
        })
        
        if balance["oversupply_risk_score"] >= 70:
            oversupply_alerts.append(
                f"Oversupply risk is high for {crop.title()} in {state}. FPOs are advised to stagger planting schedules."
            )
            
    return {
        "region": state,
        "location": location_name,
        "projections": crops_projection,
        "oversupply_alerts": oversupply_alerts or ["No active oversupply alerts for this region."],
        "suggested_diversification": ["Chilli", "Groundnut"] if state.lower() == "telangana" else ["Maize", "Turmeric"]
    }
