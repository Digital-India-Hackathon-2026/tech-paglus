from typing import Any

def get_irrigation_advisory(
    water_source: str,
    water_availability: str,
    income_level: str,
    soil_type: str,
    crop: str,
    season: str,
    land_size: float,
    forecast_rain: float
) -> dict[str, Any]:
    """
    Formulates a comprehensive, customized irrigation advice bundle.
    """
    crop_lower = crop.lower()
    soil_lower = soil_type.lower()
    
    # 1. Best practice recommendation
    if crop_lower == "paddy":
        best_practice = "Alternate Wetting and Drying (AWD). Keep a water depth of 2-5 cm during vegetative stage, then let the soil dry slightly before next watering to save 30% water."
        low_cost_alternative = "Direct Seeded Rice (DSR) to avoid high nursery puddling water requirement."
    elif crop_lower in ("chilli", "turmeric"):
        best_practice = "Drip irrigation with 16mm inline drippers. Apply water daily for 45 minutes during flowering/fruiting stage."
        low_cost_alternative = "Broadbed and Furrow (BBF) irrigation to direct water flow specifically into crop root zones."
    elif crop_lower == "cotton":
        best_practice = "Alternate furrow irrigation. Irrigate odd-numbered furrows in one cycle and even furrows in the next."
        low_cost_alternative = "Organic mulching using cotton stalk residues to conserve moisture."
    else:
        best_practice = "Sprinkler irrigation systems during early vegetative growth."
        low_cost_alternative = "Basin method of irrigation around crop rows."

    # 2. 7-Day Schedule with Rain Awareness
    seven_day_schedule = []
    has_heavy_rain = forecast_rain >= 25.0
    
    for day in range(1, 8):
        if day == 1:
            if has_heavy_rain:
                seven_day_schedule.append("Day 1: SKIP irrigation. Forecasted heavy rainfall will replenish soil.")
            else:
                seven_day_schedule.append(f"Day 1: Apply standard {crop.title()} watering cycle for 30 minutes in morning.")
        elif day == 3:
            if forecast_rain >= 15.0:
                seven_day_schedule.append("Day 3: SKIP irrigation. Rainfall forecasted in next 24 hours.")
            else:
                seven_day_schedule.append("Day 3: Alternate Furrow/Drip cycle. Ensure zero standing water.")
        elif day == 5:
            seven_day_schedule.append("Day 5: Check soil moisture manually. If damp, delay watering by 24 hours.")
        elif day == 7:
            if has_heavy_rain:
                seven_day_schedule.append("Day 7: Drain any excess water from lower plots to prevent root waterlogging.")
            else:
                seven_day_schedule.append("Day 7: Run normal light irrigation. Verify discharge pressure of borewell.")
        else:
            seven_day_schedule.append(f"Day {day}: Monitor weather alerts.")
            
    # 3. Mulching advice
    if soil_lower == "sandy":
        mulching_advice = "CRITICAL: Sandy soil dries very quickly. Apply 25-micron plastic mulch sheets or 3-inch thick crop residue mulch to cut moisture evaporation by 50%."
    else:
        mulching_advice = "Spread organic straw/biomass mulch along crop lines to suppress weeds and lock in soil moisture."
        
    # 4. Farm pond recommendation
    if water_availability.lower() == "low" or water_source.lower() == "rainfed":
        farm_pond = "Highly recommended to construct a 20m x 20m x 3m farm pond lined with HDPE sheets. Capture monsoon runoff to provide survival irrigation during dry spells."
    else:
        farm_pond = "A small farm pond can act as a secondary buffer, though canal/borewell provides main security."
        
    # 5. Subsidies
    if income_level.lower() == "low" or income_level.lower() == "medium":
        subsidy_suggestion = "PM Krishi Sinchayee Yojana (PMKSY): Small & marginal farmers get up to 90% subsidy for micro-irrigation systems (drip/sprinkler). Contact your mandal agriculture officer."
    else:
        subsidy_suggestion = "Standard micro-irrigation subsidy of 70% is applicable. Apply on the state horticulture portal."
        
    # 6. Expected Benefit & Risk Warnings
    expected_benefit = f"By adopting this plan, you will reduce water usage by 25-45% and increase fertilizer use efficiency by preventing leaching."
    
    if crop_lower == "paddy" and water_source.lower() == "borewell" and water_availability.lower() == "low":
        risk_warning = "HIGH RISK: Borewell water levels may deplete before the crop reaches grain filling stage. Consider shifting 50% of the land to cotton or groundnut."
    elif has_heavy_rain:
        risk_warning = "HEAVY RAIN WARNING: Ensure field drains are clear. Standing water in cotton or chilli causes root rot and damping-off within 48 hours."
    else:
        risk_warning = "Keep a watch on daily temperature spikes. Heat stress increases crop transpirational demand."
        
    return {
        "best_practice": best_practice,
        "low_cost_alternative": low_cost_alternative,
        "seven_day_schedule": seven_day_schedule,
        "mulching_advice": mulching_advice,
        "farm_pond": farm_pond,
        "subsidy_suggestion": subsidy_suggestion,
        "expected_benefit": expected_benefit,
        "risk_warning": risk_warning
    }
