from io import BytesIO
import sqlite3

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from main import app
from services.vision.config import settings


def image_bytes(size=(800, 600), textured=True) -> bytes:
    image = Image.new("RGB", size, "white")
    if textured:
        draw = ImageDraw.Draw(image)
        for index in range(0, size[0], 20):
            draw.line((index, 0, size[0] - index, size[1]), fill=(30 + index % 180, 130, 50), width=5)
    out = BytesIO()
    image.save(out, "JPEG", quality=90)
    return out.getvalue()


def test_health_reports_development_mode_without_weights():
    with TestClient(app) as client:
        response = client.get("/api/vision/health")
    assert response.status_code == 200
    assert response.json()["development_mode"] is True


def test_valid_image_does_not_receive_fake_prediction():
    with TestClient(app) as client:
        response = client.post(
            "/api/vision/analyze-session",
            files=[("files", ("plant.jpg", image_bytes(), "image/jpeg"))],
            data={"owner_id": "pytest_owner_1234", "crop": "auto", "consent": "false"},
        )
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "model_unavailable"
    assert payload["detected_crop"] == "unknown"
    assert payload["diseases"] == []
    assert payload["pests"] == []


def test_blurry_image_returns_capture_guidance():
    with TestClient(app) as client:
        response = client.post(
            "/api/vision/analyze",
            files={"file": ("blur.jpg", image_bytes(textured=False), "image/jpeg")},
            data={"owner_id": "pytest_owner_1234"},
        )
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "needs_better_images"
    assert payload["images"][0]["quality"]["capture_guidance"]


def test_unsupported_content_is_rejected_even_with_jpg_name():
    with TestClient(app) as client:
        response = client.post(
            "/api/vision/analyze",
            files={"file": ("fake.jpg", b"not an image", "image/jpeg")},
            data={"owner_id": "pytest_owner_1234"},
        )
    assert response.status_code == 415


def test_oversized_upload_is_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/api/vision/analyze",
            files={"file": ("huge.jpg", b"x" * (13 * 1024 * 1024), "image/jpeg")},
            data={"owner_id": "pytest_owner_1234"},
        )
    assert response.status_code == 413


def test_history_and_feedback_flow():
    with TestClient(app) as client:
        analysis = client.post(
            "/api/vision/analyze",
            files={"file": ("plant.jpg", image_bytes(), "image/jpeg")},
            data={"owner_id": "pytest_history_1234"},
        ).json()
        history = client.get("/api/vision/history", params={"owner_id": "pytest_history_1234"})
        feedback = client.post(
            "/api/vision/feedback",
            json={"analysis_id": analysis["analysis_id"], "owner_id": "pytest_history_1234", "verdict": "incorrect"},
        )
    assert history.status_code == 200
    assert history.json()["items"]
    assert feedback.status_code == 200
    assert "expert review" in feedback.json()["message"].lower()
    feedback_id = feedback.json()["feedback_id"]
    candidate = settings.dataset_candidate_dir / "pending" / f"feedback-{feedback_id}.json"
    assert candidate.exists()
    assert '"approval_required": true' in candidate.read_text(encoding="utf-8")


def test_database_unavailable_returns_service_unavailable(monkeypatch):
    def fail_save(*args, **kwargs):
        raise sqlite3.OperationalError("database unavailable")

    monkeypatch.setattr("services.vision.runtime.save_analysis", fail_save)
    with TestClient(app) as client:
        response = client.post(
            "/api/vision/analyze",
            files={"file": ("plant.jpg", image_bytes(), "image/jpeg")},
            data={"owner_id": "pytest_db_failure_1234"},
        )
    assert response.status_code == 503
    assert "database" in response.json()["detail"].lower()


def test_existing_application_routes_remain_registered():
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert {
        "/api/advisory",
        "/api/auth/login",
        "/api/document-intake",
        "/api/mandi",
        "/api/pest-animal-detect",
        "/api/recommend",
    }.issubset(paths)
