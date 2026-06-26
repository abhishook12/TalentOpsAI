#!/usr/bin/env python
"""Database Dead Tuple & Column Bloat Audit Engine - TalentOpsAI"""
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

def check_bloat():
    db = SessionLocal()
    try:
        print("\n" + "=" * 65)
        print("         POSTGRESQL STORAGE BLOAT & RECLAMATION AUDIT")
        print("=" * 65)

        # 1. Check table sizes of all relations in public schema
        tables = db.execute(text("""
            SELECT 
                relname as table_name,
                pg_size_pretty(pg_total_relation_size(relid)) as total_size,
                pg_total_relation_size(relid) as size_bytes
            FROM pg_catalog.pg_statio_user_tables
            ORDER BY pg_total_relation_size(relid) DESC;
        """)).fetchall()

        print("TABLE STORAGE BREAKDOWN:")
        for t in tables:
            print(f"   -> {t.table_name:<25}: {t.total_size}")

        # 2. Check Dead Tuples (MVCC Update Bloat)
        dead_tups = db.execute(text("""
            SELECT relname, n_live_tup, n_dead_tup
            FROM pg_stat_user_tables
            WHERE n_dead_tup > 0
            ORDER BY n_dead_tup DESC;
        """)).fetchall()

        print("\nMVCC DEAD TUPLES (Reclaimable via VACUUM ANALYZE):")
        total_dead = 0
        for d in dead_tups:
            print(f"   -> {d.relname:<25}: {d.n_dead_tup:,} dead rows (vs {d.n_live_tup:,} live)")
            total_dead += d.n_dead_tup
        if total_dead == 0:
            print("   -> Zero dead tuples detected.")

        # 3. Check raw_data JSON string bloat
        raw_rec_bytes = db.execute(text("SELECT SUM(PG_COLUMN_SIZE(raw_data)) FROM recruiters WHERE raw_data IS NOT NULL;")).scalar() or 0
        raw_comp_bytes = db.execute(text("SELECT SUM(PG_COLUMN_SIZE(raw_data)) FROM companies WHERE raw_data IS NOT NULL;")).scalar() or 0
        raw_total_mb = round((raw_rec_bytes + raw_comp_bytes) / (1024 * 1024), 2)

        print("\nHISTORICAL CSV IMPORT ARTIFACTS (`raw_data` text column):")
        print(f"   -> Recruiters raw_data   : {round(raw_rec_bytes / (1024*1024), 2)} MB")
        print(f"   -> Companies raw_data    : {round(raw_comp_bytes / (1024*1024), 2)} MB")
        print(f"   -> Total raw_data Bloat  : {raw_total_mb} MB")

        print("=" * 65 + "\n")

    except Exception as e:
        print(f"Bloat audit error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_bloat()
