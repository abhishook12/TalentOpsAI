import urllib.request
import urllib.error

urls = [
    "http://localhost:8000/docs",
    "http://localhost:5173",
    "https://talentopsai.onrender.com/docs"
]

for url in urls:
    try:
        response = urllib.request.urlopen(url, timeout=5)
        print(f"UP: {url} (Status: {response.status})")
    except urllib.error.URLError as e:
        print(f"DOWN: {url} (Error: {e.reason})")
    except Exception as e:
        print(f"DOWN: {url} (Exception: {e})")
