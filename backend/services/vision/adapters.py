from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from PIL import Image

from .config import settings
from .registry import ModelRecord


class ModelLoadError(RuntimeError):
    pass


def _ultralytics_device() -> str | int:
    configured = settings.inference_device
    if configured and configured != "auto":
        return 0 if configured in {"cuda", "gpu", "0"} else configured
    try:
        import torch

        if torch.cuda.is_available():
            return 0
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


@dataclass
class AdapterStatus:
    key: str
    ready: bool
    message: str


class BaseAdapter:
    def __init__(self, record: ModelRecord):
        self.record = record
        self.ready = False
        self.message = "not loaded"

    def load(self) -> AdapterStatus:
        raise NotImplementedError

    def predict(self, image: Image.Image) -> dict[str, Any]:
        raise NotImplementedError


class UltralyticsAdapter(BaseAdapter):
    def __init__(self, record: ModelRecord):
        super().__init__(record)
        self.model = None

    def load(self) -> AdapterStatus:
        if not self.record.weights_available:
            self.message = "weights missing or model disabled"
            return AdapterStatus(self.record.key, False, self.message)
        try:
            from ultralytics import YOLO

            self.model = YOLO(str(self.record.file_path))
            self.ready = True
            self.message = "loaded"
        except Exception as exc:
            self.ready = False
            self.message = f"load failed: {exc}"
        return AdapterStatus(self.record.key, self.ready, self.message)

    def predict(self, image: Image.Image) -> dict[str, Any]:
        if not self.ready or self.model is None:
            return {"ready": False, "error": self.message}
        results = self.model.predict(
            source=image,
            imgsz=self.record.input_size,
            conf=self.record.threshold,
            verbose=False,
            device=_ultralytics_device(),
        )
        if not results:
            return {"ready": True, "predictions": [], "detections": [], "regions": []}
        result = results[0]
        names = result.names or {}

        if getattr(result, "probs", None) is not None:
            probs = result.probs.data.detach().cpu().tolist()
            ranked = sorted(enumerate(probs), key=lambda item: item[1], reverse=True)[:5]
            return {
                "ready": True,
                "predictions": [
                    {"label": str(names.get(idx, idx)), "confidence": float(score)}
                    for idx, score in ranked
                ],
            }

        detections: list[dict[str, Any]] = []
        regions: list[dict[str, Any]] = []
        image_w, image_h = image.size
        boxes = getattr(result, "boxes", None)
        masks = getattr(result, "masks", None)
        mask_data = None
        if masks is not None and getattr(masks, "data", None) is not None:
            try:
                mask_data = masks.data.detach().cpu().numpy()
            except Exception:
                mask_data = None

        union_area_fraction = None
        if mask_data is not None and len(mask_data):
            try:
                union_area_fraction = float((mask_data > 0.5).any(axis=0).mean())
            except Exception:
                union_area_fraction = None

        if boxes is not None:
            for idx, box in enumerate(boxes):
                xyxy = box.xyxy[0].detach().cpu().tolist()
                x1, y1, x2, y2 = [float(v) for v in xyxy]
                cls_idx = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                label = str(names.get(cls_idx, cls_idx))
                bbox = [
                    max(0.0, x1 / image_w),
                    max(0.0, y1 / image_h),
                    min(1.0, (x2 - x1) / image_w),
                    min(1.0, (y2 - y1) / image_h),
                ]
                item = {
                    "label": label,
                    "confidence": confidence,
                    "bbox": bbox,
                    "bbox_pixels": [x1, y1, x2, y2],
                }
                detections.append(item)
                area_fraction = bbox[2] * bbox[3]
                polygon = None
                if mask_data is not None and idx < len(mask_data):
                    mask = mask_data[idx]
                    area_fraction = float(mask.mean())
                if masks is not None and getattr(masks, "xy", None) is not None and idx < len(masks.xy):
                    try:
                        polygon = [
                            [max(0.0, min(1.0, float(px) / image_w)), max(0.0, min(1.0, float(py) / image_h))]
                            for px, py in masks.xy[idx].tolist()
                        ]
                    except Exception:
                        polygon = None
                regions.append({
                    **item,
                    "polygon": polygon,
                    "area_fraction": max(0.0, min(1.0, area_fraction)),
                })
        return {
            "ready": True,
            "detections": detections,
            "regions": regions,
            "union_area_fraction": union_area_fraction,
        }


class OnnxMultiLabelAdapter(BaseAdapter):
    def __init__(self, record: ModelRecord):
        super().__init__(record)
        self.session = None
        self.labels: list[str] = []
        self.input_name = ""

    def load(self) -> AdapterStatus:
        if not self.record.weights_available:
            self.message = "weights missing or model disabled"
            return AdapterStatus(self.record.key, False, self.message)
        try:
            import onnxruntime as ort

            providers = ["CPUExecutionProvider"]
            available = ort.get_available_providers()
            if "CoreMLExecutionProvider" in available:
                providers = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
            self.session = ort.InferenceSession(str(self.record.file_path), providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            if self.record.labels_path and self.record.labels_path.exists():
                payload = json.loads(self.record.labels_path.read_text(encoding="utf-8"))
                self.labels = payload if isinstance(payload, list) else list(payload.get("labels", []))
            self.ready = bool(self.labels)
            self.message = "loaded" if self.ready else "label file missing or empty"
        except Exception as exc:
            self.ready = False
            self.message = f"load failed: {exc}"
        return AdapterStatus(self.record.key, self.ready, self.message)

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value >= 0:
            z = math.exp(-value)
            return 1.0 / (1.0 + z)
        z = math.exp(value)
        return z / (1.0 + z)

    @staticmethod
    def _softmax(values: list[float]) -> list[float]:
        if not values:
            return []
        maximum = max(values)
        exps = [math.exp(value - maximum) for value in values]
        total = sum(exps) or 1.0
        return [value / total for value in exps]

    def predict(self, image: Image.Image) -> dict[str, Any]:
        if not self.ready or self.session is None:
            return {"ready": False, "error": self.message}
        import numpy as np

        resized = image.resize((self.record.input_size, self.record.input_size), Image.Resampling.LANCZOS)
        array = np.asarray(resized).astype("float32") / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype="float32")
        std = np.array([0.229, 0.224, 0.225], dtype="float32")
        array = ((array - mean) / std).transpose(2, 0, 1)[None, ...]
        output = self.session.run(None, {self.input_name: array})[0]
        logits = output.reshape(-1).tolist()
        if self.record.output_activation == "sigmoid":
            probabilities = [self._sigmoid(float(value)) for value in logits]
        else:
            probabilities = self._softmax([float(value) for value in logits])
        ranked = sorted(enumerate(probabilities), key=lambda item: item[1], reverse=True)
        return {
            "ready": True,
            "predictions": [
                {"label": self.labels[idx], "confidence": float(score)}
                for idx, score in ranked[: min(5, len(ranked))]
                if idx < len(self.labels)
            ],
        }


def build_adapter(record: ModelRecord) -> BaseAdapter:
    if record.adapter == "onnx_multilabel":
        return OnnxMultiLabelAdapter(record)
    return UltralyticsAdapter(record)
