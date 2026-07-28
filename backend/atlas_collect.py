"""
ATLAS Forensic Evidence Collection Script
Runs against the live TalentOpsAI application and collects evidence for all AC items.
"""
import subprocess, json, os, sys, datetime

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwic2Vzc2lvbl9pZCI6MjQsImV4cCI6MTc4NTIwMzA2OH0.JrHNuGu5tW01vztKtegii_04rRRDVDwHRwqekutyWX8"
BASE = "http://127.0.0.1:8000"
EVIDENCE_DIR = r"C:\TalentOpsAI\release_certification\evidence"
os.makedirs(EVIDENCE_DIR, exist_ok=True)

def api(method, path, body=None, auth=True, label=None):
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {TOKEN}"
    
    import urllib.request, urllib.error
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        status = resp.status
        content = resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        status = e.code
        content = e.read().decode('utf-8')
    except Exception as ex:
        status = 0
        content = str(ex)
    
    result = {"status": status, "body": content[:2000], "url": url, "method": method, "timestamp": str(datetime.datetime.now())}
    if label:
        path_safe = label.replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_")
        with open(os.path.join(EVIDENCE_DIR, f"{path_safe}.json"), "w") as f:
            json.dump(result, f, indent=2)
    print(f"  [{status}] {method} {path}" + (f" -> {content[:100]}" if len(content) < 200 else f" -> {content[:100]}..."))
    return result

def db_query(sql, label=None):
    import sqlite3
    db_path = r"C:\TalentOpsAI\backend\dev.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description] if cursor.description else []
        conn.close()
        result = {"columns": cols, "rows": rows[:50], "count": len(rows), "sql": sql, "timestamp": str(datetime.datetime.now())}
    except Exception as e:
        result = {"error": str(e), "sql": sql}
    
    if label:
        with open(os.path.join(EVIDENCE_DIR, f"DB_{label}.json"), "w") as f:
            json.dump(result, f, indent=2)
    print(f"  [DB] {sql[:80]} -> {len(result.get('rows', []))} rows")
    return result

evidence = {}

print("=" * 60)
print("ATLAS FORENSIC EVIDENCE COLLECTION ENGINE")
print(f"Timestamp: {datetime.datetime.now()}")
print("=" * 60)

# ============================================================
# 1. LOGIN MODULE
# ============================================================
print("\n[1] LOGIN MODULE")

# AC-LOGIN-001: Admin login with valid credentials
r = api("POST", "/auth/login", {"email": "admin@talentops.com", "password": "Admin@TalentOps2026"}, auth=False, label="AC_LOGIN_001_admin_valid_login")
evidence["AC-LOGIN-001"] = {"status": r["status"], "has_token": "token" in r["body"], "collected": r["status"] == 200}

# AC-LOGIN-003: Invalid email format rejection
r = api("POST", "/auth/login", {"email": "notanemail", "password": "anything"}, auth=False, label="AC_LOGIN_003_invalid_email")
evidence["AC-LOGIN-003"] = {"status": r["status"], "error_shown": r["status"] >= 400, "body": r["body"][:200]}

# AC-LOGIN-004: Wrong password rejection
r = api("POST", "/auth/login", {"email": "admin@talentops.com", "password": "wrongpassword123"}, auth=False, label="AC_LOGIN_004_wrong_password")
evidence["AC-LOGIN-004"] = {"status": r["status"], "rejected": r["status"] >= 400, "body": r["body"][:200]}

# AC-LOGIN-008: Logout endpoint
r = api("POST", "/auth/logout", label="AC_LOGIN_008_logout")
evidence["AC-LOGIN-008"] = {"status": r["status"], "body": r["body"][:200]}

# ============================================================
# 2. GOOGLE LOGIN MODULE
# ============================================================
print("\n[2] GOOGLE LOGIN MODULE")
r = api("GET", "/auth/google", auth=False, label="AC_GLOGIN_001_google_button_endpoint")
evidence["AC-GLOGIN-001"] = {"status": r["status"], "body": r["body"][:300], "endpoint_exists": r["status"] != 404}

# ============================================================
# 3. DASHBOARD MODULE
# ============================================================
print("\n[3] DASHBOARD MODULE")
r = api("GET", "/analytics/stats", label="AC_DASH_001_admin_metrics")
evidence["AC-DASH-001"] = {"status": r["status"], "has_data": r["status"] == 200, "body": r["body"][:500]}

r2 = api("GET", "/analytics/recruiter-distribution", label="AC_DASH_003_charts_data")
evidence["AC-DASH-003"] = {"status": r2["status"], "body": r2["body"][:300]}

# ============================================================
# 4. RECRUITERS MODULE
# ============================================================
print("\n[4] RECRUITERS MODULE")

# AC-REC-001: Paginated list
r = api("GET", "/recruiters/?page=1&limit=20", label="AC_REC_001_paginated_list")
evidence["AC-REC-001"] = {"status": r["status"], "body": r["body"][:500]}

# AC-REC-006: Search by name
r = api("GET", "/recruiters/?search=john", label="AC_REC_006_search_name")
evidence["AC-REC-006"] = {"status": r["status"], "body": r["body"][:500]}

# Empty search results
r = api("GET", "/recruiters/?search=xyznotexistentname999abc", label="AC_REC_006b_search_empty")
evidence["AC-REC-006-EMPTY"] = {"status": r["status"], "body": r["body"][:300]}

# AC-REC-007: Filter by state
r = api("GET", "/recruiters/?state=CA", label="AC_REC_007_filter_state")
evidence["AC-REC-007"] = {"status": r["status"], "body": r["body"][:500]}

# Pagination page 2
r = api("GET", "/recruiters/?page=2&limit=20", label="AC_REC_001b_pagination_page2")
evidence["AC-REC-001-PAGE2"] = {"status": r["status"], "body": r["body"][:300]}

# AC-REC-003: Duplicate email
r = api("POST", "/recruiters/", {"recruiter_name": "Test Dup", "email": "admin@talentops.com", "company_id": 1}, label="AC_REC_003_duplicate_email")
evidence["AC-REC-003"] = {"status": r["status"], "rejected": r["status"] >= 400, "body": r["body"][:300]}

# ============================================================
# 5. DIRECTORY MODULE
# ============================================================
print("\n[5] DIRECTORY MODULE")
r = api("GET", "/companies/?page=1&limit=10", label="AC_DIR_001_companies_list")
evidence["AC-DIR-001"] = {"status": r["status"], "body": r["body"][:500]}

r2 = api("GET", "/analytics/state-distribution", label="AC_DIR_002_state_distribution")
evidence["AC-DIR-002"] = {"status": r2["status"], "body": r2["body"][:500]}

# DB: State-level recruiter counts
db_r = db_query("SELECT state, count(*) as cnt FROM recruiters WHERE state IS NOT NULL AND state != '' GROUP BY state ORDER BY cnt DESC LIMIT 10", "DIR_state_counts")
evidence["AC-DIR-004"] = {"db_rows": db_r.get("rows", [])[:5], "count": db_r.get("count", 0)}

# ============================================================
# 6. COMPANIES MODULE
# ============================================================
print("\n[6] COMPANIES MODULE")
r = api("GET", "/companies/?page=1&limit=10", label="AC_COMP_001_company_list")
evidence["AC-COMP-001"] = {"status": r["status"], "body": r["body"][:500]}

r2 = api("GET", "/companies/?search=tech", label="AC_COMP_search")
evidence["AC-COMP-SEARCH"] = {"status": r2["status"], "body": r2["body"][:300]}

# ============================================================
# 7. CAMPAIGNS MODULE
# ============================================================
print("\n[7] CAMPAIGNS MODULE")
r = api("GET", "/campaigns/", label="AC_CAMP_004_campaign_list")
evidence["AC-CAMP-004"] = {"status": r["status"], "body": r["body"][:500]}

# Check openapi for campaign routes
r2 = api("GET", "/openapi.json", auth=False, label="AC_CAMP_001_openapi_routes")
routes = [p for p in json.loads(r2["raw_body"]).get("paths", {}).keys() if "campaign" in p] if r2["status"] == 200 else []
evidence["AC-CAMP-001"] = {"campaign_routes": routes, "count": len(routes)}

# ============================================================
# 8. AI SEARCH MODULE
# ============================================================
print("\n[8] AI SEARCH MODULE")
r = api("GET", "/recruiters/search?q=Java%20developer%20recruiter%20in%20Texas", label="AC_AI_001_natural_language")
evidence["AC-AI-001"] = {"status": r["status"], "body": r["body"][:500]}

r2 = api("GET", "/recruiters/search?q=xyzgarblednonsensequeryabc123", label="AC_AI_004_nonsense_query")
evidence["AC-AI-004"] = {"status": r2["status"], "body": r2["body"][:300]}

# ============================================================
# 9. ANALYTICS MODULE
# ============================================================
print("\n[9] ANALYTICS MODULE")
r = api("GET", "/analytics/stats", label="AC_ANAL_001_stats")
evidence["AC-ANAL-001"] = {"status": r["status"], "body": r["body"][:500]}

r2 = api("GET", "/analytics/state-distribution", label="AC_ANAL_state")
evidence["AC-ANAL-STATE"] = {"status": r2["status"], "body": r2["body"][:300]}

# ============================================================
# 10. SENTINEL MODULE
# ============================================================
print("\n[10] SENTINEL MODULE")
r = api("GET", "/sentinel/status", label="AC_SENT_001_sentinel_status")
evidence["AC-SENT-001"] = {"status": r["status"], "body": r["body"][:500]}

r2 = api("GET", "/sentinel/audit-log?limit=5", label="AC_SENT_002_audit_log")
evidence["AC-SENT-002"] = {"status": r2["status"], "body": r2["body"][:500]}

db_r = db_query("SELECT sentinel_status, count(*) as cnt FROM recruiters GROUP BY sentinel_status", "SENT_status_distribution")
evidence["AC-SENT-DB"] = {"rows": db_r.get("rows", [])[:10]}

# ============================================================
# 11. USER MANAGEMENT MODULE
# ============================================================
print("\n[11] USER MANAGEMENT MODULE")
r = api("GET", "/auth/users", label="AC_UM_001_user_list")
evidence["AC-UM-001"] = {"status": r["status"], "body": r["body"][:500]}

# ============================================================
# 12. PROFILE MODULE
# ============================================================
print("\n[12] PROFILE MODULE")
r = api("GET", "/auth/me", label="AC_PROF_001_profile")
evidence["AC-PROF-001"] = {"status": r["status"], "body": r["body"][:500]}

# ============================================================
# 13. FRONTEND BUILD CHECK
# ============================================================
print("\n[13] FRONTEND BUILD CHECK")
dist_exists = os.path.exists(r"C:\TalentOpsAI\frontend\dist\index.html")
assets = os.listdir(r"C:\TalentOpsAI\frontend\dist\assets") if dist_exists else []
evidence["FRONTEND-BUILD"] = {"dist_index_exists": dist_exists, "asset_count": len(assets), "sample": assets[:5]}
print(f"  dist/index.html: {dist_exists}, assets: {len(assets)}")

# ============================================================
# 14. DATABASE HEALTH
# ============================================================
print("\n[14] DATABASE HEALTH")
db_r = db_query("SELECT COUNT(*) as total FROM recruiters", "DB_recruiters_count")
evidence["DB-RECRUITERS"] = {"total": db_r.get("rows", [[0]])[0][0] if db_r.get("rows") else 0}

db_r2 = db_query("SELECT COUNT(*) as total FROM companies", "DB_companies_count")
evidence["DB-COMPANIES"] = {"total": db_r2.get("rows", [[0]])[0][0] if db_r2.get("rows") else 0}

db_r3 = db_query("SELECT COUNT(*) as total FROM campaigns", "DB_campaigns_count")
evidence["DB-CAMPAIGNS"] = {"total": db_r3.get("rows", [[0]])[0][0] if db_r3.get("rows") else 0}

db_r4 = db_query("SELECT COUNT(*) as total FROM users", "DB_users_count")
evidence["DB-USERS"] = {"total": db_r4.get("rows", [[0]])[0][0] if db_r4.get("rows") else 0}

# ============================================================
# SAVE FULL EVIDENCE PACKAGE
# ============================================================
with open(r"C:\TalentOpsAI\release_certification\ATLAS_EVIDENCE_PACKAGE.json", "w") as f:
    json.dump(evidence, f, indent=2)

print("\n" + "=" * 60)
print("ATLAS COLLECTION COMPLETE")
print(f"Evidence artifacts saved to: {EVIDENCE_DIR}")
print(f"Evidence Package: C:\\TalentOpsAI\\release_certification\\ATLAS_EVIDENCE_PACKAGE.json")
print(f"Total AC items with evidence: {len(evidence)}")
print("=" * 60)
