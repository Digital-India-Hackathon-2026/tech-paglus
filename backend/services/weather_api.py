from models.schemas import ApiStatus, LocationData
from services.http_client import ApiError, get_json

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

def get_weather_forecast(location: LocationData, forecast_days: int = 3) -> ApiStatus:
    hourly = [
        "temperature_2m",
        "relative_humidity_2m",
        "rain",
        "showers",
        "precipitation_probability",
        "wind_speed_10m",
        "wind_gusts_10m",
        "soil_moisture_0_to_1cm",
        "et0_fao_evapotranspiration",
    ]

    try:
        data = get_json(
            FORECAST_URL,
            {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "hourly": ",".join(hourly),
                "forecast_days": forecast_days,
                "timezone": "auto",
            },
        )
        
        # Analyze parameters and add helper metrics
        if "hourly" in data:
            temp = data["hourly"].get("temperature_2m", [])
            rh = data["hourly"].get("relative_humidity_2m", [])
            wind = data["hourly"].get("wind_speed_10m", [])
            rain = data["hourly"].get("rain", [])
            showers = data["hourly"].get("showers", [])
            
            total_rain = sum(r for r in rain if r) + sum(s for s in showers if s)
            
            # Check spray safety window
            # Pesticide spray is optimal if wind is 5-15 km/h, temp < 34C, and no rain
            safe_hours = []
            for idx in range(min(len(temp), 24)):
                t_val = temp[idx] if idx < len(temp) else 30
                w_val = wind[idx] if idx < len(wind) else 10
                r_val = (rain[idx] or 0) + (showers[idx] or 0) if idx < len(rain) else 0
                
                is_safe = (5.0 <= w_val <= 18.0) and (t_val < 35.0) and (r_val == 0)
                safe_hours.append(is_safe)
                
            data["analysis"] = {
                "total_precipitation_72h": round(total_rain, 1),
                "safe_spraying_hours_next_24h": sum(1 for h in safe_hours if h),
                "pest_humidity_index": "High" if any(h > 80 for h in rh[:24]) else "Moderate",
                "heat_stress_hours": sum(1 for t in temp[:24] if t > 38.0),
                "soil_sowing_moisture_fit": "Favorable" if any(0.15 <= m <= 0.35 for m in data["hourly"].get("soil_moisture_0_to_1cm", [])) else "Dry"
            }
            
        return ApiStatus(source="Open-Meteo Forecast API", data=data)
    except ApiError as exc:
        return ApiStatus(
            source="Open-Meteo Forecast API",
            configured=True,
            message=f"weather api failed: {exc}",
            data={},
        )
