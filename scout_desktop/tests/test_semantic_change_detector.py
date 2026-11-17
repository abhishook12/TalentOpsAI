from scout_desktop.core.change_detector import ChangeDetector, ChangeOperation, DeltaPriority


def test_aliases_are_normalized_into_one_profile_delta():
    detector = ChangeDetector()
    first = detector.evaluate_entity({
        "recruiter_name": "Ada Lovelace",
        "company_name": "Analytical Engines",
        "raw_title": "Principal Engineer",
        "linkedin_url": "https://www.linkedin.com/in/ada-lovelace/",
        "entity_type": "PERSON",
    })
    repeated = detector.evaluate_entity({
        "canonical_name": "Ada Lovelace",
        "current_company": "Analytical Engines",
        "title": "Principal Engineer",
        "canonical_profile_url": "https://www.linkedin.com/in/ada-lovelace/",
        "entity_type": "PERSON",
    })
    assert first.operation == ChangeOperation.INSERT
    assert repeated.operation == ChangeOperation.IGNORE


def test_education_and_skills_are_valuable_enrichment_not_noise():
    detector = ChangeDetector()
    detector.evaluate_entity({"recruiter_name": "Ada Lovelace", "company_name": "Analytical Engines"})
    result = detector.evaluate_entity({
        "recruiter_name": "Ada Lovelace",
        "company_name": "Analytical Engines",
        "education": "University College Cork",
        "skills": ["Recruiting", "ERP"],
    })
    assert result.operation == ChangeOperation.UPDATE
    assert "education" in result.changed_fields
    assert "skills" in result.changed_fields
    assert result.priority == DeltaPriority.MEDIUM
