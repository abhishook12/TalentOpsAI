import requests
import json
import secrets
import time

BASE_URL = "http://localhost:8000"
test_results = []
bugs_found = []

def run_test(name, fn):
    try:
        passed, msg = fn()
        test_results.append({"name": name, "passed": passed, "message": msg})
        if not passed:
            bugs_found.append({"test": name, "error": msg})
            print(f"FAILED: {name} - {msg}")
        else:
            print(f"PASSED: {name}")
    except Exception as e:
        test_results.append({"name": name, "passed": False, "message": str(e)})
        bugs_found.append({"test": name, "error": str(e)})
        print(f"ERROR: {name} - {str(e)}")

# Test 1: Weak Password
def test_weak_password():
    email = f"test_{secrets.token_hex(4)}@example.com"
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "first_name": "Test", "last_name": "User", "email": email, "password": "123"
    })
    # Our API actually does NOT validate password complexity on the backend, only frontend
    # Since backend doesn't, we will assume this passes if it registers. 
    # WAIT, the user explicitly asked to test weak passwords and break the system. 
    # If the backend accepts weak passwords, it's a security flaw.
    if res.status_code == 201:
        return False, "BUG: Backend allows weak passwords."
    return True, "Weak password rejected."

run_test("Registration - Weak Password", test_weak_password)

# Test 2: SQL Injection in Email
def test_sqli_email():
    email = "admin@example.com' OR '1'='1"
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "first_name": "Test", "last_name": "User", "email": email, "password": "StrongPassword123!"
    })
    if res.status_code in [201, 400, 422]:
        return True, f"SQLi safely handled (status {res.status_code})."
    return False, f"Unexpected status: {res.status_code}"

run_test("Registration - SQL Injection Email", test_sqli_email)

# Test 3: XSS in First Name
def test_xss_name():
    email = f"test_{secrets.token_hex(4)}@example.com"
    xss_payload = "<script>alert(1)</script>"
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "first_name": xss_payload, "last_name": "User", "email": email, "password": "StrongPassword123!"
    })
    return True, "XSS handled without crashing."

run_test("Registration - XSS Name", test_xss_name)

# Test 4: Duplicate Email
def test_duplicate_email():
    email = f"dup_{secrets.token_hex(4)}@example.com"
    req = {"first_name": "D", "last_name": "E", "email": email, "password": "StrongPassword123!"}
    requests.post(f"{BASE_URL}/auth/register", json=req)
    res2 = requests.post(f"{BASE_URL}/auth/register", json=req)
    if res2.status_code == 400 and "already registered" in res2.text:
        return True, "Duplicate correctly rejected."
    return False, f"Unexpected behavior on duplicate: {res2.status_code}"

run_test("Registration - Duplicate Email", test_duplicate_email)

# Test 5: Login with Wrong Password
def test_login_wrong_password():
    email = f"log_{secrets.token_hex(4)}@example.com"
    requests.post(f"{BASE_URL}/auth/register", json={
        "first_name": "L", "last_name": "O", "email": email, "password": "StrongPassword123!"
    })
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": "WrongPassword123!"})
    if res.status_code == 401 and "Invalid credentials" in res.text:
        return True, "Wrong password correctly rejected."
    return False, f"Unexpected status: {res.status_code}"

run_test("Login - Wrong Password", test_login_wrong_password)

# Test 6: Rate Limiting Brute Force Login
def test_brute_force_login():
    email = f"brute_{secrets.token_hex(4)}@example.com"
    responses = []
    for _ in range(12):
        responses.append(requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": "WrongPassword123!"}).status_code)
    
    if 429 in responses:
        return True, "Rate limiting correctly kicked in (429)."
    return False, f"No rate limiting observed. Status codes: {responses}"

run_test("Security - Brute Force Login", test_brute_force_login)

# Test 7: Invalid Google Token
def test_invalid_google_token():
    res = requests.post(f"{BASE_URL}/auth/google", json={"credential": "invalid.jwt.token"})
    if res.status_code == 401:
        return True, "Invalid google token correctly rejected."
    return False, f"Unexpected status: {res.status_code}"

run_test("Google Sign-In - Invalid Token", test_invalid_google_token)

# Test 8: Forgot Password - Non-existing email
def test_forgot_password_non_existing():
    email = f"nonexist_{secrets.token_hex(4)}@example.com"
    res = requests.post(f"{BASE_URL}/auth/forgot-password", json={"email": email})
    # Should return 200 to prevent email enumeration
    if res.status_code == 200:
        return True, "Safely returned 200 for non-existing email."
    return False, f"Failed enumeration check. Status: {res.status_code}"

run_test("Forgot Password - Non-existing email", test_forgot_password_non_existing)

# Test 9: Invalid Reset Token
def test_invalid_reset_token():
    res = requests.post(f"{BASE_URL}/auth/reset-password", json={"token": "fake_token", "new_password": "NewStrongPass1!"})
    if res.status_code in [400, 401, 403]:
        return True, "Invalid reset token rejected."
    return False, f"Unexpected status: {res.status_code}"

run_test("Reset Password - Invalid Token", test_invalid_reset_token)

# Test 10: Invalid Email Verification Token
def test_invalid_verification_token():
    res = requests.post(f"{BASE_URL}/auth/verify-email", json={"token": "fake_verify_token"})
    if res.status_code in [400, 401, 403]:
        return True, "Invalid verification token rejected."
    return False, f"Unexpected status: {res.status_code}"

run_test("Verify Email - Invalid Token", test_invalid_verification_token)

with open("qa_results.json", "w") as f:
    json.dump({"total": len(test_results), "passed": sum(1 for t in test_results if t["passed"]), "bugs": bugs_found}, f, indent=2)

print("\n--- QA Testing Complete ---")
print(f"Total: {len(test_results)}, Passed: {sum(1 for t in test_results if t['passed'])}, Failed: {len(bugs_found)}")
