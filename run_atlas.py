import os
import requests
import sqlite3
import json
from datetime import datetime

base_url = "http://127.0.0.1:8000"
evidence_dir = r"C:\TalentOpsAI\release_certification\evidence"
os.makedirs(evidence_dir, exist_ok=True)

def save_evidence(module, test_name, content):
    path = os.path.join(evidence_dir, f"{module}_{test_name}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"--- EVIDENCE: {module} - {test_name} ---\n")
        f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n\n")
        if isinstance(content, dict) or isinstance(content, list):
            f.write(json.dumps(content, indent=2))
        else:
            f.write(str(content))
    print(f"Saved {path}")

# 1. LOGIN MODULE
login_url = f"{base_url}/auth/login"
db_path = r"C:\TalentOpsAI\backend\dev.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute("SELECT hashed_password FROM users WHERE email = 'admin@talentops.com'")
        print("Admin user hash:", cur.fetchone())
    except Exception as e:
        print("Error reading users:", e)
else:
    print("DB not found at", db_path)

credentials = [
    {"username": "admin@talentops.com", "password": "Admin@123"},
    {"username": "admin@talentops.com", "password": "password"},
    {"username": "admin@talentops.com", "password": "admin123"},
]

token = None
for cred in credentials:
    try:
        res = requests.post(login_url, json=cred)
        if res.status_code == 200:
            token = res.json().get("access_token")
            save_evidence("LOGIN", "success_json", f"Status: {res.status_code}\nBody: {res.text}")
            break
        
        res = requests.post(login_url, data=cred)
        if res.status_code == 200:
            token = res.json().get("access_token")
            save_evidence("LOGIN", "success_form", f"Status: {res.status_code}\nBody: {res.text}")
            break
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)

try:
    res = requests.post(login_url, data={"username": "admin@talentops.com", "password": "wrongpassword"})
    save_evidence("LOGIN", "failure", f"Status: {res.status_code}\nBody: {res.text}")
except requests.exceptions.RequestException as e:
    save_evidence("LOGIN", "failure", str(e))

headers = {"Authorization": f"Bearer {token}"} if token else {}

def try_request(method, url, module, test_name, **kwargs):
    try:
        res = method(url, headers=headers, **kwargs)
        save_evidence(module, test_name, f"Status: {res.status_code}\nBody: {res.text}")
        return res
    except Exception as e:
        save_evidence(module, test_name, f"Exception: {str(e)}")
        return None

# 2. DASHBOARD MODULE
try_request(requests.get, f"{base_url}/analytics/stats", "DASHBOARD", "analytics_stats")
try_request(requests.get, f"{base_url}/analytics/recruiter-distribution", "DASHBOARD", "recruiter_distribution")

# 3. RECRUITERS MODULE
try_request(requests.get, f"{base_url}/recruiters/?page=1&limit=10", "RECRUITERS", "page_1")
try_request(requests.get, f"{base_url}/recruiters/?search=john", "RECRUITERS", "search_john")
try_request(requests.get, f"{base_url}/recruiters/?search=xyznotexistentname123", "RECRUITERS", "search_not_existent")
try_request(requests.get, f"{base_url}/recruiters/?state=CA", "RECRUITERS", "state_ca")
try_request(requests.get, f"{base_url}/recruiters/?page=2&limit=10", "RECRUITERS", "page_2")

# 4. DIRECTORY MODULE 
try_request(requests.get, f"{base_url}/companies/?page=1&limit=10", "DIRECTORY", "companies")
try_request(requests.get, f"{base_url}/companies/by-state", "DIRECTORY", "by_state")

if os.path.exists(db_path):
    try:
        cur.execute("SELECT state, count(*) FROM recruiters GROUP BY state ORDER BY count(*) DESC LIMIT 10")
        save_evidence("DIRECTORY", "db_state_count", cur.fetchall())
    except Exception as e:
        save_evidence("DIRECTORY", "db_state_count", str(e))

# 5. COMPANIES MODULE
try_request(requests.get, f"{base_url}/companies/?search=google", "COMPANIES", "search_google")

# 6. CAMPAIGNS MODULE
try_request(requests.get, f"{base_url}/campaigns/", "CAMPAIGNS", "list")

try:
    res = requests.get(f"{base_url}/openapi.json", headers=headers)
    if res.status_code == 200:
        routes = res.json().get("paths", {})
        campaign_routes = {k: v for k, v in routes.items() if "/campaigns" in k}
        save_evidence("CAMPAIGNS", "openapi_routes", campaign_routes)
    else:
        save_evidence("CAMPAIGNS", "openapi_routes", f"Failed to fetch openapi.json. Status: {res.status_code}")
except Exception as e:
    save_evidence("CAMPAIGNS", "openapi_routes", f"Exception: {str(e)}")

# 7. AI SEARCH MODULE
try_request(requests.post, f"{base_url}/recruiters/ai-search", "AI_SEARCH", "results", json={"query": "Java developer recruiter in Texas"})

# 8. ANALYTICS MODULE 
try_request(requests.get, f"{base_url}/analytics/state-distribution", "ANALYTICS", "state_distribution")

# 9. SENTINEL/DATA QUALITY MODULE
try_request(requests.get, f"{base_url}/sentinel/status", "SENTINEL", "status")
try_request(requests.get, f"{base_url}/sentinel/audit-log?limit=5", "SENTINEL", "audit_log")

if os.path.exists(db_path):
    try:
        cur.execute("SELECT sentinel_status, count(*) FROM recruiters GROUP BY sentinel_status")
        save_evidence("SENTINEL", "db_status", cur.fetchall())
    except Exception as e:
        save_evidence("SENTINEL", "db_status", str(e))

# 10. USER MANAGEMENT MODULE
try_request(requests.get, f"{base_url}/auth/users", "USER_MANAGEMENT", "list")

# 11. FRONTEND BUILD
dist_path = r"C:\TalentOpsAI\frontend\dist\index.html"
assets_dir = r"C:\TalentOpsAI\frontend\dist\assets"
if os.path.exists(dist_path):
    save_evidence("FRONTEND", "index_html", "index.html exists")
else:
    save_evidence("FRONTEND", "index_html", "index.html DOES NOT exist")

if os.path.exists(assets_dir):
    save_evidence("FRONTEND", "assets", os.listdir(assets_dir))
else:
    save_evidence("FRONTEND", "assets", "assets directory DOES NOT exist")

# 12. DATABASE HEALTH
if os.path.exists(db_path):
    try:
        cur.execute("SELECT count(*) FROM recruiters")
        recruiters_count = cur.fetchone()[0]
        try:
            cur.execute("SELECT count(*) FROM companies")
            companies_count = cur.fetchone()[0]
        except:
            companies_count = "Table not found"
        try:
            cur.execute("SELECT count(*) FROM campaigns")
            campaigns_count = cur.fetchone()[0]
        except:
            campaigns_count = "Table not found"
        
        save_evidence("DATABASE", "counts", f"Recruiters: {recruiters_count}\nCompanies: {companies_count}\nCampaigns: {campaigns_count}")
        
        # Check for NULL critical fields in recruiters
        cur.execute("SELECT count(*) FROM recruiters WHERE email IS NULL OR first_name IS NULL")
        null_critical_rec = cur.fetchone()[0]
        save_evidence("DATABASE", "null_checks", f"Recruiters with NULL critical fields (email or first_name): {null_critical_rec}")
        
    except Exception as e:
        save_evidence("DATABASE", "counts", str(e))
