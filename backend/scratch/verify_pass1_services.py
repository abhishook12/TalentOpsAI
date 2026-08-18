"""
CHECK 1 (PASS 1): SMTP Prober Unit Tests
==========================================
Verifies:
  1.1 SmtpProber can be instantiated and cached
  1.2 LinkedIn URL synthesis produces correct slugs
  1.3 Campaign preflight gate correctly categorizes emails
  1.4 Contact enrichment completeness scoring works
"""
import sys, os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

print("=" * 80)
print("CHECK 1 (PASS 1): BACKEND SERVICES UNIT TESTS")
print("=" * 80)

errors = []

# ─── 1.1 SmtpProber instantiation ────────────────────────────────────────────
print("\n[1.1] Testing SmtpProber instantiation...")
try:
    from app.services.smtp_prober import SmtpProber, SmtpProbeResult
    prober = SmtpProber()
    assert prober is not None
    assert isinstance(prober._probe_cache, dict)
    assert isinstance(prober._catchall_cache, dict)
    stats = prober.get_stats()
    assert 'total_probed' in stats
    assert 'mailbox_exists' in stats
    assert 'catchall_domains' in stats
    print("  ✅ SmtpProber instantiation PASSED")
    print(f"     Cache stats: {stats}")
except Exception as e:
    errors.append(f"1.1 SmtpProber instantiation: {e}")
    print(f"  ❌ FAILED: {e}")

# ─── 1.2 LinkedIn URL synthesis ──────────────────────────────────────────────
print("\n[1.2] Testing LinkedIn URL synthesis...")
try:
    from app.services.contact_enrichment_worker import ContactEnrichmentWorker
    worker = ContactEnrichmentWorker()
    
    test_cases = [
        ("Duncan Blythe", "https://www.linkedin.com/in/duncan-blythe"),
        ("Lauren Davis, MPH, PMP", "https://www.linkedin.com/in/lauren-davis"),
        ("Kyle Roehm, CSM", "https://www.linkedin.com/in/kyle-roehm"),
        ("Mike Nicholas", "https://www.linkedin.com/in/mike-nicholas"),
        ("John Hall", "https://www.linkedin.com/in/john-hall"),
    ]
    
    all_pass = True
    for name, expected in test_cases:
        result = worker.synthesize_linkedin_url(name)
        if result != expected:
            print(f"  ❌ '{name}' → got '{result}', expected '{expected}'")
            all_pass = False
        else:
            print(f"  ✅ '{name}' → {result}")
    
    if all_pass:
        print("  ✅ LinkedIn URL synthesis ALL PASSED")
    else:
        errors.append("1.2 LinkedIn URL synthesis: Some cases failed")
except Exception as e:
    errors.append(f"1.2 LinkedIn URL synthesis: {e}")
    print(f"  ❌ FAILED: {e}")

# ─── 1.3 Campaign Pre-Flight Gate ────────────────────────────────────────────
print("\n[1.3] Testing Campaign Pre-Flight gate categorization...")
try:
    from app.services.campaign_preflight import run_preflight_check, STATUS_TO_TIER, _classify_action
    
    # Test tier mapping
    assert STATUS_TO_TIER['verified'][0] == 1
    assert STATUS_TO_TIER['likely_deliverable'][0] == 2
    assert STATUS_TO_TIER['risky_catchall'][0] == 3
    assert STATUS_TO_TIER['undeliverable'][0] == 4
    assert STATUS_TO_TIER['missing'][0] == 5
    
    # Test action classification
    assert _classify_action(1) == 'send'
    assert _classify_action(2) == 'send'
    assert _classify_action(3) == 'review'
    assert _classify_action(4) == 'block'
    assert _classify_action(5) == 'block'
    
    print("  ✅ Tier mapping verified: 1=send, 2=send, 3=review, 4=block, 5=block")
    
    # Test preflight with known emails
    test_emails = [
        "dblythe@davislaine.com",    # Should be verified (Tier 1)
        "ldavis@davislaine.com",     # Should be verified (Tier 1)
        "fake@nonexistent.invalid"   # Should be missing (Tier 5)
    ]
    result = run_preflight_check(999, test_emails, ["Duncan", "Lauren", "Fake"])
    
    print(f"  Total: {result.total_recipients}, Safe: {result.safe_to_send}, "
          f"Risky: {result.risky_review}, Blocked: {result.blocked}")
    print(f"  Deliverability Rate: {result.deliverability_rate}%")
    print(f"  Risk Level: {result.risk_level}")
    print(f"  Can Proceed: {result.can_proceed}")
    
    assert result.total_recipients == 3
    assert result.deliverability_rate > 0
    print("  ✅ Campaign Pre-Flight gate PASSED")
except Exception as e:
    errors.append(f"1.3 Campaign Pre-Flight gate: {e}")
    print(f"  ❌ FAILED: {e}")

# ─── 1.4 Completeness scoring ────────────────────────────────────────────────
print("\n[1.4] Testing Completeness scoring...")
try:
    score, missing = ContactEnrichmentWorker.calculate_completeness({
        'email': 'dblythe@davislaine.com',
        'phone': '(314) 725-9922',
        'position': 'Federal Recruiting Manager',
        'company_name': 'Davis Laine, LLC',
        'linkedin_url': 'https://www.linkedin.com/in/duncan-blythe',
        'state': 'MO'
    })
    print(f"  Full record: score={score}, missing={missing}")
    assert score == 100, f"Expected 100, got {score}"
    assert missing == []
    
    score2, missing2 = ContactEnrichmentWorker.calculate_completeness({
        'email': 'test@test.com',
        'phone': '',
        'position': '',
        'company_name': '',
        'linkedin_url': '',
        'state': ''
    })
    print(f"  Sparse record: score={score2}, missing={missing2}")
    assert score2 == 30  # Only email
    assert 'phone' in missing2
    assert 'position' in missing2
    
    print("  ✅ Completeness scoring PASSED")
except Exception as e:
    errors.append(f"1.4 Completeness scoring: {e}")
    print(f"  ❌ FAILED: {e}")

# ─── Final Result ────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
if errors:
    print(f"CHECK 1 (PASS 1) RESULT: {len(errors)} FAILURE(S)")
    for err in errors:
        print(f"  ✗ {err}")
else:
    print("CHECK 1 (PASS 1) RESULT: ALL BACKEND SERVICE UNIT TESTS PASSED! ✅")
print("=" * 80)
