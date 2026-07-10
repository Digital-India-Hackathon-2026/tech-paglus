#!/usr/bin/env python3
"""Validate a manifest, remove corrupt/exact-duplicate images, and create leakage-safe group splits."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import imagehash
import pandas as pd
from PIL import Image
from sklearn.model_selection import GroupShuffleSplit


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_image(path: Path) -> tuple[bool, str]:
    try:
        with Image.open(path) as image:
            image.verify()
        return True, ""
    except Exception as exc:
        return False, str(exc)


def split_by_group(frame: pd.DataFrame, group_column: str, seed: int, ratios: dict[str, float]) -> pd.DataFrame:
    train_ratio, val_ratio = ratios["train"], ratios["val"]
    splitter = GroupShuffleSplit(n_splits=1, train_size=train_ratio, random_state=seed)
    train_idx, remainder_idx = next(splitter.split(frame, groups=frame[group_column]))
    result = frame.copy()
    result["split"] = ""
    result.loc[result.index[train_idx], "split"] = "train"
    remainder = frame.iloc[remainder_idx]
    relative_val = val_ratio / max(1e-9, 1 - train_ratio)
    splitter_2 = GroupShuffleSplit(n_splits=1, train_size=relative_val, random_state=seed + 1)
    val_local, test_local = next(splitter_2.split(remainder, groups=remainder[group_column]))
    result.loc[remainder.index[val_local], "split"] = "val"
    result.loc[remainder.index[test_local], "split"] = "test"
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/dataset_config.json")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--output", default="datasets/classification_manifest_clean.csv")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / args.config).read_text())
    section = config["classification"]
    manifest_path = root / (args.manifest or section["manifest"])
    frame = pd.read_csv(manifest_path)
    required = {section["image_column"], section["label_column"], section["group_column"]}
    missing = required.difference(frame.columns)
    if missing:
        raise SystemExit(f"Manifest is missing columns: {sorted(missing)}")

    random.seed(config.get("seed", 42))
    rows, corrupt, duplicates, near_duplicates = [], [], [], []
    seen_hashes: dict[str, str] = {}
    seen_perceptual: list[tuple[imagehash.ImageHash, str]] = []
    perceptual_threshold = int(config.get("perceptual_hash_threshold", 4))
    for row in frame.to_dict("records"):
        path = Path(row[section["image_column"]]).expanduser()
        if not path.is_absolute():
            path = (root / path).resolve()
        valid, error = validate_image(path)
        if not valid:
            corrupt.append({"image_path": str(path), "error": error})
            continue
        digest = sha256_file(path)
        if digest in seen_hashes:
            duplicates.append({"image_path": str(path), "duplicate_of": seen_hashes[digest]})
            continue
        with Image.open(path) as image:
            perceptual = imagehash.phash(image.convert("RGB"))
        near_match = next(
            ((known_hash, known_path) for known_hash, known_path in seen_perceptual if perceptual - known_hash <= perceptual_threshold),
            None,
        )
        if near_match:
            near_duplicates.append({
                "image_path": str(path),
                "near_duplicate_of": near_match[1],
                "phash_distance": int(perceptual - near_match[0]),
            })
            continue
        seen_hashes[digest] = str(path)
        seen_perceptual.append((perceptual, str(path)))
        row[section["image_column"]] = str(path)
        row["sha256"] = digest
        row["perceptual_hash"] = str(perceptual)
        rows.append(row)

    clean = pd.DataFrame(rows)
    if clean.empty:
        raise SystemExit("No valid unique images remain after validation.")
    clean = split_by_group(
        clean,
        section["group_column"],
        int(config.get("seed", 42)),
        section["split_ratios"],
    )
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(output, index=False)
    report = {
        "input_rows": len(frame),
        "kept_rows": len(clean),
        "corrupt_images": corrupt,
        "exact_duplicates": duplicates,
        "near_duplicates": near_duplicates,
        "perceptual_hash_threshold": perceptual_threshold,
        "split_counts": clean["split"].value_counts().to_dict(),
        "group_overlap": {
            "train_val": bool(set(clean.loc[clean.split == "train", section["group_column"]]) & set(clean.loc[clean.split == "val", section["group_column"]])),
            "train_test": bool(set(clean.loc[clean.split == "train", section["group_column"]]) & set(clean.loc[clean.split == "test", section["group_column"]])),
            "val_test": bool(set(clean.loc[clean.split == "val", section["group_column"]]) & set(clean.loc[clean.split == "test", section["group_column"]])),
        },
    }
    (output.with_suffix(".report.json")).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
