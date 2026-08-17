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
            device="3-Pass Verifier",
            ip_address="127.0.0.1"
        )
        db.add(db_sess)
        db.commit()
        db.refresh(db_sess)
        return create_access_token({"sub": str(user.id), "session_id": db_sess.id})
    finally:
        db.close()

def run_check_1_dataset_zero_fragmentation():
    print("="*75)
    print("=== [CHECK 1 / 3]: ZERO DOMAIN FRAGMENTATION IN 2.3M DATASET ===")
    print("="*75)
    
    con = duckdb.connect()
    PARQUET_FILE = 'backend/data/recruiters_full.parquet'
    
    FREE_DOMAINS = (
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
        'icloud.com', 'live.com', 'msn.com', 'comcast.net', 'att.net',
        'sbcglobal.net', 'verizon.net', 'me.com', 'mail.com', 'protonmail.com',
        'ymail.com', 'cox.net', 'charter.net', 'earthlink.net', 'talentops.ai'
    )
    free_sql = ", ".join(f"'{d}'" for d in FREE_DOMAINS)
    
    total_records = con.execute(f"SELECT COUNT(*) FROM '{PARQUET_FILE}'").fetchone()[0]
    print(f"  [PASS] Total Recruiters Verified: {total_records:,}", flush=True)
    assert total_records >= 2300000
    
    frag_query = con.execute(f"""
        SELECT 
            LOWER(SPLIT_PART(email, '@', 2)) as domain, 
            COUNT(DISTINCT company_id) as distinct_cids,
            COUNT(*) as total_rows
        FROM '{PARQUET_FILE}'
        WHERE email IS NOT NULL 
          AND email LIKE '%@%'
          AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_sql})
        GROUP BY domain
        HAVING COUNT(DISTINCT company_id) > 1
    """).fetchall()
    
    print(f"  [PASS] Remaining Fragmented Corporate Domains: {len(frag_query)} (Expected: 0)", flush=True)
    assert len(frag_query) == 0, f"Found {len(frag_query)} fragmented domains"

    # Verify key enterprise domains
    enterprise_domains = [
        ('rht.com', '163785'),
        ('roberthalf.com', '161735'),
        ('insightglobal.com', '168275'),
        ('teksystems.com', '153421'),
        ('kforce.com', '174887'),
    ]
    for dom, expected_cid in enterprise_domains:
        rows = con.execute(f"SELECT DISTINCT company_id, COUNT(*) FROM '{PARQUET_FILE}' WHERE email LIKE '%@{dom}' GROUP BY 1").fetchall()
        print(f"  [PASS] Domain '{dom}' -> Exactly 1 Company ID ({rows[0][0]}) with {rows[0][1]:,} Recruiters", flush=True)
        assert len(rows) == 1, f"Domain {dom} has multiple company IDs: {rows}"

    print("\n>>> CHECK 1 PASSED WITH ZERO DATASET FRAGMENTATION <<<\n")

def run_check_2_api_search_deduplication():
    print("="*75)
    print("=== [CHECK 2 / 3]: API SEARCH & DIRECTORY DEDUPLICATION ===")
    print("="*75)
    
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    test_queries = ['r', 'robert', 'tek', 'insight', 'kforce', 'aerotek']
    for q in test_queries:
        r = requests.get(f"http://localhost:8000/analytics/companies-search?q={q}&limit=100&min_recruiters=1", headers=headers)
        assert r.status_code == 200, f"Search for '{q}' failed with {r.status_code}"
        results = r.json()
        
        seen_domains = set()
        duplicate_domains = []
        for row in results:
            dom = (row.get('logo_domain') or row.get('email_pattern') or '').lower().strip()
            if dom and dom not in ('n/a', 'none', ''):
                if dom in seen_domains:
                    duplicate_domains.append(dom)
                seen_domains.add(dom)
                
        print(f"  [PASS] Query '{q:10}': {len(results):3} Companies Returned | {len(seen_domains):3} Domains | Duplicate Cards: {len(duplicate_domains)}", flush=True)
        assert len(duplicate_domains) == 0, f"Duplicate domain cards found in search '{q}': {duplicate_domains}"

    print("\n>>> CHECK 2 PASSED WITH ZERO DUPLICATE COMPANY CARDS IN API <<<\n")

def run_check_3_drilldown_and_recruiter_listings():
    print("="*75)
    print("=== [CHECK 3 / 3]: STATE DRILLDOWN & RECRUITER LISTING INTEGRITY ===")
    print("="*75)
    
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Check states for Robert Half Technology (163785)
    r_states = requests.get("http://localhost:8000/analytics/company-states?company_key=163785", headers=headers)
    assert r_states.status_code == 200
    states_data = r_states.json()
    print(f"  [PASS] Company 163785 States API: {len(states_data)} States Mapped", flush=True)
    assert len(states_data) > 0
    
    # Check recruiter listings for Company 163785
    r_recs = requests.get("http://localhost:8000/recruiters/?company_id=163785&limit=10&page=1", headers=headers)
    assert r_recs.status_code == 200, f"Recruiter listing failed with status {r_recs.status_code}"
    recs_data = r_recs.json()
    rec_count = recs_data.get('total') or recs_data.get('total_count') or len(recs_data.get('results', []))
    print(f"  [PASS] Recruiters API for Company 163785: {rec_count:,} Total Recruiters Listed", flush=True)
    assert rec_count >= 3000
    
    # Verify sample recruiters all belong to rht.com
    recs_list = recs_data.get('results', [])
    for rec in recs_list[:5]:
        email = rec.get('email') or ''
        print(f"    -> Recruiter: {rec.get('recruiter_name'):25} | Email: {email:30} | State: {rec.get('state')}", flush=True)
        assert 'rht.com' in email.lower()

    print("\n>>> CHECK 3 PASSED WITH PERFECT RECRUITER DRILLDOWN INTEGRITY <<<\n")

if __name__ == "__main__":
    t0 = time.time()
    run_check_1_dataset_zero_fragmentation()
    run_check_2_api_search_deduplication()
    run_check_3_drilldown_and_recruiter_listings()
    total_time = time.time() - t0
    print("="*75)
    print(f"=== ALL 3 CHECKS FULLY VERIFIED IN {total_time:.2f}s ===")
    print("="*75)
