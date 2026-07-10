from datetime import date, timedelta

from models.schemas import ApiStatus, LocationData
from services.http_client import ApiError, get_json


NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


def get_satellite_agri_weather(location: LocationData, days_back: int = 7) -> ApiStatus:
    end = date.today()
    start = end - timedelta(days=days_back)

    params = {
        "parameters": "PRECTOTCORR,T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN",
        "community": "AG",
        "longitude": location.longitude,
        "latitude": location.latitude,
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }

    try:
        data = get_json(NASA_POWER_URL, params)
        return ApiStatus(source="NASA POWER Agroclimatology API", data=data)
    except ApiError as exc:
        return ApiStatus(
            source="NASA POWER Agroclimatology API",
            configured=True,
            message=f"satellite api failed: {exc}",
            data={},
        )
