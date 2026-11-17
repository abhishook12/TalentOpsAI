from scout_desktop.extractor.capture_intelligence_router import (
    CaptureIntelligenceRouter,
    ROUTE_COMPANY,
    ROUTE_DROP,
    ROUTE_JOB,
    ROUTE_PERSON,
    ROUTE_REVIEW,
)


def test_routes_person_to_profile_intelligence():
    result = CaptureIntelligenceRouter.decide({"entity_type": "PERSON", "recruiter_name": "Ada Lovelace", "quality_score": 90})
    assert result.route == ROUTE_PERSON
    assert "matching" in result.destinations


def test_routes_company_without_creating_person_data():
    result = CaptureIntelligenceRouter.decide({"entity_type": "COMPANY", "company_name": "Example Systems", "quality_score": 88})
    assert result.route == ROUTE_COMPANY
    assert "company_intelligence" in result.destinations


def test_routes_job_to_demand_intelligence():
    result = CaptureIntelligenceRouter.decide({"entity_type": "JOB_POSTING", "title": "Senior Data Engineer", "company_name": "Example Systems"})
    assert result.route == ROUTE_JOB
    assert "hiring_signals" in result.destinations


def test_holds_contact_fragment_for_review_and_drops_noise():
    review = CaptureIntelligenceRouter.decide({"entity_type": "CONTACT_INFO", "company_name": "Example Systems"})
    noise = CaptureIntelligenceRouter.decide({"entity_type": "NOISE"})
    assert review.route == ROUTE_REVIEW
    assert noise.route == ROUTE_DROP
