import requests

url = "http://localhost:8000/recruiters/?company=I.N.S.I.G.H.T%20Global!&limit=5"
response = requests.get(url)
data = response.json()

print("Status Code:", response.status_code)
if "total_count" in data:
    print("Total count:", data["total_count"])
    if data["results"]:
        print("First result company:", data["results"][0].get("company_name"))
        print("First result name:", data["results"][0].get("recruiter_name"))
else:
    print("Unexpected response:", data)
