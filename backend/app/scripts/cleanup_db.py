import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from ..database import SessionLocal, engine


PAGE_VISIT_RETENTION_DAYS = int(os.getenv("PAGE_VISIT_RETENTION_DAYS", "30"))
ACTION_LOG_RETENTION_DAYS = int(os.getenv("ACTION_LOG_RETENTION_DAYS", "30"))
UPLOAD_RETENTION_DAYS = int(os.getenv("UPLOAD_RETENTION_DAYS", "30"))
RECLAIM_STORAGE = os.getenv("RECLAIM_STORAGE", "false").lower() in ("1", "true", "yes")
AGGRESSIVE_STORAGE_CLEANUP = os.getenv("AGGRESSIVE_STORAGE_CLEANUP", "false").lower() in ("1", "true", "yes")


def _delete_count(db, sql: str, params: dict | None = None) -> int:
    result = db.execute(text(sql), params or {})
    return int(result.rowcount or 0)


def _table_exists(table_name: str) -> bool:
    dialect = engine.dialect.name
    if dialect == "postgresql":
        with engine.connect() as conn:
            return bool(
                conn.execute(
                    text("SELECT to_regclass(:table_name) IS NOT NULL"),
                    {"table_name": table_name},
                ).scalar()
            )
    if dialect == "sqlite":
        with engine.connect() as conn:
            return bool(
                conn.execute(
                    text("SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = :table_name"),
                    {"table_name": table_name},
                ).scalar()
            )
    return False


def _column_exists(table_name: str, column_name: str) -> bool:
    dialect = engine.dialect.name
    if dialect == "postgresql":
        with engine.connect() as conn:
            return bool(
                conn.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM information_schema.columns
                        WHERE table_name = :table_name
                          AND column_name = :column_name
                    """),
                    {"table_name": table_name, "column_name": column_name},
                ).scalar()
            )
    if dialect == "sqlite":
        with engine.connect() as conn:
            rows = conn.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
            return any(row.get("name") == column_name for row in rows)
    return False


def _run_vacuum() -> None:
    dialect = engine.dialect.name
    if dialect == "postgresql":
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("VACUUM (FULL, ANALYZE)"))
        return
    if dialect == "sqlite":
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("VACUUM"))
        return


def run_cleanup(reclaim_storage: bool = RECLAIM_STORAGE):
    """Remove retention-bounded analytics/upload data and optionally compact storage."""
    db = SessionLocal()
    report: dict[str, int | str | bool] = {}
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        visit_cutoff = now - timedelta(days=PAGE_VISIT_RETENTION_DAYS)
        action_cutoff = now - timedelta(days=ACTION_LOG_RETENTION_DAYS)
        upload_cutoff = now - timedelta(days=UPLOAD_RETENTION_DAYS)

        if AGGRESSIVE_STORAGE_CLEANUP:
            report["deleted_page_visits"] = _delete_count(db, "DELETE FROM page_visits")
            report["deleted_action_logs"] = _delete_count(db, "DELETE FROM action_logs")
        else:
            report["deleted_page_visits"] = _delete_count(
                db,
                "DELETE FROM page_visits WHERE visited_at < :cutoff",
                {"cutoff": visit_cutoff},
            )
            report["deleted_action_logs"] = _delete_count(
                db,
                "DELETE FROM action_logs WHERE created_at < :cutoff",
                {"cutoff": action_cutoff},
            )

        for table in ("analytics_logs", "session_logs"):
            if _table_exists(table):
                report[f"deleted_{table}"] = _delete_count(
                    db,
                    f"DELETE FROM {table} WHERE created_at < :cutoff",
                    {"cutoff": action_cutoff},
                )
            else:
                report[f"deleted_{table}"] = 0

        if AGGRESSIVE_STORAGE_CLEANUP:
            for table in ("smart_import_rows", "raw_uploads", "staging_recruiters", "staging_companies", "smart_import_jobs", "upload_jobs"):
                report[f"deleted_{table}"] = _delete_count(db, f"DELETE FROM {table}") if _table_exists(table) else 0
        else:
            old_job_filter = """
                SELECT job_id
                FROM upload_jobs
                WHERE COALESCE(completed_at, started_at) < :cutoff
                  AND status IN ('completed', 'failed', 'error')
            """

            for table in ("smart_import_rows", "raw_uploads"):
                if _table_exists(table) and _column_exists(table, "job_id"):
                    report[f"deleted_{table}"] = _delete_count(
                        db,
                        f"DELETE FROM {table} WHERE job_id IN ({old_job_filter})",
                        {"cutoff": upload_cutoff},
                    )
                else:
                    report[f"deleted_{table}"] = 0

            for table in ("staging_recruiters", "staging_companies"):
                if _table_exists(table) and _column_exists(table, "created_at"):
                    report[f"deleted_{table}"] = _delete_count(
                        db,
                        f"DELETE FROM {table} WHERE created_at < :cutoff",
                        {"cutoff": upload_cutoff},
                    )
                else:
                    report[f"deleted_{table}"] = 0

            if _table_exists("smart_import_jobs"):
                report["deleted_smart_import_jobs"] = _delete_count(
                    db,
                    """
                    DELETE FROM smart_import_jobs
                    WHERE COALESCE(completed_at, started_at) < :cutoff
                      AND status IN ('completed', 'failed')
                    """,
                    {"cutoff": upload_cutoff},
                )
            else:
                report["deleted_smart_import_jobs"] = 0

            if _table_exists("upload_jobs"):
                report["deleted_upload_jobs"] = _delete_count(
                    db,
                    """
                    DELETE FROM upload_jobs
                    WHERE COALESCE(completed_at, started_at) < :cutoff
                      AND status IN ('completed', 'failed', 'error')
                    """,
                    {"cutoff": upload_cutoff},
                )
            else:
                report["deleted_upload_jobs"] = 0

        db.commit()
        report["reclaimed_storage_requested"] = reclaim_storage

        if reclaim_storage:
            try:
                _run_vacuum()
                report["vacuum"] = "ok"
            except (OperationalError, DBAPIError) as exc:
                logging.warning("Storage compaction failed: %s", exc)
                report["vacuum"] = "failed"
        return report
    except Exception as exc:
        db.rollback()
        logging.error("Database cleanup failed: %s", exc)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    result = run_cleanup()
    print(result)
