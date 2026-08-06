import sys
sys.path.append('C:/TalentOpsAI/backend')

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("--- Verification 3: FastAPI Routes Testing ---")

print("1. Testing GET /recruiters")
response = client.get("/recruiters?limit=5")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Total count returned in header: {response.headers.get('x-total-count')}")
    print(f"Number of results: {len(data['results'])}")
else:
    print(response.json())

print("\n2. Testing GET /recruiters/search?q=john")
response = client.get("/recruiters/search?q=john&limit=3")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Number of search results: {len(data)}")
    for r in data:
        print(f"  - {r.get('recruiter_name')} | Score: {r.get('relevance_score')}")
else:
    print(response.json())

print("\n3. Testing GET /companies")
response = client.get("/companies?limit=5")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Number of companies: {len(data)}")
    for c in data:
        print(f"  - {c.get('company_name')} | Total Recruiters: {c.get('total_recruiters')}")
else:
    print(response.json())
