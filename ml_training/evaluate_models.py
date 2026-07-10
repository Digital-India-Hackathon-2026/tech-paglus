#!/usr/bin/env python3
"""Evaluate detector/segmenter models on held-out test data.

Ultralytics supplies precision, recall and mAP. For segmentation, this script
also rasterizes YOLO polygon labels and computes mean image-level IoU and Dice
for the union of damaged regions. Results are written to reports/.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import yaml
from PIL import Image, ImageDraw
from ultralytics import YOLO

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def _resolve_split_images(data_yaml: Path, split: str = "test") -> list[Path]:
    payload = yaml.safe_load(data_yaml.read_text(encoding="utf-8")) or {}
    base = Path(payload.get("path", data_yaml.parent))
    if not base.is_absolute():
        base = (data_yaml.parent / base).resolve()
    entry = payload.get(split)
    if not entry:
        return []
    target = Path(entry)
    if not target.is_absolute():
        target = (base / target).resolve()
    if target.is_file() and target.suffix.lower() == ".txt":
        images = []
        for line in target.read_text(encoding="utf-8").splitlines():
            value = line.strip()
            if not value:
                continue
            image = Path(value)
            if not image.is_absolute():
                image = (base / image).resolve()
            images.append(image)
        return images
    if target.is_dir():
        return sorted(path for path in target.rglob("*") if path.suffix.lower() in IMAGE_SUFFIXES)
    return [target] if target.suffix.lower() in IMAGE_SUFFIXES else []


def _label_path_for_image(image_path: Path) -> Path:
    parts = list(image_path.parts)
    if "images" in parts:
        index = len(parts) - 1 - parts[::-1].index("images")
        parts[index] = "labels"
        return Path(*parts).with_suffix(".txt")
    return image_path.parent.parent / "labels" / image_path.parent.name / f"{image_path.stem}.txt"


def _ground_truth_union(label_path: Path, width: int, height: int) -> np.ndarray:
    canvas = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(canvas)
    if not label_path.exists():
        return np.zeros((height, width), dtype=bool)
    for line in label_path.read_text(encoding="utf-8").splitlines():
        values = line.split()
        if len(values) < 7:  # class plus at least three polygon points
            continue
        coords = [float(value) for value in values[1:]]
        points = [
            (int(max(0.0, min(1.0, coords[index])) * width), int(max(0.0, min(1.0, coords[index + 1])) * height))
            for index in range(0, len(coords) - 1, 2)
        ]
        if len(points) >= 3:
            draw.polygon(points, fill=1)
    return np.asarray(canvas, dtype=bool)


def _predicted_union(result, width: int, height: int) -> np.ndarray:
    masks = getattr(result, "masks", None)
    if masks is None or getattr(masks, "data", None) is None:
        return np.zeros((height, width), dtype=bool)
    data = masks.data.detach().cpu().numpy()
    if not len(data):
        return np.zeros((height, width), dtype=bool)
    union = np.any(data > 0.5, axis=0).astype(np.uint8) * 255
    resized = Image.fromarray(union).resize((width, height), Image.Resampling.NEAREST)
    return np.asarray(resized, dtype=np.uint8) > 0


def segmentation_iou_dice(model: YOLO, data_yaml: Path) -> dict:
    images = _resolve_split_images(data_yaml, "test")
    rows = []
    for image_path in images:
        if not image_path.exists():
            continue
        with Image.open(image_path) as image:
            width, height = image.size
        result_list = model.predict(str(image_path), verbose=False)
        if not result_list:
            continue
        predicted = _predicted_union(result_list[0], width, height)
        truth = _ground_truth_union(_label_path_for_image(image_path), width, height)
        intersection = int(np.logical_and(predicted, truth).sum())
        union = int(np.logical_or(predicted, truth).sum())
        pred_area = int(predicted.sum())
        truth_area = int(truth.sum())
        iou = 1.0 if union == 0 else intersection / union
        denominator = pred_area + truth_area
        dice = 1.0 if denominator == 0 else (2 * intersection) / denominator
        rows.append({"image": str(image_path), "iou": float(iou), "dice": float(dice)})
    return {
        "images_evaluated": len(rows),
        "mean_iou": float(np.mean([row["iou"] for row in rows])) if rows else None,
        "mean_dice": float(np.mean([row["dice"] for row in rows])) if rows else None,
        "per_image": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--detector", default=None)
    parser.add_argument("--detector-data", default="configs/pest_detection.yaml")
    parser.add_argument("--segmenter", default=None)
    parser.add_argument("--segmenter-data", default="configs/damage_segmentation.yaml")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    consolidated = {}
    if args.detector:
        data_path = (root / args.detector_data).resolve()
        metrics = YOLO(args.detector).val(data=str(data_path), split="test", plots=True)
        consolidated["detector"] = {
            "map50_95": float(metrics.box.map),
            "map50": float(metrics.box.map50),
            "precision": float(metrics.box.mp),
            "recall": float(metrics.box.mr),
        }
    if args.segmenter:
        data_path = (root / args.segmenter_data).resolve()
        model = YOLO(args.segmenter)
        metrics = model.val(data=str(data_path), split="test", plots=True)
        consolidated["segmenter"] = {
            "box_map50_95": float(metrics.box.map),
            "mask_map50_95": float(metrics.seg.map),
            "mask_map50": float(metrics.seg.map50),
            "iou_dice": segmentation_iou_dice(model, data_path),
        }
    if not consolidated:
        raise SystemExit("Provide --detector and/or --segmenter. Classifier metrics are written by train_classifier.py.")
    output = root / "reports" / "consolidated_evaluation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(consolidated, indent=2), encoding="utf-8")
    print(json.dumps(consolidated, indent=2))


if __name__ == "__main__":
    main()
