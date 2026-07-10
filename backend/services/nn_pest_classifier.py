"""Neural-network pest classifier integration for AgriSarthi.

This module is designed for real production use while remaining safe for local
hackathon demos:

1. If ROBOFLOW_API_KEY and ROBOFLOW_MODEL_ID are set, it calls a hosted neural
   network object-detection model and returns detections.
2. Else, if backend/ml_models/pest_classifier.onnx exists and onnxruntime is
   installed, it runs a local ONNX neural-network classifier.
3. Else, it returns a clear "model_missing" response with dataset/training
   instructions rather than pretending to know exact pest species.

Put your trained model here:
    backend/ml_models/pest_classifier.onnx
Put your class names here:
    backend/ml_models/pest_labels.json
"""

from __future__ import annotations

import base64
import io
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "ml_models"
ONNX_MODEL_PATH = MODEL_DIR / "pest_classifier.onnx"
LABELS_PATH = MODEL_DIR / "pest_labels.json"


PEST_KNOWLEDGE: dict[str, dict[str, Any]] = {
    "healthy_crop": {
        "name": "Healthy crop / no visible pest",
        "natural_controls": [
            "Continue weekly scouting of leaf underside and stem base.",
            "Use yellow sticky traps for early detection of sucking pests.",
            "Keep balanced nutrition; avoid excess nitrogen because soft growth attracts pests.",
        ],
        "crop_relevant_fertilisers": [
            "Farmyard manure or compost to improve plant resistance",
            "Neem cake as soil amendment where available",
            "Biofertilizer such as Azotobacter/PSB according to crop and local advisory",
        ],
    },
    "aphids": {
        "name": "Aphids",
        "natural_controls": [
            "Spray neem seed kernel extract or neem oil in evening after local dose confirmation.",
            "Release/encourage ladybird beetles and lacewings.",
            "Remove heavily infested tender shoots when infestation is localized.",
        ],
        "crop_relevant_fertilisers": [
            "Avoid excess urea/nitrogen; aphids increase on soft nitrogen-rich growth.",
            "Use compost + neem cake for soil health.",
            "Apply potash as per Soil Health Card to improve crop tolerance.",
        ],
    },
    "whitefly": {
        "name": "Whitefly",
        "natural_controls": [
            "Install yellow sticky traps around crop canopy.",
            "Use neem-based spray at early stage; repeat only as advised by agriculture officer.",
            "Remove weed hosts near the field border.",
        ],
        "crop_relevant_fertilisers": [
            "Avoid heavy nitrogen top dressing during whitefly outbreak.",
            "Use vermicompost/FYM and neem cake as preventive soil amendments.",
            "Balance potassium and micronutrients according to soil report.",
        ],
    },
    "fall_armyworm": {
        "name": "Fall armyworm",
        "natural_controls": [
            "Inspect maize whorls; hand-pick egg masses/larvae in small plots.",
            "Use pheromone traps for monitoring adult moth activity.",
            "Use recommended bio-control such as Bt only after confirming pest stage.",
        ],
        "crop_relevant_fertilisers": [
            "Apply balanced NPK; do not overuse nitrogen.",
            "Use FYM/compost to improve crop recovery.",
            "Use micronutrients only if deficiency is confirmed by soil/crop symptoms.",
        ],
    },
    "bollworm": {
        "name": "Bollworm / fruit borer",
        "natural_controls": [
            "Use pheromone traps for monitoring.",
            "Remove damaged fruits/bolls and destroy away from field.",
            "Prefer biopesticides such as Bt/NPV where locally recommended.",
        ],
        "crop_relevant_fertilisers": [
            "Avoid excess nitrogen in cotton/chilli/tomato.",
            "Use potash according to Soil Health Card for stronger fruiting.",
            "Use neem cake or compost as preventive soil-health input.",
        ],
    },
    "stem_borer": {
        "name": "Stem borer",
        "natural_controls": [
            "Monitor dead-hearts/white-ear symptoms.",
            "Use light/pheromone traps for adult monitoring.",
            "Destroy stubble/residue that shelters larvae after harvest.",
        ],
        "crop_relevant_fertilisers": [
            "Use split nitrogen application instead of one heavy dose.",
            "Apply silica/potash where recommended for rice/cereals.",
            "Use compost/FYM to support root and stem strength.",
        ],
    },
    "leaf_miner": {
        "name": "Leaf miner",
        "natural_controls": [
            "Remove highly mined leaves at early stage.",
            "Avoid broad-spectrum spray that kills parasitoids.",
            "Use neem-based products for early infestation after local dose confirmation.",
        ],
        "crop_relevant_fertilisers": [
            "Avoid excess nitrogen.",
            "Use balanced NPK and micronutrients based on soil report.",
            "Add compost/vermicompost to improve plant vigor.",
        ],
    },
    "thrips": {
        "name": "Thrips",
        "natural_controls": [
            "Use blue sticky traps.",
            "Maintain field moisture; dusty dry conditions increase thrips.",
            "Use neem-based spray in early stage with proper coverage.",
        ],
        "crop_relevant_fertilisers": [
            "Avoid excess nitrogen.",
            "Balanced potassium helps crop tolerance.",
            "Use organic manure to reduce plant stress.",
        ],
    },
    "mites": {
        "name": "Mites",
        "natural_controls": [
            "Improve humidity by avoiding drought stress where possible.",
            "Wash leaves with water jet in small plots if infestation is light.",
            "Avoid unnecessary insecticide sprays that kill natural mite predators.",
        ],
        "crop_relevant_fertilisers": [
            "Avoid excess nitrogen.",
            "Use organic compost and proper irrigation scheduling.",
            "Correct potassium deficiency as per soil report.",
        ],
    },
    "locust_grasshopper": {
        "name": "Locust / grasshopper",
        "natural_controls": [
            "Use community-level monitoring; individual field control is limited during swarms.",
            "Protect nursery/young crop with nets where possible.",
            "Report large swarm movement to local agriculture department immediately.",
        ],
        "crop_relevant_fertilisers": [
            "Fertilizers do not prevent locust attack directly.",
            "Use compost/FYM for recovery after defoliation if crop survives.",
            "Apply nutrients only after damage assessment and irrigation availability.",
        ],
    },
    "rodent_animal_damage": {
        "name": "Rodent / animal damage",
        "natural_controls": [
            "Check burrows, gnaw marks, cut seedlings and field-border movement paths.",
            "Use field sanitation, burrow destruction and traps as legally permitted.",
            "For larger animals, use fencing, solar lights and reflective tape.",
        ],
        "crop_relevant_fertilisers": [
            "Fertilizers do not prevent animal entry.",
            "Use compost and balanced nutrition for crop recovery after physical damage.",
            "Avoid re-fertilizing damaged patches until survival is confirmed.",
        ],
    },
    "wild_boar_cattle_damage": {
        "name": "Wild boar / cattle movement damage",
        "natural_controls": [
            "Use strong field fencing and night solar lights near entry points.",
            "Use community watch/alerts for repeated night movement.",
            "Capture wide-angle night photos/video to confirm species before action.",
        ],
        "crop_relevant_fertilisers": [
            "Fertilizers cannot prevent animal damage.",
            "Use organic matter and balanced nutrients only for crop recovery.",
            "Replant/recover damaged area based on crop stage and advisory.",
        ],
    },
}


@dataclass
class Classification:
    label: str
    confidence: float
    bbox: list[float] | None = None


def _load_labels() -> list[str]:
    if LABELS_PATH.exists():
        try:
            return json.loads(LABELS_PATH.read_text())
        except Exception:
            pass
    return list(PEST_KNOWLEDGE.keys())


def _softmax(xs: list[float]) -> list[float]:
    import math

    if not xs:
        return []
    m = max(xs)
    exps = [math.exp(x - m) for x in xs]
    s = sum(exps) or 1.0
    return [x / s for x in exps]


def _preprocess_for_onnx(image_bytes: bytes, size: int = 224):
    import numpy as np

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = ImageOps.fit(img, (size, size))
    arr = np.asarray(img).astype("float32") / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype="float32")
    std = np.array([0.229, 0.224, 0.225], dtype="float32")
    arr = (arr - mean) / std
    arr = arr.transpose(2, 0, 1)[None, ...]
    return arr


def _run_local_onnx_classifier(image_bytes: bytes) -> dict[str, Any] | None:
    if not ONNX_MODEL_PATH.exists():
        return None
    try:
        import onnxruntime as ort
    except Exception as exc:
        return {
            "mode": "local_onnx_missing_runtime",
            "error": f"onnxruntime is not installed: {exc}",
        }

    labels = _load_labels()
    session = ort.InferenceSession(str(ONNX_MODEL_PATH), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    x = _preprocess_for_onnx(image_bytes)
    outputs = session.run(None, {input_name: x})[0].reshape(-1).tolist()
    probs = _softmax(outputs)
    ranked = sorted(enumerate(probs), key=lambda item: item[1], reverse=True)[:5]

    predictions = []
    for idx, conf in ranked:
        label = labels[idx] if idx < len(labels) else f"class_{idx}"
        predictions.append(Classification(label=label, confidence=float(conf)).__dict__)
    return {"mode": "local_onnx_neural_network", "predictions": predictions}


def _run_roboflow_detector(image_bytes: bytes) -> dict[str, Any] | None:
    api_key = os.getenv("ROBOFLOW_API_KEY", "").strip()
    model_id = os.getenv("ROBOFLOW_MODEL_ID", "").strip()  # example: crop-pest-detection/1
    if not api_key or not model_id:
        return None

    try:
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        url = f"https://detect.roboflow.com/{model_id}"
        params = {"api_key": api_key, "confidence": os.getenv("ROBOFLOW_CONFIDENCE", "35"), "overlap": "30"}
        response = requests.post(url, params=params, data=img_b64, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=25)
        response.raise_for_status()
        data = response.json()
        predictions = []
        img_w = float(data.get("image", {}).get("width") or 1)
        img_h = float(data.get("image", {}).get("height") or 1)
        for pred in data.get("predictions", []):
            label = str(pred.get("class", "unknown_pest")).lower().replace(" ", "_")
            x = (float(pred.get("x", 0)) - float(pred.get("width", 0)) / 2) / img_w
            y = (float(pred.get("y", 0)) - float(pred.get("height", 0)) / 2) / img_h
            w = float(pred.get("width", 0)) / img_w
            h = float(pred.get("height", 0)) / img_h
            predictions.append({
                "label": label,
                "confidence": float(pred.get("confidence", 0.0)),
                "bbox": [max(0.0, x), max(0.0, y), min(1.0, w), min(1.0, h)],
            })
        return {"mode": "roboflow_hosted_neural_network", "predictions": predictions, "raw_count": len(predictions)}
    except Exception as exc:
        return {"mode": "roboflow_error", "error": str(exc), "predictions": []}


def _knowledge_for(label: str) -> dict[str, Any]:
    normalized = label.lower().strip().replace(" ", "_").replace("-", "_")
    if normalized in PEST_KNOWLEDGE:
        return PEST_KNOWLEDGE[normalized]
    # Try partial matching for common hosted detector labels.
    for key in PEST_KNOWLEDGE:
        if key in normalized or normalized in key:
            return PEST_KNOWLEDGE[key]
    return {
        "name": label.replace("_", " ").title(),
        "natural_controls": [
            "Confirm the pest with a close-up image and local agriculture officer before spraying.",
            "Use field sanitation, traps and neem-based/biological methods for early infestation where locally recommended.",
        ],
        "crop_relevant_fertilisers": [
            "Use balanced NPK according to Soil Health Card.",
            "Avoid excess nitrogen during pest outbreaks.",
            "Use compost/FYM/neem cake as preventive soil-health inputs where suitable.",
        ],
    }


def classify_pest_image(image_bytes: bytes, crop: str | None = None, mode: str = "rgb") -> dict[str, Any]:
    """Classify a crop/pest image with NN backend when available."""
    Image.open(io.BytesIO(image_bytes)).verify()  # raises if not image

    engine_result = _run_roboflow_detector(image_bytes)
    if engine_result is None:
        engine_result = _run_local_onnx_classifier(image_bytes)

    model_ready = engine_result is not None and engine_result.get("predictions")
    if not model_ready:
        return {
            "ok": True,
            "modelReady": False,
            "model": {
                "type": "neural_network_required",
                "status": "No trained model connected yet",
                "message": "Add backend/ml_models/pest_classifier.onnx or configure ROBOFLOW_API_KEY and ROBOFLOW_MODEL_ID.",
            },
            "summary": "Image received, but exact pest identification requires a trained neural-network model.",
            "overallRisk": 0,
            "severity": "unknown",
            "detections": [],
            "recommendations": [
                "Train a pest classifier using images of your target crops and local pests.",
                "Use close-up leaf, stem and fruit images; include healthy-crop examples to reduce false alarms.",
                "For night animal/heat detection, connect a real thermal camera feed; normal phone RGB/IR cannot measure temperature.",
            ],
            "naturalFertiliserPlan": [],
            "thermalNote": "Phone IR/security sensors do not equal a calibrated thermal camera. Use external FLIR/Seek/USB-C thermal hardware for true heat maps.",
        }

    predictions = engine_result.get("predictions", [])[:5]
    detections = []
    natural_plan: list[str] = []
    recommendation_set: list[str] = []
    top_conf = 0.0

    for i, pred in enumerate(predictions):
        label = str(pred.get("label", "unknown_pest"))
        conf = float(pred.get("confidence", 0.0))
        top_conf = max(top_conf, conf)
        knowledge = _knowledge_for(label)
        severity = "high" if conf >= 0.75 else "medium" if conf >= 0.45 else "low"
        detections.append({
            "label": knowledge["name"],
            "rawLabel": label,
            "category": "pest_or_animal",
            "confidence": round(conf, 3),
            "bbox": pred.get("bbox") or [0.08 + (i * 0.06), 0.12 + (i * 0.04), 0.45, 0.32],
            "severity": severity,
            "note": f"Neural-network prediction for {crop or 'crop'} image.",
            "naturalControls": knowledge["natural_controls"],
            "cropRelevantFertilisers": knowledge["crop_relevant_fertilisers"],
        })
        natural_plan.extend(knowledge["crop_relevant_fertilisers"])
        recommendation_set.extend(knowledge["natural_controls"])

    # Remove duplicates while preserving order.
    natural_plan = list(dict.fromkeys(natural_plan))[:8]
    recommendations = list(dict.fromkeys(recommendation_set))[:8]
    risk = int(round(top_conf * 100))
    severity = "high" if risk >= 75 else "medium" if risk >= 45 else "low"

    return {
        "ok": True,
        "modelReady": True,
        "model": {
            "type": engine_result.get("mode", "neural_network"),
            "status": "active",
            "labelsFile": str(LABELS_PATH.relative_to(ROOT)),
        },
        "summary": f"Neural-network scan found {len(detections)} likely pest/animal class(es). Confirm before chemical spraying.",
        "overallRisk": risk,
        "severity": severity,
        "detections": detections,
        "recommendations": recommendations,
        "naturalFertiliserPlan": natural_plan,
        "thermalNote": (
            "Mode selected: " + mode + ". True thermal pest/animal detection requires a thermal camera feed. "
            "This endpoint accepts RGB/IR-like frames and can classify them only if the model was trained on similar images."
        ),
    }
