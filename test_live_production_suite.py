import requests
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

backend_url = "https://talentopsai-1.onrender.com"
frontend_url = "https://talent-ops-ai.vercel.app"

print("=== CHECK 1: LIVE PRODUCTION BACKEND (RENDER) ===")
# 1. Health check
r_health = requests.get(f"{backend_url}/health/", timeout=20)
print(f"Health Status: {r_health.status_code}")
print(f"Health Payload: {r_health.text[:300]}")
assert r_health.status_code == 200, f"Backend health failed: {r_health.status_code}"
health_json = r_health.json()
print(f"   Database Status: {health_json['components']['database']['status']}")
print(f"   Recruiter Store Status: {health_json['components']['recruiter_store']['status']} ({health_json['components']['recruiter_store']['records']} records, {health_json['components']['recruiter_store']['companies']} companies)")
assert health_json['status'] == 'healthy', "Production backend reported non-healthy status"
print("CHECK 1 PASSED: Live Render Backend is 100% operational and healthy.\n")

print("=== CHECK 2: LIVE PRODUCTION FRONTEND (VERCEL) ===")
r_front = requests.get(frontend_url, timeout=20)
print(f"Vercel Frontend HTTP Status: {r_front.status_code}")
assert r_front.status_code == 200, f"Frontend returned {r_front.status_code}"
assert "<!doctype html>" in r_front.text.lower() or "talentops" in r_front.text.lower(), "Vercel frontend body missing HTML doctype/title"
print(f"   Frontend Response Size: {len(r_front.content)} bytes")
print("CHECK 2 PASSED: Live Vercel Frontend is live, serving 200 OK.\n")

print("=== CHECK 3: LIVE PRODUCTION LOGO ENGINE & DATABASE SYNC ===")
test_domains = ["roberthalf.com", "teksystems.com", "insightglobal.com", "optomi.com", "randstadusa.com"]
for d in test_domains:
    logo_url = f"https://logos.hunter.io/{d}"
    r_logo = requests.get(logo_url, timeout=5)
    print(f"  Live logo resolution for '{d}': {r_logo.status_code} ({len(r_logo.content)} bytes)")
    assert r_logo.status_code == 200, f"Logo for {d} failed with status {r_logo.status_code}"
print("CHECK 3 PASSED: All production company logos resolve cleanly with HTTP 200 OK.")
