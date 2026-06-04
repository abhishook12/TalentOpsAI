from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


RUNNING_UPLOAD_STATES = {"queued", "uploading", "analyzing", "parsing", "mapping", "validating", "preview_ready", "importing", "processing"}
TERMINAL_STATES = {"completed", "failed", "cancelled", "stuck"}


def utc_now() -> datetime:
    return datetime.utcnow()


def update_fields(job: Any, **fields: Any) -> Any:
    for key, value in fields.items():
        if hasattr(job, key) and value is not None:
            setattr(job, key, value)
    if hasattr(job, "last_heartbeat_at"):
        job.last_heartbeat_at = utc_now()
    if hasattr(job, "updated_at"):
        job.updated_at = utc_now()
    return job


def mark_progress(job: Any, status: str | None = None, current_step: str | None = None, progress_percent: int | None = None, **fields: Any) -> Any:
    payload = dict(fields)
    if status is not None:
        payload["status"] = status
    if current_step is not None:
        payload["current_step"] = current_step
    if progress_percent is not None:
        payload["progress_percent"] = max(0, min(100, int(progress_percent)))
    return update_fields(job, **payload)


def compute_job_status(job: Any) -> str:
    status = getattr(job, "status", None) or "queued"
    if status in TERMINAL_STATES:
        return status

    last_heartbeat = getattr(job, "last_heartbeat_at", None)
    if last_heartbeat and utc_now() - last_heartbeat > timedelta(seconds=90):
        return "stuck"
    return status


def serialize_upload_job(job: Any) -> dict[str, Any]:
    started_at = getattr(job, "started_at", None)
    updated_at = getattr(job, "updated_at", None) or started_at
    last_heartbeat_at = getattr(job, "last_heartbeat_at", None) or updated_at
    return {
        "job_id": getattr(job, "job_id", None),
        "filename": getattr(job, "filename", None),
        "status": compute_job_status(job),
        "current_step": getattr(job, "current_step", None),
        "progress_percent": int(getattr(job, "progress_percent", 0) or 0),
        "file_size_bytes": int(getattr(job, "file_size_bytes", 0) or 0),
        "total_rows": int(getattr(job, "total_rows", 0) or 0),
        "processed_rows": int(getattr(job, "processed_rows", 0) or 0),
        "valid_rows": int(getattr(job, "valid_rows", 0) or 0),
        "warning_rows": int(getattr(job, "warning_rows", 0) or 0),
        "duplicate_rows": int(getattr(job, "duplicate_rows", 0) or 0),
        "possible_duplicate_rows": int(getattr(job, "possible_duplicate_rows", 0) or 0),
        "enriched_rows": int(getattr(job, "enriched_rows", 0) or 0),
        "failed_rows": int(getattr(job, "failed_rows", 0) or 0),
        "inserted_rows": int(getattr(job, "inserted_rows", 0) or 0),
        "skipped_rows": int(getattr(job, "skipped_rows", 0) or 0),
        "error_count": int(getattr(job, "error_count", 0) or 0),
        "error_message": getattr(job, "error_message", None),
        "errors": getattr(job, "errors", None),
        "started_at": started_at.isoformat() if started_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
        "completed_at": getattr(job, "completed_at", None).isoformat() if getattr(job, "completed_at", None) else None,
        "last_heartbeat_at": last_heartbeat_at.isoformat() if last_heartbeat_at else None,
    }


def serialize_smart_job(job: Any) -> dict[str, Any]:
    started_at = getattr(job, "started_at", None)
    updated_at = getattr(job, "updated_at", None) or started_at
    last_heartbeat_at = getattr(job, "last_heartbeat_at", None) or updated_at
    return {
        "job_id": getattr(job, "job_id", None),
        "filename": getattr(job, "filename", None),
        "status": compute_job_status(job),
        "current_step": getattr(job, "current_step", None),
        "progress_percent": int(getattr(job, "progress_percent", 0) or 0),
        "file_size_bytes": int(getattr(job, "file_size_bytes", 0) or 0),
        "total_rows": int(getattr(job, "total_rows", 0) or 0),
        "processed_rows": int(getattr(job, "processed_rows", 0) or 0),
        "valid_rows": int(getattr(job, "valid_rows", 0) or 0),
        "warning_rows": int(getattr(job, "warning_rows", 0) or 0),
        "error_rows": int(getattr(job, "error_rows", 0) or 0),
        "duplicate_rows": int(getattr(job, "duplicate_rows", 0) or 0),
        "possible_duplicate_rows": int(getattr(job, "possible_duplicate_rows", 0) or 0),
        "enriched_rows": int(getattr(job, "enriched_rows", 0) or 0),
        "inserted_rows": int(getattr(job, "inserted_rows", 0) or 0),
        "skipped_rows": int(getattr(job, "skipped_rows", 0) or 0),
        "failed_rows": int(getattr(job, "failed_rows", 0) or 0),
        "error_message": getattr(job, "error_message", None),
        "column_mapping": getattr(job, "column_mapping", None),
        "detected_format": getattr(job, "detected_format", None),
        "format_confidence": int(getattr(job, "format_confidence", 0) or 0),
        "user_email": getattr(job, "user_email", None),
        "started_at": started_at.isoformat() if started_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
        "completed_at": getattr(job, "completed_at", None).isoformat() if getattr(job, "completed_at", None) else None,
        "last_heartbeat_at": last_heartbeat_at.isoformat() if last_heartbeat_at else None,
    }
