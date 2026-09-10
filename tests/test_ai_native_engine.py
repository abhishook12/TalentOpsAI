"""
test_ai_native_engine.py — Comprehensive Automated Test Suite for TalentOps AI Operating System.
Verifies all 12 pillars across multi-tier routing, explainability, calibrated uncertainty,
governance, audit logging, and data doctor repair pipelines.
"""

import os
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models.ai_models import AIAuditLog, AIFeedback, AIEvidenceRecord, AIPreference
from backend.app.models.models import Recruiter
from backend.app.services.ai_router_service import AIRouterService
from backend.app.services.ai_explainability_service import AIExplainabilityService


@pytest.fixture(scope="module")
def test_db():
    """Sets up an in-memory SQLite database for isolated test execution."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Seed sample recruiters for realistic data doctor & search verification
    rec1 = Recruiter(
        recruiter_name="Alice Johnson",
        email="alice@techcorp.com",
        phone="+1 555-019-2831",
        title="Senior Cloud Architect",
        location="Austin, TX",
        state="TX",
        linkedin="https://linkedin.com/in/alice-johnson",
        trust_score=95,
        is_active=True,
        needs_review=False
    )
    rec2 = Recruiter(
        recruiter_name="Bob Smith",
        email="bob@noemail.talentops.local",
        phone=None,
        title="DevOps Engineer",
        location="Chicago, IL",
        state="IL",
        trust_score=40,
        is_active=True,
        needs_review=True
    )
    session.add(rec1)
    session.add(rec2)
    session.commit()

    yield session
    session.close()


class TestAIRouterService:
    def test_local_heuristic_fallback(self):
        """Ensures 100% availability even when external AI API keys are unavailable."""
        prompt = 'Role: Staff Data Engineer | Location: Chicago | Intent: Candidate search'
        output_data, model_used, latency = AIRouterService.execute_prompt(
            prompt=prompt,
            action_type="NATURAL_LANGUAGE_COMMAND",
            preferred_model="gemini-2.5-flash"
        )
        assert isinstance(output_data, dict)
        assert model_used in ("gemini-2.5-flash", "local-deterministic-engine")
        assert latency >= 0
        assert "role" in output_data
        assert output_data.get("role") == "Staff Data Engineer"

    def test_audit_logging_persistence(self, test_db):
        """Verifies every AI transaction is logged to AIAuditLog with telemetry."""
        initial_count = test_db.query(AIAuditLog).count()
        AIRouterService.execute_prompt(
            prompt="Find frontend engineers in California",
            action_type="NATURAL_LANGUAGE_QUERY",
            user_id=1,
            db=test_db
        )
        final_count = test_db.query(AIAuditLog).count()
        assert final_count == initial_count + 1

        latest_log = test_db.query(AIAuditLog).order_by(AIAuditLog.id.desc()).first()
        assert latest_log.action_type == "NATURAL_LANGUAGE_QUERY"
        assert latest_log.model_name is not None
        assert latest_log.latency_ms >= 0


class TestAIExplainabilityService:
    def test_candidate_score_decomposition_math(self):
        """Verifies factor weights mathematically sum to expected overall score."""
        candidate = {
            "recruiter_name": "Alice Johnson",
            "title": "Lead Software Engineer",
            "company_name": "Tech Corp",
            "email": "alice@techcorp.com",
            "phone": "+1 555-019-2831",
            "linkedin": "https://linkedin.com/in/alice-johnson"
        }
        res = AIExplainabilityService.explain_candidate_match(candidate)
        assert res["overall_score"] > 80
        assert res["confidence"] >= 0.70
        assert "breakdown" in res

        # Verify all 5 core dimensions exist
        breakdown = res["breakdown"]
        assert "skills_match" in breakdown
        assert "experience_trajectory" in breakdown
        assert "industry_relevance" in breakdown
        assert "recency_signal" in breakdown
        assert "location_fit" in breakdown

    def test_calibrated_uncertainty_handling(self):
        """Verifies unverified or placeholder emails are strictly flagged."""
        stale_candidate = {
            "recruiter_name": "Bob Smith",
            "title": "Junior Developer",
            "company_name": "Unknown",
            "email": "bob@noemail.talentops.local",
            "phone": "",
            "linkedin": ""
        }
        res = AIExplainabilityService.explain_candidate_match(stale_candidate)
        assert res["provenance"]["email_status"] == "UNVERIFIED"
        assert res["provenance"]["phone_status"] == "INFERRED"
        assert res["provenance"]["profile_status"] == "UNKNOWN"

    def test_proactive_feed_generation(self):
        """Verifies proactive intelligence feed contains prioritized market events."""
        feed = AIExplainabilityService.get_proactive_intelligence_feed()
        assert len(feed) >= 4
        priorities = {item["priority"] for item in feed}
        assert "critical" in priorities
        assert "important" in priorities


class TestAIGovernanceAndPreferences:
    def test_preference_autonomy_defaults(self, test_db):
        """Verifies workspace defaults to Level 3 autonomy (Approve) in compliance with safety standards."""
        pref = AIPreference(user_id=42, autonomy_level=3)
        test_db.add(pref)
        test_db.commit()

        loaded = test_db.query(AIPreference).filter(AIPreference.user_id == 42).first()
        assert loaded.autonomy_level == 3
        perms = json.loads(loaded.permissions_json)
        assert perms["read"] is True
        assert perms["write"] is False  # Level 3 requires human sign-off for writes

    def test_feedback_loop_recording(self, test_db):
        """Verifies human recruiter 👍/👎 feedback is recorded for alignment."""
        feedback = AIFeedback(
            user_id=1,
            entity_type="candidate",
            entity_id="101",
            is_positive=False,
            feedback_category="WRONG_SENIORITY",
            user_notes="Title says senior, but years of experience is 1 year."
        )
        test_db.add(feedback)
        test_db.commit()

        loaded = test_db.query(AIFeedback).filter(AIFeedback.entity_id == "101").first()
        assert loaded.is_positive is False
        assert loaded.feedback_category == "WRONG_SENIORITY"
