from typing import Any
import logging
from models.schemas import LocationData, ApiStatus

def calculate_monsoon_risk(location: LocationData, weather: ApiStatus, historical: ApiStatus) -> dict[str, Any]:
    """
    Computes monsoon-related agricultural risks:
    - monsoon_delay_risk: risk score (0-100) that monsoon is late / insufficient
    - moisture_deficit_risk: risk score (0-100) of lack of soil moisture
    - overall_monsoon_risk: weighted score
    - explanation: text describing the current monsoon outlook
    """
    import services.weather_api as wapi
    
    # Defaults
    delay_risk = 25
    deficit_risk = 20
    explanation = "Normal monsoon behavior expected. Standard sowing window is open."
    
    # Extract forecast rain
    forecast_rain = 0.0
    if weather and weather.data:
        hourly = weather.data.get("hourly", {})
        rain = hourly.get("rain", []) or []
        showers = hourly.get("showers", []) or []
        forecast_rain = sum(r for r in rain if r) + sum(s for s in showers if s)
        
    # Extract historical rain anomaly (last 30 days compared to normal if available, or static index)
    hist_rain_low = False
    if historical and historical.data:
        daily = historical.data.get("daily", {})
        precip = daily.get("precipitation_sum", []) or []
        # sum of precipitation in the last 15 days
        recent_rain = sum(p for p in precip[-15:] if p)
        if recent_rain < 20.0:
            hist_rain_low = True
            
    # Calculate risks based on location and season
    state = (location.state or "Unknown").lower()
    
    # South/Central India Kharif rainfall patterns
    is_south_india = any(s in state for s in ("telangana", "andhra", "karnataka", "tamil", "maharashtra"))
    
    if is_south_india:
        if forecast_rain < 10.0:
            delay_risk = 65
            deficit_risk = 55
            explanation = "Late monsoon spell detected. Shortage of rain forecast for the next 7 days in this region. Sowing paddy might face delay; consider dry-sowing cotton or shifting to maize/groundnut."
        else:
            delay_risk = 30
            deficit_risk = 25
            explanation = "Good rainfall forecast. Soil moisture levels are favorable for sowing Kharif crops."
            
        if hist_rain_low and forecast_rain < 5.0:
            delay_risk = 85
            deficit_risk = 75
            explanation = "ALERT: severe dry spell. Rain deficit detected over the past fortnight. Delay sowing or irrigate immediately if borewell is available. Prefer crop mulching."
    else:
        # Default behavior
        if forecast_rain < 5.0:
            delay_risk = 45
            deficit_risk = 40
            explanation = "Moderate moisture deficit. Maintain irrigation scheduling."
            
    overall_risk = int(0.6 * delay_risk + 0.4 * deficit_risk)
    
    return {
        "monsoon_delay_risk": delay_risk,
        "moisture_deficit_risk": deficit_risk,
        "overall_monsoon_risk": overall_risk,
        "explanation": explanation
    }
