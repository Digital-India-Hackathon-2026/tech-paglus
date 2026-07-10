from typing import Any

from pydantic import BaseModel, Field


class FarmRequest(BaseModel):
    farmer_name: str = Field("Demo Farmer", examples=["Ramesh"])
    location: str = Field(..., examples=["Hyderabad"])
    crop: str = Field("cotton", examples=["cotton"])
    soil_type: str = Field("black", examples=["black", "red", "sandy", "loamy"])
    season: str = Field("kharif", examples=["kharif", "rabi", "summer"])
    land_type: str = Field("normal", examples=["low", "normal", "high"])
    irrigation_available: bool = True
    farm_area_acres: float | None = None
    budget_per_acre: float | None = Field(None, examples=[35000])
    preferred_language: str = Field("English", examples=["English", "Telugu", "Hindi"])
    gps_latitude: float | None = None
    gps_longitude: float | None = None


class SoilReportAnalysis(BaseModel):
    file_name: str
    extracted_text_preview: str
    inferred_soil_type: str
    confidence: int
    nutrients: dict[str, Any] = Field(default_factory=dict)
    detected_issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class InferredFarmProfile(BaseModel):
    farmer_name: str | None = None
    location: str | None = None
    crop: str | None = None
    soil_type: str | None = None
    season: str | None = None
    land_type: str | None = None
    irrigation_available: bool | None = None
    farm_area_acres: float | None = None
    budget_per_acre: float | None = None
    preferred_language: str | None = None
    confidence: int = 0
    missing_fields: list[str] = Field(default_factory=list)
    evidence: dict[str, str] = Field(default_factory=dict)


class DocumentIntakeAnalysis(BaseModel):
    file_names: list[str]
    document_types: list[str]
    extracted_text_preview: str
    soil_report: SoilReportAnalysis | None = None
    inferred_profile: InferredFarmProfile
    farmer_ready_summary: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)


class LocationData(BaseModel):
    name: str
    latitude: float
    longitude: float
    country: str | None = None
    state: str | None = None
    verification_status: str | None = "unverified"
    confidence_score: str | None = "Low"
    verification_notes: str | None = ""


class ApiStatus(BaseModel):
    source: str
    configured: bool = True
    message: str = "ok"
    data: dict[str, Any] = Field(default_factory=dict)


class RiskScores(BaseModel):
    flood: int
    drought: int
    heat: int
    wind: int
    overall: int
    level: str
    monsoon_risk: int = 0
    pest_disease_risk: int = 0
    spray_window_safe: bool = True
    crop_stress_level: str = "Low"


class FertilizerPlan(BaseModel):
    basal: str
    top_dressing: str
    organic: str
    soil_note: str


class SeedSuggestion(BaseModel):
    name: str
    type: str
    duration_days: int
    note: str


class MandiPrice(BaseModel):
    mandi: str
    commodity: str
    modal_price_per_quintal: int
    state: str
    trend: str


class CropRecommendation(BaseModel):
    crop: str
    rank: int
    total_score: int
    soil_suitability_score: int
    weather_season_score: int
    mandi_price_score: int
    market_demand_score: int
    expected_profit_score: int
    risk_score: int
    expected_profit_per_acre: int
    estimated_cost_per_acre: int
    water_requirement: str
    risk_level: str
    reason: str
    fertilizer_plan: FertilizerPlan
    seed_suggestions: list[SeedSuggestion]
    mandi_prices: list[MandiPrice]
    soil_n_score: int = 100
    soil_p_score: int = 100
    soil_k_score: int = 100
    soil_ph_score: int = 100
    oversupply_risk_score: int = 0
    climate_risk_score: int = 0


class RegionalDemandItem(BaseModel):
    crop: str
    demand_score: int
    recommendation: str


class AdminDashboard(BaseModel):
    region: str
    total_farm_area_acres: float
    recommended_crop_mix: list[RegionalDemandItem]
    oversupply_alerts: list[str]
    fpo_actions: list[str]


class AdvisoryResponse(BaseModel):
    location: LocationData
    crop: str
    farmer_name: str
    soil_type: str
    season: str
    land_type: str
    farm_area_acres: float | None = None
    budget_per_acre: float | None = None
    weather: ApiStatus
    radar: ApiStatus
    satellite: ApiStatus
    historical_weather: ApiStatus
    ml_weather_risk: ApiStatus
    soil_topography: ApiStatus
    mandi_market: ApiStatus
    crop_knowledge: ApiStatus
    risk: RiskScores
    recommendations: list[CropRecommendation]
    mandi_price_comparison: list[MandiPrice]
    ai_explanation: str
    admin_dashboard: AdminDashboard
    farmer_advice: list[str]
    government_alert: list[str]
    pest_disease_alerts: list[str] = Field(default_factory=list)
    scheme_matches: list[dict[str, Any]] = Field(default_factory=list)
    marketplace_items: list[dict[str, Any]] = Field(default_factory=list)
    alert_plan: list[str] = Field(default_factory=list)
    ai_detailed: dict[str, Any] = Field(default_factory=dict)



# New models for APIs
class ConsentRequest(BaseModel):
    farmer_name: str
    consent: bool


class FeedbackRequest(BaseModel):
    farmer_name: str
    crop: str
    location: str
    soil_type: str
    useful: bool
    rating: int = 5  # 1 to 5 stars or scale
    comments: str | None = None


class LocationVerifyRequest(BaseModel):
    text_address: str
    gps_latitude: float | None = None
    gps_longitude: float | None = None


class LocationVerifyResponse(BaseModel):
    resolved_address: str
    latitude: float
    longitude: float
    country: str | None = None
    state: str | None = None
    gps_distance_km: float | None = None
    confidence: str
    warning: str | None = None


class RegisterRequest(BaseModel):
    name: str = Field(..., examples=["Ramesh Kumar"])
    phone: str = Field(..., examples=["9876543210"])
    password: str = Field(..., examples=["farm@1234"])
    terms_accepted: bool = Field(..., description="Must be true — user must accept Terms & Conditions to register")


class LoginRequest(BaseModel):
    phone: str = Field(..., examples=["9876543210"])
    password: str = Field(..., examples=["farm@1234"])


class UserOut(BaseModel):
    id: int
    name: str
    phone: str
    termsAccepted: bool
    termsVersion: str | None = None
    createdAt: str | None = None


class AuthResponse(BaseModel):
    token: str
    user: UserOut


class MemoryResponse(BaseModel):
    farmer_name: str
    consent: bool
    profile: dict[str, Any] | None = None
    feedback_history: list[dict[str, Any]] = Field(default_factory=list)

