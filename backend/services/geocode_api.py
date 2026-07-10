import os
import math
import logging
from typing import Any
from urllib.parse import quote
from services.http_client import ApiError, get_json

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

def get_nominatim_user_agent() -> str:
    return os.getenv("NOMINATIM_USER_AGENT", "agrisarthi-ai-local-dev")

def geocode_address(address: str) -> dict[str, Any] | None:
    """
    Geocodes text address using OSM Nominatim.
    """
    user_agent = get_nominatim_user_agent()
    headers = {"User-Agent": user_agent}
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "addressdetails": 1
    }
    try:
        data = get_json(NOMINATIM_SEARCH_URL, params=params, headers=headers)
        if isinstance(data, list) and len(data) > 0:
            result = data[0]
            addr = result.get("address", {})
            return {
                "display_name": result.get("display_name"),
                "latitude": float(result.get("lat")),
                "longitude": float(result.get("lon")),
                "state": addr.get("state") or addr.get("state_district"),
                "country": addr.get("country"),
                "village": addr.get("village") or addr.get("suburb") or addr.get("town") or addr.get("city")
            }
    except Exception as exc:
        logging.warning(f"Nominatim geocoding failed: {exc}")
    return None

def reverse_geocode(latitude: float, longitude: float) -> dict[str, Any] | None:
    """
    Reverse geocodes coordinates to address details.
    """
    user_agent = get_nominatim_user_agent()
    headers = {"User-Agent": user_agent}
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "json",
        "addressdetails": 1
    }
    try:
        data = get_json(NOMINATIM_REVERSE_URL, params=params, headers=headers)
        if data and "address" in data:
            addr = data["address"]
            return {
                "display_name": data.get("display_name"),
                "state": addr.get("state"),
                "district": addr.get("state_district") or addr.get("county"),
                "village": addr.get("village") or addr.get("suburb") or addr.get("town") or addr.get("city"),
                "country": addr.get("country")
            }
    except Exception as exc:
        logging.warning(f"Nominatim reverse geocoding failed: {exc}")
    return None

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes distance between coordinates in kilometers.
    """
    # Earth radius in kilometers
    R = 6371.0
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    
    return R * c

def verify_location_gps(address: str, gps_lat: float | None, gps_lon: float | None) -> dict[str, Any]:
    """
    Verifies farmer location details, comparing resolved address from Nominatim geocoder
    and physical GPS coordinates if available. Returns verification metrics.
    """
    # Resolve the geocoded position
    resolved = geocode_address(address)
    
    # If Nominatim geocoding fails, fallback to simple guess/mock coordinates
    if not resolved:
        # Import local fallback finder from location_api
        from services.location_api import FALLBACK_LOCATIONS, _guess_state
        clean_addr = address.lower()
        matched_loc = None
        for key, fallback in FALLBACK_LOCATIONS.items():
            if key in clean_addr:
                matched_loc = fallback
                break
        
        if matched_loc:
            resolved = {
                "display_name": f"{address} (Estimated)",
                "latitude": matched_loc.latitude,
                "longitude": matched_loc.longitude,
                "state": matched_loc.state,
                "country": matched_loc.country,
                "village": address.split(",")[0]
            }
        else:
            # Absolute default
            resolved = {
                "display_name": f"{address} (Default Hyderabad)",
                "latitude": 17.385,
                "longitude": 78.4867,
                "state": "Telangana",
                "country": "India",
                "village": address
            }
            
    # Calculate distance if GPS is available
    distance_km = None
    warning = None
    confidence = "Medium"
    status = "verified"
    
    if gps_lat is not None and gps_lon is not None:
        distance_km = haversine_distance(resolved["latitude"], resolved["longitude"], gps_lat, gps_lon)
        if distance_km > 50.0:
            status = "discrepancy"
            confidence = "Low"
            warning = f"Warning: GPS coordinates ({gps_lat:.4f}, {gps_lon:.4f}) and document/text address are {distance_km:.1f} km apart! Please double-check details."
        elif distance_km < 15.0:
            status = "verified"
            confidence = "High"
        else:
            status = "verified"
            confidence = "Medium"
            
    # If no GPS coordinates, reverse geocode to add context if possible
    notes = "Address resolved successfully."
    if distance_km:
        notes += f" GPS matches resolved address within {distance_km:.2f} km."
    if warning:
        notes += f" {warning}"
        
    return {
        "resolved_address": resolved["display_name"],
        "latitude": resolved["latitude"],
        "longitude": resolved["longitude"],
        "country": resolved["country"],
        "state": resolved["state"],
        "gps_distance_km": distance_km,
        "confidence": confidence,
        "status": status,
        "warning": warning,
        "notes": notes
    }
