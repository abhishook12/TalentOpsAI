"""
Comprehensive Site & API Health Inspector (Local + Production)
Checks:
1. Local Frontend (http://localhost:5173)
2. Local Backend API (http://localhost:8000)
3. Production Frontend (https://talent-ops-ai.vercel.app)
4. Production Backend API (https://talentopsai-1.onrender.com)
5. Key API Endpoints (/health, /version, /analytics/summary, /recruiters, /companies)
"""

import urllib.request
import urllib.error
import json
import ssl
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def test_endpoint(name, url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'TalentOps-Auditor/1.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            status = resp.status
            raw = resp.read(1000).decode('utf-8', errors='ignore')
            print(f"  [PASS] {name:<42} | HTTP {status} | {url}")
            if raw.strip().startswith('{'):
                try:
                    data = json.loads(raw)
                    print(f"         Payload sample: {str(data)[:120]}")
                except Exception:
                    print(f"         Payload sample: {raw[:120]}")
            return True, status, raw
    except urllib.error.HTTPError as e:
        raw = e.read(300).decode('utf-8', errors='ignore')
        print(f"  [HTTP {e.code}] {name:<38} | {url} -> {raw[:100]}")
        return False, e.code, raw
    except Exception as e:
        print(f"  [FAIL] {name:<42} | {url} -> {e}")
        return False, 0, str(e)

def run_checks():
    print("=" * 85)
    print("TALENTOPS AI — COMPREHENSIVE SITE & API DIAGNOSTIC")
    print("=" * 85)

    print("\n1. LOCAL ENVIRONMENT CHECKS (localhost:5173 & localhost:8000):")
    test_endpoint("Local Frontend Root", "http://127.0.0.1:5173/")
    test_endpoint("Local Backend Health", "http://127.0.0.1:8000/health")
    test_endpoint("Local Backend Version", "http://127.0.0.1:8000/version")
    test_endpoint("Local Backend Docs", "http://127.0.0.1:8000/docs")
    test_endpoint("Local Backend Analytics Summary", "http://127.0.0.1:8000/analytics/summary")
    test_endpoint("Local Backend Recruiters List", "http://127.0.0.1:8000/recruiters?limit=5")
    test_endpoint("Local Backend Companies List", "http://127.0.0.1:8000/companies?limit=5")

    print("\n2. PRODUCTION ENVIRONMENT CHECKS (Vercel & Render):")
    test_endpoint("Production Vercel Frontend Root", "https://talent-ops-ai.vercel.app/")
    test_endpoint("Production Vercel Proxy Health", "https://talent-ops-ai.vercel.app/api/health", timeout=25)
    test_endpoint("Production Vercel Proxy Version", "https://talent-ops-ai.vercel.app/api/version", timeout=25)
    test_endpoint("Production Render Direct Health", "https://talentopsai-1.onrender.com/health", timeout=25)
    test_endpoint("Production Render Direct Analytics", "https://talentopsai-1.onrender.com/analytics/summary", timeout=25)
    test_endpoint("Production Render Direct Recruiters", "https://talentopsai-1.onrender.com/recruiters?limit=5", timeout=25)

    print("\n" + "=" * 85)

if __name__ == "__main__":
    run_checks()
