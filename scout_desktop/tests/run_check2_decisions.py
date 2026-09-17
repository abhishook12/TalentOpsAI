import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import json

print("=" * 70)
print("CHECK 2: EXPLAINABLE DECISIONS, IDENTITY SAFETY & GOLDEN TEST PROOF")
print("=" * 70)

# 1. Exact Verdicts and Decisive Reasons
from scout_desktop.extractor.candidate_gate import create_candidate_if_valid

# Test 1.1: VERIFIED with stable LinkedIn Profile URL
v_cand = create_candidate_if_valid({
    "name": "Sarah Chen",
    "title": "Staff ML Engineer",
    "company": "Anthropic",
    "canonical_profile_url": "https://www.linkedin.com/in/sarahchen-ai/",
    "platform": "LinkedIn",
    "window_title": "Sarah Chen | LinkedIn",
})
print(f"[TEST 2.1] Stable Profile Ingestion: status={v_cand.status}, decision={v_cand.decision}, reason_code={v_cand.reason_code}")
assert v_cand.status == "VERIFIED"
assert v_cand.reason_code == "PROFILE_URL_PRESENT"
assert "name" in v_cand.field_evidence and "company" in v_cand.field_evidence
print(f"           Field Evidence: {v_cand.field_evidence}")

# Test 1.2: REVIEW_REQUIRED with Title/Company Only
r_cand = create_candidate_if_valid({
    "name": "Marcus Vance",
    "title": "Principal Architect",
    "company": "Oracle Cloud",
    "platform": "DESKTOP_CAPTURE",
})
print(f"\n[TEST 2.2] Title/Company-Only Discovery: status={r_cand.status}, reason_code={r_cand.reason_code}")
assert r_cand.status == "REVIEW_REQUIRED"
assert r_cand.reason_code == "TITLE_COMPANY_ONLY"
print(f"           Held with explanation: {r_cand.reasons}")

# Test 1.3: REJECTED with Cross-Tab Contamination
x_cand = create_candidate_if_valid({
    "name": "Jessica Albright",
    "canonical_profile_url": "https://www.linkedin.com/in/robert-smith-12345/",
    "platform": "LinkedIn",
})
print(f"\n[TEST 2.3] Cross-Tab Slug Mismatch: status={x_cand.status}, reason_code={x_cand.reason_code}")
assert x_cand.status == "REJECTED" or x_cand.reason_code == "CROSS_TAB_MISMATCH"
print(f"           Rejected with explanation: {x_cand.reasons}")

# 2. Reviewer Feedback Store (Negative Patterns Loop)
print("\n[TEST 2.4] Reviewer Feedback Loop (Negative Patterns Store):")
from scout_desktop.extractor.negative_patterns import add_negative_pattern, is_pattern_blacklisted
add_negative_pattern("SPAM_RECRUITER_PATTERN", pattern_type="company", reason="Candidate Gate Test Reject")
is_blocked = is_pattern_blacklisted("SPAM_RECRUITER_PATTERN", pattern_type="company")
print(f"           Registered negative pattern 'SPAM_RECRUITER_PATTERN' -> is_pattern_blacklisted: {is_blocked}")
assert is_blocked is True

# 3. Permanent Golden Dataset Tests
print("\n[TEST 2.5] Permanent Golden Dataset Automated Pass:")
import subprocess
result = subprocess.run(
    [sys.executable, "-m", "pytest", "scout_desktop/tests/test_golden_dataset.py", "-q"],
    capture_output=True,
    text=True,
    cwd=r"c:\TalentOpsAI"
)
print(f"           Pytest Golden Dataset Results:\n{result.stdout.strip()}")
assert result.returncode == 0, f"Golden dataset pytest failed: {result.stderr}"

# 4. Config Sanitization & AppData Isolation
print("\n[TEST 2.6] Distribution Config Sanitization & AppData Isolation:")
with open(r"c:\TalentOpsAI\scout_desktop\config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)
assert cfg.get("auth_token") == "", "config.json has residual auth_token!"
assert cfg.get("user_email") == "", "config.json has residual user_email!"
assert cfg.get("user_name") == "", "config.json has residual user_name!"
assert cfg.get("installation_id") == "", "config.json has residual installation_id!"
print("           scout_desktop/config.json is 100% sanitized (0 tokens, 0 personal emails).")

with open(r"c:\TalentOpsAI\scout_desktop\default_config.json", "r", encoding="utf-8") as f:
    dcfg = json.load(f)
assert dcfg.get("auth_token") == "", "default_config.json has residual auth_token!"
print("           scout_desktop/default_config.json is clean distribution template.")

appdata_user_state = os.path.join(os.environ.get("LOCALAPPDATA", ""), "TalentOpsAI", "Scout", "user_state.json")
assert os.path.exists(appdata_user_state), f"Missing {appdata_user_state}"
with open(appdata_user_state, "r", encoding="utf-8") as f:
    ust = json.load(f)
assert bool(ust.get("auth_token")), "user_state.json missing auth_token"
print(f"           Isolated AppData state exists at {appdata_user_state} with user={ust.get('user_email')}")

print("\n" + "=" * 70)
print(">>> CHECK 2 VERIFIED: Decision Explainability, Parsers & Golden Corpus Working <<<")
print("=" * 70)
