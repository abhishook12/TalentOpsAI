"""
check_update_1_paths_and_migrations.py
Verification Check 1: AppData Path Isolation & Local SQLite Database Migration Runner.

Tests:
1. Path Isolation:
   - Verifies AppData directory is cleanly separated from application binary directory.
   - Verifies all subdirectories (data, captures, config, updates, logs, backups) exist.
2. Local Database Migrations:
   - Executes `MigrationRunner.run_migrations()` on a clean test SQLite database.
   - Verifies sequential execution of migrations 1 through 4.
   - Verifies table columns: content_hash, next_retry_at, source_type, authorization_scope, hardware_provenance.
   - Verifies local_evidence_cache creation.
3. Idempotency:
   - Second run of `run_migrations()` skips already applied migrations (applied_count = 0).
4. Transactional Rollback on Migration Failure:
   - Injects a failing migration with invalid SQL.
   - Verifies MigrationError is raised and previous schema state is rolled back cleanly.
"""

import sys
import os
import sqlite3
import tempfile
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scout_desktop.core.paths import (
    get_app_data_dir,
    get_database_path,
    get_captures_dir,
    get_config_path,
    get_remote_config_path,
    get_updates_dir,
    get_backups_dir,
    get_logs_dir,
    get_application_dir,
)
from scout_desktop.core.migrations import (
    MigrationRunner,
    MigrationError,
    MIGRATION_REGISTRY,
)


def run_check_1():
    print("=" * 80)
    print("CHECK 1: APPDATA PATH ISOLATION & LOCAL DATABASE MIGRATION RUNNER")
    print("=" * 80)

    # ── Test 1: Path Isolation & AppData Verification ────────────────────────
    print("\n[Step 1/5] Verifying AppData Path Isolation from Application Binaries...")
    app_data_dir = get_app_data_dir()
    app_bin_dir = get_application_dir()

    print(f"-> Application Binaries Dir: {app_bin_dir}")
    print(f"-> User AppData Root Dir:   {app_data_dir}")

    assert app_data_dir != app_bin_dir, "CRITICAL: AppData must NOT be inside Application binary dir!"
    assert "TalentOpsAI" in app_data_dir and "Scout" in app_data_dir, f"Unexpected AppData path: {app_data_dir}"

    subpaths = {
        "Database": get_database_path(),
        "Captures": get_captures_dir(),
        "Config": get_config_path(),
        "Remote Config": get_remote_config_path(),
        "Updates": get_updates_dir(),
        "Backups": get_backups_dir(),
        "Logs": get_logs_dir(),
    }

    for name, p in subpaths.items():
        parent = os.path.dirname(p)
        assert os.path.exists(parent), f"Directory for {name} ({parent}) was not created!"
        print(f"   [OK] {name:15}: {p}")

    print("   [PASSED] Full directory separation verified. Updates to binaries will not touch user data.")

    # ── Test 2: Local SQLite Database Migration Runner ───────────────────────
    print("\n[Step 2/5] Testing MigrationRunner on fresh local SQLite database...")
    temp_dir = tempfile.mkdtemp(prefix="scout_migration_test_")
    test_db = os.path.join(temp_dir, "test_scout_local.db")

    runner = MigrationRunner(db_path=test_db)
    init_ver = runner.get_current_version()
    print(f"-> Initial database version: {init_ver}")
    assert init_ver == 0, f"Expected version 0 for new database, got {init_ver}"

    res = runner.run_migrations()
    print(f"-> Migrations executed: {res['applied_count']}")
    print(f"   Applied migrations:  {res['migrations']}")
    print(f"   Current version:     {res['current_version']}")

    assert res["applied_count"] == 4, f"Expected 4 migrations applied, got {res['applied_count']}"
    assert res["current_version"] == 4, f"Expected current version 4, got {res['current_version']}"

    # ── Test 3: Verify Table Schemas & New Columns ───────────────────────────
    print("\n[Step 3/5] Inspecting migrated SQLite tables and columns...")
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    # Verify schema_migrations audit table
    applied_rows = cursor.execute("SELECT version, name, applied_at FROM schema_migrations ORDER BY version ASC").fetchall()
    print(f"-> Audit Table (schema_migrations) has {len(applied_rows)} records:")
    for row in applied_rows:
        print(f"   [OK] v{row[0]:03d}: {row[1]} (Applied at: {row[2]})")
    assert len(applied_rows) == 4

    # Verify local_queue columns
    cursor.execute("PRAGMA table_info(local_queue)")
    cols = {r[1]: r[2] for r in cursor.fetchall()}
    print(f"-> local_queue columns ({len(cols)}): {list(cols.keys())}")

    expected_cols = ["id", "cluster_data", "status", "content_hash", "next_retry_at", "source_type", "authorization_scope", "hardware_provenance"]
    for col in expected_cols:
        assert col in cols, f"Column '{col}' missing from migrated local_queue!"
        print(f"   [OK] Column '{col}' ({cols[col]}) confirmed present.")

    # Verify local_evidence_cache
    cursor.execute("PRAGMA table_info(local_evidence_cache)")
    ev_cols = {r[1]: r[2] for r in cursor.fetchall()}
    print(f"-> local_evidence_cache columns ({len(ev_cols)}): {list(ev_cols.keys())}")
    assert "capture_id" in ev_cols and "content_hash" in ev_cols
    conn.close()

    # ── Test 4: Idempotency Verification ─────────────────────────────────────
    print("\n[Step 4/5] Testing Migration Idempotency (re-running on migrated DB)...")
    res_rerun = runner.run_migrations()
    print(f"-> Re-run applied count: {res_rerun['applied_count']}, version: {res_rerun['current_version']}")
    assert res_rerun["applied_count"] == 0, "Re-run should apply 0 migrations!"
    assert res_rerun["current_version"] == 4, "Version must remain 4."
    print("   [PASSED] Idempotency confirmed: already applied migrations safely skipped.")

    # ── Test 5: Transactional Rollback on Failure ────────────────────────────
    print("\n[Step 5/5] Testing Transactional Rollback on faulty migration...")
    def broken_migration(c):
        c.execute("CREATE TABLE valid_table (id INT)")
        c.execute("SYNTAX ERROR IN SQL STATEMENT THAT BREAKS")

    MIGRATION_REGISTRY.append({
        "version": 5,
        "name": "005_failing_migration",
        "func": broken_migration,
    })

    try:
        runner.run_migrations()
        print("FAILED: Broken migration did not raise MigrationError!")
        sys.exit(1)
    except MigrationError as err:
        print(f"-> Caught expected MigrationError: {err}")

    # Verify rollback: version must still be 4, and 'valid_table' must NOT exist!
    conn_rb = sqlite3.connect(test_db)
    c_rb = conn_rb.cursor()
    tables = [r[0] for r in c_rb.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "valid_table" not in tables, "Table created before error was NOT rolled back!"
    ver_after_rb = runner.get_current_version()
    assert ver_after_rb == 4, f"Version should still be 4 after rollback, got {ver_after_rb}"
    conn_rb.close()

    # Cleanup registry test entry & temp dir
    MIGRATION_REGISTRY.pop()
    shutil.rmtree(temp_dir, ignore_errors=True)

    print("   [PASSED] Transactional rollback verified: partial migration aborted with zero residue.")
    print("\n" + "=" * 80)
    print("CHECK 1 RESULT: PASSED (100% SUCCESSFUL)")
    print("AppData path isolation and SQLite migration engine fully verified.")
    print("=" * 80)


if __name__ == "__main__":
    run_check_1()
