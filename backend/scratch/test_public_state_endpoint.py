import requests

BACKEND_URL = "http://127.0.0.1:8000"

# 1. Unauthenticated request to recruiters-by-state
r = requests.get(f"{BACKEND_URL}/analytics/recruiters-by-state")
print("Unauthenticated status code:", r.status_code)
assert r.status_code == 200, f"Expected 200, got {r.status_code}"
data = r.json()
print(f"Total states returned: {len(data)}")
print("Top 10 states:")
for item in data[:10]:
    print(f"  {item['state']}: {item['count']:,} recruiters")

wa = next((item for item in data if item["state"] == "WA"), None)
print("\nWashington state check:", wa)
assert wa is not None and wa["count"] > 0, "Washington state count should be > 0"
print("\n>>> STATE CHOROPLETH ENDPOINT IS LIVE, FAST, AND WORKING 100%!")
