from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import settings


@dataclass
class ModelRecord:
    key: str
    name: str
    version: str
    task: str
    adapter: str
    file_path: Path
    labels_path: Path | None
    input_size: int
    threshold: float
    supported_crops: list[str]
    training_date: str | None
    validation_metrics: dict[str, Any]
    enabled: bool
    output_activation: str = "softmax"

    @property
    def weights_available(self) -> bool:
        return self.enabled and self.file_path.exists()

    def public_info(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "version": self.version,
            "task": self.task,
            "adapter": self.adapter,
            "input_size": self.input_size,
            "threshold": self.threshold,
            "supported_crops": self.supported_crops,
            "training_date": self.training_date,
            "validation_metrics": self.validation_metrics,
            "enabled": self.enabled,
            "weights_available": self.weights_available,
        }


def _resolve(path_value: str | None) -> Path:
    if not path_value:
        return settings.model_dir / "missing.model"
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = settings.model_dir / path
    return path.resolve()


def load_registry() -> dict[str, ModelRecord]:
    if not settings.registry_path.exists():
        return {}
    payload = json.loads(settings.registry_path.read_text(encoding="utf-8"))
    records: dict[str, ModelRecord] = {}
    for item in payload.get("models", []):
        key = str(item["key"])
        labels = item.get("labels_path")
        records[key] = ModelRecord(
            key=key,
            name=str(item.get("name", key)),
            version=str(item.get("version", "unversioned")),
            task=str(item.get("task", key)),
            adapter=str(item.get("adapter", "ultralytics")),
            file_path=_resolve(item.get("file_path")),
            labels_path=_resolve(labels) if labels else None,
            input_size=int(item.get("input_size", 640)),
            threshold=float(item.get("confidence_threshold", 0.5)),
            supported_crops=list(item.get("supported_crops", [])),
            training_date=item.get("training_date"),
            validation_metrics=dict(item.get("validation_metrics", {})),
            enabled=bool(item.get("enabled", True)),
            output_activation=str(item.get("output_activation", "softmax")),
        )
    return records
