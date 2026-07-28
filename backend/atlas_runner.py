import requests
import sqlite3

print("--- DB Verification ---")
try:
    conn = sqlite3.connect('dev.db')
    c = conn.cursor()
    c.execute("SELECT count(*) FROM users")
    print("Users count:", c.fetchone()[0])
    c.execute("SELECT * FROM devices LIMIT 5")
    print("Devices:", c.fetchall())
except Exception as e:
    print("DB error:", e)

print("--- Login Endpoint ---")
try:
    resp = requests.post("http://localhost:8000/auth/login", json={"email": "admin@talentops.com", "password": "1012"}, timeout=5)
    print(resp.status_code)
    print(resp.text)
except Exception as e:
    print("Login error:", e)

print("--- Dashboard Endpoint ---")
try:
    resp = requests.get("http://localhost:8000/analytics/dashboard", timeout=5)
    print(resp.status_code)
    print(resp.text)
except Exception as e:
    print("Dashboard error:", e)
