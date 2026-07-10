from typing import Any

# Base crop parameters for financial modeling
CROP_PROFIT_BASICS = {
    "cotton": {"base_cost": 42000, "avg_yield": 9.5, "fallback_price": 7200},
    "chilli": {"base_cost": 68000, "avg_yield": 18.0, "fallback_price": 9500},
    "paddy": {"base_cost": 52000, "avg_yield": 28.0, "fallback_price": 2300},
    "maize": {"base_cost": 34000, "avg_yield": 26.0, "fallback_price": 2450},
    "groundnut": {"base_cost": 31000, "avg_yield": 12.0, "fallback_price": 6700},
    "turmeric": {"base_cost": 76000, "avg_yield": 42.0, "fallback_price": 8200}
}

def calculate_crop_profit(
    crop: str,
    soil_type: str,
    irrigation_available: bool,
    mandi_price: float | None = None
) -> dict[str, Any]:
    """
    Calculates expected cost, yield, gross revenue, and profit per acre.
    Applies penalties for unfavorable soil or lack of irrigation.
    """
    crop_lower = crop.lower()
    model = CROP_PROFIT_BASICS.get(crop_lower, {"base_cost": 40000, "avg_yield": 15.0, "fallback_price": 4000})
    
    # Cost calculations
    input_cost = model["base_cost"]
    
    # Irrigated farming has higher seed/water management costs
    if irrigation_available:
        input_cost += 3000
    else:
        input_cost -= 2000 # lower inputs in dryland
        
    # Yield adjustments
    yield_multiplier = 1.0
    
    # Soil suitability modifiers
    soil_lower = soil_type.lower()
    if crop_lower == "cotton" and soil_lower == "sandy":
        yield_multiplier -= 0.3
    elif crop_lower == "paddy" and soil_lower == "sandy":
        yield_multiplier -= 0.5
    elif crop_lower == "groundnut" and soil_lower == "black":
        yield_multiplier -= 0.15  # likes red/sandy soil better
        
    # Water modifier
    if not irrigation_available:
        if crop_lower == "paddy":
            # Paddy is extremely sensitive to drought
            yield_multiplier -= 0.45
        elif crop_lower in ("chilli", "turmeric"):
            yield_multiplier -= 0.3
        elif crop_lower == "cotton":
            yield_multiplier -= 0.2
        elif crop_lower == "groundnut":
            # Groundnut is relatively drought-tolerant
            yield_multiplier -= 0.1
            
    expected_yield = round(model["avg_yield"] * yield_multiplier, 2)
    
    # Calculate revenue
    price = mandi_price or model["fallback_price"]
    gross_revenue = round(expected_yield * price)
    expected_profit = round(gross_revenue - input_cost)
    
    # Calculate profit score (ratio of profit to cost)
    profit_margin = expected_profit / max(1, input_cost)
    profit_score = int(min(100, max(10, 50 + (profit_margin * 40))))
    
    return {
        "estimated_cost_per_acre": input_cost,
        "expected_yield_per_acre": expected_yield,
        "gross_revenue_per_acre": gross_revenue,
        "expected_profit_per_acre": expected_profit,
        "profit_score": profit_score
    }
