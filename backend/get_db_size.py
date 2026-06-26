#!/usr/bin/env python
"""Database Storage & Record Tally Audit Engine - TalentOpsAI"""
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

def check_size():
    db = SessionLocal()
    try:
        # Total database storage size
        db_size = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()));")).scalar()
        
        # Table specific storage sizes (data + indexes)
        rec_size = db.execute(text("SELECT pg_size_pretty(pg_total_relation_size('recruiters'));")).scalar()
        comp_size = db.execute(text("SELECT pg_size_pretty(pg_total_relation_size('companies'));")).scalar()
        
        # Exact record counts
        rec_total = db.execute(text("SELECT count(*) FROM recruiters;")).scalar()
        rec_active = db.execute(text("SELECT count(*) FROM recruiters WHERE is_active = true;")).scalar()
        
        comp_total = db.execute(text("SELECT count(*) FROM companies;")).scalar()
        comp_active = db.execute(text("SELECT count(*) FROM companies WHERE is_active = true;")).scalar()

        print("\n" + "=" * 55)
        print("          LIVE SUPABASE DATABASE STORAGE AUDIT")
        print("=" * 55)
        print(f"Total Cloud Database Size : {db_size}")
        print("-" * 55)
        print(f"Recruiters Table Storage  : {rec_size}")
        print(f"   -> Total Records       : {rec_total:,}")
        print(f"   -> Active Profiles     : {rec_active:,} ({round(rec_active/rec_total*100, 1)}%)")
        print("-" * 55)
        print(f"Companies Table Storage   : {comp_size}")
        print(f"   -> Total Entities      : {comp_total:,}")
        print(f"   -> Active HQ Groups    : {comp_active:,} ({round(comp_active/comp_total*100, 1)}%)")
        print("=" * 55 + "\n")
        
    except Exception as e:
        print(f"Audit error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_size()
