import duckdb
import requests
import json
import sys
import os
import time

sys.path.append('backend')
from app.database import SessionLocal
from app.models.auth_models import User, TrustedDevice, Session as DBSession
from app.services.auth_service import create_access_token

def get_auth_token():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == 'admin@talentops.ai').first() or db.query(User).first()
        t_dev = db.query(TrustedDevice).filter(TrustedDevice.user_id == user.id, TrustedDevice.status == 'Trusted').first()
        import hashlib, time
        token_hash = hashlib.sha256(f"test_{time.time()}".encode('utf-8')).hexdigest()
        from datetime import datetime, timedelta
        db_sess = DBSession(
            user_id=user.id,
            token_hash=token_hash,
            trusted_device_id=t_dev.id,
            is_active=True,
            expires_at=datetime.now() + timedelta(days=30),
            device="Sanitization Verifier",
            ip_address="127.0.0.1"
        )
        db.add(db_sess)
        db.commit()
        db.refresh(db_sess)
        return create_access_token({"sub": str(user.id), "session_id": db_sess.id})
    finally:
        db.close()

def run_check_1_dataset_purity():
    print("="*80)
    print("=== [CHECK 1 / 3]: COMPLETE DATASET PURITY & DEDUPLICATION AUDIT ===")
    print("="*80)
    
    con = duckdb.connect()
    PARQUET = 'backend/data/recruiters_full.parquet'
    
    total = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}'").fetchone()[0]
    print(f"  [PASS] Total Master Clean Profiles: {total:,}", flush=True)
    assert total > 400000
    
    # 1. Names containing '@'
    name_emails = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE recruiter_name LIKE '%@%'").fetchone()[0]
    print(f"  [PASS] Names containing email addresses: {name_emails} (Expected: 0)", flush=True)
    assert name_emails == 0
    
    # 2. Names that are numeric phone digits
    name_digits = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE regexp_matches(recruiter_name, '^[0-9+() -]+$') AND LENGTH(recruiter_name) >= 6").fetchone()[0]
    print(f"  [PASS] Names that are numeric/phone digits: {name_digits} (Expected: 0)", flush=True)
    assert name_digits == 0

    # 3. Duplicate emails
    dup_emails = con.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT LOWER(TRIM(email)) 
            FROM '{PARQUET}' 
            WHERE email IS NOT NULL AND email LIKE '%@%'
            GROUP BY LOWER(TRIM(email)) 
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    print(f"  [PASS] Duplicate Email Profiles Remaining: {dup_emails} (Expected: 0)", flush=True)
    assert dup_emails == 0
    
    # 4. Negative scraper IDs
    neg_ids = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE recruiter_id < 0").fetchone()[0]
    print(f"  [PASS] Negative Scraper IDs Remaining: {neg_ids} (Expected: 0)", flush=True)
    assert neg_ids == 0

    # Inspect SystemOne in Parquet
    so_rows = con.execute(f"""
        SELECT recruiter_id, recruiter_name, email, phone, title 
        FROM '{PARQUET}' 
        WHERE email LIKE '%@systemone.com' 
        LIMIT 5
    """).fetchall()
    print("\n  Sample Cleaned SystemOne Profiles:")
    for row in so_rows:
        print(f"    -> ID: {row[0]} | Name: {row[1]:25} | Email: {row[2]:30} | Phone: {row[3] or 'N/A'}")
        assert '@' not in row[1]
        
    print("\n>>> CHECK 1 PASSED: 100% DATASET PURITY VERIFIED <<<\n")

def run_check_2_live_search_deduplication():
    print("="*80)
    print("=== [CHECK 2 / 3]: LIVE SEARCH API & NAME INTEGRITY VERIFICATION ===")
    print("="*80)
    
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    queries = ['systemone', 'michaela', 'aaron dehart', 'rachel frumkin', 'aerotek', 'insight global']
    for q in queries:
        r = requests.get(f"http://localhost:8000/recruiters/search?q={q}&limit=50", headers=headers)
        assert r.status_code == 200, f"Search '{q}' failed: {r.status_code}"
        data = r.json()
        results = data if isinstance(data, list) else data.get('results', [])
        
        # Check duplicate emails in search results
        seen_emails = set()
        dup_in_search = []
        for rec in results:
            em = (rec.get('email') or '').lower().strip()
            name = rec.get('recruiter_name')
            assert '@' not in name, f"Recruiter name '{name}' still contains '@'!"
            if em and em not in ('none', 'n/a', ''):
                if em in seen_emails:
                    dup_in_search.append(em)
                seen_emails.add(em)
                
        print(f"  [PASS] Query '{q:15}': {len(results):2} Results | Duplicate Profiles in Search: {len(dup_in_search)}", flush=True)
        assert len(dup_in_search) == 0, f"Found duplicate search rows: {dup_in_search}"
        
        if q == 'systemone' and results:
            print("     Sample SystemOne Search Results:")
            for rec in results[:4]:
                print(f"       -> Name: {str(rec.get('recruiter_name')):22} | Email: {str(rec.get('email') or 'N/A'):30} | Match: {rec.get('match_reason')}")

    print("\n>>> CHECK 2 PASSED: 0 DUPLICATES & 100% CLEAN NAMES IN SEARCH <<<\n")

def run_check_3_recruiter_drilldown_and_company_linking():
    print("="*80)
    print("=== [CHECK 3 / 3]: DRILLDOWN & COMPANY LINKING INTEGRITY ===")
    print("="*80)
    
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Company States API
    r_states = requests.get("http://localhost:8000/analytics/company-states?company_key=161888", headers=headers)
    assert r_states.status_code == 200
    states = r_states.json()
    print(f"  [PASS] SystemOne (161888) States API: {len(states)} States Mapped", flush=True)
    assert len(states) > 0

    # 2. Company Recruiters Listing
    r_recs = requests.get("http://localhost:8000/recruiters/?company_id=161888&limit=10&page=1", headers=headers)
    assert r_recs.status_code == 200
    recs = r_recs.json().get('results', [])
    print(f"  [PASS] SystemOne Directory Recruiters: {len(recs)} Recruiters Fetched on Page 1", flush=True)
    assert len(recs) > 0
    for rec in recs[:5]:
        name = rec.get('recruiter_name')
        email = rec.get('email')
        print(f"    -> Recruiter: {str(name):25} | Email: {str(email or 'N/A'):30} | Phone: {rec.get('phone') or 'N/A'}")
        assert '@' not in str(name)

    print("\n>>> CHECK 3 PASSED: PERFECT RECRUITER DRILLDOWN & COMPANY LINKING <<<\n")

if __name__ == "__main__":
    t0 = time.time()
    run_check_1_dataset_purity()
    run_check_2_live_search_deduplication()
    run_check_3_recruiter_drilldown_and_company_linking()
    total_time = time.time() - t0
    print("="*80)
    print(f"=== ALL 3 CHECKS FULLY VERIFIED IN {total_time:.2f}s ===")
    print("="*80)
