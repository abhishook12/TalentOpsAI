import requests
import json

base_url = "http://127.0.0.1:8000/api/import"

# 1. Parse File
csv_data = """Name,Email,Phone,Company,Location,Title,Favorite Color,Extra Notes,Personal Email
Test User,testuser@example.com,5551234567,Test Company,Austin,Recruiter,Blue,Very nice person,personal@example.com
Messy User,messyuser@example.com,,Messy Company,,Senior Recruiter,Red,,
Duplicate Phone,dup@example.com,555-123-4567,Other Company,Dallas,Recruiter,Green,Phone should trigger dedupe,
Duplicate Name,new@example.com,9999999999,Test Company,Houston,Recruiter,Yellow,Name+Company dedupe,
"""

files = {'file': ('test.csv', csv_data.encode('utf-8'), 'text/csv')}
print("Uploading file...")
resp = requests.post(f"{base_url}/parse", files=files, headers={"Authorization": "Bearer admin_dummy"})
print(resp.json())
job_id = resp.json()["job_id"]

# 2. Validate
print(f"Validating job {job_id}...")
# We let the backend auto-detect columns, or we provide them explicitly
mapping = {
    "name": "Name",
    "email": "Email",
    "phone": "Phone",
    "company": "Company",
    "location": "Location",
    "title": "Title"
}
resp = requests.post(f"{base_url}/validate/{job_id}", json=mapping)
print(resp.json())

# 3. Commit
print(f"Committing job {job_id}...")
resp = requests.post(f"{base_url}/commit/{job_id}")
print(resp.json())

print("Done testing!")
