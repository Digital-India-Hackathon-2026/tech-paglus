#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="configs/damage_segmentation.yaml")
    parser.add_argument("--model", default="yolo11n-seg.pt")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    model = YOLO(args.model)
    model.train(data=str(root / args.data), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
                project=str(root / "models"), name="damage_segmenter", seed=42, deterministic=True,
                patience=15, cache=False, resume=args.resume)
    model.val(data=str(root / args.data), split="test", project=str(root / "reports"), name="damage_segmenter_test")


if __name__ == "__main__":
    main()
