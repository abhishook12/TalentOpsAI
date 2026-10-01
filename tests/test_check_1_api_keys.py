"""
Test Check 1: API Key Full Lifecycle & Authentication Verification
Verifies creation, listing, X-API-Key auth, Bearer top_ auth, invalid key rejection, revocation, and post-revocation rejection.
"""
import sys
import requests
import json

BASE_URL = "http://127.0.0.1:8000"
BYPASS_TOKEN = "legacy_admin_bypass_token"
ADMIN_HEADERS = {"Authorization": f"Bearer {BYPASS_TOKEN}"}

def run_test():
    print("=== [TEST CHECK 1] API KEY AUTHENTICATION & LIFECYCLE ===")
    
    # 1. Health check
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    print("[PASS] 1. Backend is reachable and healthy (status 200)")

    # 2. Create API key
    key_name = "Automated Test Key"
    r = requests.post(f"{BASE_URL}/api/keys", json={"name": key_name}, headers=ADMIN_HEADERS, timeout=5)
    assert r.status_code in (200, 201), f"Create API key failed: {r.status_code} {r.text}"
    created = r.json()
    api_key_str = created.get("api_key")
    key_id = created.get("id")
    print(f"[PASS] 2. Created API Key ID={key_id}, Prefix={created.get('key_prefix')}")
    assert api_key_str and api_key_str.startswith("top_"), f"API key must start with top_: {api_key_str}"
    
    # 3. List API keys
    r = requests.get(f"{BASE_URL}/api/keys", headers=ADMIN_HEADERS, timeout=5)
    assert r.status_code == 200, f"List API keys failed: {r.status_code}"
    keys_list = r.json()
    assert any(k["id"] == key_id for k in keys_list), f"Created key {key_id} not in listing"
    print(f"[PASS] 3. Listed API Keys ({len(keys_list)} keys active/recorded)")

    # 4. Check API key usage endpoint
    r = requests.get(f"{BASE_URL}/api/keys/usage", headers=ADMIN_HEADERS, timeout=5)
    assert r.status_code == 200, f"Usage check failed: {r.status_code}"
    usage = r.json()
    print(f"[PASS] 4. API Usage Info: active_keys={usage.get('active_keys')}, max_keys={usage.get('max_keys')}")

    # 5. Authenticate using X-API-Key header
    r = requests.get(f"{BASE_URL}/api/keys", headers={"X-API-Key": api_key_str}, timeout=5)
    assert r.status_code == 200, f"X-API-Key authentication failed: {r.status_code} {r.text}"
    print("[PASS] 5. Authenticated successfully via 'X-API-Key' header (status 200)")

    # 6. Authenticate using Bearer top_ token in Authorization header
    r = requests.get(f"{BASE_URL}/api/keys", headers={"Authorization": f"Bearer {api_key_str}"}, timeout=5)
    assert r.status_code == 200, f"Bearer top_ authentication failed: {r.status_code} {r.text}"
    print("[PASS] 6. Authenticated successfully via 'Authorization: Bearer top_...' header (status 200)")

    # 7. Negative test: Invalid API Key
    r = requests.get(f"{BASE_URL}/api/keys", headers={"X-API-Key": "top_invalid_bogus_key_99999"}, timeout=5)
    assert r.status_code == 401, f"Expected 401 for invalid API key, got: {r.status_code}"
    print("[PASS] 7. Rejected invalid API key with HTTP 401 as expected")

    # 8. Revoke the API Key
    r = requests.delete(f"{BASE_URL}/api/keys/{key_id}", headers=ADMIN_HEADERS, timeout=5)
    assert r.status_code == 200, f"Revoke API key failed: {r.status_code} {r.text}"
    print(f"[PASS] 8. Revoked API Key ID={key_id} successfully")

    # 9. Verify revoked key cannot authenticate
    r = requests.get(f"{BASE_URL}/api/keys", headers={"X-API-Key": api_key_str}, timeout=5)
    assert r.status_code == 401, f"Expected 401 for revoked API key, got: {r.status_code}"
    print("[PASS] 9. Revoked API key is denied access with HTTP 401")

    print(">>> CHECK 1 PASSED: ALL 9 VERIFICATION ASSERTIONS SUCCEEDED <<<\n")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"[FAIL] Check 1 failed: {e}")
        sys.exit(1)
