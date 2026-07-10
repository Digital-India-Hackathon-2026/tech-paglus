from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import settings


def _connect() -> sqlite3.Connection:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_vision_db() -> None:
    migration = Path(__file__).resolve().parents[2] / "migrations" / "001_create_vision_tables.sql"
    sql = migration.read_text(encoding="utf-8")
    with _connect() as conn:
        conn.executescript(sql)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(vision_damage_regions)").fetchall()}
        if "mask_json" not in columns:
            conn.execute("ALTER TABLE vision_damage_regions ADD COLUMN mask_json TEXT")


def save_analysis(result: dict[str, Any], owner_id: str, consent: bool, expires_at: str) -> None:
    init_vision_db()
    analysis_id = result["analysis_id"]
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO vision_analysis_sessions
            (analysis_id, owner_id, status, crop, plant_part, growth_stage, harvest_stage,
             location, consent_status, model_version, severity, affected_percentage,
             result_json, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                owner_id,
                result.get("status"),
                result.get("detected_crop"),
                result.get("plant_part"),
                result.get("growth_stage"),
                result.get("harvest_stage"),
                result.get("location"),
                1 if consent else 0,
                result.get("model_summary", {}).get("version"),
                result.get("severity", {}).get("level"),
                result.get("severity", {}).get("affected_percentage"),
                json.dumps(result, ensure_ascii=False),
                result.get("created_at"),
                expires_at,
            ),
        )
        for image in result.get("images", []):
            conn.execute(
                """
                INSERT OR REPLACE INTO vision_uploaded_images
                (image_id, analysis_id, original_name, mime_type, sha256, width, height,
                 quality_status, original_path, annotated_path, zoom_path, consent_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    image.get("image_id"), analysis_id, image.get("original_name"), image.get("mime_type"),
                    image.get("sha256"), image.get("quality", {}).get("width"),
                    image.get("quality", {}).get("height"),
                    "suitable" if image.get("quality", {}).get("suitable") else "unsuitable",
                    image.get("paths", {}).get("original"), image.get("paths", {}).get("annotated"),
                    image.get("paths", {}).get("zoom"), 1 if consent else 0,
                ),
            )
            generic_predictions = []
            crop_prediction = image.get("crop_prediction") or {}
            if crop_prediction.get("label"):
                generic_predictions.append(("crop_part", crop_prediction))
            generic_predictions.extend(("disease", item) for item in image.get("diseases", []))
            if image.get("health_assessment"):
                generic_predictions.append(("health", image["health_assessment"]))
            generic_predictions.extend(("pest", item) for item in image.get("pests", []))
            for task, prediction in generic_predictions:
                conn.execute(
                    """INSERT INTO vision_predictions
                    (analysis_id, image_id, task, label, confidence, model_version, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (analysis_id, image.get("image_id"), task,
                     prediction.get("label") or prediction.get("name"),
                     prediction.get("confidence"),
                     result.get("model_summary", {}).get("version"),
                     json.dumps(prediction, ensure_ascii=False)),
                )
            for disease in image.get("diseases", []):
                conn.execute(
                    """INSERT INTO vision_detected_diseases
                    (analysis_id, image_id, disease_name, category, confidence, alternative_rank)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (analysis_id, image.get("image_id"), disease.get("name"), disease.get("category"),
                     disease.get("confidence"), disease.get("rank")),
                )
            for pest in image.get("pests", []):
                conn.execute(
                    """INSERT INTO vision_detected_pests
                    (analysis_id, image_id, pest_name, confidence, lifecycle_stage, directly_visible,
                     crop_part, damage_type, bbox_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (analysis_id, image.get("image_id"), pest.get("name"), pest.get("confidence"),
                     pest.get("lifecycle_stage"), 1 if pest.get("directly_visible") else 0,
                     pest.get("crop_part"), pest.get("damage_type"), json.dumps(pest.get("bbox"))),
                )
            for region in image.get("damage_regions", []):
                conn.execute(
                    """INSERT INTO vision_damage_regions
                    (analysis_id, image_id, label, confidence, affected_fraction, bbox_json, mask_json, method)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (analysis_id, image.get("image_id"), region.get("label"), region.get("confidence"),
                     region.get("area_fraction"), json.dumps(region.get("bbox")),
                     json.dumps(region.get("polygon")), region.get("method")),
                )
        for recommendation in result.get("recommendations", {}).get("all", []):
            conn.execute(
                """INSERT INTO vision_recommendations
                (analysis_id, recommendation_type, title, detail, cost_category, verification_status)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (analysis_id, recommendation.get("type"), recommendation.get("title"),
                 recommendation.get("detail"), recommendation.get("cost_category"),
                 recommendation.get("verification_status")),
            )


def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    init_vision_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT result_json, expires_at FROM vision_analysis_sessions WHERE analysis_id = ?",
            (analysis_id,),
        ).fetchone()
    if not row:
        return None
    if row["expires_at"] and datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        return None
    return json.loads(row["result_json"])


def list_history(owner_id: str, limit: int = 20) -> list[dict[str, Any]]:
    init_vision_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT analysis_id, status, crop, plant_part, severity, affected_percentage, created_at
            FROM vision_analysis_sessions
            WHERE owner_id = ? AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC LIMIT ?
            """,
            (owner_id, datetime.now(timezone.utc).isoformat(), max(1, min(limit, 100))),
        ).fetchall()
    return [dict(row) for row in rows]


def save_vision_feedback(payload: dict[str, Any]) -> int:
    init_vision_db()
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO vision_feedback
            (analysis_id, owner_id, verdict, crop_correct, disease_correct, pest_correct,
             treatment_helpful, corrected_label, expert_diagnosis, notes, dataset_candidate_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_expert_review')
            """,
            (
                payload.get("analysis_id"), payload.get("owner_id"), payload.get("verdict"),
                payload.get("crop_correct"), payload.get("disease_correct"), payload.get("pest_correct"),
                payload.get("treatment_helpful"), payload.get("corrected_label"),
                payload.get("expert_diagnosis"), payload.get("notes"),
            ),
        )
        feedback_id = int(cursor.lastrowid)
        analysis = conn.execute(
            "SELECT consent_status, result_json FROM vision_analysis_sessions WHERE analysis_id = ?",
            (payload.get("analysis_id"),),
        ).fetchone()

    settings.dataset_candidate_dir.mkdir(parents=True, exist_ok=True)
    pending_dir = settings.dataset_candidate_dir / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    consent_status = bool(analysis["consent_status"]) if analysis else False
    result = json.loads(analysis["result_json"]) if analysis else {}
    candidate = {
        "feedback_id": feedback_id,
        "analysis_id": payload.get("analysis_id"),
        "status": "pending_expert_review",
        "verdict": payload.get("verdict"),
        "crop_correct": payload.get("crop_correct"),
        "disease_correct": payload.get("disease_correct"),
        "pest_correct": payload.get("pest_correct"),
        "treatment_helpful": payload.get("treatment_helpful"),
        "corrected_label": payload.get("corrected_label"),
        "expert_diagnosis": payload.get("expert_diagnosis"),
        "notes": payload.get("notes"),
        "image_use_consent": consent_status,
        "eligible_image_paths": [
            image.get("paths", {}).get("original")
            for image in result.get("images", [])
            if consent_status and image.get("paths", {}).get("original")
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "approval_required": True,
    }
    (pending_dir / f"feedback-{feedback_id}.json").write_text(
        json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return feedback_id


def expiry_for_consent(consent: bool) -> str:
    now = datetime.now(timezone.utc)
    delta = (
        timedelta(days=settings.retention_days_with_consent)
        if consent
        else timedelta(hours=settings.retention_hours_without_consent)
    )
    return (now + delta).isoformat()
