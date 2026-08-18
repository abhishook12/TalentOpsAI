"""
CHECK 3 (PASS 3): Full End-to-End Workflow & Persistence Verification
=====================================================================
Verifies:
  3.1 Live SmtpProber batch execution & JSON cache file persistence
  3.2 Contact Enrichment Worker test run on target batch & metrics validation
  3.3 End-to-end Campaign Pre-flight Gate enforcement (safe dispatch simulation)
"""
import sys, os, json
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

print("=" * 80)
print("CHECK 3 (PASS 3): FULL END-TO-END WORKFLOW & PERSISTENCE VERIFICATION")
print("=" * 80)

errors = []

# ─── 3.1 SmtpProber Batch & Cache Persistence ─────────────────────────────────
print("\n[3.1] Testing SmtpProber batch interface & cache persistence...")
try:
    from app.services.smtp_prober import SmtpProber, PROBE_CACHE_FILE
    prober = SmtpProber()
    
    test_probe_list = [
        "dblythe@davislaine.com",
        "alan.graham@corneralliance.com",
        "invalid_local_part_12345@gmail.com"
    ]
    
    # Run batch probe
    batch_results = prober.probe_batch(test_probe_list)
    print(f"  Probed {len(batch_results)} mailboxes.")
    for r in batch_results:
        print(f"    - {r.email}: code={r.smtp_code}, exists={r.mailbox_exists}, delta={r.confidence_delta}, time={r.probe_time_ms}ms")
    
    assert len(batch_results) == len(test_probe_list)
    assert os.path.exists(PROBE_CACHE_FILE), f"Cache file {PROBE_CACHE_FILE} should exist on disk"
    
    with open(PROBE_CACHE_FILE, 'r') as f:
        cache_data = json.load(f)
    print(f"  Cache file contains {len(cache_data)} persisted entries.")
    assert len(cache_data) >= 1
    
    print("  ✅ SmtpProber batch & cache persistence PASSED")
except Exception as e:
    errors.append(f"3.1 SmtpProber batch & cache persistence: {e}")
    print(f"  ❌ FAILED: {e}")

# ─── 3.2 Contact Enrichment Worker Execution ─────────────────────────────────
print("\n[3.2] Testing Contact Enrichment Worker batch execution...")
try:
    from app.services.contact_enrichment_worker import ContactEnrichmentWorker
    worker = ContactEnrichmentWorker()
    
    # Run 1 batch of 1000 records to test performance and integrity
    enrich_result = worker.run_enrichment(batch_size=500, max_batches=2)
    stats = enrich_result.get('stats', {})
    
    print(f"  Enrichment Status: {enrich_result.get('status')}")
    print(f"  Total Processed: {stats.get('total_processed')}")
    print(f"  LinkedIn Synthesized: {stats.get('linkedin_enriched')}")
    print(f"  Completeness Scores Updated: {stats.get('completeness_updated')}")
    print(f"  Duration: {stats.get('last_run_duration_s')}s")
    
    assert stats.get('total_processed', 0) > 0
    assert len(stats.get('errors', [])) == 0, f"Enrichment errors: {stats.get('errors')}"
    
    print("  ✅ Contact Enrichment Worker execution PASSED")
except Exception as e:
    errors.append(f"3.2 Contact Enrichment Worker execution: {e}")
    print(f"  ❌ FAILED: {e}")

# ─── 3.3 Campaign Pre-Flight Gate Simulation ──────────────────────────────────
print("\n[3.3] Simulating campaign dispatch preflight safety gate...")
try:
    from app.services.campaign_preflight import run_preflight_check
    
    # Campaign mix: 10 verified contacts from Davis Laine + 2 fake emails
    emails = [
        "dblythe@davislaine.com",
        "twilliams@davislaine.com",
        "ldavis@davislaine.com",
        "kroehm@davislaine.com",
        "jhall@davislaine.com",
        "uahmed@davislaine.com",
        "mlawler@davislaine.com",
        "conyia@davislaine.com",
        "baustensen@davislaine.com",
        "mnicholas@davislaine.com",
        "bounced.recipient@fakeinbox123.com",
        "dead.mailbox@badcompany999.xyz"
    ]
    names = [
        "Duncan Blythe", "Trystan Williams", "Lauren Davis", "Kyle Roehm",
        "John Hall", "Usama Ahmed", "Melanie Lawler", "Chukwunonso Onyia",
        "Blake Austensen", "Mike Nicholas", "Fake User 1", "Fake User 2"
    ]
    
    preflight = run_preflight_check(campaign_id=9999, recipient_emails=emails, recipient_names=names)
    
    print(f"  Total in Campaign: {preflight.total_recipients}")
    print(f"  Safe To Send (Enrolled): {preflight.safe_to_send}")
    print(f"  Blocked from Dispatch: {preflight.blocked}")
    print(f"  Pre-Flight Deliverability Rate: {preflight.deliverability_rate}%")
    print(f"  Gate Verdict: {'APPROVED' if preflight.can_proceed else 'REJECTED'}")
    
    # Exactly the 10 Davis Laine contacts must be approved for sending
    assert preflight.safe_to_send == 10
    assert preflight.blocked == 2
    assert preflight.can_proceed is True
    
    print("  ✅ Campaign Pre-Flight Gate Simulation PASSED with 100% accuracy")
except Exception as e:
    errors.append(f"3.3 Campaign Pre-Flight Gate Simulation: {e}")
    print(f"  ❌ FAILED: {e}")

# ─── Final Result ────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
if errors:
    print(f"CHECK 3 (PASS 3) RESULT: {len(errors)} FAILURE(S)")
    for err in errors:
        print(f"  ✗ {err}")
else:
    print("CHECK 3 (PASS 3) RESULT: ALL END-TO-END VERIFICATIONS PASSED! ✅")
print("=" * 80)
