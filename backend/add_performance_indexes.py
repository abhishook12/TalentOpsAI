#!/usr/bin/env python
"""Database Performance Indexing Engine - TalentOpsAI"""
import sys, os, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

indexes = [
    ("idx_companies_state", "CREATE INDEX IF NOT EXISTS idx_companies_state ON companies(state) WHERE state IS NOT NULL;"),
    ("idx_companies_active", "CREATE INDEX IF NOT EXISTS idx_companies_active ON companies(is_active);"),
    ("idx_recruiters_company", "CREATE INDEX IF NOT EXISTS idx_recruiters_company ON recruiters(company_id);"),
    ("idx_recruiters_state", "CREATE INDEX IF NOT EXISTS idx_recruiters_state ON recruiters(state) WHERE state IS NOT NULL;"),
    ("idx_recruiters_active", "CREATE INDEX IF NOT EXISTS idx_recruiters_active ON recruiters(is_active);"),
    ("idx_recruiters_review", "CREATE INDEX IF NOT EXISTS idx_recruiters_review ON recruiters(needs_review) WHERE needs_review = true;"),
    ("idx_recruiters_email", "CREATE INDEX IF NOT EXISTS idx_recruiters_email ON recruiters(email) WHERE email IS NOT NULL;")
]

def create_indexes():
    start_time = time.time()
    print("STARTING SUPABASE PERFORMANCE INDEX HARDENING...")
    db = SessionLocal()
    try:
        for name, sql in indexes:
            print(f"   -> Hardening index: {name}...")
            db.execute(text(sql))
            db.commit()
        elapsed = round(time.time() - start_time, 2)
        print(f"\nAll 7 Database Performance Indexes Hardened in {elapsed}s!")
    except Exception as e:
        db.rollback()
        print(f"Index hardening error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_indexes()
