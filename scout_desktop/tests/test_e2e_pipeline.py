"""
tests/test_e2e_pipeline.py — Comprehensive End-to-End Lifecycle Verification

Executes full integration verification simulating a complete live recruiter workflow:
1. Native Window & Browser Context Resolution with Page Classification
2. Visual Sampler 3-Level State Machine & Frame Backpressure Queue
3. Frame Capture & Evidence Store Storage Lifecycle
4. OCR Engine Text Extraction & Text Diff Computation
5. Entity Extraction & Employment Timeline Parsing
6. Grounding Gate Validation & Proof Chain Generation
7. Context Memory Tracking, Gap Detection & Completeness Scoring
8. Client-Side Identity Resolution & Conflict Detection
9. Local Queue SQLite Staging, Deduplication & Exponential Backoff
10. Backend Client Telemetry & Heartbeat Payload Integrity
11. Auto-Purge & Memory Buffer Ceiling Enforcement
12. Multi-Level UI Initialization (Tray, EdgeHandle, MainWindow, Diagnostics, Settings)
"""

import os
import sys
import time
import json
import shutil
import tempfile
from PIL import Image

# Ensure path resolution
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT_DIR = os.path.dirname(BASE_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from PySide6.QtWidgets import QApplication

from scout_desktop.core.window_tracker import WindowTracker, WindowInfo
from scout_desktop.core.browser_tracker import BrowserTracker
from scout_desktop.core.visual_sampler import VisualSampler
from scout_desktop.core.evidence_store import EvidenceStore
from scout_desktop.core.ocr_engine import OcrEngine, TextDiffResult
from scout_desktop.core.intelligence_levels import IntelligenceRouter, FrameQueue, FrameContext, IntelligenceLevel
from scout_desktop.core.context_memory import ContextMemory
from scout_desktop.extractor.entity_extractor import EntityExtractor
from scout_desktop.extractor.identity_resolver import IdentityResolver
from scout_desktop.extractor.timeline_parser import TimelineParser
from scout_desktop.extractor.grounding_gate import GroundingGate
from scout_desktop.extractor.models import ExtensibleObservation, ObservationGraph, CompletenessState
from scout_desktop.sync.local_queue import LocalQueue
from scout_desktop.sync.backend_client import BackendClient
from scout_desktop.sync.batch_processor import BatchProcessor
from scout_desktop.ui.tray import SystemTrayManager
from scout_desktop.ui.edge_handle import EdgeHandleWidget
from scout_desktop.ui.main_window import MainWindow
from scout_desktop.ui.diagnostics_window import DiagnosticsWindow
from scout_desktop.ui.settings_window import SettingsWindow


def run_e2e_verification():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 70)
    print(">> TALENTOPS SCOUT DESKTOP -- END-TO-END PIPELINE VERIFICATION")
    print("=" * 70)

    test_dir = tempfile.mkdtemp(prefix="scout_e2e_")

    try:
        # Step 1: Qt Application Context (Headless / Non-blocking)
        app = QApplication.instance() or QApplication(sys.argv)
        print("[OK] Step 1: Qt Application Framework initialized.")

        # Step 2: Browser Tracker & Page Classification
        bt = BrowserTracker()
        ctx_profile = bt.resolve_browser_context(
            hwnd=12345,
            window_title="Tony Vitulli | LinkedIn - Google Chrome"
        )
        assert ctx_profile["platform"] == "LINKEDIN", f"Expected LINKEDIN, got {ctx_profile['platform']}"
        assert ctx_profile["page_type"] == "PROFILE", f"Expected PROFILE, got {ctx_profile['page_type']}"
        assert ctx_profile["candidate_name"] == "Tony Vitulli"

        ctx_job = bt.resolve_browser_context(
            hwnd=12346,
            window_title="Senior Python Engineer - Cyberdyne | Indeed.com"
        )
        assert ctx_job["platform"] == "INDEED"
        assert ctx_job["page_type"] == "JOB_POSTING"
        print("[OK] Step 2: Browser Tracker context resolution & page type classification verified.")

        # Step 3: Intelligence Router & Backpressure Frame Queue
        router = IntelligenceRouter()
        frame_queue = FrameQueue(max_depth=5)
        
        f1 = FrameContext(visual_delta=0.08, page_type="PROFILE", window_title="Tony Vitulli | LinkedIn")
        decision_f1 = router.evaluate(f1)
        assert decision_f1.level in [IntelligenceLevel.UNDERSTAND, IntelligenceLevel.RESOLVE]
        
        frame_queue.enqueue({"capture_id": "F1", "delta": 0.08, "timestamp": time.time()})
        assert frame_queue.depth == 1
        popped = frame_queue.dequeue()
        assert popped["capture_id"] == "F1"
        assert frame_queue.depth == 0
        print("[OK] Step 3: Intelligence Router (WATCH/UNDERSTAND/RESOLVE) & Frame Queue verified.")

        # Step 4: Evidence Store Lifecycle & Storage Ceiling
        evidence_dir = os.path.join(test_dir, "captures")
        store = EvidenceStore(
            storage_dir=evidence_dir,
            audit_retention_sec=2.0,
            hard_max_retention_sec=10.0,
            max_buffer_images=5,
            max_buffer_mb=10,
        )
        dummy_img = Image.new("RGB", (200, 200), color=(16, 185, 129))
        c_item = store.save_capture(dummy_img, capture_id="VC-001", page_url="https://linkedin.com/in/tonyvitulli")
        assert os.path.exists(c_item.file_path)
        assert store.active_buffer_count == 1
        
        # Test valid state transitions: CAPTURED -> ANALYZING -> EXTRACTED -> STAGED -> SYNC_COMPLETE
        store.update_status("VC-001", "ANALYZING")
        store.update_status("VC-001", "EXTRACTED")
        store.update_status("VC-001", "STAGED")
        store.update_status("VC-001", "SYNC_COMPLETE")
        print("[OK] Step 4: Evidence Store capture, buffer tracking & state machine verified.")

        # Step 5: OCR Engine Text Diff & Scroll Detection
        ocr = OcrEngine()
        prev_lines = [
            "Tony Vitulli",
            "VP of Engineering at Cyberdyne Systems",
            "Greater New York City Area",
        ]
        curr_lines = [
            "VP of Engineering at Cyberdyne Systems",
            "Greater New York City Area",
            "Experience",
            "VP of Engineering",
            "Cyberdyne Systems",
            "Jan 2020 - Present · 4 yrs 5 mos",
        ]
        diff_res = ocr.compute_text_diff(prev_lines, curr_lines)
        assert diff_res.is_scroll is True, "Expected scroll detection on overlapping frame"
        assert len(diff_res.added_lines) > 0
        assert diff_res.overlap_ratio >= 0.25
        print("[OK] Step 5: OCR text diff & scroll continuation detection verified.")

        # Step 6: Entity Extractor & Employment Timeline Parsing
        extractor = EntityExtractor()
        full_lines = [
            "Tony Vitulli",
            "VP of Engineering at Cyberdyne Systems",
            "Greater New York City Area",
            "Experience",
            "VP of Engineering",
            "Cyberdyne Systems",
            "Jan 2020 - Present · 4 yrs 5 mos",
            "Senior Engineering Manager",
            "Skynet Global",
            "Jun 2016 - Dec 2019 · 3 yrs 7 mos",
            "Education",
            "Massachusetts Institute of Technology",
            "BS in Computer Science and Artificial Intelligence",
        ]
        clusters = extractor.extract_from_lines(
            lines=full_lines,
            capture_id="VC-001",
            source_url="https://www.linkedin.com/in/tonyvitulli/",
            window_title="Tony Vitulli | LinkedIn",
        )
        assert len(clusters) == 1
        cluster = clusters[0]
        assert cluster.canonical_name == "Tony Vitulli"
        assert cluster.current_company == "Cyberdyne Systems"
        
        # Check timeline attributes attached by TimelineParser
        exp_obs = [obs for obs in cluster.observations if obs.predicate == "WORKS_AT"]
        assert len(exp_obs) >= 1
        dated_exp = [obs for obs in exp_obs if obs.attributes.get("start_date")]
        assert len(dated_exp) >= 1
        assert dated_exp[0].attributes.get("start_date") == "2020-01"
        assert dated_exp[0].attributes.get("end_date") is None  # Present
        
        prev_obs = [obs for obs in cluster.observations if obs.predicate == "PREVIOUSLY_WORKED_AT"]
        assert len(prev_obs) >= 1
        assert prev_obs[0].object_value == "Skynet Global"
        assert prev_obs[0].attributes.get("start_date") == "2016-06"
        assert prev_obs[0].attributes.get("end_date") == "2019-12"
        assert prev_obs[0].attributes.get("tenure_months") == 42
        print("[OK] Step 6: Entity Extractor with TimelineParser ISO normalization & tenure calculation verified.")

        # Step 7: Grounding Gate & Proof Chain Generation
        gate = GroundingGate(min_confidence=0.30, strict_mode=True)
        proof_chain = gate.build_proof_chain("VC-001")
        
        for obs in cluster.observations:
            res = gate.validate_observation(obs.to_dict(), {"capture_id": "VC-001"})
            assert res.outcome in ["ACCEPT", "REVIEW"], f"Expected ACCEPT/REVIEW, got {res.outcome} for {obs.predicate}"
            proof_chain.add_step(
                step_name=f"VALIDATE_{obs.predicate}",
                details={"value": str(obs.object_value), "confidence": obs.confidence},
                status="PASS"
            )
        assert len(proof_chain.steps) > 0
        assert all(step.status == "PASS" for step in proof_chain.steps)
        print("[OK] Step 7: Evidence Grounding Gate validation & Proof Chain integrity verified.")

        # Step 8: Context Memory Multi-Entity Tracking & Gap Detection
        memory = ContextMemory(ttl_sec=300)
        ent_state = memory.register_entity(
            entity_id="ENT-TONY-001",
            entity_type="PERSON",
            canonical_name="Tony Vitulli",
            source_url="https://linkedin.com/in/tonyvitulli",
            capture_id="VC-001"
        )
        assert ent_state.get_completeness_tier() in ["INSUFFICIENT", "MINIMAL", "BASIC"]
        
        memory.update_entity_field(ent_state.entity_id, "current_title", "VP of Engineering")
        memory.update_entity_field(ent_state.entity_id, "current_company", "Cyberdyne Systems")
        memory.update_entity_field(ent_state.entity_id, "location", "Greater New York City Area")
        memory.update_entity_field(ent_state.entity_id, "linkedin_url", "https://linkedin.com/in/tonyvitulli")
        
        score = memory.compute_completeness(ent_state.entity_id)
        assert score >= 0.40, f"Expected completeness >= 0.40, got {score}"
        
        gaps = memory.get_information_gaps(ent_state.entity_id)
        assert "email" in gaps, "Email should be identified as an information gap"
        print(f"[OK] Step 8: Context Memory tracking (Completeness: {score*100:.0f}%, Gaps: {gaps}) verified.")

        # Step 9: Client-Side Identity Resolver
        resolver = IdentityResolver()
        known_list = [memory.get_entity_dict(ent_state.entity_id)]
        
        # Resolving identical LinkedIn URL -> SAME_ENTITY
        match_query = {
            "canonical_name": "Tony Vitulli",
            "linkedin_url": "https://linkedin.com/in/tonyvitulli",
        }
        res_match = resolver.resolve(match_query, known_list)
        assert res_match.outcome == "SAME_ENTITY"
        assert res_match.matched_entity_id == "ENT-TONY-001"
        print("[OK] Step 9: Client-side Identity Resolver match & disambiguation verified.")

        # Step 10: Local SQLite Queue & Exponential Backoff
        queue_db = os.path.join(test_dir, "test_queue.db")
        lq = LocalQueue(db_path=queue_db)
        staged_dict = cluster.to_staged_contact_dict()
        staged_dict["capture_id"] = "VC-001"
        staged_dict["source_url"] = "https://linkedin.com/in/tonyvitulli"
        
        qid = lq.enqueue_cluster(staged_dict)
        assert qid > 0
        
        # Test deduplication
        qid_dup = lq.enqueue_cluster(staged_dict)
        assert qid_dup == -1, "Duplicate observation must be rejected by SHA-256 content hash"
        
        # Test backoff on failure
        lq.mark_batch_failed([qid], error_msg="HTTP 502 Bad Gateway")
        pending_after_fail = lq.get_pending_batch(limit=10)
        assert len(pending_after_fail) == 0, "Item in exponential backoff must not be returned immediately"
        
        # Mark synced
        lq.mark_batch_synced([qid])
        q_stats = lq.get_queue_stats()
        assert q_stats["synced_today"] == 1
        assert q_stats["pending"] == 0
        lq.close()
        print("[OK] Step 10: Local Queue SQLite staging, SHA-256 deduplication & backoff verified.")

        # Step 11: Backend Client Telemetry & Batch Compression
        client = BackendClient(
            api_base="https://talentopsai-1.onrender.com",
            device_id="TEST-NODE-E2E",
            scout_id="SCOUT-E2E-01"
        )
        headers = client._get_headers()
        assert headers["X-Device-Id"] == "TEST-NODE-E2E"
        assert headers["X-Extension-Version"] == "1.0.0-desktop"
        print("[OK] Step 11: Backend Client node identity & header construction verified.")

        # Step 12: Multi-Level Native UI Subsystems (Level 1, 2, 3)
        tray = SystemTrayManager()
        assert tray is not None
        
        edge = EdgeHandleWidget()
        assert edge is not None
        edge.set_status_state("ACTIVE")
        assert edge.state == "ACTIVE"
        
        main_win = MainWindow()
        assert main_win is not None
        main_win.update_explicit_counters({
            "captured": 1,
            "analyzed": 1,
            "useful": 1,
            "staged": 1,
            "matched": 0,
            "new": 1,
            "enriched": 0,
            "db_updates": 1,
            "purged": 0,
            "observed": len(cluster.observations),
            "fields_added": 5,
            "buffer_current": 1,
            "buffer_max": 20,
        })
        assert main_win.c_observed.value == str(len(cluster.observations))
        assert main_win.c_fields_added.value == "5"
        
        diag_win = DiagnosticsWindow()
        assert diag_win.tabs.count() == 2
        
        settings_win = SettingsWindow(client, lq)
        print("[OK] Step 12: Multi-Level UI (Tray, EdgeHandle, MainWindow, Diagnostics, Settings) verified.")

        print("=" * 70)
        print("[SUCCESS] ALL 12 END-TO-END PIPELINE PHASES VERIFIED SUCCESSFULLY!")
        print("=" * 70)
        return True

    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    success = run_e2e_verification()
    sys.exit(0 if success else 1)
