import urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/analytics/companies-count-by-state") as response:
        html = response.read()
        print("Companies:", html[:200])
except Exception as e:
    print("Error Companies:", e)
