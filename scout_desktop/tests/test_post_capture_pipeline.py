"""
Comprehensive 3-Check Verification Suite for Post-Capture Processing Pipeline
Tests all 7 layers of extraction, validation, stitching, and gatekeeping.
"""
import sys, os
sys.path.insert(0, r"c:\TalentOpsAI")

def run_all_tests():
    from scout_desktop.extractor.patterns import (
        clean_person_name,
        is_valid_person_name,
        clean_company_name,
        is_valid_company_name,
        classify_semantic_entity,
        CHECKMARK_AND_STATUS_SYMBOLS,
    )
    from scout_desktop.extractor.candidate_gate import create_candidate_if_valid
    from scout_desktop.extractor.cross_channel_stitcher import CrossChannelStitcher
    from scout_desktop.extractor.extraction_engine import ScoutExtractionEngine

    passed = 0
    total = 0

    def assert_eq(desc, actual, expected):
        nonlocal passed, total
        total += 1
        ok = (actual == expected)
        if ok:
            passed += 1
            print(f"  [PASS] {desc}: {actual!r}")
        else:
            print(f"  [FAIL] {desc}: got {actual!r}, expected {expected!r}")
        return ok

    def assert_true(desc, condition):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {desc}")
        else:
            print(f"  [FAIL] {desc}")
        return condition

    print("=" * 70)
    print("TEST SUITE 1: Candidate Name Cleaning & Degree / Bullet Preservation")
    print("=" * 70)

    # 1. Degree suffixes and middle dots (LinkedIn format)
    assert_eq("LinkedIn degree suffix 1st", clean_person_name("Kitab Ali · 1st"), "Kitab Ali")
    assert_eq("LinkedIn degree suffix 2nd bullet", clean_person_name("Daniel Rodis • 2nd"), "Daniel Rodis")
    assert_eq("LinkedIn degree suffix 3rd+", clean_person_name("Kim Fields · 3rd+"), "Kim Fields")
    assert_eq("Middle dot with degree", clean_person_name("Josh Goodner \u00B7 1st"), "Josh Goodner")

    # 2. Abbreviated last initials with period
    assert_eq("Abbreviated initial Brandon R.", clean_person_name("Brandon R."), "Brandon R")
    assert_eq("Abbreviated initial Shannon S.", clean_person_name("Shannon S."), "Shannon S")
    assert_eq("Abbreviated initial Sarah T.", clean_person_name("Sarah T."), "Sarah T")

    # 3. Maiden names and bracketed qualifiers
    assert_eq("Maiden name Michelle Lefebvre (Besler)", clean_person_name("Michelle Lefebvre (Besler)"), "Michelle Lefebvre")
    assert_eq("LinkedIn badge Vashu Sharma (LION)", clean_person_name("Vashu Sharma (LION)"), "Vashu Sharma")

    # 4. Post-nominal professional credentials
    assert_eq("Credentials Jennifer Eversole, CPA, CISSP", clean_person_name("Jennifer Eversole, CPA, CISSP"), "Jennifer Eversole")
    assert_eq("Credentials Kate Threewitts, SPHR, SHRM-SCP", clean_person_name("Kate Threewitts, SPHR, SHRM-SCP"), "Kate Threewitts")
    assert_eq("Credentials Megan Alford, PRC, CIR, CMVR", clean_person_name("Megan Alford, PRC, CIR, CMVR"), "Megan Alford")

    # 5. Negative noise suppression
    assert_eq("Reject full job description", clean_person_name("Full Job Description"), None)
    assert_eq("Reject company with colon", clean_person_name("RGP: People"), None)
    assert_eq("Reject chrome noise", clean_person_name("ask gemini"), None)
    assert_eq("Reject truncated ellipsis", clean_person_name("54 Ri Ht..."), None)
    assert_eq("Reject checkmark status", clean_person_name("\u2713 Open to work"), None)

    print("\n" + "=" * 70)
    print("TEST SUITE 2: Candidate Gate — Sourcing Platform Partial Signals")
    print("=" * 70)

    # Candidate on LinkedIn with title only (URL not read) -> must be REVIEW_REQUIRED, NOT REJECTED_OBSERVATION!
    res1 = create_candidate_if_valid({
        "name": "Kitab Ali",
        "title": "Technical Recruiter",
        "platform": "LINKEDIN",
        "window_title": "Kitab Ali | LinkedIn - Google Chrome"
    })
    assert_eq("LinkedIn title-only decision", res1.decision, "REVIEW_REQUIRED")
    assert_eq("LinkedIn title-only status", res1.status, "REVIEW_REQUIRED")
    assert_eq("LinkedIn title-only name", res1.canonical_name, "Kitab Ali")

    # Candidate on ZoomInfo with company only -> REVIEW_REQUIRED
    res2 = create_candidate_if_valid({
        "name": "Daniel Rodis",
        "company": "Amazon",
        "platform": "ZOOMINFO",
        "window_title": "Daniel Rodis | ZoomInfo"
    })
    assert_eq("ZoomInfo company-only decision", res2.decision, "REVIEW_REQUIRED")

    # Full profile on LinkedIn with URL -> CANDIDATE_VERIFIED
    res3 = create_candidate_if_valid({
        "name": "Sarah Connor",
        "title": "Staff Engineer",
        "company": "Cyberdyne Systems",
        "canonical_profile_url": "https://www.linkedin.com/in/sarah-connor",
        "platform": "LINKEDIN",
        "window_title": "Sarah Connor | LinkedIn - Google Chrome"
    })
    assert_eq("Full LinkedIn candidate decision", res3.decision, "CANDIDATE_VERIFIED")
    assert_eq("Full LinkedIn candidate status", res3.status, "VERIFIED")

    # Non-candidate noise -> REJECTED
    res4 = create_candidate_if_valid({
        "name": "Full Job Description",
        "platform": "LINKEDIN",
    })
    assert_eq("Noise candidate decision", res4.decision, "UNRESOLVED_UI_TEXT")

    print("\n" + "=" * 70)
    print("TEST SUITE 3: Cross-Channel Stitching & Multi-Scroll Continuity")
    print("=" * 70)

    stitcher = CrossChannelStitcher()

    # Frame 1: Top of profile (Name + Title + Company)
    f1 = {
        "recruiter_name": "Elyse Thomas",
        "title": "Senior Talent Acquisition Specialist",
        "company_name": "HealthPeak",
        "location": "Denver, CO",
    }
    p1 = stitcher.stitch_observation(f1, channel="LINKEDIN")
    assert_eq("Stitcher Frame 1 name", p1.canonical_name, "Elyse Thomas")
    assert_eq("Stitcher Frame 1 company", p1.current_company, "HealthPeak")
    assert_eq("Stitcher Frame 1 title", p1.current_title, "Senior Talent Acquisition Specialist")

    # Frame 2: User scrolled down to skills (Header out of view; only Name + Skills available)
    f2 = {
        "recruiter_name": "Elyse Thomas",
        "metadata_json": {"skills": ["Technical Recruiting", "Sourcing", "Executive Search"]}
    }
    p2 = stitcher.stitch_observation(f2, channel="LINKEDIN")
    assert_eq("Stitcher Frame 2 resolved to same entity", p2.entity_id, p1.entity_id)
    assert_eq("Stitcher Frame 2 preserved company", p2.current_company, "HealthPeak")
    assert_eq("Stitcher Frame 2 preserved title", p2.current_title, "Senior Talent Acquisition Specialist")
    assert_true("Stitcher Frame 2 observations accumulated", p2.observations_count >= 2)

    print("\n" + "=" * 70)
    print("TEST SUITE 4: End-to-End Extraction Engine Pipeline")
    print("=" * 70)

    engine = ScoutExtractionEngine()
    lines = [
        "Kitab Ali",
        "Senior Technical Recruiter at Amazon",
        "Seattle, Washington, United States",
        "Experience",
        "Amazon",
        "Senior Technical Recruiter",
        "Jan 2021 - Present",
    ]
    candidates, telemetry = engine.process_frame(
        img=None,
        delta=0.25,
        ocr_lines=lines,
        window_title="Kitab Ali | LinkedIn - Google Chrome",
        source_url="https://www.linkedin.com/in/kitab-ali",
        platform="LINKEDIN",
        capture_id="VC-TEST01",
        force_process=True,
    )
    assert_eq("Candidates count", len(candidates), 1)
    if candidates:
        c = candidates[0]
        assert_eq("Extracted name", c.canonical_name, "Kitab Ali")
        assert_eq("Extracted title", c.current_title, "Senior Technical Recruiter")
        assert_eq("Extracted company", c.current_company, "Amazon")
        assert_true("Extracted profile url", "linkedin.com/in/kitab-ali" in (c.canonical_profile_url or ""))

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("=" * 70)
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
