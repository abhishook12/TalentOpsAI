import urllib.request

try:
    with urllib.request.urlopen("http://127.0.0.1:8000/analytics/dashboard-kpis") as response:
        html = response.read()
        print("KPIs:", html[:200])
except Exception as e:
    print("Error KPIs:", e)

try:
    with urllib.request.urlopen("http://127.0.0.1:8000/analytics/companies-search?state=ALL&limit=6&skip=0&min_recruiters=1") as response:
        html = response.read()
        print("Search:", html[:200])
except Exception as e:
    print("Error Search:", e)

try:
    with urllib.request.urlopen("http://127.0.0.1:8000/analytics/visit-stats") as response:
        html = response.read()
        print("Visits:", html[:200])
except Exception as e:
    print("Error Visits:", e)
