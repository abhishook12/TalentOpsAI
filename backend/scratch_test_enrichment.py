import requests
import json
import time

base_url = "http://127.0.0.1:8000/api/import"

# 1. We will assume the backend is running and the DB is connected.
# Let's seed a recruiter via API first.
# Wait, we can't easily seed via API unless we use the backend directly.
# Let's just upload a file twice!

csv_data_1 = """Name,Email,Company,Location
John Smith,john@abc.com,ABC,New York
Jane Doe,jane@abc.com,ABC,Boston
"""

print("--- UPLOAD 1: INITIAL DATA ---")
files1 = {'file': ('test1.csv', csv_data_1.encode('utf-8'), 'text/csv')}
resp1 = requests.post(f"{base_url}/parse", files=files1, headers={"Authorization": "Bearer admin"})
job1 = resp1.json()["job_id"]
mapping1 = {"name": "Name", "email": "Email", "company": "Company", "location": "Location"}
requests.post(f"{base_url}/validate/{job1}", json=mapping1)
print(f"Commit Job 1: {requests.post(f'{base_url}/commit/{job1}').json()}")


print("\n--- UPLOAD 2: ENRICHMENT & POSSIBLE DUPLICATES ---")
csv_data_2 = """Name,Email,Company,Location,Phone,Title,Personal Email
John Smith,john@abc.com,ABC,,9999999999,Tech Recruiter,john.smith.personal@gmail.com
Jane Doe,jane.alternate@abc.com,ABC,Boston,,,
"""

files2 = {'file': ('test2.csv', csv_data_2.encode('utf-8'), 'text/csv')}
resp2 = requests.post(f"{base_url}/parse", files=files2, headers={"Authorization": "Bearer admin"})
job2 = resp2.json()["job_id"]
mapping2 = {"name": "Name", "email": "Email", "company": "Company", "location": "Location", "phone": "Phone", "title": "Title"}
resp_val2 = requests.post(f"{base_url}/validate/{job2}", json=mapping2)

print("\nValidation Results for Upload 2:")
# fetch preview
preview = requests.get(f"{base_url}/preview/{job2}?page=1&limit=50").json()
for r in preview["rows"]:
    print(f"{r['name']} ({r['email']}) -> Status: {r['status']} | Issues: {r['issues']}")

print(f"\nCommit Job 2: {requests.post(f'{base_url}/commit/{job2}').json()}")

print("\nDone testing! You can verify the DB now.")
