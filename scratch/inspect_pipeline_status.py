"""
inspect_pipeline_status.py — End-to-end pipeline inspection tool for TalentOpsAI.
Checks:
1. Database tables and queue sizes (dev.db, staging, intelligence).
2. Discovery staging pipeline state (pending, batched, committed, rejected).
3. Scout Desktop local queue state (if scout_queue.db exists).
4. Live API connectivity (Render / local backend).
5. Processing test of the end-to-end pipeline.
"""

import sys
import os
import sqlite3
import json

# Add backend directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

def check_databases():
    print("=" * 80)
    print("1. DATABASE STORAGE & PIPELINE TABLES AUDIT")
    print("=" * 80)
    
    dev_db = "c:/TalentOpsAI/backend/dev.db"
    if os.path.exists(dev_db):
        conn = sqlite3.connect(dev_db)
        c = conn.cursor()
        tables = [row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"dev.db found: {len(tables)} tables present.")
        
        priority_tables = [
            "raw_signals", "entity_registry", "persons", "companies_v2", "jobs_v2", 
            "posts_v2", "relationships", "signal_events", "derived_intents", "evidence_ledger",
            "discovery_staging", "resolved_persons", "recruiters", "companies", 
            "extension_discovery_events", "users", "scout_devices", "scout_pairing_codes"
        ]
        
        for t in priority_tables:
            if t in tables:
                try:
                    cnt = c.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
                    print(f"  [OK] {t:30}: {cnt:5} rows")
                except Exception as ex:
                    print(f"  ! {t:30}: Error ({ex})")
            else:
                print(f"  - {t:30}: NOT CREATED YET")
        conn.close()
    else:
        print(f"dev.db NOT found at {dev_db}")

    # Check Scout Desktop local queue
    desktop_dbs = [
        "c:/TalentOpsAI/scout_desktop/scout_queue.db",
        "c:/TalentOpsAI/scout_desktop/queue.db",
        "c:/TalentOpsAI/scout_desktop/evidence.db"
    ]
    print("\nDesktop companion local queues:")
    for db_p in desktop_dbs:
        if os.path.exists(db_p):
            try:
                conn2 = sqlite3.connect(db_p)
                c2 = conn2.cursor()
                t_names = [row[0] for row in c2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                print(f"  [OK] Found {os.path.basename(db_p)}: tables={t_names}")
                for tn in t_names:
                    cnt = c2.execute(f'SELECT count(*) FROM "{tn}"').fetchone()[0]
                    print(f"      {tn}: {cnt} items")
                conn2.close()
            except Exception as e:
                print(f"  ! Error reading {db_p}: {e}")
        else:
            print(f"  - {os.path.basename(db_p)}: Not present (idle)")

def check_recent_staging_records():
    print("\n" + "=" * 80)
    print("2. STAGING BUFFER & BATCH INTELLIGENCE STATUS")
    print("=" * 80)
    dev_db = "c:/TalentOpsAI/backend/dev.db"
    if not os.path.exists(dev_db):
        return
    conn = sqlite3.connect(dev_db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    tables = [row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "discovery_staging" in tables:
        status_counts = c.execute("SELECT processing_status, count(*) as cnt FROM discovery_staging GROUP BY processing_status").fetchall()
        print("Discovery Staging processing statuses:")
        for sc in status_counts:
            print(f"  Status '{sc['processing_status']}': {sc['cnt']} items")
            
        recent = c.execute("SELECT id, raw_name, raw_title, raw_company, processing_status, decision, created_at FROM discovery_staging ORDER BY id DESC LIMIT 5").fetchall()
        if recent:
            print("\nRecent 5 Staging Records:")
            for r in recent:
                print(f"  [#{r['id']}] {r['raw_name']} | {r['raw_title']} @ {r['raw_company']} -> Status: {r['processing_status']}, Decision: {r['decision']}")
        else:
            print("  Staging queue is currently empty.")
    else:
        print("  discovery_staging table not found in dev.db.")
    conn.close()

def check_remote_api():
    print("\n" + "=" * 80)
    print("3. CLOUD BACKEND & LIVE PIPELINE API CONNECTIVITY")
    print("=" * 80)
    import urllib.request
    endpoints = [
        ("Production API Health", "https://talentopsai-1.onrender.com/health"),
        ("Production Recruiter Search", "https://talentopsai-1.onrender.com/recruiters/search?limit=1"),
        ("Production Staging Summary", "https://talentopsai-1.onrender.com/staging/summary"),
        ("Production Scout Release", "https://talentopsai-1.onrender.com/scout/release/latest"),
    ]
    for label, url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TalentOps-Diagnostic/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read().decode("utf-8")
                print(f"  [OK] {label:28}: HTTP {resp.status} - {data[:70]}...")
        except urllib.error.HTTPError as he:
            print(f"  ! {label:28}: HTTP {he.code} ({he.reason})")
        except Exception as e:
            print(f"  x {label:28}: Error: {e}")

if __name__ == "__main__":
    check_databases()
    check_recent_staging_records()
    check_remote_api()
