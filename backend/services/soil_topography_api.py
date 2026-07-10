from models.schemas import ApiStatus, LocationData
from services.http_client import ApiError, get_json


ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"


def get_soil_topography(location: LocationData, weather_status: ApiStatus) -> ApiStatus:
    try:
        elevation_data = get_json(
            ELEVATION_URL,
            {
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
        )
    except ApiError as exc:
        elevation_data = {"error": str(exc)}

    hourly = weather_status.data.get("hourly", {}) if weather_status.data else {}
    soil_values = [
        value
        for value in hourly.get("soil_moisture_0_to_1cm", [])
        if value is not None
    ]

    average_soil_moisture = None
    if soil_values:
        average_soil_moisture = sum(soil_values) / len(soil_values)

    return ApiStatus(
        source="Open-Meteo Elevation API + Forecast Soil Moisture",
        data={
            "elevation": elevation_data,
            "average_soil_moisture_0_to_1cm": average_soil_moisture,
        },
    )
