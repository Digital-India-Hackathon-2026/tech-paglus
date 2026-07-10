from models.schemas import ApiStatus, LocationData
from services.http_client import ApiError, get_json


RAINVIEWER_URL = "https://api.rainviewer.com/public/weather-maps.json"


def get_radar_layer(location: LocationData) -> ApiStatus:
    try:
        data = get_json(RAINVIEWER_URL)
        radar_frames = data.get("radar", {}).get("past", []) + data.get("radar", {}).get("nowcast", [])
        latest_frame = radar_frames[-1] if radar_frames else {}
        host = data.get("host", "")
        path = latest_frame.get("path", "")

        return ApiStatus(
            source="RainViewer Public Radar API",
            data={
                "latitude": location.latitude,
                "longitude": location.longitude,
                "latest_frame": latest_frame,
                "tile_url_template": f"{host}{path}/256/{{z}}/{{x}}/{{y}}/2/1_1.png" if host and path else None,
                "field_radar_tile_url": f"{host}{path}/512/7/{location.latitude:.6f}/{location.longitude:.6f}/2/1_1.png" if host and path else None,
                "coverage_tile_url": f"{host}/v2/coverage/0/512/7/{location.latitude:.6f}/{location.longitude:.6f}/0/0_0.png" if host else None,
                "precision_note": "Radar tile is centered on the resolved field coordinates.",
            },
        )
    except ApiError as exc:
        return ApiStatus(
            source="RainViewer Public Radar API",
            configured=True,
            message=f"radar api failed: {exc}",
            data={},
        )
