"""
tests/test_profile_archetypes.py — Multi-Archetype Extraction Invariance Test Suite

Guarantees that Scout Desktop never regresses or produces garbled/synthetic field
mismatches across 12 diverse real-world profile variations.
"""
import pytest
from scout_desktop.extractor.extraction_engine import ScoutExtractionEngine
from scout_desktop.extractor.candidate_gate import create_candidate_if_valid

ARCHETYPES = [
    {
        "id": "ARCH-01",
        "name": "Tom Shearman (Title-only headline, company on right card, bullet location)",
        "lines": [
            "Tom Shearman",
            "Staffing Advisor",
            "Wicrosoft",
            "University of California, Davis",
            "New York, United States \u00b7 Contact info",
            "Connect", "Message", "More",
        ],
        "url": "https://www.linkedin.com/in/tom-shearman/",
        "window": "Tom Shearman | LinkedIn",
        "expected_name": "Tom Shearman",
        "expected_title": "Staffing Advisor",
        "expected_company": "Wicrosoft",
        "expected_location": "New York, United States",
    },
    {
        "id": "ARCH-02",
        "name": "Standard inline 'Title at Company'",
        "lines": [
            "Rachel Green",
            "Senior Technical Recruiter at Amazon",
            "Seattle, Washington, United States \u00b7 Contact info",
            "500+ connections",
        ],
        "url": "https://www.linkedin.com/in/rachel-green/",
        "window": "Rachel Green | LinkedIn",
        "expected_name": "Rachel Green",
        "expected_title": "Senior Technical Recruiter",
        "expected_company": "Amazon",
        "expected_location": "Seattle, Washington, United States",
    },
    {
        "id": "ARCH-03",
        "name": "Degree badge, pronouns, and @ company syntax",
        "lines": [
            "Sarah Jenkins (She/Her) \u00b7 2nd",
            "Lead Talent Partner @ Figma",
            "San Francisco Bay Area \u00b7 Contact info",
            "Connect",
        ],
        "url": "https://www.linkedin.com/in/sarah-jenkins/",
        "window": "Sarah Jenkins (She/Her) | LinkedIn",
        "expected_name": "Sarah Jenkins",
        "expected_title": "Lead Talent Partner",
        "expected_company": "Figma",
        "expected_location": "San Francisco Bay Area",
    },
    {
        "id": "ARCH-04",
        "name": "Multi-line pipe headline with ex-companies",
        "lines": [
            "Alex Rivera",
            "Talent Acquisition Leader | Scaling Engineering Teams | ex-Google",
            "Stripe",
            "Austin, Texas, United States \u00b7 Contact info",
        ],
        "url": "https://www.linkedin.com/in/alex-rivera/",
        "window": "Alex Rivera | LinkedIn",
        "expected_name": "Alex Rivera",
        "expected_title": "Talent Acquisition Leader",
        "expected_company": "Stripe",
        "expected_location": "Austin, Texas, United States",
    },
    {
        "id": "ARCH-05",
        "name": "International location (India) with at Company",
        "lines": [
            "Deepak Sharma \u00b7 1st",
            "Principal Recruiter at Microsoft",
            "Bengaluru, Karnataka, India \u00b7 Contact info",
        ],
        "url": "https://www.linkedin.com/in/deepak-sharma/",
        "window": "Deepak Sharma | LinkedIn",
        "expected_name": "Deepak Sharma",
        "expected_title": "Principal Recruiter",
        "expected_company": "Microsoft",
        "expected_location": "Bengaluru, Karnataka, India",
    },
    {
        "id": "ARCH-06",
        "name": "European layout with company on right card",
        "lines": [
            "Helena M\u00fcller",
            "Senior Executive Search Consultant",
            "Siemens",
            "Munich, Bavaria, Germany \u00b7 Contact info",
        ],
        "url": "https://www.linkedin.com/in/helena-muller/",
        "window": "Helena M\u00fcller | LinkedIn",
        "expected_name": "Helena M\u00fcller",
        "expected_title": "Senior Executive Search Consultant",
        "expected_company": "Siemens",
        "expected_location": "Munich, Bavaria, Germany",
    },
    {
        "id": "ARCH-07",
        "name": "Modern startup company on right card",
        "lines": [
            "Marcus Chen",
            "Founding Recruiter",
            "Linear",
            "New York City Metropolitan Area \u00b7 Contact info",
        ],
        "url": "https://www.linkedin.com/in/marcus-chen/",
        "window": "Marcus Chen | LinkedIn",
        "expected_name": "Marcus Chen",
        "expected_title": "Founding Recruiter",
        "expected_company": "Linear",
        "expected_location": "New York City Metropolitan Area",
    },
    {
        "id": "ARCH-08",
        "name": "Headline with pipe separator to company",
        "lines": [
            "Jessica Taylor",
            "Director of Talent | Datadog",
            "Boston, MA \u00b7 Contact info",
        ],
        "url": "https://www.linkedin.com/in/jessica-taylor/",
        "window": "Jessica Taylor | LinkedIn",
        "expected_name": "Jessica Taylor",
        "expected_title": "Director of Talent",
        "expected_company": "Datadog",
        "expected_location": "Boston, MA",
    },
    {
        "id": "ARCH-09",
        "name": "Profile with company in Experience section",
        "lines": [
            "David Kim",
            "Technical Recruiter",
            "Chicago, Illinois, United States \u00b7 Contact info",
            "Experience",
            "Meta",
            "Technical Recruiter",
            "2022 - Present",
        ],
        "url": "https://www.linkedin.com/in/david-kim/",
        "window": "David Kim | LinkedIn",
        "expected_name": "David Kim",
        "expected_title": "Technical Recruiter",
        "expected_company": "Meta",
        "expected_location": "Chicago, Illinois, United States",
    },
    {
        "id": "ARCH-10",
        "name": "Certifications in name suffix",
        "lines": [
            "Emily Watson, SHRM-CP",
            "HR & Talent Acquisition Specialist at Dell Technologies",
            "Round Rock, Texas \u00b7 Contact info",
        ],
        "url": "https://www.linkedin.com/in/emily-watson/",
        "window": "Emily Watson, SHRM-CP | LinkedIn",
        "expected_name": "Emily Watson",
        "expected_title": "HR & Talent Acquisition Specialist",
        "expected_company": "Dell Technologies",
        "expected_location": "Round Rock, Texas",
    },
    {
        "id": "ARCH-11",
        "name": "UK format with Greater Area",
        "lines": [
            "Jordan Vance",
            "Global Sourcing Lead at Spotify",
            "Greater London, England, United Kingdom \u00b7 Contact info",
        ],
        "url": "https://www.linkedin.com/in/jordan-vance/",
        "window": "Jordan Vance | LinkedIn",
        "expected_name": "Jordan Vance",
        "expected_title": "Global Sourcing Lead",
        "expected_company": "Spotify",
        "expected_location": "Greater London, England, United Kingdom",
    },
    {
        "id": "ARCH-12",
        "name": "Fintech startup on card, Consultant title",
        "lines": [
            "Oliver Wright",
            "Staffing Consultant",
            "Revolut",
            "London Area, United Kingdom \u00b7 Contact info",
        ],
        "url": "https://www.linkedin.com/in/oliver-wright/",
        "window": "Oliver Wright | LinkedIn",
        "expected_name": "Oliver Wright",
        "expected_title": "Staffing Consultant",
        "expected_company": "Revolut",
        "expected_location": "London Area, United Kingdom",
    },
]

@pytest.mark.parametrize("arch", ARCHETYPES, ids=[a["id"] for a in ARCHETYPES])
def test_profile_archetype_extraction(arch):
    engine = ScoutExtractionEngine()
    cands, telemetry = engine.process_frame(
        img=None,
        delta=1.0,
        ocr_lines=arch["lines"],
        window_title=arch["window"],
        source_url=arch["url"],
        platform="LinkedIn",
        capture_id=f"cap-{arch['id'].lower()}",
        force_process=True,
    )

    assert len(cands) >= 1, f"No candidate extracted for {arch['id']}: {telemetry}"
    c = cands[0]

    gate_res = create_candidate_if_valid({
        "name": c.canonical_name,
        "title": c.current_title,
        "company": c.current_company,
        "location": c.location,
        "platform": "LinkedIn",
        "source_url": arch["url"],
        "window_title": arch["window"],
    })
    d = gate_res.to_dict()

    assert d["is_valid_candidate"] is True, f"Candidate rejected by gate: {gate_res.reasons}"
    assert d["canonical_name"] == arch["expected_name"], f"Name mismatch: expected {arch['expected_name']}, got {d['canonical_name']}"
    if arch["expected_title"]:
        assert arch["expected_title"].lower() in (d["title"] or "").lower(), f"Title mismatch: expected {arch['expected_title']}, got {d['title']}"
    if arch["expected_company"]:
        assert arch["expected_company"].lower() in (d["company"] or "").lower(), f"Company mismatch: expected {arch['expected_company']}, got {d['company']}"
    if arch["expected_location"]:
        assert arch["expected_location"].lower() in (d["location"] or "").lower(), f"Location mismatch: expected {arch['expected_location']}, got {d['location']}"
    assert d["status"] == "VERIFIED", f"Expected VERIFIED, got {d['status']}"
