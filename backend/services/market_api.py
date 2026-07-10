import os
from datetime import date
from hashlib import sha256

from models.schemas import ApiStatus, LocationData
from services.http_client import ApiError, get_json


DATA_GOV_RESOURCE_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

BASE_PRICES = {
    "cotton": 7200,
    "chilli": 9500,
    "paddy": 2300,
    "maize": 2450,
    "groundnut": 6700,
    "turmeric": 8200,
}

LOCAL_MANDIS = {
    "warangal": [("Enumamula", "Telangana", 1.04), ("Jangaon", "Telangana", 0.99), ("Khammam", "Telangana", 0.97)],
    "hanamkonda": [("Enumamula", "Telangana", 1.04), ("Warangal", "Telangana", 1.0), ("Jangaon", "Telangana", 0.98)],
    "nizamabad": [("Nizamabad", "Telangana", 1.03), ("Bodhan", "Telangana", 1.0), ("Kamareddy", "Telangana", 0.97)],
    "karimnagar": [("Karimnagar", "Telangana", 1.02), ("Jagtial", "Telangana", 0.99), ("Siddipet", "Telangana", 0.96)],
    "guntur": [("Guntur", "Andhra Pradesh", 1.06), ("Tenali", "Andhra Pradesh", 1.01), ("Chilakaluripet", "Andhra Pradesh", 0.98)],
    "vijayawada": [("Vijayawada", "Andhra Pradesh", 1.03), ("Guntur", "Andhra Pradesh", 1.0), ("Eluru", "Andhra Pradesh", 0.97)],
    "kurnool": [("Kurnool", "Andhra Pradesh", 1.02), ("Nandyal", "Andhra Pradesh", 0.99), ("Anantapur", "Andhra Pradesh", 0.96)],
    "bengaluru": [("Bengaluru", "Karnataka", 1.04), ("Ramanagara", "Karnataka", 1.0), ("Tumakuru", "Karnataka", 0.97)],
    "raichur": [("Raichur", "Karnataka", 1.03), ("Yadgir", "Karnataka", 1.0), ("Ballari", "Karnataka", 0.97)],
    "nagpur": [("Nagpur", "Maharashtra", 1.03), ("Wardha", "Maharashtra", 1.0), ("Amravati", "Maharashtra", 0.98)],
    "pune": [("Pune", "Maharashtra", 1.04), ("Baramati", "Maharashtra", 1.0), ("Ahmednagar", "Maharashtra", 0.97)],
}

STATE_MANDIS = {
    "Telangana": [("Hyderabad", "Telangana", 1.02), ("Warangal", "Telangana", 1.0), ("Nizamabad", "Telangana", 0.98)],
    "Andhra Pradesh": [("Guntur", "Andhra Pradesh", 1.03), ("Vijayawada", "Andhra Pradesh", 1.0), ("Kurnool", "Andhra Pradesh", 0.97)],
    "Maharashtra": [("Nagpur", "Maharashtra", 1.02), ("Pune", "Maharashtra", 1.0), ("Amravati", "Maharashtra", 0.98)],
    "Karnataka": [("Bengaluru", "Karnataka", 1.02), ("Raichur", "Karnataka", 1.0), ("Hubballi", "Karnataka", 0.98)],
}


def get_mandi_market(crop: str, location: LocationData) -> ApiStatus:
    api_key = os.getenv("DATAGOV_API_KEY")
    if not api_key:
        return ApiStatus(
            source="data.gov.in Agmarknet API",
            configured=False,
            message="DATAGOV_API_KEY is not configured; showing locality-based mandi estimate",
            data=_local_mandi_estimate(crop, location),
        )

    filters = {"api-key": api_key, "format": "json", "limit": 10}
    if crop:
        filters["filters[commodity]"] = crop.title()
    if location.state:
        filters["filters[state]"] = location.state
    district = _district_hint(location.name)
    if district:
        filters["filters[district]"] = district

    try:
        data = get_json(DATA_GOV_RESOURCE_URL, filters)
        if data.get("records"):
            return ApiStatus(source="data.gov.in Agmarknet API", data=data)
        return ApiStatus(
            source="data.gov.in Agmarknet API",
            configured=True,
            message="no live AGMARKNET record found for this exact crop/location; showing locality-based estimate",
            data=_local_mandi_estimate(crop, location),
        )
    except ApiError as exc:
        return ApiStatus(
            source="data.gov.in Agmarknet API",
            configured=True,
            message=f"mandi api failed: {exc}; showing locality-based estimate",
            data=_local_mandi_estimate(crop, location),
        )


def _local_mandi_estimate(crop: str, location: LocationData) -> dict:
    crop_key = (crop or "cotton").strip().lower()
    base_price = BASE_PRICES.get(crop_key, 5000)
    mandi_rows = _nearby_mandis(location)
    day_factor = _stable_daily_factor(crop_key, location.name)
    records = []

    for index, (market, state, multiplier) in enumerate(mandi_rows):
        price = round(base_price * multiplier * day_factor * (1 - index * 0.012))
        records.append(
            {
                "state": state,
                "district": _district_hint(location.name) or market,
                "market": market,
                "commodity": crop_key.title(),
                "modal_price": price,
                "arrival_date": date.today().isoformat(),
                "data_quality": "estimated-local",
            }
        )

    return {
        "records": records,
        "estimated": True,
        "basis": "crop, state/district hint, nearby mandi cluster, and deterministic daily local variation",
        "latitude": location.latitude,
        "longitude": location.longitude,
    }


def _nearby_mandis(location: LocationData) -> list[tuple[str, str, float]]:
    lower_name = location.name.lower()
    for district, mandis in LOCAL_MANDIS.items():
        if district in lower_name:
            return mandis
    return STATE_MANDIS.get(location.state or "", [("Nearest Mandi", location.state or "Local Region", 1.0), ("District Mandi", location.state or "Local Region", 0.98), ("Regional Mandi", location.state or "Local Region", 0.96)])


def _stable_daily_factor(crop: str, location_name: str) -> float:
    key = f"{crop}:{location_name.lower()}:{date.today().isoformat()}"
    digest = sha256(key.encode("utf-8")).hexdigest()
    bucket = int(digest[:4], 16) % 11
    return 0.95 + bucket * 0.01


def _district_hint(location_name: str) -> str | None:
    lower_name = location_name.lower()
    for district in LOCAL_MANDIS:
        if district in lower_name:
            return district.title()
    parts = [part.strip() for part in location_name.split(",") if part.strip()]
    if len(parts) >= 2:
        return parts[-2].title()
    return None
