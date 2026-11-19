from __future__ import annotations

import json
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scout_desktop.core.context_memory import ContextMemory
from scout_desktop.extractor.parsers import parse_with_modular_parsers
from scout_desktop.extractor.candidate_gate import create_candidate_if_valid
from backend.app.models.models import Company, Recruiter
from backend.app.models.staging_models import DiscoveryStaging
from backend.app.services import ingestion_funnel


def test_benchmark_anjan_chowdhury_extraction():
    """
    Benchmark 1: Anjan Chowdhury
    Expected: Sr. Engineering Manager, Myntra, Bengaluru, India, St. Thomas' College of Engineering & Technology.
    Karnataka limitation: Karnataka was visible in the raw screenshot but is not captured in the location string.
    """
    ocr_lines = [
        "Anjan Chowdhury · 2nd",
        "Sr. Engineering Manager @ Myntra | Ex-Ola | Goomo",
        "Bengaluru, India   Contact info",
        "Myntra",
        "St. Thomas' College of Engineering & Technology",
        "About",
        "Engineering leader with 14+ years experience building scalable systems.",
    ]
    ctx = {
        "source_url": "https://www.linkedin.com/in/anjan-chowdhury/",
        "window_title": "Anjan Chowdhury | LinkedIn",
        "platform": "LinkedIn",
    }
    parsed = parse_with_modular_parsers("\n".join(ocr_lines), ctx)
    assert parsed is not None
    assert parsed["recruiter_name"] == "Anjan Chowdhury"
    assert parsed["title"] == "Sr. Engineering Manager"
    assert parsed["company_name"] == "Myntra"
    assert "Bengaluru, India" in parsed["location"]
    # Explicit limitation verification: Karnataka was missed by the OCR layout parser
    assert "Karnataka" not in parsed["location"]
    assert parsed["education"] == "St. Thomas' College of Engineering & Technology"


def test_benchmark_katie_malone_extraction():
    """
    Benchmark 2: Katie Malone
    Expected: Principal Technology Consultant, Morgan McKinley, Cork, County Cork, Ireland, University College Cork.
    """
    ocr_lines = [
        "Katie Malone · 2nd",
        "Principal Technology Consultant | ERP / MES / PLM",
        "Cork, County Cork, Ireland   Contact info",
        "Morgan McKinley",
        "University College Cork",
        "About",
        "Recruitment consultant specializing in ERP and life sciences.",
    ]
    ctx = {
        "source_url": "https://www.linkedin.com/in/katie-malone-049410189/",
        "window_title": "Katie Malone | LinkedIn",
        "platform": "LinkedIn",
    }
    parsed = parse_with_modular_parsers("\n".join(ocr_lines), ctx)
    assert parsed is not None
    assert parsed["recruiter_name"] == "Katie Malone"
    assert parsed["title"] == "Principal Technology Consultant"
    assert parsed["company_name"] == "Morgan McKinley"
    assert parsed["location"] == "Cork, County Cork, Ireland"
    assert parsed["education"] == "University College Cork"


def test_benchmark_chandana_shree_p_extraction():
    """
    Benchmark 3: Chandana Shree P
    Expected: HR Operations Professional, Myntra, Bengaluru, India. No college was visible.
    Karnataka limitation: Karnataka was missed.
    """
    ocr_lines = [
        "Chandana Shree P · 2nd",
        "HR Operations Professional @ Myntra",
        "Bengaluru, India   Contact info",
        "Myntra",
        "About",
        "Human Resources professional specializing in people operations and onboarding.",
    ]
    ctx = {
        "source_url": "https://www.linkedin.com/in/chandana-shree-p/",
        "window_title": "Chandana Shree P | LinkedIn",
        "platform": "LinkedIn",
    }
    parsed = parse_with_modular_parsers("\n".join(ocr_lines), ctx)
    assert parsed is not None
    assert parsed["recruiter_name"] == "Chandana Shree P"
    assert parsed["title"] == "HR Operations Professional"
    assert parsed["company_name"] == "Myntra"
    assert "Bengaluru, India" in parsed["location"]
    assert "Karnataka" not in parsed["location"]
    assert parsed.get("education") is None


def test_rapid_profile_switch_prevents_field_cross_contamination():
    """
    When switching rapidly between two profiles, fields from the first profile
    must never be inherited by the second profile.
    """
    memory = ContextMemory()

    # Step 1: User views Profile A (Anjan Chowdhury)
    url_a = "https://www.linkedin.com/in/anjan-chowdhury/"
    memory.update_page_context("PERSON_PROFILE", url_a, "LINKEDIN")
    ent_a = memory.register_entity("ent-a", "PERSON", "Anjan Chowdhury", url_a)
    memory.update_entity_field(ent_a.entity_id, "HAS_TITLE", "Sr. Engineering Manager", "HAS_TITLE")
    memory.update_entity_field(ent_a.entity_id, "WORKS_AT", "Myntra", "WORKS_AT")
    memory.update_entity_field(ent_a.entity_id, "STUDIED_AT", "St. Thomas' College of Engineering & Technology", "STUDIED_AT")

    staged_a = memory.enrich_staged_profile(ent_a.entity_id, {"recruiter_name": "Anjan Chowdhury"})
    assert staged_a["title"] == "Sr. Engineering Manager"
    assert staged_a["education"] == "St. Thomas' College of Engineering & Technology"

    # Step 2: Rapid switch to Profile B (Katie Malone)
    url_b = "https://www.linkedin.com/in/katie-malone-049410189/"
    memory.update_page_context("PERSON_PROFILE", url_b, "LINKEDIN")
    ent_b = memory.register_entity("ent-b", "PERSON", "Katie Malone", url_b)

    # Profile B must start with zero fields inherited from Profile A
    assert not ent_b.known_fields
    staged_b = memory.enrich_staged_profile(ent_b.entity_id, {"recruiter_name": "Katie Malone"})
    assert staged_b.get("title") is None
    assert staged_b.get("company_name") is None
    assert staged_b.get("education") is None

    # Adding Profile B's own fields
    memory.update_entity_field(ent_b.entity_id, "HAS_TITLE", "Principal Technology Consultant", "HAS_TITLE")
    memory.update_entity_field(ent_b.entity_id, "WORKS_AT", "Morgan McKinley", "WORKS_AT")
    staged_b_updated = memory.enrich_staged_profile(ent_b.entity_id, {"recruiter_name": "Katie Malone"})
    assert staged_b_updated["company_name"] == "Morgan McKinley"
    assert staged_b_updated.get("education") is None  # Does NOT inherit St. Thomas' College!


def test_non_person_job_listing_and_interface_labels_rejection():
    """
    Test job listings, company page headers, and UI placeholder labels are strictly rejected
    and do not become a candidate's employer, title, or location.
    """
    # 1. Job search heading as title & "Remote" as location
    res1 = create_candidate_if_valid({
        "name": "Jane Doe",
        "title": "Software Engineer Remote Jobs",
        "company": "Our Team - Acme Corp",
        "location": "Remote",
        "canonical_profile_url": "https://www.linkedin.com/in/janedoe/",
        "platform": "LinkedIn",
    })
    assert res1.company is None
    assert res1.location is None
    assert res1.title is None

    # 2. Interface labels rejection ("Company", "Job Title", "Select Region")
    res2 = create_candidate_if_valid({
        "name": "Jane Doe",
        "title": "Job Title",
        "company": "Company Name",
        "location": "Select Region",
        "canonical_profile_url": "https://www.linkedin.com/in/janedoe/",
        "platform": "LinkedIn",
    })
    assert res2.company is None
    assert res2.location is None
    assert res2.title is None


def test_sync_to_database_and_evidence_read_back(monkeypatch):
    """
    Full end-to-end sync verification: Staged record promotes into master Recruiter DB.
    Verifies that name, title, employer, location, education, and source provenance
    are faithfully persisted and read back.
    """
    engine = create_engine("sqlite://")
    Company.__table__.create(engine)
    Recruiter.__table__.create(engine)
    monkeypatch.setattr(ingestion_funnel.smtp_prober, "probe_mailbox",
                        lambda email: SimpleNamespace(smtp_code=250))
    funnel = ingestion_funnel.UniversalIngestionFunnel()

    staging = DiscoveryStaging(
        raw_name="Katie Malone",
        raw_title="Principal Technology Consultant | ERP / MES / PLM",
        raw_company="Morgan McKinley",
        raw_location="Cork, County Cork, Ireland · Contact info",
        source_url="https://www.linkedin.com/in/katie-malone-049410189/",
        raw_linkedin="https://www.linkedin.com/in/katie-malone-049410189/",
        raw_email="kmalone@morganmckinley.com",
        capture_id="scout-cap-20261119-01",
        source_page_title="Katie Malone | LinkedIn",
        metadata_json=json.dumps({"education": "University College Cork"}),
    )

    with Session(engine) as db:
        res = funnel.process_staging_record(staging, db)
        assert res["status"] == "PROMOTED"
        db.commit()

        saved = db.get(Recruiter, res["recruiter_id"])
        assert saved is not None
        assert saved.recruiter_name == "Katie Malone"
        assert "Principal Technology Consultant" in saved.title
        assert saved.company.company_name == "Morgan McKinley"
        assert saved.location == "Cork, County Cork, Ireland"
        assert saved.email == "kmalone@morganmckinley.com"

        meta = json.loads(saved.metadata_json or "{}")
        assert meta.get("education") == "University College Cork"
        assert "person_field_evidence" in meta
        assert meta["person_field_evidence"]["employer"]["section"] == "company_field"
        assert meta["person_field_evidence"]["location"]["capture_id"] == "scout-cap-20261119-01"


def test_benchmark_bev_wood_extraction():
    """
    Benchmark 4: Bev Wood (live bug regression — v2.14.5 showed Company:'krit', Location:'Not detected')

    Root causes fixed in v2.14.7:
    - 'Followed by Kritika' was bleeding into header; OCR fragment 'krit' became Company.
    - middle-dot '·' in 'South Africa · Contact info' was not recognised as a location separator.
    - 'Temporary Staffing Professionals + 1 more' affiliation pill suffix was not stripped.
    - Name anchor regex did not handle the '3rd' connection-degree badge on the name line.
    - 'South Africa', 'Eastern Cape', 'Port Elizabeth' were absent from GEO_INDICATORS.

    Expected: Bev Wood, Payroll Manager EMEA, Temporary Staffing Professionals,
              Port Elizabeth, Eastern Cape, South Africa.
    """
    ocr_lines = [
        "Bev Wood 3rd",
        "Payroll Manager EMEA | Payroll Manager SA | Global Head of Operations Payroll | EOR | Re-Engineering Payroll Process through Web Development & Innovation",
        "Temporary Staffing Professionals + 1 more",
        "Port Elizabeth, Eastern Cape, South Africa \u00b7 Contact info",
        "302 connections",
        "Followed by Kritika",
        "Message",
        "Follow",
        "About",
        "I am an outgoing person who strives to live a fulfilling life.",
        "Activity",
        "More profiles for you",
    ]
    ctx = {
        "source_url": "https://www.linkedin.com/in/bev-wood-smile/",
        "window_title": "Bev Wood | LinkedIn - Google Chrome",
        "platform": "LinkedIn",
    }
    parsed = parse_with_modular_parsers("\n".join(ocr_lines), ctx)
    assert parsed is not None, "Parser returned None for Bev Wood profile"

    # Name
    assert parsed["recruiter_name"] == "Bev Wood", f"Name: {parsed['recruiter_name']!r}"

    # Title — headline may be truncated at first pipe segment
    assert parsed["title"] is not None, "Title must not be None"
    assert "Payroll Manager" in parsed["title"], f"Title: {parsed['title']!r}"

    # Company — must be the affiliation pill, not noise
    assert parsed["company_name"] == "Temporary Staffing Professionals", \
        f"Company: {parsed['company_name']!r}"
    assert parsed["company_name"] != "krit", "OCR noise 'krit' must never become a company"
    assert "krit" not in (parsed["company_name"] or "").lower(), \
        f"'krit' fragment must not appear in company: {parsed['company_name']!r}"
    assert "Kritika" not in (parsed["company_name"] or ""), \
        f"Social-proof name must not bleed into company: {parsed['company_name']!r}"

    # Location — South African three-part comma format
    assert parsed["location"] == "Port Elizabeth, Eastern Cape, South Africa", \
        f"Location: {parsed['location']!r}"
