# AgriSarthi vision training workspace

This directory is intentionally separate from `backend/`. It contains reproducible training, evaluation, and export code; it does not contain production model claims or trained weights.

## Dataset manifest

For multi-label disease training, create `datasets/classification_manifest.csv` with:

```csv
image_path,labels,group_id
/path/to/image1.jpg,fungal__early_blight|nutrient__nitrogen_deficiency,fieldA_plant12
/path/to/image2.jpg,healthy,fieldB_plant03
```

`group_id` must identify the same plant, field burst, or video sequence. `scripts/prepare_dataset.py` keeps each group in only one split to prevent leakage.

For YOLO detection and segmentation, use standard Ultralytics directory and annotation formats. Fill the real class names in the YAML files before training.

## Public dataset download and licensing

Copy `configs/dataset_sources.example.json` to `configs/dataset_sources.json`, enter only official HTTPS download URLs, exact licenses and SHA-256 checksums, then set `accepted` to `true` only after reviewing the terms:

```bash
python scripts/download_datasets.py --extract
```

The downloader rejects unaccepted licenses, checksum mismatches and unsafe ZIP paths. It does not bundle or silently fetch any dataset.

## Public dataset checklist

Before downloading or combining a public dataset, record:

1. Dataset URL, owner, and version.
2. License and whether commercial/redistribution use is permitted.
3. Crop, disease, pest, geography, imaging conditions, and label quality.
4. Whether images are duplicated across public datasets.
5. Whether field/video groups can be identified for leakage-safe splitting.

Never mix test images into training. Farmer images require explicit consent and expert review before becoming dataset candidates.

## Commands

```bash
cd ml_training
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-training.txt

python scripts/prepare_dataset.py
# detects corrupt images, exact duplicates, perceptual near-duplicates and group leakage
python train_classifier.py
python train_detector.py --data configs/pest_detection.yaml
python train_segmenter.py --data configs/damage_segmentation.yaml
python evaluate_models.py --detector models/pest_detector/weights/best.pt --segmenter models/damage_segmenter/weights/best.pt
python export_models.py --classifier-checkpoint models/disease_classifier/best.pt --detector models/pest_detector/weights/best.pt --segmenter models/damage_segmenter/weights/best.pt
```

## Evaluation outputs

- Classifier: precision, recall, micro/macro F1, per-class metrics, multi-label confusion matrices, false-positive/false-negative error rows, ROC-AUC where possible, and expected calibration error.
- Detector: precision, recall, mAP@0.50, and mAP@0.50:0.95.
- Segmenter: mask mAP, validation plots, and held-out image-level union-mask IoU and Dice scores from YOLO polygon labels.
- Always inspect false positives, false negatives, class imbalance, geographic bias, and performance by crop, plant part, growth stage, and capture device.

The sample folders contain only empty structure markers. They do not demonstrate accuracy.
