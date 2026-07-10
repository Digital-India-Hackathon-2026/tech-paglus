#!/usr/bin/env python3
"""Download explicitly approved public datasets with checksum and license gates.

The script refuses entries whose license has not been marked accepted. Dataset
URLs and checksums remain configuration data, so the production source does not
silently download or redistribute an unreviewed dataset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/dataset_sources.json")
    parser.add_argument("--extract", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config_path = (root / args.config).resolve()
    if not config_path.exists():
        raise SystemExit(
            "Create configs/dataset_sources.json from dataset_sources.example.json, verify every license, "
            "set accepted=true, and provide an official URL plus SHA-256 checksum."
        )
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    download_dir = root / "datasets" / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    for source in payload.get("sources", []):
        if not source.get("accepted"):
            print(f"SKIP {source.get('name')}: license not accepted")
            continue
        url = str(source.get("url") or "")
        expected = str(source.get("sha256") or "").lower()
        if not url.startswith("https://") or len(expected) != 64:
            raise SystemExit(f"{source.get('name')}: HTTPS URL and 64-character SHA-256 are required")
        archive = download_dir / Path(source.get("archive_name") or f"{source['name']}.zip").name
        print(f"Downloading {source['name']} from its configured source...")
        with urllib.request.urlopen(url, timeout=120) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
        actual = sha256_file(archive)
        if actual != expected:
            archive.unlink(missing_ok=True)
            raise SystemExit(f"Checksum mismatch for {source['name']}; downloaded file was deleted")
        if args.extract:
            destination = (root / source.get("destination", f"datasets/raw/{source['name']}")).resolve()
            destination.mkdir(parents=True, exist_ok=True)
            if not zipfile.is_zipfile(archive):
                raise SystemExit(f"{archive.name} is not a ZIP archive; extract it manually after verification")
            with zipfile.ZipFile(archive) as bundle:
                for member in bundle.infolist():
                    target = (destination / member.filename).resolve()
                    if destination not in target.parents and target != destination:
                        raise SystemExit(f"Unsafe archive member rejected: {member.filename}")
                bundle.extractall(destination)
        print(f"Verified {source['name']} ({source.get('license')})")


if __name__ == "__main__":
    main()
