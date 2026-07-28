"""
Performance Verification Benchmark
Runs 3 iterations of all critical API endpoints and measures p50/p95 latency.
Also verifies database indexes exist.
"""
import requests
import time
import statistics
import sqlalchemy

API = 'https://talentopsai-1.onrender.com'
DATABASE_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"

ENDPOINTS = [
    ("Dashboard KPIs", "/analytics/dashboard"),
    ("Data Quality", "/analytics/data-quality"),
    ("Recruiters Page 1", "/recruiters?page=1&limit=50"),
    ("Recruiters Page 2", "/recruiters?page=2&limit=50"),
    ("Companies Search", "/analytics/companies-search?q=&limit=50"),
]

REQUIRED_INDEXES = [
    "ix_recruiters_created_at",
    "ix_recruiters_updated_at",
    "ix_recruiters_last_scan_at",
    "ix_companies_company_name",
    "ix_companies_created_at",
    "ix_companies_updated_at",
]

def benchmark_api(token):
    headers = {'Authorization': f'Bearer {token}'}
    results = {}
    
    for name, endpoint in ENDPOINTS:
        times = []
        for i in range(3):
            start = time.time()
            try:
                r = requests.get(f'{API}{endpoint}', headers=headers, timeout=30)
                elapsed = (time.time() - start) * 1000  # ms
                times.append(elapsed)
                status = r.status_code
            except Exception as e:
                times.append(30000)
                status = f"ERROR: {e}"
        
        p50 = statistics.median(times)
        p95 = max(times)
        results[name] = {"p50": p50, "p95": p95, "times": times}
    
    return results

def verify_indexes():
    engine = sqlalchemy.create_engine(DATABASE_URL)
    with engine.connect() as conn:
        existing = conn.execute(sqlalchemy.text(
            "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
        )).fetchall()
        existing_names = {r[0] for r in existing}
    
    results = {}
    for idx in REQUIRED_INDEXES:
        results[idx] = idx in existing_names
    return results

def main():
    # Login
    print("=" * 60)
    print("PERFORMANCE VERIFICATION BENCHMARK")
    print("=" * 60)
    
    print("\n1. Authenticating...")
    r = requests.post(f'{API}/auth/login', json={
        'email': 'admin@talentops.com',
        'password': 'Password123!',
        'remember_me': False
    }, timeout=30)
    token = r.json().get('token')
    if not token:
        print(f"Login failed: {r.text}")
        return
    print("   Authenticated successfully.")
    
    # Benchmark API
    print("\n2. Benchmarking API endpoints (3 iterations each)...")
    results = benchmark_api(token)
    
    print(f"\n{'Endpoint':<30} {'p50 (ms)':>10} {'p95 (ms)':>10} {'Runs (ms)':>30}")
    print("-" * 80)
    for name, data in results.items():
        runs = ", ".join([f"{t:.0f}" for t in data['times']])
        print(f"{name:<30} {data['p50']:>10.0f} {data['p95']:>10.0f} {runs:>30}")
    
    # Verify indexes
    print("\n3. Verifying database indexes...")
    idx_results = verify_indexes()
    all_ok = True
    for idx_name, exists in idx_results.items():
        status = "OK" if exists else "MISSING!"
        if not exists: all_ok = False
        print(f"   {idx_name}: {status}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_fast = all(data['p95'] < 5000 for data in results.values())
    recruiter_detail_blocked = False  # No longer blocking on DuckDuckGo
    
    if all_fast and all_ok:
        print("ALL CHECKS PASSED")
    else:
        if not all_fast:
            print("WARNING: Some endpoints are slow (p95 > 5s)")
        if not all_ok:
            print("WARNING: Some indexes are missing")

if __name__ == "__main__":
    main()
