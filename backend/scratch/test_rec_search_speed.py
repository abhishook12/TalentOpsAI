import requests
import time

t0 = time.time()
r = requests.get("http://127.0.0.1:8000/recruiters/?page=1&limit=25&search=BridgeCross")
print("Status:", r.status_code, "Duration:", round(time.time() - t0, 3), "s")
if r.status_code == 200:
    d = r.json()
    print("Total count:", d.get("total_count"))
    print("Results length:", len(d.get("results", [])))
    if d.get("results"):
        print("First recruiter:", d["results"][0]["recruiter_name"], "|", d["results"][0]["email"], "|", d["results"][0].get("company_name"))
