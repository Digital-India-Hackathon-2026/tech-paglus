import re
from hashlib import sha256

from models.schemas import LocationData
from services.http_client import ApiError, get_json


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

FALLBACK_LOCATIONS = {
    "hyderabad": LocationData(name="Hyderabad", latitude=17.385, longitude=78.4867, country="India", state="Telangana"),
    "warangal": LocationData(name="Warangal", latitude=17.9689, longitude=79.5941, country="India", state="Telangana"),
    "hanamkonda": LocationData(name="Hanamkonda", latitude=18.0072, longitude=79.5584, country="India", state="Telangana"),
    "nizamabad": LocationData(name="Nizamabad", latitude=18.6725, longitude=78.0941, country="India", state="Telangana"),
    "karimnagar": LocationData(name="Karimnagar", latitude=18.4386, longitude=79.1288, country="India", state="Telangana"),
    "khammam": LocationData(name="Khammam", latitude=17.2473, longitude=80.1514, country="India", state="Telangana"),
    "adilabad": LocationData(name="Adilabad", latitude=19.6641, longitude=78.532, country="India", state="Telangana"),
    "medak": LocationData(name="Medak", latitude=18.0453, longitude=78.2608, country="India", state="Telangana"),
    "suryapet": LocationData(name="Suryapet", latitude=17.1405, longitude=79.6205, country="India", state="Telangana"),
    "mahabubnagar": LocationData(name="Mahabubnagar", latitude=16.7488, longitude=78.0035, country="India", state="Telangana"),
    "guntur": LocationData(name="Guntur", latitude=16.3067, longitude=80.4365, country="India", state="Andhra Pradesh"),
    "vijayawada": LocationData(name="Vijayawada", latitude=16.5062, longitude=80.648, country="India", state="Andhra Pradesh"),
    "kurnool": LocationData(name="Kurnool", latitude=15.8281, longitude=78.0373, country="India", state="Andhra Pradesh"),
    "anantapur": LocationData(name="Anantapur", latitude=14.6819, longitude=77.6006, country="India", state="Andhra Pradesh"),
    "tirupati": LocationData(name="Tirupati", latitude=13.6288, longitude=79.4192, country="India", state="Andhra Pradesh"),
    "visakhapatnam": LocationData(name="Visakhapatnam", latitude=17.6868, longitude=83.2185, country="India", state="Andhra Pradesh"),
    "nellore": LocationData(name="Nellore", latitude=14.4426, longitude=79.9865, country="India", state="Andhra Pradesh"),
    "bengaluru": LocationData(name="Bengaluru", latitude=12.9716, longitude=77.5946, country="India", state="Karnataka"),
    "bangalore": LocationData(name="Bengaluru", latitude=12.9716, longitude=77.5946, country="India", state="Karnataka"),
    "raichur": LocationData(name="Raichur", latitude=16.2076, longitude=77.3463, country="India", state="Karnataka"),
    "hubballi": LocationData(name="Hubballi", latitude=15.3647, longitude=75.124, country="India", state="Karnataka"),
    "mysuru": LocationData(name="Mysuru", latitude=12.2958, longitude=76.6394, country="India", state="Karnataka"),
    "belagavi": LocationData(name="Belagavi", latitude=15.8497, longitude=74.4977, country="India", state="Karnataka"),
    "nagpur": LocationData(name="Nagpur", latitude=21.1458, longitude=79.0882, country="India", state="Maharashtra"),
    "pune": LocationData(name="Pune", latitude=18.5204, longitude=73.8567, country="India", state="Maharashtra"),
    "aurangabad": LocationData(name="Aurangabad", latitude=19.8762, longitude=75.3433, country="India", state="Maharashtra"),
    "amravati": LocationData(name="Amravati", latitude=20.9374, longitude=77.7796, country="India", state="Maharashtra"),
}


def get_location(location_name: str, gps_lat: float | None = None, gps_lon: float | None = None) -> LocationData:
    from services.geocode_api import verify_location_gps
    verify_result = verify_location_gps(location_name, gps_lat, gps_lon)
    return LocationData(
        name=verify_result["resolved_address"],
        latitude=verify_result["latitude"],
        longitude=verify_result["longitude"],
        country=verify_result["country"],
        state=verify_result["state"],
        verification_status=verify_result["status"],
        confidence_score=verify_result["confidence"],
        verification_notes=verify_result["notes"]
    )


def _geocode_best_effort(location_name: str) -> dict | None:
    for query in _candidate_queries(location_name):
        try:
            data = get_json(
                GEOCODING_URL,
                {
                    "name": query,
                    "count": 5,
                    "language": "en",
                    "format": "json",
                },
            )
        except ApiError:
            continue

        result = _pick_india_result(data.get("results", []), location_name)
        if result:
            return result
    return None


def _candidate_queries(location_name: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"[,|/]", location_name) if part.strip()]
    candidates = [location_name]
    candidates.extend(parts)
    if len(parts) >= 2:
        candidates.extend([", ".join(parts[index:]) for index in range(1, len(parts))])
    return list(dict.fromkeys(candidates))


def _pick_india_result(results: list[dict], original: str) -> dict | None:
    if not results:
        return None
    india_results = [item for item in results if str(item.get("country", "")).lower() == "india"]
    results = india_results or results
    guessed_state = _guess_state(original)
    if guessed_state:
        for result in results:
            if str(result.get("admin1", "")).lower() == guessed_state.lower():
                return result
    return results[0]


def _fallback_from_parts(location_name: str) -> LocationData | None:
    normalized = location_name.lower()
    for key, fallback in FALLBACK_LOCATIONS.items():
        if re.search(rf"\b{re.escape(key)}\b", normalized):
            return _refine_fallback_location(location_name, fallback, key)
    tokens = [part.strip().lower() for part in re.split(r"[,|/]", normalized) if part.strip()]
    tokens.extend(re.findall(r"[a-z]+(?:\s+[a-z]+)?", normalized))
    for token in tokens:
        if token in FALLBACK_LOCATIONS:
            fallback = FALLBACK_LOCATIONS[token]
            return _refine_fallback_location(location_name, fallback, token)
    return None


def _refine_fallback_location(location_name: str, fallback: LocationData, matched_key: str) -> LocationData:
    if location_name.strip().lower() == matched_key:
        return fallback

    digest = sha256(location_name.lower().encode("utf-8")).hexdigest()
    north_south = (int(digest[:4], 16) % 1201 - 600) / 100000
    east_west = (int(digest[4:8], 16) % 1201 - 600) / 100000
    return fallback.model_copy(
        update={
            "name": location_name,
            "latitude": round(fallback.latitude + north_south, 6),
            "longitude": round(fallback.longitude + east_west, 6),
        }
    )


def _clean_location(location_name: str) -> str:
    return re.sub(r"\s+", " ", location_name.replace("\n", ", ")).strip(" ,")


def _parse_coordinates(location_name: str) -> tuple[float, float] | None:
    patterns = [
        r"(?:lat(?:itude)?\s*[:=]?\s*)?(-?\d{1,2}\.\d+)\s*[, ]+\s*(?:lon(?:gitude)?\s*[:=]?\s*)?(-?\d{2,3}\.\d+)",
        r"(-?\d{1,2}\.\d+)\s*[NS]?\s*,?\s*(-?\d{2,3}\.\d+)\s*[EW]?",
    ]
    for pattern in patterns:
        match = re.search(pattern, location_name, flags=re.IGNORECASE)
        if not match:
            continue
        latitude = float(match.group(1))
        longitude = float(match.group(2))
        if 6 <= latitude <= 38 and 68 <= longitude <= 98:
            return latitude, longitude
    return None


def _guess_state(location_name: str) -> str | None:
    lower = location_name.lower()
    state_aliases = {
        "Telangana": ["telangana", "ts"],
        "Andhra Pradesh": ["andhra pradesh", "andhra", "ap"],
        "Karnataka": ["karnataka", "ka"],
        "Maharashtra": ["maharashtra", "mh"],
    }
    for state, aliases in state_aliases.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", lower) for alias in aliases):
            return state
    for key, value in FALLBACK_LOCATIONS.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            return value.state
    return None


def _display_name(original: str, result: dict) -> str:
    admin_parts = [result.get("name"), result.get("admin2"), result.get("admin1")]
    detected = ", ".join(part for part in admin_parts if part)
    if len(original) > len(str(result.get("name", ""))) + 5:
        return original
    return detected or original
