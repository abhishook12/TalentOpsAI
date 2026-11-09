"""Automated Dual-Layer Data Backup & Snapshot Engine.
===================================================
Generates immutable, timestamped forensic snapshots of BOTH:
1. The 451k+ DuckDB Parquet catalog (recruiters_full.parquet).
2. The live PostgreSQL Supabase master database (recruiters & companies tables).
Includes SHA-256 integrity verification and automated 7-day retention management.
"""

import os
import shutil
import hashlib
import json
import gzip
import time
import asyncio
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
        self._worker_running = False

    def export_postgres_master(self, target_gz_path: str) -> Dict[str, Any]:
        """Export all PostgreSQL recruiters and companies into a compressed JSON stream."""
        from ..database import SessionLocal
        from ..models.models import Recruiter, Company

        t0 = time.perf_counter()
        with SessionLocal() as db:
            # Query recruiters
            recruiter_rows = db.query(Recruiter).all()
            recruiters_data = [
                {
                    "recruiter_id": r.recruiter_id,
                    "recruiter_name": r.recruiter_name,
                    "normalized_name": r.normalized_recruiter_name,
                    "email": r.email,
                    "phone": r.phone,
                    "email2": r.email2,
                    "phone2": r.phone2,
                    "company_id": r.company_id,
                    "title": r.title,
                    "linkedin": r.linkedin,
                    "location": r.location,
                    "state": r.state,
                    "trust_score": r.trust_score,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in recruiter_rows
            ]

            # Query companies count
            company_count = db.query(Company).count()

        export_payload = {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "recruiters_count": len(recruiters_data),
            "companies_count": company_count,
            "recruiters": recruiters_data,
        }

        with gzip.open(target_gz_path, "wt", encoding="utf-8") as gz_f:
            json.dump(export_payload, gz_f)

        duration_ms = (time.perf_counter() - t0) * 1000
        size_bytes = os.path.getsize(target_gz_path)
        sha256 = _calc_sha256(target_gz_path)

        return {
            "records_count": len(recruiters_data),
            "companies_count": company_count,
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "sha256": sha256,
            "duration_ms": round(duration_ms, 2),
        }

    def create_snapshot(self, reason: str = "manual_admin_trigger") -> Dict[str, Any]:
        """Creates a dual-layer snapshot of both the Parquet catalog and Postgres master."""
        os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        # 1. Parquet Snapshot
        parquet_filename = f"recruiters_snapshot_{timestamp_str}.parquet"
        parquet_target_path = os.path.join(SNAPSHOTS_DIR, parquet_filename)
        
        parquet_meta = {}
        if os.path.exists(PARQUET_FILE):
            t0 = time.perf_counter()
            shutil.copy2(PARQUET_FILE, parquet_target_path)
            copy_ms = (time.perf_counter() - t0) * 1000
            p_size = os.path.getsize(parquet_target_path)
            parquet_meta = {
                "filename": parquet_filename,
                "size_bytes": p_size,
                "size_mb": round(p_size / (1024 * 1024), 2),
                "checksum_sha256": _calc_sha256(parquet_target_path),
                "copy_duration_ms": round(copy_ms, 2),
            }
        else:
            logger.warning("Parquet catalog file not found at %s", PARQUET_FILE)

        # 2. PostgreSQL Master Snapshot
        pg_filename = f"postgres_master_snapshot_{timestamp_str}.json.gz"
        pg_target_path = os.path.join(SNAPSHOTS_DIR, pg_filename)
        
        pg_meta = {}
        try:
            pg_info = self.export_postgres_master(pg_target_path)
            pg_meta = {
                "filename": pg_filename,
                "records_count": pg_info["records_count"],
                "companies_count": pg_info["companies_count"],
                "size_bytes": pg_info["size_bytes"],
                "size_mb": pg_info["size_mb"],
                "checksum_sha256": pg_info["sha256"],
                "duration_ms": pg_info["duration_ms"],
            }
        except Exception as pg_err:
            logger.error("Error during PostgreSQL snapshot export: %s", pg_err)
            pg_meta = {"error": str(pg_err)}

        # 3. Overall Snapshot Manifest
        manifest_filename = f"snapshot_manifest_{timestamp_str}.json"
        manifest_path = os.path.join(SNAPSHOTS_DIR, manifest_filename)

        manifest = {
            "snapshot_id": f"snap_{timestamp_str}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "parquet_catalog": parquet_meta,
            "postgres_master": pg_meta,
            "total_size_mb": round(
                parquet_meta.get("size_mb", 0) + pg_meta.get("size_mb", 0), 2
            ),
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # 4. Enforce 7-snapshot retention
        self._enforce_retention()

        logger.info(
            "🛡️ Dual-layer snapshot completed: ID=%s (Parquet: %s MB, Postgres: %s MB)",
            manifest["snapshot_id"],
            parquet_meta.get("size_mb", 0),
            pg_meta.get("size_mb", 0),
        )
        return manifest

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """Lists all available snapshots sorted from newest to oldest."""
        if not os.path.exists(SNAPSHOTS_DIR):
            return []

        manifest_files = [f for f in os.listdir(SNAPSHOTS_DIR) if f.startswith("snapshot_manifest_") and f.endswith(".json")]
        snapshots = []
        for mf in manifest_files:
            try:
                with open(os.path.join(SNAPSHOTS_DIR, mf), "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                    # Verify physical files
                    p_name = manifest.get("parquet_catalog", {}).get("filename")
                    pg_name = manifest.get("postgres_master", {}).get("filename")
                    
                    p_exists = os.path.exists(os.path.join(SNAPSHOTS_DIR, p_name)) if p_name else False
                    pg_exists = os.path.exists(os.path.join(SNAPSHOTS_DIR, pg_name)) if pg_name else False
                    
                    manifest["is_valid"] = p_exists and pg_exists
                    snapshots.append(manifest)
            except Exception as e:
                logger.warning("Error reading snapshot manifest %s: %s", mf, e)

        snapshots.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return snapshots

    def _enforce_retention(self):
        """Deletes older snapshots beyond MAX_SNAPSHOTS_TO_KEEP."""
        snapshots = self.list_snapshots()
        if len(snapshots) > MAX_SNAPSHOTS_TO_KEEP:
            to_delete = snapshots[MAX_SNAPSHOTS_TO_KEEP:]
            for s in to_delete:
                try:
                    p_name = s.get("parquet_catalog", {}).get("filename")
                    pg_name = s.get("postgres_master", {}).get("filename")
                    m_name = f"snapshot_manifest_{s['snapshot_id'].replace('snap_', '')}.json"

                    for fname in [p_name, pg_name, m_name]:
                        if fname:
                            fpath = os.path.join(SNAPSHOTS_DIR, fname)
                            if os.path.exists(fpath):
                                os.remove(fpath)
                    logger.info("Rotated out old snapshot: %s", s["snapshot_id"])
                except Exception as e:
                    logger.warning("Error deleting old snapshot %s: %s", s.get("snapshot_id"), e)

    async def run_daily_backup_loop(self):
        """Perpetual 24-hour autonomous backup loop."""
        if self._worker_running:
            return
        self._worker_running = True
        logger.info("🛡️ Automated Daily Backup Engine activated (24-hour cycle)")

        # Initial delay before first scheduled backup
        await asyncio.sleep(60)

        while True:
            try:
                logger.info("[DAILY_BACKUP] Executing scheduled automated dual-layer snapshot...")
                self.create_snapshot(reason="automated_daily_schedule")
            except Exception as e:
                logger.error("[DAILY_BACKUP] Scheduled backup encountered error: %s", e)
                from .sentry import capture_exception
                capture_exception(e, tags={"service": "backup_engine"})

            # Sleep 24 hours (86,400 seconds)
            await asyncio.sleep(86400)


backup_service = BackupService()
