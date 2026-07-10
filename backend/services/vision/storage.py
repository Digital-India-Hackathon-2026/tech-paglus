from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import settings


def analysis_dir(analysis_id: str) -> Path:
    safe_id = "".join(ch for ch in analysis_id if ch.isalnum() or ch in {"-", "_"})
    path = settings.storage_dir / safe_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_bytes(analysis_id: str, filename: str, data: bytes) -> Path:
    path = analysis_dir(analysis_id) / Path(filename).name
    path.write_bytes(data)
    return path


def cleanup_expired() -> int:
    """Remove expired DB records and their analysis folders.

    If the DB cannot be read, a conservative fallback removes only folders older
    than the maximum configured retention period.
    """
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    removed = 0
    expired_ids: list[str] = []

    if settings.database_path.exists():
        try:
            with sqlite3.connect(settings.database_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                rows = conn.execute(
                    "SELECT analysis_id FROM vision_analysis_sessions WHERE expires_at IS NOT NULL AND expires_at <= ?",
                    (now.isoformat(),),
                ).fetchall()
                expired_ids = [str(row[0]) for row in rows]
                if expired_ids:
                    conn.executemany(
                        "DELETE FROM vision_analysis_sessions WHERE analysis_id = ?",
                        [(analysis_id,) for analysis_id in expired_ids],
                    )
        except sqlite3.Error:
            expired_ids = []

    for analysis_id in expired_ids:
        folder = settings.storage_dir / analysis_id
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
            removed += 1

    max_age = timedelta(days=max(settings.retention_days_with_consent, 1))
    for child in settings.storage_dir.iterdir():
        if not child.is_dir() or child.name in expired_ids:
            continue
        try:
            modified = datetime.fromtimestamp(child.stat().st_mtime, tz=timezone.utc)
            if now - modified > max_age:
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
        except OSError:
            continue
    return removed
