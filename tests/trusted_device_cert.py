import requests
import json
import time
import string
import random
import sys

BASE_URL = "http://127.0.0.1:8000"

def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def generate_fingerprint():
    return {
        "device_id": f"device_{random_string(16)}",
        "browser": "Chrome",
        "os": "Windows",
        "device_name": f"Test-PC-{random_string(4)}",
        "device_type": "desktop"
    }

def register_user(email, password):
    payload = {
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": random_string(4)
    }
    res = requests.post(f"{BASE_URL}/auth/register", json=payload)
    if res.status_code == 201:
        make_active(email)
        return True
    print(f"Register error for {email}:", res.status_code, res.text)
    return False

def make_admin(email):
    import sqlite3
    try:
        conn = sqlite3.connect('backend/dev.db')
        c = conn.cursor()
        c.execute("UPDATE users SET role_id = 1 WHERE email=?", (email,))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Failed to make admin:", e)

def make_active(email):
    import sqlite3
    try:
        conn = sqlite3.connect('backend/dev.db')
        c = conn.cursor()
        c.execute("UPDATE users SET status = 'Active' WHERE email=?", (email,))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Failed to make active:", e)

def login(email, password, fingerprint, existing_cookie=None):
    payload = {
        "email": email,
        "password": password
    }
    
    # Construct a User-Agent based on fingerprint
    user_agent = f"Mozilla/5.0 ({fingerprint['os']}) AppleWebKit/537.36 (KHTML, like Gecko) {fingerprint['browser']}/114.0.0.0 Safari/537.36"
    headers = {"User-Agent": user_agent}
    
    session = requests.Session()
    if existing_cookie:
        session.cookies.set("device_id", existing_cookie)
        
    res = session.post(f"{BASE_URL}/auth/login", json=payload, headers=headers)
    device_id_cookie = None
    for cookie in session.cookies:
        if cookie.name == "device_id":
            device_id_cookie = cookie.value
            break
    return res.status_code, res.json(), device_id_cookie

def admin_approve_device(admin_token, device_id):
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {"status": "Trusted"}
    res = requests.put(f"{BASE_URL}/admin/devices/{device_id}/status", json=payload, headers=headers)
    return res.status_code, res.json()

def admin_revoke_device(admin_token, device_id):
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {"status": "Revoked"}
    res = requests.put(f"{BASE_URL}/admin/devices/{device_id}/status", json=payload, headers=headers)
    return res.status_code, res.json()

def complete_device_approval(device_id_cookie):
    cookies = {"device_id": device_id_cookie}
    res = requests.post(f"{BASE_URL}/auth/complete-device-approval", cookies=cookies)
    return res.status_code, res.json()

def test_unapproved_completion():
    print("\n--- TEST: Unapproved Device Completion ---")
    user_email = f"user_{random_string()}@test.com"
    password = "Password123!"
    register_user(user_email, password)
    
    fp = generate_fingerprint()
    status, res, cookie = login(user_email, password, fp)
    
    status, res = complete_device_approval(cookie)
    print("Attempting to bypass approval:", status, res)
    if status != 403:
        print("DEFECT: Unapproved device bypassed completion check!")
    else:
        print("PASS: Unapproved device properly rejected.")

def test_revocation_enforcement():
    print("\n--- TEST: Revocation Session Kill ---")
    admin_email = f"admin_{random_string()}@test.com"
    user_email = f"user_{random_string()}@test.com"
    password = "Password123!"
    register_user(admin_email, password)
    make_admin(admin_email)
    
    admin_fp = generate_fingerprint()
    _, res, _ = login(admin_email, password, admin_fp)
    admin_token = res.get('token')
    
    register_user(user_email, password)
    fp = generate_fingerprint()
    status, res, cookie = login(user_email, password, fp)
    print("User Login returned:", status, res)
    trusted_device_id = res.get('device_id')
    admin_approve_device(admin_token, trusted_device_id)
    
    status, res = complete_device_approval(cookie)
    status, res, cookie = login(user_email, password, fp, existing_cookie=cookie)
    user_token = res.get('token')
    
    headers = {"Authorization": f"Bearer {user_token}"}
    status = requests.get(f"{BASE_URL}/auth/me", headers=headers).status_code
    print("User Auth /me (Before Revoke):", status)
    
    admin_revoke_device(admin_token, trusted_device_id)
    print("Admin Revoked Device.")
    
    res = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    status = res.status_code
    json_data = res.json() if status == 200 else {}
    print("User Auth /me (After Revoke):", status, json_data)
    if status == 200 and json_data.get("authenticated") is not False:
        print("DEFECT: Revoked device token still active!")
    else:
        print(f"PASS: Revoked device correctly rejected (status {status}).")

def test_device_spoofing():
    print("\n--- TEST: Device Spoofing (Cookie Stolen) ---")
    user_email = f"user_{random_string()}@test.com"
    password = "Password123!"
    register_user(user_email, password)
    
    fp1 = generate_fingerprint()
    status, res, cookie = login(user_email, password, fp1)
    
    admin_email = f"admin_{random_string()}@test.com"
    register_user(admin_email, password)
    make_admin(admin_email)
    _, a_res, _ = login(admin_email, password, generate_fingerprint())
    admin_approve_device(a_res['token'], res['device_id'])
    
    status, res, cookie = login(user_email, password, fp1, existing_cookie=cookie)
    print("Legit Login Status:", status)
    
    fp_attacker = {
        "device_id": "ignored",
        "browser": "Safari",
        "os": "iOS",
        "device_name": "Attacker-iPhone",
        "device_type": "mobile"
    }
    status, res, _ = login(user_email, password, fp_attacker, existing_cookie=cookie)
    print("Spoofed Login Status (Stolen Cookie, Diff Fingerprint):", status, res)
    if status == 200:
        print("DEFECT: System allowed spoofed device login without triggering Re-verification or flagging Risk!")
    else:
        print(f"PASS: Spoofed device correctly blocked/flagged (status {status}).")

if __name__ == "__main__":
    test_unapproved_completion()
    test_revocation_enforcement()
    test_device_spoofing()
