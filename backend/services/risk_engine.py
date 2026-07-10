from statistics import mean

from models.schemas import ApiStatus, FarmRequest, RiskScores


def _numbers(values: list | dict) -> list[float]:
    if isinstance(values, dict):
        values = list(values.values())
    return [float(value) for value in values if value is not None]


def calculate_risk(
    farm: FarmRequest,
    weather: ApiStatus,
    soil_topography: ApiStatus,
    satellite: ApiStatus | None = None,
    historical_weather: ApiStatus | None = None,
) -> RiskScores:
    hourly = weather.data.get("hourly", {}) if weather.data else {}

    rain = _numbers(hourly.get("rain", []))
    showers = _numbers(hourly.get("showers", []))
    precipitation_probability = _numbers(hourly.get("precipitation_probability", []))
    wind = _numbers(hourly.get("wind_speed_10m", []))
    gusts = _numbers(hourly.get("wind_gusts_10m", []))
    temperature = _numbers(hourly.get("temperature_2m", []))
    evapotranspiration = _numbers(hourly.get("et0_fao_evapotranspiration", []))

    rain_total = sum(rain) + sum(showers)
    peak_rain = max(rain + showers, default=0.0)
    rain_chance = max(precipitation_probability, default=0.0)
    max_temp = max(temperature, default=0.0)
    max_wind = max(wind + gusts, default=0.0)
    et0_total = sum(evapotranspiration)
    historical_daily = historical_weather.data.get("daily", {}) if historical_weather and historical_weather.data else {}
    historical_rain = _numbers(historical_daily.get("precipitation_sum", []))
    historical_temp = _numbers(historical_daily.get("temperature_2m_max", []))
    historical_wind = _numbers(historical_daily.get("wind_speed_10m_max", []))
    normal_daily_rain = mean(historical_rain) if historical_rain else 4
    normal_max_temp = mean(historical_temp) if historical_temp else 34
    normal_wind = mean(historical_wind) if historical_wind else 14

    satellite_params = satellite.data.get("properties", {}).get("parameter", {}) if satellite and satellite.data else {}
    satellite_rain = sum(_numbers(satellite_params.get("PRECTOTCORR", {})))

    soil_moisture = soil_topography.data.get("average_soil_moisture_0_to_1cm")
    low_land_bonus = 15 if farm.land_type.lower() in {"low", "lowland", "low-lying"} else 0
    high_land_bonus = 10 if farm.land_type.lower() in {"high", "highland"} else 0

    rain_anomaly_bonus = max(0, rain_total - normal_daily_rain * 3) * 1.4
    satellite_rain_bonus = min(18, satellite_rain * 0.18)
    flood = min(100, round(rain_total * 2.5 + peak_rain * 5 + rain_chance * 0.25 + low_land_bonus + rain_anomaly_bonus + satellite_rain_bonus))
    drought_base = 45 if soil_moisture is None else max(0, (0.35 - soil_moisture) * 220)
    drought = min(100, round(drought_base + et0_total * 4 + high_land_bonus + max(0, normal_daily_rain * 2 - rain_total) * 1.8 - rain_total * 1.5))
    heat = min(100, round(max(0, max_temp - 32) * 7 + max(0, max_temp - normal_max_temp) * 6))
    wind_risk = min(100, round(max_wind * 1.1 + max(0, max_wind - normal_wind) * 2.2))

    overall = round((flood + drought + heat + wind_risk) / 4)
    if overall >= 70:
        level = "HIGH"
    elif overall >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"

    return RiskScores(
        flood=max(0, flood),
        drought=max(0, drought),
        heat=max(0, heat),
        wind=max(0, wind_risk),
        overall=max(0, min(100, overall)),
        level=level,
    )
