import urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/analytics/dashboard") as response:
        html = response.read()
        print("Dashboard:", html[:200])
except Exception as e:
    print("Error Dashboard:", e)
