import requests

def prove_golden_baseline():
    print("================ CHECK 1: LIVE DASHBOARD API (ADMIN ROLE) ================")
    try:
        r = requests.post("http://127.0.0.1:8000/auth/login", json={"email": "admin@talentops.com", "password": "1012"})
        token = r.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        dq = requests.get("http://127.0.0.1:8000/analytics/data-quality", headers=headers)
        print("Dashboard 'Total Recruiters' API returns:", dq.json().get("total_recruiters"))
    except Exception as e:
        print("Error:", e)

    print("\n================ CHECK 2: LIVE RECRUITERS API (ADMIN ROLE) ================")
    try:
        rec = requests.get("http://127.0.0.1:8000/recruiters/?page=1&limit=5", headers=headers)
        print("Recruiters page 'matches found' API returns:", rec.headers.get("X-Total-Count"))
    except Exception as e:
        print("Error:", e)

    print("\n================ CHECK 3: PRODUCTION DATABASE INTEGRITY ================")
    try:
        import psycopg
        conn = psycopg.connect("postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres")
        count = conn.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0]
        print("True production database row count:", count)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    prove_golden_baseline()
