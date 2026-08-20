import os
import sys
import time
import requests
import json

sys.path.append(os.path.abspath('C:/TalentOpsAI/backend'))

from app.services.enrichment_service import (
    enrichment_engine,
    clean_domain_from_email,
    derive_company_name_from_domain,
    extract_area_code_from_phone,
    infer_specialization,
    AREA_CODE_MAP,
    DOMAIN_BRAND_OVERRIDES
)
from app.utils.enricher_state import get_enricher_state
from app.services.recruiter_store import recruiter_store

def run_check_1_deterministic_rule_accuracy():
    print("\n" + "="*70)
    print("=== [CHECK 1 / 3]: ZERO-COST DETERMINISTIC ENRICHMENT ACCURACY ===")
    print("="*70)
    
    # 1. Company Name Derivation from Email Domains
    print("\n[Vector 1.1: Company Name Extraction from Email Domain]")
    domain_tests = [
        ("alex@bridgecrossllc.com", "bridgecrossllc.com", "BridgeCross LLC"),
        ("recruiter@insightglobal.com", "insightglobal.com", "Insight Global"),
        ("talent@aerotek.com", "aerotek.com", "Aerotek"),
        ("hr@teksystems.com", "teksystems.com", "TEKsystems"),
        ("sourcing@apexsystems.com", "apexsystems.com", "Apex Systems"),
        ("lead@roberthalf.com", "roberthalf.com", "Robert Half"),
        ("admin@randstadusa.com", "randstadusa.com", "Randstad"),
        ("contact@prolinkstaffing.com", "prolinkstaffing.com", "Prolink Staffing"),
        ("careers@cybercoders.com", "cybercoders.com", "CyberCoders"),
        ("jobs@beaconhillstaffing.com", "beaconhillstaffing.com", "Beacon Hill Staffing Group"),
    ]
    for email, exp_domain, exp_company in domain_tests:
        d = clean_domain_from_email(email)
        c = derive_company_name_from_domain(d)
        assert d == exp_domain, f"Domain failed for {email}: got {d}, exp {exp_domain}"
        assert c == exp_company, f"Company failed for {email}: got {c}, exp {exp_company}"
        print(f"  [PASS] {email:35} -> Domain: {d:25} -> Company: {c}")

    # 1.2 Exclusion of Generic / Free Email Providers
    print("\n[Vector 1.2: Strict Generic Provider Exclusion]")
    generic_emails = [
        "john.doe@gmail.com", "recruiter@yahoo.com", "sales@hotmail.com",
        "lead@outlook.com", "hr@icloud.com", "contact@proton.me", "candidate@aol.com"
    ]
    for g_email in generic_emails:
        d = clean_domain_from_email(g_email)
        assert d is None, f"Generic domain {g_email} should not resolve to company domain!"
        print(f"  [PASS] Generic email safely rejected: {g_email}")

    # 2. Area Code Geo-Inference
    print("\n[Vector 2: Area Code Geo-Inference across US Metros]")
    phone_tests = [
        ("(212) 555-0199", "NY", "New York, NY"),
        ("312-555-4321", "IL", "Chicago, IL"),
        ("+1 (415) 888-0000", "CA", "San Francisco, CA"),
        ("512.555.7890", "TX", "Austin, TX"),
        ("2065551234", "WA", "Seattle, WA"),
        ("617-555-9876", "MA", "Boston, MA"),
        ("404-555-1122", "GA", "Atlanta, GA"),
        ("303-555-3344", "CO", "Denver, CO"),
        ("704-555-5566", "NC", "Charlotte, NC"),
        ("602-555-7788", "AZ", "Phoenix, AZ"),
    ]
    for phone, exp_state, exp_city in phone_tests:
        ac = extract_area_code_from_phone(phone)
        assert ac in AREA_CODE_MAP, f"Area code {ac} missing"
        state, city = AREA_CODE_MAP[ac]
        assert state == exp_state, f"State mismatch: {state} != {exp_state}"
        assert city == exp_city, f"City mismatch: {city} != {exp_city}"
        print(f"  [PASS] Phone: {phone:20} -> AC: {ac:4} -> State: {state:3} -> City: {city}")

    # 3. Specialization Taxonomy & Phrase Precedence
    print("\n[Vector 3: Specialization Taxonomy & Phrase Precedence]")
    title_tests = [
        ("Principal Technical Recruiter", "Information Technology"),
        ("Senior Software Talent Partner", "Information Technology"),
        ("Full Stack IT Sourcing Lead", "Information Technology"),
        ("Travel Nurse Sourcing Specialist", "Healthcare & Nursing"),
        ("Clinical Healthcare Recruiter", "Healthcare & Nursing"),
        ("Finance & Accounting Headhunter", "Finance & Accounting"),
        ("Aerospace & Mechanical Engineering Recruiter", "Engineering & Manufacturing"),
        ("Executive Search Director", "Executive & Leadership"),
        ("Chief Executive Officer", "Executive & Leadership"),
        ("Vice President of Talent Acquisition", "Human Resources"),
        ("Legal Counsel & Compliance Recruiter", "Legal & Compliance"),
    ]
    for title, exp_spec in title_tests:
        spec = infer_specialization(title)
        assert spec == exp_spec, f"Spec failed for '{title}': got '{spec}', expected '{exp_spec}'"
        print(f"  [PASS] Title: {title:46} -> Spec: {spec}")

    # 4. Multi-Field JIT Record Enrichment
    print("\n[Vector 4: Composite JIT Record Mutation]")
    raw_record = {
        "recruiter_id": 99999001,
        "recruiter_name": "Marcus Vance",
        "email": "m.vance@bridgecrossllc.com",
        "phone": "(312) 800-4491",
        "title": "Principal Technical Recruiter",
        "company_id": None,
        "state": None,
        "location": None,
        "specialization": None
    }
    enriched_output = enrichment_engine.enrich_single_recruiter(raw_record)
    assert enriched_output["company_id"] == "BridgeCross LLC"
    assert enriched_output["state"] == "IL"
    assert enriched_output["location"] == "Chicago, IL"
    assert enriched_output["specialization"] == "Information Technology"
    print(f"  [PASS] Composite JIT Output: {json.dumps(enriched_output, indent=2)}")
    print("\n>>> CHECK 1 PASSED WITH 100% ACCURACY <<<")


def run_check_2_daemon_lifecycle_and_batch_execution():
    print("\n" + "="*70)
    print("=== [CHECK 2 / 3]: DAEMON LIFECYCLE, CONCURRENCY & BATCH RUNNER ===")
    print("="*70)

    # 1. Start Daemon
    print("\n[2.1: Starting Enrichment Daemon]")
    res_start = enrichment_engine.start()
    print("  -> Daemon Start Response:", res_start)
    assert res_start["state"]["status"] == "running"
    time.sleep(3)

    # 2. Check Live State & Telemetry
    print("\n[2.2: Live State & Progress Inspection]")
    state = enrichment_engine.get_status()
    print(f"  -> State: status={state.get('status')} | processed={state.get('records_processed')} | success={state.get('success_count')} | phase={state.get('current_phase')}")
    assert state.get("status") == "running"

    # 3. Pause Daemon
    print("\n[2.3: Pausing Daemon]")
    res_pause = enrichment_engine.pause()
    print("  -> Daemon Pause Response:", res_pause)
    assert res_pause["state"]["status"] == "paused"
    time.sleep(1)

    # 4. Resume Daemon
    print("\n[2.4: Resuming Daemon]")
    res_resume = enrichment_engine.resume()
    print("  -> Daemon Resume Response:", res_resume)
    assert res_resume["state"]["status"] == "running"
    time.sleep(2)

    # 5. Stop Daemon
    print("\n[2.5: Stopping Daemon]")
    res_stop = enrichment_engine.stop()
    print("  -> Daemon Stop Response:", res_stop)
    assert res_stop["state"]["status"] == "stopped"

    # 6. Verify DuckDB / Parquet Record Store Integrity
    print("\n[2.6: Verifying RecruiterStore Query Integrity]")
    recruiter_store._ensure_loaded()
    cur = recruiter_store._conn.cursor()
    total_count = cur.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0]
    print(f"  -> Total Recruiter Count Verified in DuckDB: {total_count:,} records")
    assert total_count >= 2300000

    print("\n>>> CHECK 2 PASSED WITH 100% RELIABILITY <<<")


def run_check_3_api_and_live_telemetry():
    print("\n" + "="*70)
    print("=== [CHECK 3 / 3]: HTTP API ENDPOINTS & LIVE TELEMETRY STREAMING ===")
    print("="*70)

    base_url = "http://localhost:8000"

    # 1. Test /system/enricher/status
    print("\n[3.1: GET /system/enricher/status]")
    r_status = requests.get(f"{base_url}/system/enricher/status")
    print(f"  -> Status Code: {r_status.status_code}")
    print(f"  -> Payload: {r_status.json()}")
    assert r_status.status_code == 200
    assert "status" in r_status.json()

    # 2. Test /system/enricher/control
    print("\n[3.2: POST /system/enricher/control (start -> pause -> stop)]")
    r_ctrl_start = requests.post(f"{base_url}/system/enricher/control", json={"action": "start"})
    print(f"  -> Start: {r_ctrl_start.status_code} - {r_ctrl_start.json().get('message')}")
    assert r_ctrl_start.status_code == 200
    time.sleep(2)

    r_ctrl_pause = requests.post(f"{base_url}/system/enricher/control", json={"action": "pause"})
    print(f"  -> Pause: {r_ctrl_pause.status_code} - {r_ctrl_pause.json().get('message')}")
    assert r_ctrl_pause.status_code == 200
    time.sleep(1)

    r_ctrl_stop = requests.post(f"{base_url}/system/enricher/control", json={"action": "stop"})
    print(f"  -> Stop: {r_ctrl_stop.status_code} - {r_ctrl_stop.json().get('message')}")
    assert r_ctrl_stop.status_code == 200

    # 3. Test Live Enrichment Feed
    print("\n[3.3: In-Memory Ring Buffer & Live Feed Events]")
    enrichment_engine._record_feed_event(
        rec_name="Jane Doe",
        company="BridgeCross LLC",
        title="Senior Technical Recruiter",
        location="Chicago, IL",
        phone="(312) 555-0100",
        email="j.doe@bridgecrossllc.com",
        action_type="enriched"
    )
    feed_events = enrichment_engine.get_live_feed()
    print(f"  -> Live Feed Ring Buffer Size: {len(feed_events)} events")
    assert len(feed_events) > 0
    top_event = feed_events[0]
    print(f"  -> Latest Live Event: {top_event['name']} | Company: {top_event['company']} | Location: {top_event['location']} | Time: {top_event['timestamp']}")
    assert top_event["name"] == "Jane Doe"
    assert top_event["company"] == "BridgeCross LLC"

    print("\n>>> CHECK 3 PASSED WITH 100% COMPLIANCE <<<")


if __name__ == "__main__":
    t0 = time.time()
    run_check_1_deterministic_rule_accuracy()
    run_check_2_daemon_lifecycle_and_batch_execution()
    run_check_3_api_and_live_telemetry()
    elapsed = time.time() - t0
    print("\n" + "="*70)
    print(f"=== ALL 3 CHECKS COMPLETED AND VERIFIED IN {elapsed:.2f}s ===")
    print("="*70)
