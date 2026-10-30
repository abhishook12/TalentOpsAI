import urllib.request, json
import sys, os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.routes.auth import create_access_token
token = create_access_token({'sub': '1'})
headers = {"Authorization": f"Bearer {token}"}

def test_api():
    print("=" * 60)
    print("CHECK 1: FASTAPI + DUCKDB RECRUITER API VERIFICATION")
    print("=" * 60)

    # 1. Test basic recruiters API
    url = "http://127.0.0.1:8000/recruiters/?limit=5&sort_by=created_at&sort_desc=true"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print("\n[1.1] Default Recruiter API (All Sources, All Time)")
            print(f"Status: {resp.status} OK | Total Recruiters: {data.get('total_count'):,}")
            for r in data.get('results', [])[:3]:
                print(f"  - {r.get('recruiter_name')} | Co: {r.get('company_name')} | Source: {r.get('data_source')} | Created: {r.get('created_at')}")
    except Exception as e:
        print("[1.1] Error:", e)

    # 2. Test date_filter=today
    url_date = "http://127.0.0.1:8000/recruiters/?limit=5&date_filter=today&sort_by=created_at&sort_desc=true"
    try:
        req = urllib.request.Request(url_date, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print("\n[1.2] Date Filter: date_filter=today (< 24h)")
            print(f"Status: {resp.status} OK | Total Candidates (< 24h): {data.get('total_count'):,}")
            for r in data.get('results', [])[:3]:
                print(f"  - {r.get('recruiter_name')} | Co: {r.get('company_name')} | Source: {r.get('data_source')} | Created: {r.get('created_at')}")
    except Exception as e:
        print("[1.2] Error:", e)

    # 3. Test data_source=teams
    url_teams = "http://127.0.0.1:8000/recruiters/?limit=5&data_source=teams&sort_by=created_at&sort_desc=true"
    try:
        req = urllib.request.Request(url_teams, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print("\n[1.3] Source Filter: data_source=teams")
            print(f"Status: {resp.status} OK | Total Teams Candidates: {data.get('total_count'):,}")
            for r in data.get('results', [])[:3]:
                print(f"  - {r.get('recruiter_name')} | Co: {r.get('company_name')} | Email: {r.get('email')} | Phone: {r.get('phone')}")
    except Exception as e:
        print("[1.3] Error:", e)

    # 4. Test combined: date_filter=today AND data_source=teams
    url_combined = "http://127.0.0.1:8000/recruiters/?limit=5&data_source=teams&date_filter=today&sort_by=created_at&sort_desc=true"
    try:
        req = urllib.request.Request(url_combined, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print("\n[1.4] Combined Filter: date_filter=today & data_source=teams")
            print(f"Status: {resp.status} OK | Total New Teams Candidates Today: {data.get('total_count'):,}")
            for r in data.get('results', [])[:5]:
                print(f"  - {r.get('recruiter_name')} | Co: {r.get('company_name')} | Email: {r.get('email')} | Phone: {r.get('phone')} | Created: {r.get('created_at')}")
    except Exception as e:
        print("[1.4] Error:", e)

if __name__ == "__main__":
    test_api()
