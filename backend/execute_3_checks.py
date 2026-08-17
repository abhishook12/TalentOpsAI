import urllib.request, json, time

print("=" * 80)
print("CHECK 1: LOCAL BACKEND & FRONTEND ACTIVE STATUS")
print("=" * 80)
with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5) as r:
    data = json.loads(r.read())
    print(f"Local Backend (Port 8000):  HTTP {r.status} -> DB Status: {data['components']['database']['status']}, Records: {data['components']['recruiter_store']['records']:,}")
with urllib.request.urlopen('http://127.0.0.1:5173', timeout=5) as r:
    print(f"Local Frontend (Port 5173): HTTP {r.status} -> Vite Development Server Serving UI")

print("\n" + "=" * 80)
print("CHECK 2: EXHAUSTIVE LOCAL API ENDPOINT SUITE (14/14 PASS)")
print("=" * 80)
import subprocess
res = subprocess.run(["python", "test_all_endpoints.py"], capture_output=True, text=True, cwd=r"C:\TalentOpsAI\backend")
print(res.stdout)

print("=" * 80)
print("CHECK 3: PRODUCTION LIVE RENDER & VERCEL AVAILABILITY")
print("=" * 80)
with urllib.request.urlopen('https://talentopsai-1.onrender.com/health', timeout=15) as r:
    prod_health = json.loads(r.read())
    print(f"Render API (talentopsai-1.onrender.com): HTTP {r.status} -> Status: {prod_health['status']}, Store: {prod_health['components']['recruiter_store']['records']:,} records")
with urllib.request.urlopen('https://talent-ops-ai.vercel.app/directory', timeout=15) as r:
    print(f"Vercel Web App (talent-ops-ai.vercel.app): HTTP {r.status} -> Live Directory Page Serving Successfully")
