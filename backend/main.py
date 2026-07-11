from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from models.schemas import (
    AdvisoryResponse,
    DocumentIntakeAnalysis,
    FarmRequest,
    ConsentRequest,
    FeedbackRequest,
    LocationVerifyRequest,
    LocationVerifyResponse,
    MemoryResponse,
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    UserOut,
)
from services.advisory_api import get_ai_advisory
from services.crop_knowledge_api import get_crop_knowledge
from services.document_intake_api import analyze_farmer_documents
from services.historical_weather_api import get_historical_weather
from services.location_api import get_location
from services.market_api import get_mandi_market
from services.ml_weather_risk_api import get_ml_weather_risk
from services.production_features_api import build_production_feature_bundle
from services.radar_api import get_radar_layer
from services.recommendation_engine import build_crop_advisory
from services.risk_engine import calculate_risk
from services.satellite_api import get_satellite_agri_weather
from services.soil_topography_api import get_soil_topography
from services.soil_report_api import analyze_soil_report
from services.weather_api import get_weather_forecast

from services.agent_memory import (
    init_db,
    set_consent,
    get_consent,
    save_profile,
    get_profile,
    save_feedback,
    get_feedback_history,
)
from services.monsoon_risk_api import calculate_monsoon_risk
from services.irrigation_api import get_irrigation_advisory
from services.fertilizer_api import calculate_fertilizer_plan
from services.scheme_api import match_government_schemes
from services.voice_summary_api import generate_voice_summary
from services.geocode_api import verify_location_gps
from models.schemas import ApiStatus, RiskScores, CropRecommendation
from services.auth_service import (
    AuthError,
    init_auth_db,
    register_user,
    authenticate_user,
    create_token,
    decode_token,
    get_user_by_id,
)

import logging
import time
from concurrent.futures import ThreadPoolExecutor

load_dotenv()
init_db()  # Initialize SQLite database tables
init_auth_db()  # Initialize the users table

app = FastAPI(
    title="AgriSarthi AI Web API",
    description="Crop, mandi, seed, fertilizer, weather-risk and FPO dashboard backend.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Performance helpers
# ---------------------------------------------------------------------------
# create_advisory() makes ~7 sequential outbound HTTP calls (weather, radar,
# satellite, historical weather, soil topography, mandi, crop knowledge).
# The frontend's "Get personalized advice" flow calls it once directly
# (/api/recommend) and once more indirectly (/api/advisory-ui) with the same
# inputs, milliseconds apart. _EXECUTOR runs the independent calls inside
# create_advisory concurrently, and _ADVISORY_CACHE avoids doing that work
# twice for the same request.
_EXECUTOR = ThreadPoolExecutor(max_workers=8)
_ADVISORY_CACHE: dict[str, tuple[float, "AdvisoryResponse"]] = {}
_ADVISORY_CACHE_TTL_SECONDS = 90


def _advisory_cache_key(farm: FarmRequest) -> str:
    return "|".join(
        str(v)
        for v in (
            farm.farmer_name,
            farm.location,
            round(farm.gps_latitude or 0, 4),
            round(farm.gps_longitude or 0, 4),
            farm.crop,
            farm.soil_type,
            farm.season,
            farm.land_type,
            farm.farm_area_acres,
            farm.budget_per_acre,
            farm.irrigation_available,
            farm.preferred_language,
        )
    )


def _advisory_cache_get(key: str):
    hit = _ADVISORY_CACHE.get(key)
    if not hit:
        return None
    saved_at, value = hit
    if time.time() - saved_at > _ADVISORY_CACHE_TTL_SECONDS:
        _ADVISORY_CACHE.pop(key, None)
        return None
    return value


def _advisory_cache_set(key: str, value: "AdvisoryResponse") -> None:
    _ADVISORY_CACHE[key] = (time.time(), value)
    # keep the cache small
    if len(_ADVISORY_CACHE) > 200:
        oldest_key = min(_ADVISORY_CACHE, key=lambda k: _ADVISORY_CACHE[k][0])
        _ADVISORY_CACHE.pop(oldest_key, None)


@app.get("/")
def health_check() -> dict:
    return {
        "status": "running",
        "message": "Use POST /api/advisory to get AgriSarthi crop recommendations and farmer advice.",
    }


# ---------------------------------------------------------------------------
# Authentication (register / login / current user)
# ---------------------------------------------------------------------------

def get_current_user(request: Request) -> dict:
    """Extracts and validates the Bearer token, returning the current user."""
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header.split(" ", 1)[1].strip()
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Session expired or invalid. Please log in again.")
    user = get_user_by_id(payload.get("uid"))
    if not user:
        raise HTTPException(status_code=401, detail="Account not found. Please log in again.")
    return user


@app.post("/api/auth/register", response_model=AuthResponse)
def auth_register(payload: RegisterRequest) -> AuthResponse:
    try:
        user = register_user(
            name=payload.name,
            phone=payload.phone,
            password=payload.password,
            terms_accepted=payload.terms_accepted,
        )
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    token = create_token(user["id"], user["phone"])
    return AuthResponse(token=token, user=UserOut(**user))


@app.post("/api/auth/login", response_model=AuthResponse)
def auth_login(payload: LoginRequest) -> AuthResponse:
    try:
        user = authenticate_user(phone=payload.phone, password=payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    token = create_token(user["id"], user["phone"])
    return AuthResponse(token=token, user=UserOut(**user))


@app.get("/api/auth/me", response_model=UserOut)
def auth_me(current_user: dict = Depends(get_current_user)) -> UserOut:
    return UserOut(**current_user)


@app.post("/api/advisory", response_model=AdvisoryResponse)
def create_advisory(farm: FarmRequest) -> AdvisoryResponse:
    if not farm.location.strip():
        raise HTTPException(status_code=422, detail="Location is required")

    cache_key = _advisory_cache_key(farm)
    cached = _advisory_cache_get(cache_key)
    if cached is not None:
        return cached

    # 1. Check for saved farmer consent and profile (to get nutrients NPK details)
    consent = get_consent(farm.farmer_name)
    saved_profile = get_profile(farm.farmer_name) if consent else None
    nutrients = saved_profile.get("nutrients") if saved_profile else None

    # 2. Get location geocoding & verification (OSM Nominatim)
    try:
        location = get_location(farm.location, farm.gps_latitude, farm.gps_longitude)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # 3. Call forecast and other location-based APIs concurrently — these are
    # independent outbound HTTP calls, so running them on a thread pool
    # instead of one-by-one cuts this step down to the slowest single call
    # instead of the sum of all of them.
    weather_future = _EXECUTOR.submit(get_weather_forecast, location)
    radar_future = _EXECUTOR.submit(get_radar_layer, location)
    satellite_future = _EXECUTOR.submit(get_satellite_agri_weather, location)
    historical_future = _EXECUTOR.submit(get_historical_weather, location)
    mandi_future = _EXECUTOR.submit(get_mandi_market, farm.crop, location)
    crop_knowledge_future = _EXECUTOR.submit(get_crop_knowledge, farm.crop)

    weather = weather_future.result()
    radar = radar_future.result()
    satellite = satellite_future.result()
    historical_weather = historical_future.result()
    mandi_market = mandi_future.result()
    crop_knowledge = crop_knowledge_future.result()
    # soil topography depends on the resolved weather data, so it runs after
    soil_topography = get_soil_topography(location, weather)

    # 4. Analyze Monsoon & Weather risks
    monsoon_res = calculate_monsoon_risk(location, weather, historical_weather)
    risk = calculate_risk(farm, weather, soil_topography, satellite, historical_weather)
    
    # Inject monsoon & pest risk scores into the model
    risk.monsoon_risk = monsoon_res["overall_monsoon_risk"]
    humidity_high = weather.data.get("analysis", {}).get("pest_humidity_index", "Moderate") == "High" if weather.data else False
    risk.pest_disease_risk = 75 if humidity_high and farm.crop.lower() in ("chilli", "cotton") else 30
    risk.spray_window_safe = weather.data.get("analysis", {}).get("safe_spraying_hours_next_24h", 0) > 4 if weather.data else True
    risk.crop_stress_level = "High" if (weather.data.get("analysis", {}).get("heat_stress_hours", 0) > 4 if weather.data else False) else "Low"

    ml_weather_risk = get_ml_weather_risk(farm, weather, historical_weather, satellite)
    
    # 5. Build crop recommendations with soil nutrients (SHC) & dynamic budgets
    recommendations, mandi_price_comparison, ai_explanation, admin_dashboard = build_crop_advisory(
        farm=farm,
        weather=weather,
        risk=risk,
        mandi_market=mandi_market,
        location=location,
        state=location.state,
        nutrients=nutrients
    )

    # 6. Call LLM for structured JSON completes or local rules
    farmer_advice, government_alert, ai_detailed = get_ai_advisory(
        farm=farm,
        risk=risk,
        weather=weather,
        mandi_market=mandi_market,
        crop_knowledge=crop_knowledge,
    )
    
    # 7. Formulate agronomics: Irrigation advisory, fertilizer splitting & PM eligibility
    total_rain_7d = weather.data.get("analysis", {}).get("total_precipitation_72h", 0.0) if weather.data else 0.0
    irrigation_details = get_irrigation_advisory(
        water_source="borewell" if farm.irrigation_available else "rainfed",
        water_availability="medium" if farm.irrigation_available else "low",
        income_level="medium",
        soil_type=farm.soil_type,
        crop=farm.crop,
        season=farm.season,
        land_size=farm.farm_area_acres or 2.0,
        forecast_rain=total_rain_7d
    )
    
    # Calculate crop inputs from SHC (Soil Health Card) nutrients
    fertilizer_details = calculate_fertilizer_plan(farm.crop, farm.soil_type, nutrients or {})
    
    # Matching Central/State government subsidies
    scheme_matches = match_government_schemes(
        farmer_name=farm.farmer_name,
        location_name=location.name,
        state=location.state,
        crop=farm.crop,
        season=farm.season,
        land_size=farm.farm_area_acres,
        irrigation_available=farm.irrigation_available,
        has_soil_report=(nutrients is not None)
    )

    # Generate text for local voice TTS matching language choice
    best_crop_name = recommendations[0].crop if recommendations else farm.crop
    best_mandi_price = recommendations[0].mandi_prices[0].modal_price_per_quintal if recommendations and recommendations[0].mandi_prices else 6000
    
    # If the user selected Telugu/Hindi, translate main explanations
    if farm.preferred_language.lower() == "telugu":
        ai_explanation = f"వరంగల్ సమీపంలో మీ పొలానికి అత్యంత అనుకూలమైన పంట {best_crop_name}. మార్కెట్ లో మండి ధర క్వింటాలుకు సుమారు ఏడు వేల రూపాయలు."
    elif farm.preferred_language.lower() == "hindi":
        ai_explanation = f"आपके खेत के लिए सर्वोत्तम फसल {best_crop_name} है। मंडी में अनुमानित आय काफी बेहतर होने की संभावना है।"

    # 8. Trigger memory save if consent is verified
    if consent:
        profile_data = farm.model_dump()
        if nutrients:
            profile_data["nutrients"] = nutrients
        save_profile(farm.farmer_name, profile_data)

    pest_disease_alerts, original_schemes, marketplace_items, alert_plan = build_production_feature_bundle(
        farm=farm,
        location=location,
        risk=risk,
        best_crop=recommendations[0] if recommendations else None,
    )
    
    # Inject detailed agronomy results into production bundle lists
    pest_disease_alerts = [
        f"Pesticide spray safety window is {weather.data.get('analysis', {}).get('safe_spraying_hours_next_24h', 0) if weather.data else 8} hours today.",
        f"Pest infection risk is {risk.pest_disease_risk}% due to {weather.data.get('analysis', {}).get('pest_humidity_index', 'Moderate') if weather.data else 'Moderate'} humidity.",
        irrigation_details["risk_warning"]
    ]
    
    alert_plan = [
        f"Weather Alert: {monsoon_res['explanation']}",
        f"Water scheduling: {irrigation_details['best_practice']}",
        f"NPK correction: {fertilizer_details['basal']}"
    ]
    
    # Match default marketplace suggestions with soil properties
    marketplace_items = [
        {"item": "Certified Seeds Variety", "category": "Seeds", "note": f"Drought-resistant seed recommendation for {farm.crop}."},
        {"item": f"Basal mix ({fertilizer_details['urea_bags']} bags urea, {fertilizer_details['dap_bags']} bags DAP)", "category": "Fertilizer", "note": "Subsidized fertilizer available at cooperative yard."},
        {"item": "Bio-fertilizer compost", "category": "Organic", "note": irrigation_details["mulching_advice"]}
    ]

    result = AdvisoryResponse(
        location=location,
        crop=farm.crop,
        farmer_name=farm.farmer_name,
        soil_type=farm.soil_type,
        season=farm.season,
        land_type=farm.land_type,
        farm_area_acres=farm.farm_area_acres,
        budget_per_acre=farm.budget_per_acre,
        weather=weather,
        radar=radar,
        satellite=satellite,
        historical_weather=historical_weather,
        ml_weather_risk=ml_weather_risk,
        soil_topography=soil_topography,
        mandi_market=mandi_market,
        crop_knowledge=crop_knowledge,
        risk=risk,
        recommendations=recommendations,
        mandi_price_comparison=mandi_price_comparison,
        ai_explanation=ai_explanation,
        admin_dashboard=admin_dashboard,
        farmer_advice=farmer_advice,
        government_alert=government_alert,
        pest_disease_alerts=pest_disease_alerts,
        scheme_matches=scheme_matches,
        marketplace_items=marketplace_items,
        alert_plan=alert_plan,
        ai_detailed=ai_detailed,
    )
    _advisory_cache_set(cache_key, result)
    return result


@app.post("/api/recommendations", response_model=AdvisoryResponse)
def create_recommendations(farm: FarmRequest) -> AdvisoryResponse:
    return create_advisory(farm)


@app.post("/api/soil-report")
async def upload_soil_report(file: UploadFile = File(...)):
    allowed_extensions = (".pdf", ".txt")
    filename = file.filename or "soil_report"
    if not filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Upload a PDF or text soil report")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File is too large. Keep it below 8 MB")

    try:
        return await run_in_threadpool(analyze_soil_report, filename, content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not analyze soil report: {exc}") from exc


@app.post("/api/document-intake", response_model=DocumentIntakeAnalysis)
async def upload_farmer_documents(files: list[UploadFile] = File(...)) -> DocumentIntakeAnalysis:
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one PDF or text file")
    if len(files) > 2:
        raise HTTPException(status_code=400, detail="Upload only 1 or 2 files: Soil Health Card plus optional land record")

    allowed_extensions = (".pdf", ".txt")
    parsed_files: list[tuple[str, bytes]] = []
    total_size = 0

    for file in files:
        filename = file.filename or "farmer_document"
        if not filename.lower().endswith(allowed_extensions):
            raise HTTPException(status_code=400, detail=f"{filename}: upload PDF or text only")

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"{filename}: file is empty")
        total_size += len(content)
        if len(content) > 8 * 1024 * 1024 or total_size > 12 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Keep each file below 8 MB and total upload below 12 MB")
        parsed_files.append((filename, content))

    try:
        result = await run_in_threadpool(analyze_farmer_documents, parsed_files)
        # If there are soil nutrients and farmer name, store in DB if consent is already active
        if result.soil_report and result.inferred_profile.farmer_name:
            farmer_name = result.inferred_profile.farmer_name
            if get_consent(farmer_name):
                profile_data = {
                    "location": result.inferred_profile.location,
                    "crop": result.inferred_profile.crop,
                    "soil_type": result.inferred_profile.soil_type,
                    "season": result.inferred_profile.season,
                    "land_type": result.inferred_profile.land_type,
                    "irrigation_available": result.inferred_profile.irrigation_available,
                    "farm_area_acres": result.inferred_profile.farm_area_acres,
                    "budget_per_acre": result.inferred_profile.budget_per_acre,
                    "preferred_language": result.inferred_profile.preferred_language,
                    "nutrients": result.soil_report.nutrients
                }
                save_profile(farmer_name, profile_data)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not analyze farmer documents: {exc}") from exc


@app.post("/api/feedback")
def record_feedback(req: FeedbackRequest):
    try:
        save_feedback(
            farmer_name=req.farmer_name,
            crop=req.crop,
            location=req.location,
            soil_type=req.soil_type,
            useful=req.useful,
            rating=req.rating,
            comments=req.comments
        )
        return {"status": "success", "message": "Feedback recorded."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/memory", response_model=MemoryResponse)
def get_memory(farmer_name: str) -> MemoryResponse:
    consent = get_consent(farmer_name)
    profile = get_profile(farmer_name) if consent else None
    feedback = get_feedback_history(farmer_name)
    return MemoryResponse(
        farmer_name=farmer_name,
        consent=consent,
        profile=profile,
        feedback_history=feedback
    )


@app.post("/api/memory/consent")
def update_consent(req: ConsentRequest):
    try:
        set_consent(req.farmer_name, req.consent)
        return {"status": "success", "consent": req.consent}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/location/verify", response_model=LocationVerifyResponse)
def verify_location(req: LocationVerifyRequest) -> LocationVerifyResponse:
    try:
        verify_result = verify_location_gps(req.text_address, req.gps_latitude, req.gps_longitude)
        return LocationVerifyResponse(
            resolved_address=verify_result["resolved_address"],
            latitude=verify_result["latitude"],
            longitude=verify_result["longitude"],
            country=verify_result["country"],
            state=verify_result["state"],
            gps_distance_km=verify_result["gps_distance_km"],
            confidence=verify_result["confidence"],
            warning=verify_result["warning"]
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# -----------------------------------------------------------------------------
# Next.js frontend compatibility routes
# These routes make the uploaded agrisarthi_5 Next.js UI work as a true
# full-stack app with this FastAPI backend through Next rewrites.
# -----------------------------------------------------------------------------

async def _read_json(request: Request) -> dict:
    try:
        payload = await request.json()
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _clean_soil(value: str | None) -> str:
    value = (value or "loamy").lower().replace("_", " ")
    if "black" in value or "cotton" in value:
        return "black"
    if "red" in value:
        return "red"
    if "sandy" in value or "sand" in value:
        return "sandy"
    if "clay" in value:
        return "loamy"
    return "loamy"


def _language_name(value: str | None) -> str:
    value = (value or "en").lower()
    if value.startswith("te"):
        return "Telugu"
    if value.startswith("hi"):
        return "Hindi"
    return "English"


def _crop_id(name: str | None) -> str:
    return (name or "crop").strip().lower().replace(" ", "_")


def _budget_to_rupees(value) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value or "medium").lower()
    if text == "low":
        return 25000
    if text == "high":
        return 80000
    return 45000


def _ui_location_text(payload: dict, crop: str = "cotton") -> str:
    parts = [payload.get("village"), payload.get("district"), payload.get("state")]
    location = ", ".join(str(p) for p in parts if p)
    if not location:
        lat = payload.get("lat") or payload.get("latitude")
        lon = payload.get("lon") or payload.get("longitude")
        if lat and lon:
            location = f"{lat}, {lon}"
    return location or "Warangal, Telangana"


def _make_farm_request(payload: dict, crop: str = "cotton") -> FarmRequest:
    water = str(payload.get("water") or "medium").lower()
    return FarmRequest(
        farmer_name=str(payload.get("farmer_name") or payload.get("sessionId") or "Demo Farmer"),
        location=_ui_location_text(payload, crop),
        crop=crop or "cotton",
        soil_type=_clean_soil(payload.get("soil" ) or payload.get("soil_type")),
        season=str(payload.get("season") or "kharif"),
        land_type=str(payload.get("land_type") or "normal"),
        irrigation_available=(water != "low"),
        farm_area_acres=float(payload.get("farmSize") or payload.get("farm_area_acres") or 2),
        budget_per_acre=float(_budget_to_rupees(payload.get("budget") or payload.get("budget_per_acre"))),
        preferred_language=_language_name(payload.get("lang") or payload.get("preferred_language")),
        gps_latitude=payload.get("lat") or payload.get("gps_latitude"),
        gps_longitude=payload.get("lon") or payload.get("gps_longitude"),
    )


def _first_number(values, default=0.0):
    try:
        for item in values or []:
            if item is not None:
                return float(item)
    except Exception:
        pass
    return float(default)


def _daily_chunks(values, days=7, mode="max", default=0.0):
    out = []
    values = values or []
    for day in range(days):
        chunk = [float(v) for v in values[day*24:(day+1)*24] if v is not None]
        if not chunk:
            out.append(float(default))
        elif mode == "min":
            out.append(min(chunk))
        elif mode == "sum":
            out.append(sum(chunk))
        else:
            out.append(max(chunk))
    return out


def _adapt_weather(weather_status: ApiStatus, risk: RiskScores | None = None) -> dict:
    data = weather_status.data or {}
    hourly = data.get("hourly", {}) if isinstance(data, dict) else {}
    temps = hourly.get("temperature_2m", [])
    humidity = hourly.get("relative_humidity_2m", [])
    rain = hourly.get("rain", [])
    showers = hourly.get("showers", [])
    wind = hourly.get("wind_speed_10m", [])
    rain_combined = []
    for i in range(max(len(rain or []), len(showers or []), 168)):
        r = rain[i] if i < len(rain or []) and rain[i] is not None else 0
        s = showers[i] if i < len(showers or []) and showers[i] is not None else 0
        try:
            rain_combined.append(float(r) + float(s))
        except Exception:
            rain_combined.append(0.0)
    daily_max = _daily_chunks(temps, mode="max", default=32)
    daily_min = _daily_chunks(temps, mode="min", default=24)
    daily_rain = _daily_chunks(rain_combined, mode="sum", default=0)
    wind_daily = _daily_chunks(wind, mode="max", default=12)
    summary = {
        "rain7": round(sum(daily_rain), 1),
        "heat": round(max(daily_max or [32]), 1),
        "wind": round(max(wind_daily or [12]), 1),
        "rainMax": round(max(daily_rain or [0]), 1),
    }
    risks = []
    if risk:
        if risk.flood >= 60:
            risks.append({"id": "flood", "level": "high", "msg": "Flood/heavy rain risk detected"})
        if risk.drought >= 60:
            risks.append({"id": "drought", "level": "medium", "msg": "Dry spell risk — plan irrigation"})
        if risk.heat >= 60:
            risks.append({"id": "heat", "level": "high", "msg": "Heat stress risk"})
        if risk.wind >= 60:
            risks.append({"id": "wind", "level": "medium", "msg": "High wind risk"})
        if risk.pest_disease_risk >= 60:
            risks.append({"id": "pest", "level": "medium", "msg": "Pest/disease risk from humidity"})
    return {
        "ok": weather_status.message == "ok" or bool(data),
        "source": weather_status.source,
        "data": {
            "current": {
                "temperature_2m": _first_number(temps, 32),
                "relative_humidity_2m": _first_number(humidity, 65),
                "precipitation": _first_number(rain_combined, 0),
                "wind_speed_10m": _first_number(wind, 12),
            },
            "daily": {
                "temperature_2m_max": daily_max,
                "temperature_2m_min": daily_min,
                "precipitation_sum": daily_rain,
                "wind_speed_10m_max": wind_daily,
            },
        },
        "risks": risks,
        "summary": summary,
    }


def _adapt_recommendation(item: CropRecommendation, season: str) -> dict:
    modal = item.mandi_prices[0].modal_price_per_quintal if item.mandi_prices else 0
    water_score = 85 if "low" in item.water_requirement.lower() else 78 if "medium" in item.water_requirement.lower() else 68
    return {
        "id": _crop_id(item.crop),
        "name": item.crop,
        "name_te": item.crop,
        "name_hi": item.crop,
        "total": item.total_score,
        "scores": {
            "profit": item.expected_profit_score,
            "soil": item.soil_suitability_score,
            "season": item.weather_season_score,
            "region": item.market_demand_score,
            "water": water_score,
            "weather": item.weather_season_score,
            "mandi": item.mandi_price_score,
            "demand": item.market_demand_score,
            "budget": 80,
        },
        "inputCost": item.estimated_cost_per_acre,
        "expectedRevenue": item.estimated_cost_per_acre + item.expected_profit_per_acre,
        "expectedProfit": item.expected_profit_per_acre,
        "modalPrice": modal,
        "oversupplyRisk": item.oversupply_risk_score >= 60,
        "riskPests": [],
        "water": item.water_requirement,
        "seasons": [season],
        "reason": item.reason,
        "fertilizerPlan": item.fertilizer_plan.model_dump(),
        "seedSuggestions": [seed.model_dump() for seed in item.seed_suggestions],
    }


def _adapt_advisory_response(response: AdvisoryResponse) -> dict:
    top = [_adapt_recommendation(item, response.season) for item in response.recommendations]
    return {
        "ok": True,
        "source": "FastAPI backend",
        "season": response.season,
        "location": response.location.model_dump(),
        "weather": _adapt_weather(response.weather, response.risk),
        "top": top,
        "whyNotOthers": top[3:],
        "raw": response.model_dump(),
    }


def _adapt_mandi_records(market_status: ApiStatus, crop: str) -> dict:
    records = (market_status.data or {}).get("records", []) if market_status and market_status.data else []
    nearby = []
    for row in records[:5]:
        try:
            modal = int(float(str(row.get("modal_price") or row.get("Modal_Price") or row.get("modal") or 0).replace(",", "")))
        except Exception:
            modal = 0
        if modal <= 0:
            continue
        nearby.append({
            "market": row.get("market") or row.get("Market") or "Nearby mandi",
            "modal": modal,
            "min": int(modal * 0.92),
            "max": int(modal * 1.08),
            "commodity": row.get("commodity") or row.get("Commodity") or crop.title(),
        })
    if not nearby:
        nearby = [{"market": "Nearby mandi", "modal": 5000, "min": 4600, "max": 5400, "commodity": crop.title()}]
    return {
        "source": market_status.source if market_status else "local estimate",
        "primary": {**nearby[0], "trend": "stable"},
        "nearby": nearby,
        "raw": market_status.model_dump() if market_status else {},
    }


@app.post("/api/geocode")
async def ui_geocode(request: Request):
    payload = await _read_json(request)
    query = str(payload.get("query") or "").strip()
    if not query:
        return {"ok": False, "reason": "empty-query"}
    verify_result = await run_in_threadpool(
        verify_location_gps, query if "india" in query.lower() else f"{query}, India", None, None
    )
    try:
        from services.geocode_api import reverse_geocode
        rev = await run_in_threadpool(reverse_geocode, verify_result["latitude"], verify_result["longitude"]) or {}
    except Exception:
        rev = {}
    return {
        "ok": True,
        "source": "FastAPI geocode",
        "lat": verify_result["latitude"],
        "lon": verify_result["longitude"],
        "display": verify_result["resolved_address"],
        "state": verify_result.get("state") or rev.get("state") or "",
        "district": rev.get("district") or "",
        "village": rev.get("village") or query.split(",")[0],
        "confidence": str(verify_result.get("confidence") or "Medium").lower(),
    }


@app.post("/api/reverse-geocode")
async def ui_reverse_geocode(request: Request):
    payload = await _read_json(request)
    lat = float(payload.get("lat") or payload.get("latitude"))
    lon = float(payload.get("lon") or payload.get("longitude"))
    try:
        from services.geocode_api import reverse_geocode
        rev = await run_in_threadpool(reverse_geocode, lat, lon) or {}
    except Exception:
        rev = {}
    return {
        "ok": True,
        "lat": lat,
        "lon": lon,
        "display": rev.get("display_name") or f"{lat:.5f}, {lon:.5f}",
        "state": rev.get("state") or "",
        "district": rev.get("district") or "",
        "village": rev.get("village") or "",
    }


@app.post("/api/pdf-extract")
async def ui_pdf_extract(file: UploadFile = File(...)):
    filename = file.filename or "farmer_document.pdf"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    result = await run_in_threadpool(analyze_farmer_documents, [(filename, content)])
    profile = result.inferred_profile
    fields = {
        "farmerName": profile.farmer_name,
        "location": profile.location,
        "village": None,
        "district": None,
        "state": None,
        "soilType": profile.soil_type,
        "crop": profile.crop,
        "season": profile.season,
        "landType": profile.land_type,
        "irrigationAvailable": profile.irrigation_available,
        "farmAreaAcres": profile.farm_area_acres,
        "budgetPerAcre": profile.budget_per_acre,
        "preferredLanguage": profile.preferred_language,
    }
    if profile.location:
        parts = [part.strip() for part in profile.location.split(",") if part.strip()]
        if len(parts) >= 1:
            fields["village"] = parts[0]
        if len(parts) >= 2:
            fields["district"] = parts[-2]
        if len(parts) >= 3:
            fields["state"] = parts[-1]
    if result.soil_report:
        fields["nutrients"] = result.soil_report.nutrients
    return {
        "ok": True,
        "confidence": profile.confidence or (result.soil_report.confidence if result.soil_report else 35),
        "fields": fields,
        "summary": result.farmer_ready_summary,
        "warnings": result.warnings,
        "raw": result.model_dump(),
    }


@app.post("/api/recommend")
async def ui_recommend(request: Request):
    payload = await _read_json(request)
    farm = _make_farm_request(payload, crop=str(payload.get("crop") or "cotton"))
    response = await run_in_threadpool(create_advisory, farm)
    return _adapt_advisory_response(response)


@app.post("/api/mandi")
async def ui_mandi(request: Request):
    payload = await _read_json(request)
    crop = str(payload.get("crop") or "cotton").replace("_", " ")
    location = await run_in_threadpool(get_location, _ui_location_text(payload, crop), payload.get("lat"), payload.get("lon"))
    market_status = await run_in_threadpool(get_mandi_market, crop, location)
    return _adapt_mandi_records(market_status, crop)


@app.post("/api/irrigation")
async def ui_irrigation(request: Request):
    payload = await _read_json(request)
    crop = str(payload.get("crop") or "cotton").replace("_", " ")
    soil = _clean_soil(payload.get("soil") or payload.get("soil_type"))
    water = str(payload.get("water") or "medium")
    plan = get_irrigation_advisory(
        water_source="borewell" if water != "low" else "rainfed",
        water_availability=water,
        income_level=str(payload.get("budget") or "medium"),
        soil_type=soil,
        crop=crop,
        season=str(payload.get("season") or "kharif"),
        land_size=float(payload.get("farmSize") or 2),
        forecast_rain=0.0,
    )
    schedule = [{"day": idx, "action": text.split(":", 1)[-1].strip()} for idx, text in enumerate(plan.get("seven_day_schedule", []))]
    return {
        "ok": True,
        "plan": {
            "primary": plan.get("best_practice"),
            "alternative": plan.get("low_cost_alternative"),
            "benefit": plan.get("expected_benefit"),
            "warning": plan.get("risk_warning"),
            "schedule": schedule,
            "subsidy": plan.get("subsidy_suggestion"),
            "mulching": plan.get("mulching_advice"),
            "farmPond": plan.get("farm_pond"),
        },
        "raw": plan,
    }


@app.post("/api/advisory-ui")
async def ui_advisory(request: Request):
    payload = await _read_json(request)
    crop = str(payload.get("crop") or "cotton").replace("_", " ")
    farm = _make_farm_request(payload, crop=crop)
    response = await run_in_threadpool(create_advisory, farm)
    selected = None
    for item in response.recommendations:
        if _crop_id(item.crop) == _crop_id(crop):
            selected = item
            break
    selected = selected or (response.recommendations[0] if response.recommendations else None)
    fertilizer = selected.fertilizer_plan.basal if selected else "Use soil-test based basal fertilizer dose."
    modal = selected.mandi_prices[0].modal_price_per_quintal if selected and selected.mandi_prices else 0
    weather_note = response.weather.data.get("analysis", {}).get("soil_sowing_moisture_fit", "Check soil moisture") if response.weather.data else "Weather data is limited"
    irrigation_note = response.alert_plan[1] if len(response.alert_plan) > 1 else "Use rain-aware irrigation scheduling."
    mandi_note = f"Estimated mandi modal price is ₹{modal:,}/quintal." if modal else "Check nearby mandi before sale."
    risk_note = response.alert_plan[0] if response.alert_plan else f"Overall risk level is {response.risk.level}."
    short = response.ai_explanation or (selected.reason if selected else "AgriSarthi generated your advisory.")
    voice = f"{short} {weather_note}. {irrigation_note}. {mandi_note}. {risk_note}"
    return {
        "ok": True,
        "advisory": {
            "short": short,
            "weather": weather_note,
            "irrigation": irrigation_note,
            "mandi": mandi_note,
            "fertilizer": fertilizer,
            "risk": risk_note,
            "voice": voice,
        },
        "raw": response.model_dump(),
    }


@app.post("/api/feedback-ui")
async def ui_feedback(request: Request):
    payload = await _read_json(request)
    useful = str(payload.get("rating") or "up").lower() in ("up", "yes", "true", "1", "5")
    save_feedback(
        farmer_name=str(payload.get("sessionId") or "Demo Farmer"),
        crop=str(payload.get("cropId") or payload.get("crop") or "crop"),
        location=str(payload.get("location") or "Next.js frontend"),
        soil_type=str(payload.get("soil") or "unknown"),
        useful=useful,
        rating=5 if useful else 2,
        comments=str(payload.get("comments") or "Frontend quick feedback"),
    )
    return {"ok": True, "learned": True, "status": "success"}


@app.post("/api/profile")
async def ui_profile(request: Request):
    payload = await _read_json(request)
    # The original UI saves a local session profile without explicit consent.
    # To respect privacy, this endpoint acknowledges it but does not persist full details.
    return {"ok": True, "saved": False, "message": "Profile received. Use /api/memory/consent for persistent memory."}


@app.get("/api/profile")
async def ui_profile_get():
    return {"ok": True, "profile": None}


# ---------------------------------------------------------------------------
# Phone camera pest / animal detection module
# ---------------------------------------------------------------------------
from services.pest_animal_detector import analyze_crop_frame


@app.post("/api/pest-animal-detect")
async def pest_animal_detect(
    file: UploadFile = File(...),
    crop: str = Form("unknown crop"),
    camera_mode: str = Form("rgb"),
):
    """Analyze a phone-camera/photo frame using the neural-network pest pipeline."""
    filename = file.filename or "camera-frame.jpg"
    if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        raise HTTPException(status_code=400, detail="Upload a JPG, PNG or WEBP crop image")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image is too large. Keep it below 10 MB")
    result = analyze_crop_frame(content, filename=filename, crop=crop, mode=camera_mode)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Could not analyze image"))
    return result


@app.get("/api/pest-animal-live-tip")
def pest_animal_live_tip():
    return {
        "ok": True,
        "message": "Use POST /api/pest-animal-detect with a phone camera frame/photo.",
        "cameraAdvice": [
            "Open /pest-guard on your phone browser while backend and frontend are running.",
            "Use the rear camera and take close-up images of leaf underside, stem base and damaged crop area.",
            "For night animal detection, normal phone cameras need torch/IR light. True thermal needs an external thermal camera.",
        ],
    }
