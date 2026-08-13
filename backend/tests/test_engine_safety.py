import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.data_filler_engine import DataFillerEngine
from app.services.mailintel_engine import _status_for_score
from app.services.sentinel_engine import normalize_email, normalize_phone
from app.services.verification_state import VerificationState
from app.models.campaigns import CampaignRecruiterStatus


def test_verification_marks_domain_only_after_completion(tmp_path, monkeypatch):
    state = VerificationState()
    state.state = {
        **state.state,
        "completed_domains": [],
        "batch_number": 0,
        "total_processed": 0,
    }
    monkeypatch.setattr(state, "save", lambda: None)

    state.mark_batch_complete("example.com", 5000, 10)
    assert state.state["completed_domains"] == []

    state.mark_domain_complete("example.com", 5001)
    assert state.state["completed_domains"] == ["example.com"]
    assert state.state["last_completed_recruiter_id"] == 5001


def test_data_filler_keeps_unknown_titles_in_general_staffing():
    engine = DataFillerEngine()
    assert engine._infer_specialization("Principal Java Engineer") == "Information Technology"
    assert engine._infer_specialization("Unclassified role") == "General Staffing"
    assert engine._infer_specialization("") is None


def test_mailintel_status_thresholds():
    assert _status_for_score(95) == "verified"
    assert _status_for_score(80) == "likely_valid"
    assert _status_for_score(30) == "suspicious"
    assert _status_for_score(100, hard_bounce_count=2) == "invalid"


def test_sentinel_normalizers_handle_invalid_values():
    assert normalize_email(" ADMIN@example.com ") == {"value": "admin@example.com", "issue": "role_based"}
    assert normalize_phone("123") == {"value": "123", "issue": "invalid_length"}


def test_campaign_statuses_preserve_individual_delivery_lifecycle():
    assert CampaignRecruiterStatus.pending.value == "Pending"
    assert CampaignRecruiterStatus.sending.value == "Sending"
    assert CampaignRecruiterStatus.sent.value == "Sent"
    assert CampaignRecruiterStatus.retrying.value == "Retrying"


def test_legacy_bulk_send_is_disabled_and_authenticated():
    import inspect
    from app.routes.campaigns import bulk_send_emails

    source = inspect.getsource(bulk_send_emails)
    assert "Legacy bulk SMTP sending is disabled" in source
    assert "get_current_user_from_request" in source
