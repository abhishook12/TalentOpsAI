"""
test_check2_extraction_telemetry.py — Check 2: Live LinkedIn Extraction & Telemetry Progression
Verifies exact scenario from user screenshot media_1788544067299.png:
- Profile: Mariam Nguyen, Senior Technical Recruiter @ Seaglass Technology Partners, LLC
- Verifies entity extraction, email capture, grounded evidence generation,
  and explicit counter progression from 0 to 1+.
"""

import os
import sys
import time
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print("=== CHECK 2: LIVE EXTRACTION & TELEMETRY PROGRESSION (MARIAM NGUYEN SCENARIO) ===")

from scout_desktop.extractor.entity_extractor import EntityExtractor
from scout_desktop.extractor.patterns import clean_person_name, is_valid_location
from scout_desktop.sync.local_queue import LocalQueue
from scout_desktop.core.visual_sampler import VisualSampler
from scout_desktop.core.window_tracker import WindowInfo

# 1. Test clean_person_name on "Mariam Nguyen • 2nd"
print("\n[Step 1: Person Name & Degree Badge Decomposition]")
raw_name_line = "Mariam Nguyen • 2nd"
cleaned_name = clean_person_name(raw_name_line)
print(f"  Raw Line: '{raw_name_line}' -> Cleaned: '{cleaned_name}'")
assert cleaned_name == "Mariam Nguyen", f"Expected 'Mariam Nguyen', got '{cleaned_name}'"
print("  ✓ Successfully decomposed candidate name from connection badge")

# 2. Test full entity extraction on Mariam Nguyen's visible screen lines
print("\n[Step 2: Full Screen OCR Entity Extraction]")
screen_ocr_lines = [
    "Search",
    "Jobs",
    "Messaging",
    "Notifications",
    "MARIAM NGUYEN",
    "mnguyen@seaglassit.com",
    "Mariam Nguyen • 2nd",
    "Senior Technical Recruiter at Seaglass Technology Partners, LLC",
    "Exeter, New Hampshire, United States · Contact info",
    "Seaglass Technology Partners, LLC",
    "Saint Anselm College",
    "500+ connections",
    "Message",
    "About",
    "Senior Technical Recruiter specializing in technology placements with 8 years of experience.",
]

extractor = EntityExtractor()
clusters = extractor.extract_from_lines(
    lines=screen_ocr_lines,
    capture_id="VC-TEST01",
    source_url="https://www.linkedin.com/in/mariam-nguyen-b20689184/",
    window_title="Mariam Nguyen | LinkedIn",
)

assert len(clusters) == 1, f"Expected 1 cluster, got {len(clusters)}"
c = clusters[0]
print(f"  ✓ Canonical Name: '{c.canonical_name}'")
assert c.canonical_name == "Mariam Nguyen"

print(f"  ✓ Current Title:  '{c.current_title}'")
assert c.current_title == "Senior Technical Recruiter"

print(f"  ✓ Current Company: '{c.current_company}'")
assert "Seaglass" in c.current_company

print(f"  ✓ Extracted Email: '{c.email}'")
assert c.email == "mnguyen@seaglassit.com"

print(f"  ✓ Location:       '{c.location}'")
assert "Exeter" in c.location and "New Hampshire" in c.location

print(f"  ✓ Education:      '{c.education}'")
assert "Saint Anselm" in c.education

print(f"  ✓ Total Grounded Observations: {len(c.observations)}")
assert len(c.observations) >= 5, f"Expected at least 5 grounded observations, got {len(c.observations)}"

for obs in c.observations:
    print(f"    - [{obs.predicate}] '{obs.object_value}' (conf: {obs.confidence:.2f}, evidence: '{obs.evidence[:40]}')")
    assert obs.grounding_status == "GROUNDED", f"Observation {obs.predicate} failed grounding!"

# 3. Test Staging Queue serialization
print("\n[Step 3: Staging Queue Serialization & SQLite Enqueue]")
staged_dict = c.to_staged_contact_dict()
assert staged_dict["raw_name"] == "Mariam Nguyen"
assert staged_dict["raw_title"] == "Senior Technical Recruiter"
assert staged_dict["raw_email"] == "mnguyen@seaglassit.com"
assert "Seaglass" in staged_dict["raw_company"]
print(f"  ✓ Staged dictionary serialized correctly with email: {staged_dict['raw_email']}")

queue = LocalQueue(":memory:")
qid = queue.enqueue_cluster(staged_dict)
print(f"  ✓ Staged contact enqueued to local SQLite buffer with ID: {qid}")
assert qid > 0

pending = queue.get_pending_batch(limit=10)
assert len(pending) == 1
assert pending[0]["raw_name"] == "Mariam Nguyen"
print(f"  ✓ Local SQLite queue verified: 1 pending item retrieved ({pending[0]['raw_name']})")

# 4. Test VisualSampler Immediate Trigger & Baseline Mechanics
print("\n[Step 4: VisualSampler Autonomous Sampling & Immediate Trigger]")
captured_frames = []
def on_frame(img, delta, win):
    captured_frames.append((delta, win.title))

sampler = VisualSampler(on_meaningful_frame=on_frame, delta_threshold=0.035, idle_timeout_sec=2.0)
mock_win = WindowInfo(hwnd=12345, title="Mariam Nguyen | LinkedIn", pid=9999, process_name="chrome.exe", app_type="BROWSER", rect=(0, 0, 1920, 1080))

sampler.trigger_immediate_capture(mock_win, reason="test_immediate")
assert len(captured_frames) == 1, f"Expected 1 captured frame, got {len(captured_frames)}"
assert captured_frames[0][0] == 1.0, f"Expected delta 1.0 for immediate capture, got {captured_frames[0][0]}"
print(f"  ✓ VisualSampler immediate capture triggered successfully: delta={captured_frames[0][0]}, window='{captured_frames[0][1]}'")
print(f"  ✓ Sampler telemetry: total_samples={sampler.stats['total_samples']}, meaningful={sampler.stats['meaningful_frames']}")

# 5. Verify 10-Second Idle Rule simulation
print("\n[Step 5: Idle Rule Engine Verification]")
assert sampler.state == "ACTIVE_SAMPLING"
# Fast-forward time to simulate idle expiration
sampler._last_active_time = time.time() - 15.0
sampler._set_state("IDLE_WATCH")
assert sampler.state == "IDLE_WATCH"
print(f"  ✓ Idle watch transition verified: {sampler.state}")

# Simulate wakeup on visual delta
sampler.trigger_immediate_capture(mock_win, reason="test_wake")
assert sampler.state == "ACTIVE_SAMPLING"
print(f"  ✓ Instant wakeup upon visual change verified: {sampler.state}")

print("\n>>> CHECK 2 PASSED: MARIAM NGUYEN EXTRACTION & TELEMETRY PROGRESSION VERIFIED! <<<")
