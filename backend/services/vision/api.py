from __future__ import annotations

import asyncio
import json
import re
import sqlite3
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .config import settings
from .database import get_analysis, list_history, save_vision_feedback
from .image_io import VisionImageError
from .runtime import InputImage, get_vision_runtime

router = APIRouter(prefix="/api/vision", tags=["AI Crop Vision Analyzer"])

_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_RATE_LOCK = threading.Lock()


def _rate_limit(request: Request) -> None:
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _RATE_LOCK:
        bucket = _RATE_BUCKETS[key]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= settings.rate_limit_per_minute:
            raise HTTPException(status_code=429, detail="Too many vision requests. Try again shortly.")
        bucket.append(now)


async def _run_analysis(function, *args, **kwargs):
    try:
        return await asyncio.wait_for(
            run_in_threadpool(function, *args, **kwargs),
            timeout=settings.request_timeout_seconds,
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Vision analysis timed out. Try fewer or smaller images.") from exc
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Vision database is temporarily unavailable.") from exc
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Vision image storage is temporarily unavailable.") from exc




def _clean_text(value: str, maximum: int, field: str) -> str:
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value or "").strip()
    if len(value) > maximum:
        raise HTTPException(status_code=422, detail=f"{field} is too long.")
    return value


def _validated_options(preference: str, budget: str, latitude: float | None, longitude: float | None) -> tuple[str, str]:
    preference = preference.lower().strip()
    budget = budget.lower().strip()
    if preference not in {"natural", "artificial", "integrated", "cheapest", "fastest"}:
        raise HTTPException(status_code=422, detail="Unsupported treatment preference.")
    if budget not in {"low", "medium", "high"}:
        raise HTTPException(status_code=422, detail="Budget must be low, medium or high.")
    if latitude is not None and not -90 <= latitude <= 90:
        raise HTTPException(status_code=422, detail="Latitude is outside the valid range.")
    if longitude is not None and not -180 <= longitude <= 180:
        raise HTTPException(status_code=422, detail="Longitude is outside the valid range.")
    return preference, budget

class VisionFeedback(BaseModel):
    analysis_id: str
    owner_id: str = "anonymous"
    verdict: str = Field(pattern="^(correct|incorrect|partially_correct|unknown)$")
    crop_correct: bool | None = None
    disease_correct: bool | None = None
    pest_correct: bool | None = None
    treatment_helpful: bool | None = None
    corrected_label: str | None = Field(default=None, max_length=200)
    expert_diagnosis: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)


def _parse_soil_report(value: str) -> dict | None:
    if not value.strip():
        return None
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="soil_report_json must be valid JSON") from exc


async def _read_upload(upload: UploadFile) -> InputImage:
    data = await upload.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"{upload.filename or 'Image'} is larger than {settings.max_upload_mb} MB.",
        )
    if not data:
        raise HTTPException(status_code=400, detail=f"{upload.filename or 'Image'} is empty.")
    return InputImage(filename=upload.filename or "crop-image.jpg", data=data)


@router.post("/analyze", dependencies=[Depends(_rate_limit)])
async def analyze_single(
    file: UploadFile = File(...),
    owner_id: str = Form("anonymous"),
    crop: str = Form("auto"),
    plant_part: str = Form("auto"),
    growth_stage: str = Form("auto"),
    harvest_stage: str = Form("auto"),
    location: str = Form(""),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    treatment_preference: str = Form("integrated"),
    budget: str = Form("low"),
    previous_treatment: str = Form(""),
    soil_report_json: str = Form(""),
    consent: bool = Form(False),
    language: str = Form("en"),
):
    owner_id = _clean_text(owner_id, 120, "owner_id") or "anonymous"
    crop = _clean_text(crop, 80, "crop") or "auto"
    plant_part = _clean_text(plant_part, 80, "plant_part") or "auto"
    growth_stage = _clean_text(growth_stage, 80, "growth_stage") or "auto"
    harvest_stage = _clean_text(harvest_stage, 80, "harvest_stage") or "auto"
    location = _clean_text(location, 300, "location")
    previous_treatment = _clean_text(previous_treatment, 2000, "previous_treatment")
    language = _clean_text(language, 10, "language") or "en"
    preference, budget = _validated_options(treatment_preference, budget, latitude, longitude)
    source = await _read_upload(file)
    try:
        return await _run_analysis(
            get_vision_runtime().analyze_session,
            [source],
            owner_id=owner_id,
            crop=crop,
            plant_part=plant_part,
            growth_stage=growth_stage,
            harvest_stage=harvest_stage,
            location=location,
            latitude=latitude,
            longitude=longitude,
            treatment_preference=preference,
            budget=budget,
            previous_treatment=previous_treatment,
            soil_report=_parse_soil_report(soil_report_json),
            consent=consent,
            language=language,
        )
    except VisionImageError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/analyze-session", dependencies=[Depends(_rate_limit)])
async def analyze_session(
    files: Annotated[list[UploadFile], File(...)],
    owner_id: str = Form("anonymous"),
    crop: str = Form("auto"),
    plant_part: str = Form("auto"),
    growth_stage: str = Form("auto"),
    harvest_stage: str = Form("auto"),
    location: str = Form(""),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    treatment_preference: str = Form("integrated"),
    budget: str = Form("low"),
    previous_treatment: str = Form(""),
    soil_report_json: str = Form(""),
    consent: bool = Form(False),
    language: str = Form("en"),
):
    owner_id = _clean_text(owner_id, 120, "owner_id") or "anonymous"
    crop = _clean_text(crop, 80, "crop") or "auto"
    plant_part = _clean_text(plant_part, 80, "plant_part") or "auto"
    growth_stage = _clean_text(growth_stage, 80, "growth_stage") or "auto"
    harvest_stage = _clean_text(harvest_stage, 80, "harvest_stage") or "auto"
    location = _clean_text(location, 300, "location")
    previous_treatment = _clean_text(previous_treatment, 2000, "previous_treatment")
    language = _clean_text(language, 10, "language") or "en"
    preference, budget = _validated_options(treatment_preference, budget, latitude, longitude)
    if len(soil_report_json) > 20000:
        raise HTTPException(status_code=422, detail="soil_report_json is too large.")
    if len(files) > settings.max_images_per_session:
        raise HTTPException(
            status_code=413,
            detail=f"Upload no more than {settings.max_images_per_session} images per session.",
        )
    sources = [await _read_upload(upload) for upload in files]
    try:
        return await _run_analysis(
            get_vision_runtime().analyze_session,
            sources,
            owner_id=owner_id,
            crop=crop,
            plant_part=plant_part,
            growth_stage=growth_stage,
            harvest_stage=harvest_stage,
            location=location,
            latitude=latitude,
            longitude=longitude,
            treatment_preference=preference,
            budget=budget,
            previous_treatment=previous_treatment,
            soil_report=_parse_soil_report(soil_report_json),
            consent=consent,
            language=language,
        )
    except VisionImageError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/result/{analysis_id}")
def result(analysis_id: str):
    try:
        payload = get_analysis(analysis_id)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Vision database is temporarily unavailable.") from exc
    if not payload:
        raise HTTPException(status_code=404, detail="Analysis not found or its retention period has expired.")
    return payload


@router.get("/history")
def history(owner_id: str = Query(..., min_length=4, max_length=120), limit: int = Query(20, ge=1, le=100)):
    try:
        items = list_history(owner_id, limit)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Vision database is temporarily unavailable.") from exc
    return {"ok": True, "items": items}


@router.post("/feedback")
def feedback(payload: VisionFeedback):
    try:
        analysis = get_analysis(payload.analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found or expired.")
        feedback_id = save_vision_feedback(payload.model_dump())
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Vision database is temporarily unavailable.") from exc
    return {
        "ok": True,
        "feedback_id": feedback_id,
        "message": "Feedback saved for expert review. It will not be used for uncontrolled online training.",
    }


@router.get("/model-info")
def model_info():
    return {"ok": True, **get_vision_runtime().model_info()}


@router.get("/health")
def health():
    info = get_vision_runtime().model_info()
    return {
        "ok": True,
        "service": "AI Crop Pest and Disease Vision Analyzer",
        "status": "development_mode" if info["development_mode"] else "ready",
        "database_ready": settings.database_path.exists(),
        "storage_ready": settings.storage_dir.exists(),
        **info,
    }


@router.get("/file/{analysis_id}/{filename}", include_in_schema=False)
def vision_file(analysis_id: str, filename: str):
    payload = get_analysis(analysis_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Analysis not found or expired.")
    safe_name = Path(filename).name
    allowed = {
        path_name
        for image in payload.get("images", [])
        for path_name in image.get("paths", {}).values()
        if path_name
    }
    if safe_name not in allowed:
        raise HTTPException(status_code=404, detail="Image output not found.")
    path = (settings.storage_dir / analysis_id / safe_name).resolve()
    expected_parent = (settings.storage_dir / analysis_id).resolve()
    if path.parent != expected_parent or not path.exists():
        raise HTTPException(status_code=404, detail="Image output not found.")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=300"})
