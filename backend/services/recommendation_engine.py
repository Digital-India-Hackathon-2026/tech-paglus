from __future__ import annotations

from statistics import mean

from models.schemas import (
    AdminDashboard,
    ApiStatus,
    CropRecommendation,
    FarmRequest,
    FertilizerPlan,
    LocationData,
    MandiPrice,
    RegionalDemandItem,
    RiskScores,
    SeedSuggestion,
)


CROP_CATALOG = {
    "cotton": {
        "soils": {"black": 95, "loamy": 75, "red": 62, "sandy": 42},
        "seasons": {"kharif": 92, "rabi": 50, "summer": 35},
        "water": "Medium",
        "cost": 42000,
        "yield_quintal": 9,
        "fallback_price": 7200,
        "demand": 74,
        "trend": "stable",
        "duration": 165,
        "fertilizer": ("NPK 20:20:0:13 at sowing", "Urea and MOP split at 35 and 60 days", "FYM or compost before sowing"),
        "seeds": [("Bt Cotton Hybrid", "Hybrid"), ("Desi Cotton Improved", "Improved")],
    },
    "chilli": {
        "soils": {"black": 78, "loamy": 92, "red": 82, "sandy": 55},
        "seasons": {"kharif": 84, "rabi": 88, "summer": 45},
        "water": "Medium",
        "cost": 68000,
        "yield_quintal": 18,
        "fallback_price": 9500,
        "demand": 86,
        "trend": "rising",
        "duration": 150,
        "fertilizer": ("DAP with potash during transplanting", "Calcium nitrate and micronutrients in splits", "Neem cake and compost for root health"),
        "seeds": [("Teja Chilli", "Hybrid"), ("Byadgi Type", "Market Preferred")],
    },
    "paddy": {
        "soils": {"black": 72, "loamy": 82, "red": 58, "sandy": 35},
        "seasons": {"kharif": 90, "rabi": 72, "summer": 48},
        "water": "High",
        "cost": 52000,
        "yield_quintal": 28,
        "fallback_price": 2300,
        "demand": 66,
        "trend": "oversupply risk",
        "duration": 125,
        "fertilizer": ("DAP and zinc sulphate at transplanting", "Urea in three splits", "Green manure or FYM before puddling"),
        "seeds": [("MTU-1010", "High Yield"), ("BPT-5204", "Fine Grain")],
    },
    "maize": {
        "soils": {"black": 78, "loamy": 88, "red": 76, "sandy": 52},
        "seasons": {"kharif": 85, "rabi": 80, "summer": 62},
        "water": "Medium",
        "cost": 34000,
        "yield_quintal": 26,
        "fallback_price": 2450,
        "demand": 79,
        "trend": "rising",
        "duration": 105,
        "fertilizer": ("NPK 15:15:15 at sowing", "Urea top dressing at knee-high stage", "Compost plus biofertilizer"),
        "seeds": [("HQPM Hybrid", "Hybrid"), ("DHM-117", "Regional")],
    },
    "groundnut": {
        "soils": {"black": 65, "loamy": 86, "red": 84, "sandy": 74},
        "seasons": {"kharif": 82, "rabi": 76, "summer": 62},
        "water": "Low to Medium",
        "cost": 31000,
        "yield_quintal": 12,
        "fallback_price": 6700,
        "demand": 82,
        "trend": "stable",
        "duration": 115,
        "fertilizer": ("SSP and gypsum at sowing", "Need-based potash after flowering", "Rhizobium seed treatment and compost"),
        "seeds": [("Kadiri-6", "Drought Tolerant"), ("Dharani", "High Oil")],
    },
    "turmeric": {
        "soils": {"black": 72, "loamy": 92, "red": 75, "sandy": 45},
        "seasons": {"kharif": 86, "rabi": 58, "summer": 40},
        "water": "Medium to High",
        "cost": 76000,
        "yield_quintal": 42,
        "fallback_price": 8200,
        "demand": 80,
        "trend": "rising",
        "duration": 240,
        "fertilizer": ("NPK with basal phosphorus", "Potash and nitrogen splits after earthing-up", "FYM, neem cake, and Trichoderma"),
        "seeds": [("Pragati", "Short Duration"), ("Salem Local", "Market Preferred")],
    },
}


MANDI_FALLBACKS = {
    "Telangana": ["Hyderabad", "Warangal", "Nizamabad"],
    "Andhra Pradesh": ["Guntur", "Vijayawada", "Kurnool"],
    "Maharashtra": ["Nagpur", "Pune", "Aurangabad"],
    "Karnataka": ["Bengaluru", "Raichur", "Hubballi"],
}

LOCAL_MANDI_FALLBACKS = {
    "warangal": ["Enumamula", "Jangaon", "Khammam"],
    "hanamkonda": ["Enumamula", "Warangal", "Jangaon"],
    "nizamabad": ["Nizamabad", "Bodhan", "Kamareddy"],
    "karimnagar": ["Karimnagar", "Jagtial", "Siddipet"],
    "guntur": ["Guntur", "Tenali", "Chilakaluripet"],
    "vijayawada": ["Vijayawada", "Guntur", "Eluru"],
    "kurnool": ["Kurnool", "Nandyal", "Anantapur"],
    "anantapur": ["Anantapur", "Kurnool", "Kadiri"],
    "raichur": ["Raichur", "Yadgir", "Ballari"],
    "bengaluru": ["Bengaluru", "Ramanagara", "Tumakuru"],
    "nagpur": ["Nagpur", "Wardha", "Amravati"],
    "pune": ["Pune", "Baramati", "Ahmednagar"],
}

LOCALITY_CROP_PRIORITIES = {
    "warangal": {"cotton": 12, "chilli": 10, "turmeric": 7, "maize": 4, "paddy": -6},
    "hanamkonda": {"cotton": 10, "chilli": 8, "turmeric": 6, "maize": 4},
    "nizamabad": {"turmeric": 14, "paddy": 7, "maize": 5, "cotton": 3},
    "karimnagar": {"paddy": 8, "cotton": 7, "maize": 6, "turmeric": 5},
    "khammam": {"chilli": 12, "cotton": 8, "paddy": 4},
    "guntur": {"chilli": 15, "paddy": 7, "turmeric": 5, "cotton": -3},
    "vijayawada": {"paddy": 10, "maize": 6, "chilli": 5},
    "kurnool": {"groundnut": 12, "cotton": 8, "maize": 6, "paddy": -8},
    "anantapur": {"groundnut": 15, "maize": 6, "cotton": 4, "paddy": -12},
    "raichur": {"cotton": 10, "paddy": 7, "groundnut": 5},
    "bengaluru": {"maize": 8, "groundnut": 6, "paddy": -4},
    "nagpur": {"cotton": 13, "groundnut": 5, "maize": 5},
    "pune": {"maize": 8, "groundnut": 6, "turmeric": 4},
}

STATE_CROP_PRIORITIES = {
    "Telangana": {"cotton": 8, "chilli": 7, "turmeric": 6, "maize": 4, "paddy": -3},
    "Andhra Pradesh": {"chilli": 9, "paddy": 8, "groundnut": 5, "turmeric": 4},
    "Karnataka": {"maize": 8, "groundnut": 7, "cotton": 5, "paddy": -2},
    "Maharashtra": {"cotton": 9, "maize": 6, "groundnut": 5, "turmeric": 4},
}


def _clamp(value: float, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, round(value)))


def _weather_summary(weather: ApiStatus) -> dict[str, float]:
    hourly = weather.data.get("hourly", {}) if weather.data else {}
    temperatures = [float(v) for v in hourly.get("temperature_2m", []) if v is not None]
    rain = [float(v) for v in hourly.get("rain", []) if v is not None]
    showers = [float(v) for v in hourly.get("showers", []) if v is not None]
    evapotranspiration = [float(v) for v in hourly.get("et0_fao_evapotranspiration", []) if v is not None]
    return {
        "max_temp": max(temperatures, default=32),
        "avg_temp": mean(temperatures) if temperatures else 30,
        "rain_total": sum(rain) + sum(showers),
        "et0_total": sum(evapotranspiration),
    }


def _parse_mandi_records(crop: str, market_status: ApiStatus, fallback_state: str | None) -> list[MandiPrice]:
    records = market_status.data.get("records", []) if market_status.data else []
    parsed = []

    for record in records[:5]:
        price_text = record.get("modal_price") or record.get("Modal_Price") or record.get("modal price")
        try:
            price = int(float(str(price_text).replace(",", "")))
        except (TypeError, ValueError):
            continue

        parsed.append(
            MandiPrice(
                mandi=record.get("market") or record.get("Market") or "Nearby mandi",
                commodity=record.get("commodity") or record.get("Commodity") or crop.title(),
                modal_price_per_quintal=price,
                state=record.get("state") or record.get("State") or fallback_state or "Unknown",
                trend=record.get("data_quality") or "live",
            )
        )

    return parsed


def _fallback_mandi_prices(
    crop: str,
    state: str | None,
    base_price: int,
    trend: str,
    location: LocationData | None = None,
) -> list[MandiPrice]:
    mandis = _local_mandis(location) or MANDI_FALLBACKS.get(state or "", ["Nearest Mandi", "District Mandi", "Regional Mandi"])
    multipliers = [1.04, 1.0, 0.96]
    local_factor = _location_price_factor(crop, location)
    return [
        MandiPrice(
            mandi=mandi,
            commodity=crop.title(),
            modal_price_per_quintal=round(base_price * multipliers[index] * local_factor),
            state=state or "Local Region",
            trend=trend,
        )
        for index, mandi in enumerate(mandis[:3])
    ]


def _local_mandis(location: LocationData | None) -> list[str] | None:
    if not location:
        return None
    lower_name = location.name.lower()
    for district, mandis in LOCAL_MANDI_FALLBACKS.items():
        if district in lower_name:
            return mandis
    return None


def _location_price_factor(crop: str, location: LocationData | None) -> float:
    if not location:
        return 1.0
    seed = sum(ord(char) for char in f"{crop}:{location.name.lower()}")
    return 0.96 + (seed % 9) * 0.01


def _fertilizer_plan(crop: str, profile: dict, soil_type: str) -> FertilizerPlan:
    basal, top_dressing, organic = profile["fertilizer"]
    soil_notes = {
        "black": "Black soil usually holds moisture well; avoid excess nitrogen during heavy rainfall.",
        "red": "Red soil may need more organic matter and micronutrient support.",
        "sandy": "Sandy soil loses nutrients faster; use split fertilizer doses and mulching.",
        "loamy": "Loamy soil is balanced; maintain compost and soil testing every season.",
    }
    return FertilizerPlan(
        basal=basal,
        top_dressing=top_dressing,
        organic=organic,
        soil_note=soil_notes.get(soil_type.lower(), f"Use a soil test before finalizing the {crop} fertilizer dose."),
    )


def _seed_suggestions(profile: dict) -> list[SeedSuggestion]:
    return [
        SeedSuggestion(
            name=name,
            type=seed_type,
            duration_days=profile["duration"],
            note="Confirm local availability and certified seed label before purchase.",
        )
        for name, seed_type in profile["seeds"]
    ]


def build_crop_advisory(
    farm: FarmRequest,
    weather: ApiStatus,
    risk: RiskScores,
    mandi_market: ApiStatus,
    location: LocationData,
    state: str | None,
    nutrients: dict | None = None
) -> tuple[list[CropRecommendation], list[MandiPrice], str, AdminDashboard]:
    from services.crop_suitability import calculate_suitability
    from services.crop_balance_api import get_crop_balance
    from services.profit_model import calculate_crop_profit
    from services.preference_learning import learn_preferences

    weather_summary = _weather_summary(weather)
    live_mandi = _parse_mandi_records(farm.crop, mandi_market, state)
    requested_crop = farm.crop.strip().lower()
    candidates = list(dict.fromkeys([requested_crop, *CROP_CATALOG.keys()]))
    recommendations: list[CropRecommendation] = []
    
    # Learn farmer preferences from SQLite feedback history
    preferences = learn_preferences(farm.farmer_name)
    crop_boosts = preferences.get("crop_boosts", {})

    for crop in candidates:
        profile = CROP_CATALOG.get(crop)
        if not profile:
            continue

        mandi_prices = live_mandi if crop == requested_crop and live_mandi else _fallback_mandi_prices(
            crop,
            state,
            profile["fallback_price"],
            profile["trend"],
            location,
        )
        avg_price = mean([item.modal_price_per_quintal for item in mandi_prices])
        
        # Calculate granular soil suitability NPK/pH
        soil_res = calculate_suitability(crop, nutrients, farm.soil_type)
        soil_score = soil_res["overall_soil_suitability"]
        
        # Profit Model
        profit_res = calculate_crop_profit(crop, farm.soil_type, farm.irrigation_available, avg_price)
        estimated_cost = profit_res["estimated_cost_per_acre"]
        expected_profit = profit_res["expected_profit_per_acre"]
        profit_score = profit_res["profit_score"]
        
        # Crop balance / Demand supply
        balance_res = get_crop_balance(crop, state)
        demand_score = balance_res["demand_score"]
        oversupply_risk = balance_res["oversupply_risk_score"]
        
        season_score = profile["seasons"].get(farm.season.lower(), 55)
        locality_boost = _locality_crop_boost(crop, location, state)
        rain_total = weather_summary["rain_total"]
        max_temp = weather_summary["max_temp"]

        water_penalty = 0
        if profile["water"].lower().startswith("high") and not farm.irrigation_available:
            water_penalty = 24
        if "low" in profile["water"].lower() and risk.drought < 45:
            water_penalty -= 4

        weather_score = _clamp(season_score - water_penalty - max(0, max_temp - 38) * 2 - max(0, rain_total - 80) * 0.25)
        price_score = _clamp((avg_price / profile["fallback_price"]) * 70 + (12 if profile["trend"] == "rising" else 0))
        
        # Crop specific risks
        crop_risk = _clamp(risk.overall + water_penalty + (15 if oversupply_risk >= 65 else 0))
        
        # Apply preference boost
        crop_boost = crop_boosts.get(crop, 0.0)

        total_score = _clamp(
            soil_score * 0.22
            + weather_score * 0.20
            + price_score * 0.18
            + demand_score * 0.18
            + profit_score * 0.17
            - crop_risk * 0.15
            + locality_boost * 0.12
            + crop_boost
            + 15
        )
        risk_level = "High" if crop_risk >= 70 else "Medium" if crop_risk >= 40 else "Low"
        
        # Formulate description details
        reason = (
            f"{crop.title()} fits {farm.soil_type} soil with a {soil_score}/100 soil test match. "
            f"Expected price at local mandi is Rs {avg_price:,}/quintal (Demand: {demand_score}/100, Oversupply risk: {oversupply_risk}%). "
            f"Estimated cost is Rs {estimated_cost:,}/acre and projected profit is Rs {expected_profit:,}/acre. "
            f"{'Feedback loop has boosted this crop based on your profile.' if crop_boost > 0 else 'Feedback loop has penalized this crop.' if crop_boost < 0 else ''}"
        )

        recommendations.append(
            CropRecommendation(
                crop=crop.title(),
                rank=0,
                total_score=total_score,
                soil_suitability_score=soil_score,
                weather_season_score=weather_score,
                mandi_price_score=price_score,
                market_demand_score=demand_score,
                expected_profit_score=profit_score,
                risk_score=crop_risk,
                expected_profit_per_acre=expected_profit,
                estimated_cost_per_acre=estimated_cost,
                water_requirement=profile["water"],
                risk_level=risk_level,
                reason=reason,
                fertilizer_plan=_fertilizer_plan(crop, profile, farm.soil_type),
                seed_suggestions=_seed_suggestions(profile),
                mandi_prices=mandi_prices,
                soil_n_score=soil_res["n_score"],
                soil_p_score=soil_res["p_score"],
                soil_k_score=soil_res["k_score"],
                soil_ph_score=soil_res["ph_score"],
                oversupply_risk_score=oversupply_risk,
                climate_risk_score=crop_risk
            )
        )

    recommendations.sort(key=lambda item: item.total_score, reverse=True)
    top_recommendations = [
        item.model_copy(update={"rank": index + 1})
        for index, item in enumerate(recommendations[:3])
    ]
    mandi_comparison = top_recommendations[0].mandi_prices if top_recommendations else []
    explanation = _build_explanation(farm, top_recommendations, risk, preferences.get("explanation_style", "detailed"))
    dashboard = _build_admin_dashboard(farm, state, top_recommendations)
    return top_recommendations, mandi_comparison, explanation, dashboard


def _build_explanation(farm: FarmRequest, recommendations: list[CropRecommendation], risk: RiskScores, style: str = "detailed") -> str:
    if not recommendations:
        return "No crop recommendation could be generated. Please check the input details."

    best = recommendations[0]
    area = farm.farm_area_acres or 1
    total_profit = round(best.expected_profit_per_acre * area)
    
    if style == "simple":
        return (
            f"Hi {farm.farmer_name}, we recommend growing {best.crop} on your {area:g} acre(s). "
            f"Estimated profit is Rs {total_profit:,}. "
            f"Risk is {risk.level}. Please check fertilizer and irrigation guides below."
        )

    return (
        f"For {farm.farmer_name}, {best.crop} is the strongest option because it balances soil suitability, "
        f"season fit, mandi price, market demand, and weather risk. For {area:g} acre(s), the estimated profit is "
        f"about Rs {total_profit:,}. Current farm weather risk is {risk.level.lower()}, so follow the fertilizer and "
        f"irrigation advice before sowing."
    )


def _locality_crop_boost(crop: str, location: LocationData, state: str | None) -> int:
    lower_name = location.name.lower()
    for district, crop_scores in LOCALITY_CROP_PRIORITIES.items():
        if district in lower_name:
            return crop_scores.get(crop, 0)
    return STATE_CROP_PRIORITIES.get(state or "", {}).get(crop, 0)


def _build_admin_dashboard(
    farm: FarmRequest,
    state: str | None,
    recommendations: list[CropRecommendation],
) -> AdminDashboard:
    crop_mix = [
        RegionalDemandItem(
            crop=item.crop,
            demand_score=item.market_demand_score,
            recommendation="Promote" if item.market_demand_score >= 78 else "Monitor",
        )
        for item in recommendations
    ]
    oversupply = [
        f"Watch {item.crop} acreage before mass sowing; risk score is {item.risk_score}/100."
        for item in recommendations
        if item.risk_score >= 65 or item.market_demand_score < 70
    ]
    if not oversupply:
        oversupply.append("No major oversupply warning from the current recommendation mix.")

    return AdminDashboard(
        region=state or farm.location,
        total_farm_area_acres=farm.farm_area_acres or 0,
        recommended_crop_mix=crop_mix,
        oversupply_alerts=oversupply,
        fpo_actions=[
            "Share top crop demand with nearby FPO groups.",
            "Coordinate seed and fertilizer availability before sowing window.",
            "Track mandi price changes weekly for recommended crops.",
        ],
    )
