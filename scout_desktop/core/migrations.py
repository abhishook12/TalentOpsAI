"""
migrations.py — Autonomous SQLite Database Migration Engine for TalentOps Scout Desktop.

Guarantees database schema integrity across updates:
1. Tracks applied versions in `schema_migrations`.
2. Applies pending schema migrations sequentially in transactions.
3. Automatically rolls back on any error to prevent database corruption.
4. Provides full audit trail of local schema evolution.
"""

import sqlite3
import logging
from typing import List, Dict, Any, Callable
from .paths import get_database_path

logger = logging.getLogger("scout.migrations")


class MigrationError(Exception):
    """Raised when a local database migration fails."""
    pass


# ── Registered Migrations ───────────────────────────────────────────────────

def _migration_001_initial_queue(cursor: sqlite3.Cursor):
    """Initial local queue table."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS local_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cluster_data TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            retry_count INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            created_at REAL NOT NULL,
            synced_at REAL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON local_queue(status)")


def _migration_002_dedup_and_backoff(cursor: sqlite3.Cursor):
    """Adds content_hash and exponential backoff retry scheduling."""
    # Check if columns already exist before adding
    cursor.execute("PRAGMA table_info(local_queue)")
    cols = [r[1] for r in cursor.fetchall()]
    
    if "content_hash" not in cols:
        cursor.execute("ALTER TABLE local_queue ADD COLUMN content_hash TEXT")
    if "next_retry_at" not in cols:
        cursor.execute("ALTER TABLE local_queue ADD COLUMN next_retry_at REAL")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_hash ON local_queue(content_hash)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_retry ON local_queue(next_retry_at)")


def _migration_003_intelligence_provenance(cursor: sqlite3.Cursor):
    """Adds 4-tier intelligence metadata (source_type, scope, hardware provenance)."""
    cursor.execute("PRAGMA table_info(local_queue)")
    cols = [r[1] for r in cursor.fetchall()]
    
    if "source_type" not in cols:
        cursor.execute("ALTER TABLE local_queue ADD COLUMN source_type TEXT DEFAULT 'SCOUT_DESKTOP'")
    if "authorization_scope" not in cols:
        cursor.execute("ALTER TABLE local_queue ADD COLUMN authorization_scope TEXT DEFAULT 'desktop.active_observation'")
    if "hardware_provenance" not in cols:
        cursor.execute("ALTER TABLE local_queue ADD COLUMN hardware_provenance TEXT")


def _migration_004_evidence_ledger_cache(cursor: sqlite3.Cursor):
    """Adds local evidence ledger cache table."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS local_evidence_cache (
            capture_id TEXT PRIMARY KEY,
            filepath TEXT NOT NULL,
            content_hash TEXT,
            visual_change_score REAL,
            status TEXT NOT NULL DEFAULT 'CAPTURED',
            created_at REAL NOT NULL,
            expires_at REAL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_status ON local_evidence_cache(status)")


MIGRATION_REGISTRY: List[Dict[str, Any]] = [
    {"version": 1, "name": "001_initial_queue", "func": _migration_001_initial_queue},
    {"version": 2, "name": "002_dedup_and_backoff", "func": _migration_002_dedup_and_backoff},
    {"version": 3, "name": "003_intelligence_provenance", "func": _migration_003_intelligence_provenance},
    {"version": 4, "name": "004_evidence_ledger_cache", "func": _migration_004_evidence_ledger_cache},
]


# ── Migration Runner ─────────────────────────────────────────────────────────

class MigrationRunner:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or get_database_path()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def ensure_migration_table(self, conn: sqlite3.Connection):
        """Creates schema_migrations table if not present."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    def get_applied_versions(self) -> List[int]:
        """Returns sorted list of applied migration version numbers."""
        with self._get_connection() as conn:
            self.ensure_migration_table(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_migrations ORDER BY version ASC")
            return [row[0] for row in cursor.fetchall()]

    def get_current_version(self) -> int:
        """Returns the highest applied schema version."""
        applied = self.get_applied_versions()
        return max(applied) if applied else 0

    def run_migrations(self) -> Dict[str, Any]:
        """
        Executes all pending migrations in order.
        Transactions ensure all-or-nothing semantics per migration.
        """
        with self._get_connection() as conn:
            self.ensure_migration_table(conn)
            applied = set(self.get_applied_versions())
            
            pending = [m for m in MIGRATION_REGISTRY if m["version"] not in applied]
            if not pending:
                logger.debug("Database schema is up to date (Version %s)", self.get_current_version())
                return {"applied_count": 0, "current_version": self.get_current_version(), "migrations": []}

            logger.info("Applying %d pending database migration(s)...", len(pending))
            applied_names = []
            
            for m in pending:
                ver = m["version"]
                name = m["name"]
                func = m["func"]
                logger.info("Applying migration %03d: %s...", ver, name)
                
                try:
                    cursor = conn.cursor()
                    cursor.execute("BEGIN TRANSACTION")
                    func(cursor)
                    cursor.execute("INSERT INTO schema_migrations (version, name) VALUES (?, ?)", (ver, name))
                    conn.commit()
                    applied_names.append(name)
                    logger.info("✓ Migration %03d applied successfully.", ver)
                except Exception as e:
                    conn.rollback()
                    logger.error("❌ Migration %03d (%s) failed: %s", ver, name, e)
                    raise MigrationError(f"Migration {ver} ({name}) failed: {e}") from e

            current_v = self.get_current_version()
            logger.info("✅ Database successfully migrated to schema version %d.", current_v)
            return {
                "applied_count": len(applied_names),
                "current_version": current_v,
                "migrations": applied_names,
            }
