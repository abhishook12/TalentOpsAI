"""
CHECK 2 (PASS 2): FastAPI Endpoints & Integration Tests
========================================================
Verifies:
  2.1 Preflight check against live DuckDB Parquet dataset (e.g. Corner Alliance, Davis Laine, iConvergence)
  2.2 Deliverability report generation structure and tier aggregation
  2.3 MailIntel stats response includes enrichment and smtp_probe structures
  2.4 EmailVerificationEngine Stage 6 SMTP prober integration
"""
import sys, os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

print("=" * 80)
print("CHECK 2 (PASS 2): FASTAPI ROUTE & INTEGRATION ENGINE VERIFICATION")
print("=" * 80)

errors = []

# ─── 2.1 Live Dataset Preflight Check ─────────────────────────────────────────
print("\n[2.1] Testing Pre-Flight check against live uploaded corporate rosters...")
try:
    from app.services.campaign_preflight import run_preflight_check
    
    # Check Davis Laine, Corner Alliance & iConvergence rosters
    test_roster_emails = [
        "dblythe@davislaine.com",
        "ldavis@davislaine.com",
        "mnicholas@davislaine.com",
        "njohnson@corneralliance.com",
        "toby@iconvergence.com",
        "invalid_bounce_candidate@testnonexistent12345.org"
    ]
    test_names = [
        "Duncan Blythe",
        "Lauren Davis",
        "Mike Nicholas",
        "Noah Johnson",
        "Toby",
        "Nonexistent User"
    ]
    
    preflight = run_preflight_check(campaign_id=101, recipient_emails=test_roster_emails, recipient_names=test_names)
    
    print(f"  Preflight Evaluated: {preflight.total_recipients} recipients")
    print(f"  Safe To Send: {preflight.safe_to_send} | Risky: {preflight.risky_review} | Blocked: {preflight.blocked}")
    print(f"  Deliverability Rate: {preflight.deliverability_rate}%")
    print(f"  Can Proceed: {preflight.can_proceed}")
    
    assert preflight.total_recipients == 6, f"Expected 6, got {preflight.total_recipients}"
    assert preflight.safe_to_send >= 5, f"Expected at least 5 safe to send, got {preflight.safe_to_send}"
    assert preflight.blocked == 1, f"Expected 1 blocked, got {preflight.blocked}"
    assert preflight.deliverability_rate >= 80.0, f"Expected >=80%, got {preflight.deliverability_rate}%"
    
    # Check individual actions
    for r in preflight.recipients:
        if "davislaine.com" in r['email'] or "corneralliance.com" in r['email'] or "iconvergence.com" in r['email']:
            assert r['action'] == 'send', f"Expected 'send' for {r['email']}, got {r['action']}"
            assert r['is_deliverable'] is True
        elif "testnonexistent12345.org" in r['email']:
            assert r['action'] == 'block', f"Expected 'block' for {r['email']}, got {r['action']}"
            
    print("  ✅ Live Dataset Pre-Flight check PASSED with 100% precision")
except Exception as e:
    errors.append(f"2.1 Live Dataset Pre-Flight check: {e}")
    print(f"  ❌ FAILED: {e}")

# ─── 2.2 Deliverability Report Generation ──────────────────────────────────────
print("\n[2.2] Testing Deliverability Report generation structure...")
try:
    from app.services.campaign_preflight import get_deliverability_report
    
    report = get_deliverability_report(campaign_id=202, recipient_emails=test_roster_emails)
    
    assert 'campaign_id' in report
    assert 'summary' in report
    assert 'tiers' in report
    assert report['summary']['safe_to_send'] >= 5
    assert 'tier_1' in report['tiers']
    
    print(f"  Report Tiers present: {list(report['tiers'].keys())}")
    print(f"  Tier 1 Count: {report['tiers']['tier_1']['count']}")
    print("  ✅ Deliverability Report generation PASSED")
except Exception as e:
    errors.append(f"2.2 Deliverability Report generation: {e}")
    print(f"  ❌ FAILED: {e}")

# ─── 2.3 MailIntel Stats Integration ──────────────────────────────────────────
print("\n[2.3] Testing MailIntel Stats endpoint payload structure...")
try:
    from app.routes.mailintel import get_mailintel_stats
    from unittest.mock import MagicMock
    
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.role.name = "admin"
    
    # Execute endpoint function directly
    stats = get_mailintel_stats(db=mock_db, current_user=mock_user)
    
    assert 'total' in stats
    assert 'total_deliverable' in stats
    assert 'deliverability_rate' in stats
    assert 'breakdown' in stats
    assert 'enrichment' in stats
    assert 'smtp_probe' in stats
    
    print(f"  Total Records: {stats['total']:,}")
    print(f"  Total Deliverable: {stats['total_deliverable']:,}")
    print(f"  Deliverability Rate: {stats['deliverability_rate']}%")
    print(f"  Enrichment Section Present: {bool(stats['enrichment'])}")
    print(f"  SMTP Probe Section Present: {bool(stats['smtp_probe'])}")
    print("  ✅ MailIntel Stats schema verified PASSED")
except Exception as e:
    errors.append(f"2.3 MailIntel Stats endpoint: {e}")
    print(f"  ❌ FAILED: {e}")

# ─── 2.4 Email Verification Engine Single Email Verification ──────────────────
print("\n[2.4] Testing EmailVerificationEngine single email verification pipeline...")
try:
    from app.services.email_verification_engine import EmailVerificationEngine
    engine = EmailVerificationEngine()
    
    res_valid = engine._verify_single_email({'recruiter_id': 999991, 'email': 'dblythe@davislaine.com'})
    print(f"  Valid Corporate Email: {res_valid['email_status']} (confidence: {res_valid['email_confidence']}, source: {res_valid['email_source']})")
    assert res_valid['email_status'] == 'verified'
    assert res_valid['email_confidence'] >= 90
    
    res_invalid = engine._verify_single_email({'recruiter_id': 999992, 'email': 'invalid_bad_email@@@'})
    print(f"  Invalid Syntax: {res_invalid['email_status']} (confidence: {res_invalid['email_confidence']}, source: {res_invalid['email_source']})")
    assert res_invalid['email_status'] == 'invalid'
    assert res_invalid['email_confidence'] == 0
    
    print("  ✅ EmailVerificationEngine pipeline PASSED")
except Exception as e:
    errors.append(f"2.4 EmailVerificationEngine pipeline: {e}")
    print(f"  ❌ FAILED: {e}")

# ─── Final Result ────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
if errors:
    print(f"CHECK 2 (PASS 2) RESULT: {len(errors)} FAILURE(S)")
    for err in errors:
        print(f"  ✗ {err}")
else:
    print("CHECK 2 (PASS 2) RESULT: ALL ROUTE & INTEGRATION CHECKS PASSED! ✅")
print("=" * 80)
