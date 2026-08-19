"""
Automated Data Backup & Snapshot Engine
=======================================
Generates immutable, timestamped forensic snapshots of the 367k+ recruiter Parquet
database and system metadata with automatic retention management.
"""

import os
import shutil
import hashlib
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger("talentops.backup")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
SNAPSHOTS_DIR = os.path.join(DATA_DIR, "snapshots")
PARQUET_FILE = os.path.join(DATA_DIR, "recruiters_full.parquet")
MAX_SNAPSHOTS_TO_KEEP = 7


def _calc_sha256(filepath: str) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


class BackupService:
    def __init__(self):
        os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

    def create_snapshot(self, reason: str = "manual_admin_trigger") -> Dict[str, Any]:
        """
        Creates a new immutable snapshot of the active Parquet dataset.
        """
        if not os.path.exists(PARQUET_FILE):
            raise FileNotFoundError(f"Primary dataset file not found at: {PARQUET_FILE}")

        os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        snapshot_filename = f"recruiters_snapshot_{timestamp_str}.parquet"
        snapshot_meta_filename = f"recruiters_snapshot_{timestamp_str}.json"
        
        target_path = os.path.join(SNAPSHOTS_DIR, snapshot_filename)
        meta_target_path = os.path.join(SNAPSHOTS_DIR, snapshot_meta_filename)

        # Copy parquet file
        t0 = time.perf_counter()
        shutil.copy2(PARQUET_FILE, target_path)
        copy_ms = (time.perf_counter() - t0) * 1000

        size_bytes = os.path.getsize(target_path)
        checksum = _calc_sha256(target_path)

        metadata = {
            "snapshot_id": f"snap_{timestamp_str}",
            "filename": snapshot_filename,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "checksum_sha256": checksum,
            "reason": reason,
            "copy_duration_ms": round(copy_ms, 2)
        }

        with open(meta_target_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # Enforce retention policy
        self._enforce_retention()

        logger.info(f"Snapshot created successfully: {snapshot_filename} ({metadata['size_mb']} MB)")
        return metadata

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """
        Lists all available snapshots sorted from newest to oldest.
        """
        if not os.path.exists(SNAPSHOTS_DIR):
            return []

        meta_files = [f for f in os.listdir(SNAPSHOTS_DIR) if f.endswith(".json")]
        snapshots = []
        for mf in meta_files:
            try:
                with open(os.path.join(SNAPSHOTS_DIR, mf), "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    parquet_name = meta.get("filename")
                    parquet_exists = os.path.exists(os.path.join(SNAPSHOTS_DIR, parquet_name)) if parquet_name else False
                    meta["is_valid"] = parquet_exists
                    snapshots.append(meta)
            except Exception as e:
                logger.warning(f"Error reading snapshot meta {mf}: {e}")

        snapshots.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return snapshots

    def _enforce_retention(self):
        """
        Deletes older snapshots beyond MAX_SNAPSHOTS_TO_KEEP.
        """
        snapshots = self.list_snapshots()
        if len(snapshots) > MAX_SNAPSHOTS_TO_KEEP:
            to_delete = snapshots[MAX_SNAPSHOTS_TO_KEEP:]
            for s in to_delete:
                try:
                    p_path = os.path.join(SNAPSHOTS_DIR, s["filename"])
                    m_path = os.path.join(SNAPSHOTS_DIR, s["filename"].replace(".parquet", ".json"))
                    if os.path.exists(p_path):
                        os.remove(p_path)
                    if os.path.exists(m_path):
                        os.remove(m_path)
                    logger.info(f"Rotated out old snapshot: {s['filename']}")
                except Exception as e:
                    logger.warning(f"Error deleting old snapshot {s.get('filename')}: {e}")


backup_service = BackupService()
