#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import timm
import torch
from PIL import Image
from sklearn.metrics import f1_score, multilabel_confusion_matrix, precision_score, recall_score, roc_auc_score
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from tqdm import tqdm


class MultiLabelDataset(Dataset):
    def __init__(self, frame: pd.DataFrame, classes: list[str], image_col: str, label_col: str, separator: str, size: int, train: bool):
        self.frame = frame.reset_index(drop=True)
        self.classes = classes
        self.class_to_idx = {name: index for index, name in enumerate(classes)}
        self.image_col = image_col
        self.label_col = label_col
        self.separator = separator
        ops = [transforms.Resize((size, size))]
        if train:
            ops += [transforms.RandomHorizontalFlip(), transforms.RandomRotation(12), transforms.ColorJitter(0.15, 0.15, 0.15, 0.05)]
        ops += [transforms.ToTensor(), transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])]
        self.transform = transforms.Compose(ops)

    def __len__(self) -> int:
        return len(self.frame)

    def __getitem__(self, index: int):
        row = self.frame.iloc[index]
        image = Image.open(row[self.image_col]).convert("RGB")
        target = torch.zeros(len(self.classes), dtype=torch.float32)
        for label in str(row[self.label_col]).split(self.separator):
            label = label.strip()
            if label in self.class_to_idx:
                target[self.class_to_idx[label]] = 1.0
        return self.transform(image), target


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def device_for_training() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def evaluate(model, loader, device, threshold: float):
    model.eval()
    losses, probabilities, targets = [], [], []
    criterion = nn.BCEWithLogitsLoss()
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            logits = model(images)
            losses.append(float(criterion(logits, labels).item()))
            probabilities.append(torch.sigmoid(logits).cpu().numpy())
            targets.append(labels.cpu().numpy())
    probs = np.concatenate(probabilities)
    truth = np.concatenate(targets)
    pred = (probs >= threshold).astype(int)
    metrics = {
        "loss": float(np.mean(losses)),
        "precision_micro": float(precision_score(truth, pred, average="micro", zero_division=0)),
        "recall_micro": float(recall_score(truth, pred, average="micro", zero_division=0)),
        "f1_micro": float(f1_score(truth, pred, average="micro", zero_division=0)),
        "f1_macro": float(f1_score(truth, pred, average="macro", zero_division=0)),
    }
    try:
        metrics["roc_auc_macro"] = float(roc_auc_score(truth, probs, average="macro"))
    except ValueError:
        metrics["roc_auc_macro"] = None
    per_class = []
    for index in range(truth.shape[1]):
        per_class.append({
            "class_index": index,
            "precision": float(precision_score(truth[:, index], pred[:, index], zero_division=0)),
            "recall": float(recall_score(truth[:, index], pred[:, index], zero_division=0)),
            "f1": float(f1_score(truth[:, index], pred[:, index], zero_division=0)),
            "support": int(truth[:, index].sum()),
        })
    return metrics, per_class, probs, truth


def expected_calibration_error(probs: np.ndarray, truth: np.ndarray, bins: int = 10) -> float:
    confidences = probs.reshape(-1)
    labels = truth.reshape(-1)
    ece = 0.0
    boundaries = np.linspace(0, 1, bins + 1)
    for lower, upper in zip(boundaries[:-1], boundaries[1:]):
        mask = (confidences > lower) & (confidences <= upper)
        if not mask.any():
            continue
        accuracy = labels[mask].mean()
        confidence = confidences[mask].mean()
        ece += mask.mean() * abs(float(accuracy - confidence))
    return float(ece)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-config", default="configs/dataset_config.json")
    parser.add_argument("--train-config", default="configs/classifier_config.json")
    parser.add_argument("--resume", default=None)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    data_cfg = json.loads((root / args.dataset_config).read_text())
    train_cfg = json.loads((root / args.train_config).read_text())
    section = data_cfg["classification"]
    classes = section["classes"]
    if not classes:
        raise SystemExit("Add real class names to configs/dataset_config.json before training.")
    manifest = pd.read_csv(root / section["manifest"])
    if "split" not in manifest.columns:
        raise SystemExit("Run scripts/prepare_dataset.py first to create leakage-safe splits.")

    seed = int(train_cfg.get("seed", 42))
    set_seed(seed)
    device = device_for_training()
    size = int(train_cfg["input_size"])
    datasets = {
        split: MultiLabelDataset(
            manifest[manifest.split == split], classes, section["image_column"], section["label_column"],
            section.get("label_separator", "|"), size, train=(split == "train")
        )
        for split in ["train", "val", "test"]
    }
    loaders = {
        split: DataLoader(ds, batch_size=int(train_cfg["batch_size"]), shuffle=(split == "train"),
                          num_workers=int(train_cfg.get("num_workers", 2)), pin_memory=device.type == "cuda")
        for split, ds in datasets.items()
    }
    model = timm.create_model(train_cfg["architecture"], pretrained=bool(train_cfg.get("pretrained", True)), num_classes=len(classes))
    model.to(device)

    positives = np.zeros(len(classes), dtype=np.float64)
    for labels in manifest.loc[manifest.split == "train", section["label_column"]]:
        for label in str(labels).split(section.get("label_separator", "|")):
            if label.strip() in classes:
                positives[classes.index(label.strip())] += 1
    negatives = len(datasets["train"]) - positives
    pos_weight = torch.tensor(np.divide(negatives, np.maximum(positives, 1)), dtype=torch.float32, device=device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(train_cfg["learning_rate"]), weight_decay=float(train_cfg["weight_decay"]))
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", patience=2, factor=0.5)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda" and bool(train_cfg.get("mixed_precision", True)))

    output_dir = root / train_cfg["output_dir"]
    report_dir = root / train_cfg["report_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    start_epoch, best_val, patience_count = 0, float("inf"), 0
    if args.resume:
        checkpoint = torch.load(args.resume, map_location=device)
        model.load_state_dict(checkpoint["model"])
        optimizer.load_state_dict(checkpoint["optimizer"])
        start_epoch = checkpoint["epoch"] + 1
        best_val = checkpoint.get("best_val", best_val)

    history = []
    for epoch in range(start_epoch, int(train_cfg["epochs"])):
        model.train()
        train_losses = []
        for images, labels in tqdm(loaders["train"], desc=f"epoch {epoch + 1}"):
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=device.type == "cuda" and scaler.is_enabled()):
                logits = model(images)
                loss = criterion(logits, labels)
            if scaler.is_enabled():
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                optimizer.step()
            train_losses.append(float(loss.item()))
        val_metrics, _, _, _ = evaluate(model, loaders["val"], device, float(train_cfg["threshold"]))
        scheduler.step(val_metrics["loss"])
        row = {"epoch": epoch + 1, "train_loss": float(np.mean(train_losses)), **val_metrics}
        history.append(row)
        checkpoint = {"epoch": epoch, "model": model.state_dict(), "optimizer": optimizer.state_dict(), "best_val": best_val, "classes": classes, "config": train_cfg}
        torch.save(checkpoint, output_dir / "last.pt")
        if val_metrics["loss"] < best_val:
            best_val = val_metrics["loss"]
            checkpoint["best_val"] = best_val
            torch.save(checkpoint, output_dir / "best.pt")
            patience_count = 0
        else:
            patience_count += 1
            if patience_count >= int(train_cfg["patience"]):
                break

    best = torch.load(output_dir / "best.pt", map_location=device)
    model.load_state_dict(best["model"])
    threshold = float(train_cfg["threshold"])
    test_metrics, per_class, probs, truth = evaluate(model, loaders["test"], device, threshold)
    predicted = (probs >= threshold).astype(int)
    confusion = []
    for item, name, matrix in zip(per_class, classes, multilabel_confusion_matrix(truth, predicted)):
        item["class_name"] = name
        tn, fp, fn, tp = [int(value) for value in matrix.ravel()]
        confusion.append({"class_name": name, "tn": tn, "fp": fp, "fn": fn, "tp": tp})
    test_metrics["expected_calibration_error"] = expected_calibration_error(probs, truth)

    error_rows = []
    test_frame = datasets["test"].frame
    for sample_index in range(len(test_frame)):
        for class_index, class_name in enumerate(classes):
            expected = int(truth[sample_index, class_index])
            actual = int(predicted[sample_index, class_index])
            if expected == actual:
                continue
            error_rows.append({
                "image_path": str(test_frame.iloc[sample_index][section["image_column"]]),
                "class_name": class_name,
                "error_type": "false_positive" if actual else "false_negative",
                "target": expected,
                "probability": float(probs[sample_index, class_index]),
                "threshold": threshold,
                "group_id": str(test_frame.iloc[sample_index][section["group_column"]]),
            })
    pd.DataFrame(confusion).to_csv(report_dir / "multilabel_confusion_matrix.csv", index=False)
    pd.DataFrame(error_rows).to_csv(report_dir / "error_analysis.csv", index=False)
    report = {
        "architecture": train_cfg["architecture"],
        "classes": classes,
        "history": history,
        "test_metrics": test_metrics,
        "per_class": per_class,
        "multilabel_confusion_matrix": confusion,
        "error_analysis_rows": len(error_rows),
        "seed": seed,
    }
    (report_dir / "evaluation.json").write_text(json.dumps(report, indent=2))
    (output_dir / "labels.json").write_text(json.dumps(classes, indent=2))
    print(json.dumps(test_metrics, indent=2))


if __name__ == "__main__":
    main()
