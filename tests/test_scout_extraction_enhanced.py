"""
tests/test_scout_extraction_enhanced.py — Verification Check 1 for Scout Desktop Extraction Improvements

Verifies:
1. Rejection of checkmarks and qualification checklist items (Driver's License, Travel✓, etc.) as candidate names.
2. Rejection of browser chrome noise (All Bookmarks, Bookmarks Bar, New Tab, etc.) as companies.
3. Clean decomposition and noise stripping of job titles (Business Analyst - Edw -... -> Business Analyst).
4. Candidate gate rejection of bogus names with UNRESOLVED_UI_TEXT.
5. Calibrated dynamic confidence scoring across all fields.
"""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
sys.path.insert(0, r"c:\TalentOpsAI")

from scout_desktop.extractor.patterns import (
    clean_person_name,
    is_valid_person_name,
    clean_company_name,
    is_valid_company_name,
    clean_job_title,
    is_plausible_title,
    classify_semantic_entity,
    BROWSER_CHROME_NOISE,
    QUALIFICATION_AND_REQUIREMENT_WORDS,
)
from scout_desktop.extractor.candidate_gate import create_candidate_if_valid
from scout_desktop.extractor.layout_detector import LayoutDetector
from scout_desktop.extractor.field_classifier import FieldClassifier


def test_qualification_rejection():
    print("--- Test 1: Qualification & Checkmark Rejection ---")
    bogus_names = [
        "Driver's License Travel✓",
        "Driver's License",
        "Travel✓",
        "Travel",
        "Valid Driver's License",
        "Security Clearance",
        "Work Authorization",
        "US Citizen",
        "Background Check",
        "Drug Screen",
        "Willing to Travel",
        "Travel 100%",
        "Notice Period",
        "Immediate Joiner",
    ]
    for b in bogus_names:
        c_name = clean_person_name(b)
        is_valid = is_valid_person_name(b)
        se = classify_semantic_entity(b)
        print(f"  Testing bogus candidate name '{b}': clean='{c_name}', is_valid={is_valid}, entity_type='{se.get('entity_type')}'")
        assert c_name is None, f"Expected clean_person_name to reject '{b}', got '{c_name}'"
        assert not is_valid, f"Expected is_valid_person_name to reject '{b}'"
        assert se.get("entity_type") != "PERSON", f"Expected classify_semantic_entity to not classify '{b}' as PERSON"
    print("  ✓ All qualification and checkmark items successfully rejected!")


def test_browser_chrome_rejection():
    print("\n--- Test 2: Browser Chrome & Bookmarks Noise Rejection ---")
    chrome_noise = [
        "All Bookmarks",
        "Bookmarks",
        "Bookmarks Bar",
        "Other Bookmarks",
        "Reading List",
        "Search Tabs",
        "Tab Groups",
        "New Tab",
        "Extensions",
        "Manage Extensions",
        "Chrome Web Store",
        "Downloads",
        "Settings",
        "Ask Gemini",
    ]
    for c in chrome_noise:
        c_comp = clean_company_name(c)
        is_valid = is_valid_company_name(c)
        se = classify_semantic_entity(c)
        print(f"  Testing chrome noise '{c}': clean='{c_comp}', is_valid={is_valid}, entity_type='{se.get('entity_type')}'")
        assert c_comp is None, f"Expected clean_company_name to reject '{c}', got '{c_comp}'"
        assert not is_valid, f"Expected is_valid_company_name to reject '{c}'"
        assert se.get("entity_type") != "COMPANY", f"Expected classify_semantic_entity to not classify '{c}' as COMPANY"
    print("  ✓ All browser chrome and bookmark elements successfully rejected!")


def test_title_cleaning():
    print("\n--- Test 3: Job Title Cleaning & Noise Stripping ---")
    noisy_titles = [
        ("Business Analyst - Edw -...", "Business Analyst"),
        ("Business Analyst - Edw -", "Business Analyst"),
        ("Senior Software Engineer • 1st", "Senior Software Engineer"),
        ("Recruiter (he/him)", "Recruiter"),
        ("1. Staff Product Designer...", "Staff Product Designer"),
        ("Data Engineer - sud", "Data Engineer"),
    ]
    for raw, expected in noisy_titles:
        cleaned = clean_job_title(raw)
        print(f"  Testing title cleaning: '{raw}' -> '{cleaned}' (expected: '{expected}')")
        assert cleaned == expected, f"Expected '{expected}', got '{cleaned}'"
        assert is_plausible_title(cleaned), f"Expected '{cleaned}' to be plausible title"
    print("  ✓ All noisy job titles successfully cleaned!")


def test_genuine_candidates():
    print("\n--- Test 4: Genuine Candidate Recognition & Calibrated Confidences ---")
    genuine_people = [
        "Ritik Sharma",
        "Sarah Jenkins",
        "Michael O'Connor",
        "David A. Sinclair",
        "Abhishek Jadon",
    ]
    for p in genuine_people:
        c_name = clean_person_name(p)
        is_valid = is_valid_person_name(p)
        se = classify_semantic_entity(p)
        print(f"  Testing genuine candidate '{p}': clean='{c_name}', is_valid={is_valid}, entity_type='{se.get('entity_type')}'")
        assert c_name == p, f"Expected clean_person_name to preserve '{p}', got '{c_name}'"
        assert is_valid, f"Expected is_valid_person_name to accept '{p}'"
        assert se.get("entity_type") == "PERSON", f"Expected classify_semantic_entity to classify '{p}' as PERSON"
    print("  ✓ Genuine candidates recognized with 100% accuracy!")


def test_candidate_gate_behavior():
    print("\n--- Test 5: Candidate Creation Gate Gating & Calibration ---")
    # Case A: User's reported screenshot bug — bogus name & chrome company
    res_bug = create_candidate_if_valid({
        "name": "Driver's License Travel✓",
        "company": "All Bookmarks",
        "title": "Business Analyst - Edw -...",
        "location": "Dallas, TX",
    })
    print(f"  Bug scenario result: decision='{res_bug.decision}', is_valid={res_bug.is_valid_candidate}")
    assert res_bug.decision == "UNRESOLVED_UI_TEXT", f"Expected UNRESOLVED_UI_TEXT, got {res_bug.decision}"
    assert not res_bug.is_valid_candidate, "Bogus candidate must NOT be valid"

    # Case B: Real candidate with genuine profile
    res_real = create_candidate_if_valid({
        "name": "Sarah Jenkins",
        "title": "Senior Technical Recruiter",
        "company": "Amazon Web Services",
        "location": "Dallas, TX",
        "canonical_profile_url": "https://www.linkedin.com/in/sarah-jenkins-tech",
    }, context={
        "window_title": "Sarah Jenkins | LinkedIn - Google Chrome",
        "source_url": "https://www.linkedin.com/in/sarah-jenkins-tech",
    })
    print(f"  Genuine candidate result: decision='{res_real.decision}', status='{res_real.status}', conf={res_real.identity_confidence}")
    print(f"    Field confidences: {res_real.field_confidence}")
    assert res_real.decision == "CANDIDATE_VERIFIED", f"Expected CANDIDATE_VERIFIED, got {res_real.decision}"
    assert res_real.field_confidence["name"] >= 0.95, "Corroborated name should have high confidence"
    assert res_real.field_confidence["company"] >= 0.90, "Amazon Web Services should have high confidence"
    assert res_real.field_confidence["title"] >= 0.88, "Senior Technical Recruiter should have high confidence"
    assert res_real.field_confidence["location"] >= 0.90, "Dallas, TX should have high confidence"
    print("  ✓ Candidate gate correctly rejected bogus observation and verified genuine candidate!")


if __name__ == "__main__":
    test_qualification_rejection()
    test_browser_chrome_rejection()
    test_title_cleaning()
    test_genuine_candidates()
    test_candidate_gate_behavior()
    print("\n✅ ALL EXTRACTION UNIT TESTS PASSED SUCCESSFULLY!")
