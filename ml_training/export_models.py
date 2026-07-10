#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import timm
import torch
from ultralytics import YOLO


def export_classifier(checkpoint_path: Path, output: Path, input_size: int) -> None:
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    config = checkpoint["config"]
    classes = checkpoint["classes"]
    model = timm.create_model(config["architecture"], pretrained=False, num_classes=len(classes))
    model.load_state_dict(checkpoint["model"])
    model.eval()
    dummy = torch.randn(1, 3, input_size, input_size)
    torch.onnx.export(
        model,
        dummy,
        output,
        input_names=["images"],
        output_names=["logits"],
        dynamic_axes={"images": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
    )
    output.with_name("disease_labels.json").write_text(json.dumps(classes, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--classifier-checkpoint")
    parser.add_argument("--detector")
    parser.add_argument("--segmenter")
    parser.add_argument("--backend-model-dir", default="../backend/model_artifacts")
    parser.add_argument("--input-size", type=int, default=384)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    target = (root / args.backend_model_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    if args.classifier_checkpoint:
        export_classifier(Path(args.classifier_checkpoint), target / "disease_classifier.onnx", args.input_size)
    if args.detector:
        exported = Path(YOLO(args.detector).export(format="onnx", imgsz=640, simplify=True, dynamic=True))
        shutil.copy2(exported, target / "pest_detector.onnx")
    if args.segmenter:
        exported = Path(YOLO(args.segmenter).export(format="onnx", imgsz=640, simplify=True, dynamic=True))
        shutil.copy2(exported, target / "damage_segmenter.onnx")
    print(f"Exported available models to {target}")


if __name__ == "__main__":
    main()
