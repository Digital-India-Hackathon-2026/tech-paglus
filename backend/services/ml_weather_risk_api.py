from __future__ import annotations

import math
from statistics import mean

from models.schemas import ApiStatus, FarmRequest


def get_ml_weather_risk(
    farm: FarmRequest,
    weather: ApiStatus,
    historical_weather: ApiStatus,
    satellite: ApiStatus,
) -> ApiStatus:
    features = _build_features(farm, weather, historical_weather, satellite)
    weights = _train_tiny_weather_model()
    raw_score = weights["bias"] + sum(features[key] * weights[key] for key in weights if key != "bias")
    danger_probability = 1 / (1 + math.exp(-raw_score))
    danger_score = round(danger_probability * 100)

    if danger_score >= 70:
        label = "HIGH"
        action = "Postpone spraying/fertilizer, secure drainage, and monitor rain/wind every 6 hours."
    elif danger_score >= 40:
        label = "MEDIUM"
        action = "Proceed carefully; keep irrigation and drainage flexible for the next 2-3 days."
    else:
        label = "LOW"
        action = "Weather danger is low, but keep routine crop monitoring active."

    return ApiStatus(
        source="Local ML Weather-Risk Model",
        configured=True,
        message="forecast compared with location-specific historical climate baseline",
        data={
            "model": "tiny-logistic-risk-v1",
            "trained_on": "synthetic agronomic stress patterns calibrated against forecast and historical features",
            "danger_score": danger_score,
            "risk_level": label,
            "recommended_action": action,
            "features": features,
            "weights": weights,
        },
    )


def _build_features(
    farm: FarmRequest,
    weather: ApiStatus,
    historical_weather: ApiStatus,
    satellite: ApiStatus,
) -> dict[str, float]:
    hourly = weather.data.get("hourly", {}) if weather.data else {}
    daily = historical_weather.data.get("daily", {}) if historical_weather.data else {}
    nasa = satellite.data.get("properties", {}).get("parameter", {}) if satellite.data else {}

    forecast_rain = _sum(hourly.get("rain", [])) + _sum(hourly.get("showers", []))
    forecast_temp_max = _max(hourly.get("temperature_2m", []), default=32)
    forecast_wind_max = _max((hourly.get("wind_speed_10m", []) or []) + (hourly.get("wind_gusts_10m", []) or []), default=12)
    forecast_et0 = _sum(hourly.get("et0_fao_evapotranspiration", []))
    rain_probability = _max(hourly.get("precipitation_probability", []), default=30) / 100

    historic_rain_mean = mean(_numbers(daily.get("precipitation_sum", []))) if daily else 4
    historic_temp_max = mean(_numbers(daily.get("temperature_2m_max", []))) if daily else 34
    historic_wind_max = mean(_numbers(daily.get("wind_speed_10m_max", []))) if daily else 14
    nasa_recent_rain = _dict_sum(nasa.get("PRECTOTCORR", {}))

    rain_anomaly = max(0.0, (forecast_rain - historic_rain_mean * 3) / 50)
    heat_anomaly = max(0.0, (forecast_temp_max - historic_temp_max) / 8)
    wind_anomaly = max(0.0, (forecast_wind_max - historic_wind_max) / 25)
    dryness = max(0.0, (forecast_et0 - forecast_rain * 0.35) / 14)
    satellite_rain_signal = min(1.5, nasa_recent_rain / 80)
    low_land = 1.0 if farm.land_type.lower() in {"low", "lowland", "low-lying"} else 0.0
    high_land = 1.0 if farm.land_type.lower() in {"high", "highland"} else 0.0
    no_irrigation = 0.0 if farm.irrigation_available else 1.0

    return {
        "rain_anomaly": round(rain_anomaly, 3),
        "heat_anomaly": round(heat_anomaly, 3),
        "wind_anomaly": round(wind_anomaly, 3),
        "dryness": round(dryness, 3),
        "rain_probability": round(rain_probability, 3),
        "satellite_rain_signal": round(satellite_rain_signal, 3),
        "low_land": low_land,
        "high_land": high_land,
        "no_irrigation": no_irrigation,
    }


def _train_tiny_weather_model() -> dict[str, float]:
    samples = [
        ({"rain_anomaly": 0.0, "heat_anomaly": 0.1, "wind_anomaly": 0.0, "dryness": 0.2, "rain_probability": 0.2, "satellite_rain_signal": 0.1, "low_land": 0, "high_land": 0, "no_irrigation": 0}, 0),
        ({"rain_anomaly": 1.1, "heat_anomaly": 0.1, "wind_anomaly": 0.2, "dryness": 0.0, "rain_probability": 0.9, "satellite_rain_signal": 1.0, "low_land": 1, "high_land": 0, "no_irrigation": 0}, 1),
        ({"rain_anomaly": 0.1, "heat_anomaly": 1.2, "wind_anomaly": 0.1, "dryness": 1.1, "rain_probability": 0.1, "satellite_rain_signal": 0.0, "low_land": 0, "high_land": 1, "no_irrigation": 1}, 1),
        ({"rain_anomaly": 0.1, "heat_anomaly": 0.2, "wind_anomaly": 1.4, "dryness": 0.2, "rain_probability": 0.5, "satellite_rain_signal": 0.3, "low_land": 0, "high_land": 0, "no_irrigation": 0}, 1),
        ({"rain_anomaly": 0.2, "heat_anomaly": 0.0, "wind_anomaly": 0.0, "dryness": 0.3, "rain_probability": 0.4, "satellite_rain_signal": 0.2, "low_land": 0, "high_land": 0, "no_irrigation": 0}, 0),
        ({"rain_anomaly": 0.0, "heat_anomaly": 0.8, "wind_anomaly": 0.0, "dryness": 0.9, "rain_probability": 0.1, "satellite_rain_signal": 0.0, "low_land": 0, "high_land": 1, "no_irrigation": 1}, 1),
    ]
    feature_names = list(samples[0][0].keys())
    weights = {name: 0.0 for name in feature_names}
    bias = -0.8
    learning_rate = 0.18

    for _ in range(180):
        for feature_values, label in samples:
            raw = bias + sum(weights[name] * feature_values[name] for name in feature_names)
            prediction = 1 / (1 + math.exp(-raw))
            error = label - prediction
            bias += learning_rate * error
            for name in feature_names:
                weights[name] += learning_rate * error * feature_values[name]

    return {"bias": round(bias, 3), **{name: round(value, 3) for name, value in weights.items()}}


def _numbers(values: list | dict) -> list[float]:
    if isinstance(values, dict):
        values = list(values.values())
    return [float(value) for value in values if value is not None]


def _sum(values: list | dict) -> float:
    return sum(_numbers(values))


def _dict_sum(values: dict | list) -> float:
    return _sum(values)


def _max(values: list, default: float) -> float:
    numbers = _numbers(values)
    return max(numbers, default=default)
