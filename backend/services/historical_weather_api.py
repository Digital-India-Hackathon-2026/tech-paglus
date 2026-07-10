from __future__ import annotations

from datetime import date, timedelta

from models.schemas import ApiStatus, LocationData
from services.http_client import ApiError, get_json


ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def get_historical_weather(location: LocationData, days_back: int = 365) -> ApiStatus:
    end = date.today() - timedelta(days=5)
    start = end - timedelta(days=days_back)

    daily = [
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_sum",
        "wind_speed_10m_max",
        "et0_fao_evapotranspiration",
    ]

    try:
        data = get_json(
            ARCHIVE_URL,
            {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "daily": ",".join(daily),
                "timezone": "auto",
            },
            timeout=30,
        )
        return ApiStatus(source="Open-Meteo Historical Archive", data=data)
    except ApiError as exc:
        return ApiStatus(
            source="Open-Meteo Historical Archive",
            configured=True,
            message=f"historical weather api failed: {exc}",
            data={},
        )
