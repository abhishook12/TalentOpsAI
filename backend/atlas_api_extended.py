import os
import json
import time
import requests
import datetime

BASE_URL = "http://127.0.0.1:8000"
EVIDENCE_DIR = r"C:\TalentOpsAI\release_certification\evidence"
os.makedirs(EVIDENCE_DIR, exist_ok=True)

session = requests.Session()

def api(method, path, data=None, token=None, label=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{BASE_URL}{path}"
    
    start_time = time.time()
    try:
        if method.upper() == "GET":
            res = session.get(url, headers=headers)
        elif method.upper() == "POST":
            res = session.post(url, json=data, headers=headers)
        elif method.upper() == "PUT":
            res = session.put(url, json=data, headers=headers)
        elif method.upper() == "DELETE":
            res = session.delete(url, headers=headers)
        
        status = res.status_code
        content = res.text
    except Exception as e:
        status = 500
        content = str(e)
    
    elapsed = time.time() - start_time
    result = {
        "status": status,
        "elapsed_ms": round(elapsed * 1000, 2),
        "body": content[:2000],
        "raw_body": content,
        "url": url,
        "method": method,
        "timestamp": str(datetime.datetime.now())
    }
    
    if label:
        path_safe = label.replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_")
        with open(os.path.join(EVIDENCE_DIR, f"{path_safe}.json"), "w") as f:
            json.dump(result, f, indent=2)
    print(f"[{status}] {method} {path} ({result['elapsed_ms']}ms) -> {content[:50]}")
    return result

def main():
    print("Starting ATLAS Extended API Collection...")
    
    # 1. Admin Login
    print("\n--- ADMIN LOGIN ---")
    admin_login = api("POST", "/auth/login", {"email": "admin@talentops.com", "password": "Admin@TalentOps2026"})
    try:
        admin_token = json.loads(admin_login["raw_body"])["token"]
    except:
        print("Failed to get admin token.")
        return
        
    # 2. AC-REC-002, 004, 005 (Recruiter CRUD by Admin)
    print("\n--- ADMIN RECRUITER CRUD ---")
    rec_data = {"recruiter_name": "Atlas Test Recruiter", "email": f"atlas_test_{int(time.time())}@example.com", "company_id": 1, "status": "Active"}
    create_rec = api("POST", "/recruiters/", data=rec_data, token=admin_token, label="AC_REC_002_create_recruiter")
    rec_id = None
    if create_rec["status"] == 200:
        rec_id = json.loads(create_rec["raw_body"]).get("recruiter_id")
    
    if rec_id:
        update_rec = api("PUT", f"/recruiters/{rec_id}", data={"recruiter_name": "Updated Atlas Recruiter"}, token=admin_token, label="AC_REC_004_update_recruiter")
        del_rec = api("DELETE", f"/recruiters/{rec_id}", token=admin_token, label="AC_REC_005_delete_recruiter")
        
    # AC-REC-009 (Recruiter Search Performance)
    search_rec = api("GET", "/recruiters/?search=test", token=admin_token, label="AC_REC_009_search_performance")

    # 3. AC-UM-002-004 (User Management CRUD by Admin)
    print("\n--- ADMIN USER MANAGEMENT ---")
    user_data = {"email": f"atlas_temp_user_{int(time.time())}@talentops.com", "password": "TempUser123!", "first_name": "Temp", "last_name": "User", "role_id": 2}
    create_user = api("POST", "/users/", data=user_data, token=admin_token, label="AC_UM_002_create_user")
    temp_user_id = None
    if create_user["status"] == 200:
        temp_user_id = json.loads(create_user["raw_body"]).get("user_id")
    
    if temp_user_id:
        # Update user
        api("PUT", f"/users/{temp_user_id}/status", data={"status": "Inactive"}, token=admin_token, label="AC_UM_003_deactivate_user")
        
        # Test inactive user login
        login_inactive = api("POST", "/auth/login", {"email": user_data["email"], "password": "TempUser123!"}, label="AC_UM_004_inactive_login")
        
    # 4. User Role Flow
    print("\n--- USER ROLE TESTS ---")
    # Step 1: User Login (AC-LOGIN-002)
    user_login = api("POST", "/auth/login", {"email": "user@talentops.com", "password": "User@TalentOps2026"}, label="AC_LOGIN_002_user_login")
    
    if user_login["status"] == 403:
        # Needs device approval
        print("User device pending approval. Admin approving...")
        devices_res = api("GET", "/admin/devices/", token=admin_token)
        devices = json.loads(devices_res["raw_body"])
        # Support both array and object formats just in case
        if isinstance(devices, dict) and "devices" in devices:
            devices = devices["devices"]
        pending = [d for d in devices if d.get("status") == "Pending"]
        if pending:
            api("PUT", f"/admin/devices/{pending[-1]['id']}/status", data={"status": "Trusted"}, token=admin_token, label="AC_DEV_004_admin_approve")
            
        # Try again
        user_login = api("POST", "/auth/login", {"email": "user@talentops.com", "password": "User@TalentOps2026"}, label="AC_LOGIN_002_user_login_approved")

    user_token = None
    try:
        user_token = json.loads(user_login["raw_body"])["token"]
    except:
        print("Failed to get user token.")
    
    if user_token:
        # AC-REC-008 User cannot create recruiter
        rec_data_user = {"recruiter_name": "User Try Create", "email": "user_try@example.com", "company_id": 1, "status": "Active"}
        api("POST", "/recruiters/", data=rec_data_user, token=user_token, label="AC_REC_008_user_cannot_create")
        
        # AC-DASH-002 User Dashboard
        api("GET", "/analytics/dashboard", token=user_token, label="AC_DASH_002_user_metrics")
        
        # AC-VISIT-003 User cannot see visitor analytics
        api("GET", "/admin/visitor-analytics/overview", token=user_token, label="AC_VISIT_003_user_cannot_see_visitor_analytics")

    # 5. Lockout test
    print("\n--- LOCKOUT TEST ---")
    for i in range(6):
        res = api("POST", "/auth/login", {"email": "admin@talentops.com", "password": "WrongPassword123"})
        if i == 5:
            api("POST", "/auth/login", {"email": "admin@talentops.com", "password": "WrongPassword123"}, label="AC_LOGIN_005_lockout")

    print("\nATLAS Extended API Collection Complete.")

if __name__ == "__main__":
    main()
