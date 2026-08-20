import os
import sys
import time
import requests

sys.path.append(os.path.abspath('C:/TalentOpsAI/backend'))
from app.services.enrichment_service import (
    enrichment_engine,
    clean_domain_from_email,
    derive_company_name_from_domain,
    extract_area_code_from_phone,
    infer_specialization,
    AREA_CODE_MAP
)

def test_unit_enrichment_rules():
    print("--- [TEST SUITE 1: UNIT ENRICHMENT RULES] ---")
    
    # 1. Company name derivation from email domain
    test_cases_domain = [
        ("john@bridgecrossllc.com", "bridgecrossllc.com", "BridgeCross LLC"),
        ("sarah.smith@aerotek.com", "aerotek.com", "Aerotek"),
        ("recruiter@insightglobal.com", "insightglobal.com", "Insight Global"),
        ("lead@apexsystems.com", "apexsystems.com", "Apex Systems"),
        ("hr@cybercoders.com", "cybercoders.com", "CyberCoders"),
        ("talent@prolinkstaff.com", "prolinkstaff.com", "Prolink"),
    ]
    for email, expected_domain, expected_company in test_cases_domain:
        domain = clean_domain_from_email(email)
        company = derive_company_name_from_domain(domain)
        assert domain == expected_domain, f"Domain mismatch for {email}: got {domain}, expected {expected_domain}"
        assert company == expected_company, f"Company mismatch for {email}: got {company}, expected {expected_company}"
        print(f"  [PASS] Email: {email} -> Domain: {domain} -> Company: {company}")
        
    # Generic emails should NOT derive company names
    assert clean_domain_from_email("test@gmail.com") is None
    assert clean_domain_from_email("test@yahoo.com") is None
    print("  [PASS] Generic emails correctly rejected from company inference.")
    
    # 2. Area Code Geo-Inference
    test_cases_phone = [
        ("(312) 555-0199", "IL", "Chicago, IL"),
        ("+1 415 888 9999", "CA", "San Francisco, CA"),
        ("212.555.0100", "NY", "New York, NY"),
        ("512-555-4321", "TX", "Austin, TX"),
        ("2065551234", "WA", "Seattle, WA"),
        ("617-555-9876", "MA", "Boston, MA"),
    ]
    for phone, expected_state, expected_city in test_cases_phone:
        ac = extract_area_code_from_phone(phone)
        assert ac in AREA_CODE_MAP, f"Area code {ac} not in map"
        state, city = AREA_CODE_MAP[ac]
        assert state == expected_state, f"State mismatch for {phone}: got {state}, expected {expected_state}"
        assert city == expected_city, f"City mismatch for {phone}: got {city}, expected {expected_city}"
        print(f"  [PASS] Phone: {phone} -> AC: {ac} -> State: {state}, City: {city}")
        
    # 3. Specialization Taxonomy
    test_cases_title = [
        ("Senior Technical Recruiter", "Information Technology"),
        ("Full Stack IT Sourcing Specialist", "Information Technology"),
        ("Travel Nurse Recruiter", "Healthcare & Nursing"),
        ("Clinical Healthcare Talent Lead", "Healthcare & Nursing"),
        ("Finance & Accounting Headhunter", "Finance & Accounting"),
        ("Aerospace & Mechanical Engineering Recruiter", "Engineering & Manufacturing"),
        ("Executive Search Partner", "Executive & Leadership"),
    ]
    for title, expected_spec in test_cases_title:
        spec = infer_specialization(title)
        assert spec == expected_spec, f"Spec mismatch for '{title}': got '{spec}', expected '{expected_spec}'"
        print(f"  [PASS] Title: '{title}' -> Spec: '{spec}'")
        
    # 4. Single Recruiter JIT Enrichment
    sample_rec = {
        "recruiter_id": 99999999,
        "recruiter_name": "Marcus Vance",
        "email": "m.vance@bridgecrossllc.com",
        "phone": "(312) 800-4491",
        "title": "Principal Technical Recruiter",
        "company_id": "",
        "state": "",
        "location": "",
        "specialization": ""
    }
    enriched = enrichment_engine.enrich_single_recruiter(sample_rec)
    assert enriched["company_id"] == "BridgeCross LLC"
    assert enriched["state"] == "IL"
    assert enriched["location"] == "Chicago, IL"
    assert enriched["specialization"] == "Information Technology"
    print("  [PASS] JIT Single Recruiter Enrichment output:", enriched)

def test_daemon_lifecycle():
    print("\n--- [TEST SUITE 2: DAEMON LIFECYCLE] ---")
    
    # 1. Start
    res_start = enrichment_engine.start()
    print("  [START]", res_start)
    assert res_start["state"]["status"] == "running"
    time.sleep(2)
    
    # 2. Status
    status = enrichment_engine.get_status()
    print("  [STATUS]", status)
    assert status["status"] == "running"
    
    # 3. Pause
    res_pause = enrichment_engine.pause()
    print("  [PAUSE]", res_pause)
    assert res_pause["state"]["status"] == "paused"
    time.sleep(1)
    
    # 4. Resume
    res_resume = enrichment_engine.resume()
    print("  [RESUME]", res_resume)
    assert res_resume["state"]["status"] == "running"
    time.sleep(1)
    
    # 5. Stop
    res_stop = enrichment_engine.stop()
    print("  [STOP]", res_stop)
    assert res_stop["state"]["status"] == "stopped"

def test_http_api_endpoints():
    print("\n--- [TEST SUITE 3: HTTP API ENDPOINTS] ---")
    base_url = "http://localhost:8000"
    
    # Check /system/enricher/status
    r_status = requests.get(f"{base_url}/system/enricher/status")
    print(f"  [GET /system/enricher/status] {r_status.status_code}: {r_status.json()}")
    assert r_status.status_code == 200
    
    # Check /system/enricher/control POST
    r_ctrl_start = requests.post(f"{base_url}/system/enricher/control", json={"action": "start"})
    print(f"  [POST /system/enricher/control start] {r_ctrl_start.status_code}: {r_ctrl_start.json()}")
    assert r_ctrl_start.status_code == 200
    time.sleep(2)
    
    r_ctrl_stop = requests.post(f"{base_url}/system/enricher/control", json={"action": "stop"})
    print(f"  [POST /system/enricher/control stop] {r_ctrl_stop.status_code}: {r_ctrl_stop.json()}")
    assert r_ctrl_stop.status_code == 200
    
    # Check /analytics/enrichment-feed (public or token)
    r_feed = requests.get(f"{base_url}/analytics/enrichment-feed")
    print(f"  [GET /analytics/enrichment-feed] {r_feed.status_code}: {len(r_feed.json().get('feed', []))} items returned")
    # Public or 401/200 OK
    assert r_feed.status_code in (200, 401)

if __name__ == "__main__":
    test_unit_enrichment_rules()
    test_daemon_lifecycle()
    test_http_api_endpoints()
    print("\n========================================================")
    print("=== ALL ENRICHER TESTS PASSED SUCESSFULLY (100%) ===")
    print("========================================================")
