import os
import logging
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, DBAPIError

from ..database import SessionLocal

# Configuration via environment variables
RETENTION_DAYS = int(os.getenv("PAGE_VISIT_RETENTION_DAYS", "30"))


def run_cleanup():
    """Delete old page_visits and run VACUUM to reclaim space.
    Also removes old analytics/session logs if tables exist.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
        # Delete old page visits
        delete_visits_sql = text(
            "DELETE FROM page_visits WHERE visited_at < :cutoff"
        )
        result = db.execute(delete_visits_sql, {"cutoff": cutoff})
        logging.info(f"Deleted {result.rowcount} old page_visits records.")

        # Optionally delete analytics logs if table exists
        try:
            db.execute(text("DELETE FROM analytics_logs WHERE created_at < :cutoff"), {"cutoff": cutoff})
            logging.info("Deleted old analytics_logs records.")
        except OperationalError:
            # Table may not exist; ignore
            logging.debug("analytics_logs table not present; skipping.")

        # Optionally delete session logs if table exists
        try:
            db.execute(text("DELETE FROM session_logs WHERE created_at < :cutoff"), {"cutoff": cutoff})
            logging.info("Deleted old session_logs records.")
        except OperationalError:
            logging.debug("session_logs table not present; skipping.")

        db.commit()
        # Run VACUUM to reclaim space (PostgreSQL specific)
        try:
            db.execute(text("VACUUM (VERBOSE, ANALYZE)"))
            logging.info("VACUUM executed successfully.")
        except (OperationalError, DBAPIError) as e:
            logging.warning(f"VACUUM failed: {e}")
    except Exception as e:
        db.rollback()
        logging.error(f"Database cleanup failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    run_cleanup()
