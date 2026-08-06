import requests

print("Testing GET /recruiters...")
res = requests.get("http://localhost:8000/api/v1/recruiters?limit=5")
if res.status_code == 200:
    data = res.json()
    print(f"Success! Found {data['total_count']} total recruiters.")
    print(f"First recruiter: {data['results'][0]['recruiter_name']} ({data['results'][0]['email']})")
else:
    print(f"Failed! Status code: {res.status_code}")
    print(res.text)

print("\nTesting GET /recruiters/search...")
res = requests.get("http://localhost:8000/api/v1/recruiters/search?q=a&limit=5")
if res.status_code == 200:
    data = res.json()
    print(f"Success! Found {len(data)} results for search.")
    if data:
        print(f"Top result: {data[0]['recruiter_name']} ({data[0]['email']}) - Score: {data[0]['relevance_score']}")
else:
    print(f"Failed! Status code: {res.status_code}")
    print(res.text)

print("\nTesting GET /companies...")
res = requests.get("http://localhost:8000/api/v1/companies?limit=5")
if res.status_code == 200:
    data = res.json()
    print(f"Success! Found {len(data)} companies.")
    if data:
        print(f"First company: {data[0]['company_name']} - Total Recruiters: {data[0]['total_recruiters']}")
else:
    print(f"Failed! Status code: {res.status_code}")
    print(res.text)
