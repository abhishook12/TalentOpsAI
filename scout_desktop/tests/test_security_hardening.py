from __future__ import annotations

from unittest.mock import Mock, patch

from scout_desktop.sync.backend_client import BackendClient


def test_claim_does_not_create_a_local_identity_when_server_is_unavailable(tmp_path):
    """An unavailable pairing server must never result in an invented login."""
    client = BackendClient(
        api_base="https://scout.test",
        device_id="SCOUT-TEST-SECURITY",
        config_path=str(tmp_path / "config.json"),
    )
    existing_token = client.auth_token
    existing_email = client.user_email
    response = Mock(status_code=503, content=b'{"detail":"Temporarily unavailable"}')
    response.json.return_value = {"detail": "Temporarily unavailable"}

    with patch("scout_desktop.sync.backend_client.requests.post", return_value=response):
        ok, result = client.claim_device_with_code("TOS-ABCD-EFGH")

    assert ok is False
    assert "unavailable" in result["error"].lower()
    assert client.auth_token == existing_token
    assert client.user_email == existing_email


def test_windows_dpapi_round_trip_or_safe_failure():
    """On Windows, a persisted token is bound to the current OS account."""
    from scout_desktop.core.credential_store import protect_token, unprotect_token

    protected = protect_token("test-token-not-a-real-credential")
    if protected is not None:
        assert protected.startswith("dpapi:v1:")
        assert unprotect_token(protected) == "test-token-not-a-real-credential"
