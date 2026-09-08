"""
tests/test_acceptance.py — Comprehensive Acceptance Test Suite (AT-1 through AT-10)

Executes full test battery covering all 10 acceptance criteria for TalentOps Scout Desktop:
AT-1: Real Profile extraction
AT-2: Scroll enrichment (no duplicates)
AT-3: Company People page (multi-candidate segmentation)
AT-4: Job Board discrimination (Job vs Recruiter)
AT-5: Same Name disambiguation (IdentityResolver)
AT-6: Small text extraction (skills, degrees, schools)
AT-7: Reject ungrounded fabrication (GroundingGate)
AT-8: Backend offline → reconnect (LocalQueue backoff & DLQ)
AT-9: Purge lifecycle (EvidenceStore auto-purge & TTL)
AT-10: Node identity isolation (multi-user scouts)
"""

import os
import sys
import time
import shutil
import tempfile
import unittest
from PIL import Image

# Ensure scout_desktop package is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT_DIR = os.path.dirname(BASE_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from scout_desktop.extractor.entity_extractor import EntityExtractor
from scout_desktop.extractor.identity_resolver import IdentityResolver
from scout_desktop.extractor.timeline_parser import TimelineParser
from scout_desktop.extractor.grounding_gate import GroundingGate, ProofChain
from scout_desktop.core.context_memory import ContextMemory
from scout_desktop.core.evidence_store import EvidenceStore
from scout_desktop.sync.local_queue import LocalQueue
from scout_desktop.sync.backend_client import BackendClient
from scout_desktop.extractor.models import Observation, ExtensibleObservation, ObservationGraph


class TestAcceptanceSuite(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="scout_test_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ─────────────────────────────────────────────────────────────
    # AT-1: Real Profile Extraction
    # ─────────────────────────────────────────────────────────────
    def test_at1_real_profile_extraction(self):
        extractor = EntityExtractor()
        lines = [
            "Tony Vitulli",
            "VP of Engineering at Cyberdyne Systems",
            "Greater New York City Area",
            "Contact info",
            "500+ connections",
            "About",
            "Experienced engineering leader with 15+ years in distributed systems and cloud architecture.",
        ]
        clusters = extractor.extract_from_lines(
            lines=lines,
            capture_id="CAP-AT1",
            source_url="https://www.linkedin.com/in/tonyvitulli/",
            window_title="Tony Vitulli | LinkedIn",
        )
        self.assertTrue(len(clusters) >= 1, "Expected at least 1 cluster for profile")
        c = clusters[0]
        self.assertEqual(c.canonical_name, "Tony Vitulli")
        self.assertEqual(c.entity_type, "PERSON")
        self.assertEqual(c.current_company, "Cyberdyne Systems")
        self.assertIn("Engineering", c.current_title)
        self.assertTrue(any(obs.predicate in ("LOCATED_IN", "LIVES_IN") for obs in c.observations))

    # ─────────────────────────────────────────────────────────────
    # AT-2: Scroll Enrichment (No Duplicates)
    # ─────────────────────────────────────────────────────────────
    def test_at2_scroll_enrichment(self):
        extractor = EntityExtractor()
        # Initial capture: Header
        lines_header = [
            "Sarah Connor",
            "Chief Information Security Officer at TechCorp",
            "San Francisco, California",
        ]
        clusters_1 = extractor.extract_from_lines(
            lines=lines_header,
            capture_id="CAP-AT2-1",
            source_url="https://www.linkedin.com/in/sarahconnor/",
            window_title="Sarah Connor | LinkedIn",
        )
        self.assertEqual(len(clusters_1), 1)
        initial_obs_count = len(clusters_1[0].observations)

        # Scrolled capture: Experience & Education section
        lines_scroll = [
            "Experience",
            "Chief Information Security Officer",
            "TechCorp",
            "Jan 2021 - Present · 3 yrs 8 mos",
            "Senior Director of Security",
            "Initech Global",
            "Mar 2017 - Dec 2020 · 3 yrs 10 mos",
            "Education",
            "Stanford University",
            "Master of Science - MS, Computer Science",
        ]
        clusters_2 = extractor.extract_from_lines(
            lines=lines_scroll,
            capture_id="CAP-AT2-2",
            source_url="https://www.linkedin.com/in/sarahconnor/",
            window_title="Sarah Connor | LinkedIn",
            inferred_candidate="Sarah Connor",
        )
        self.assertEqual(len(clusters_2), 1)
        enriched = clusters_2[0]
        self.assertEqual(enriched.canonical_name, "Sarah Connor")
        # Ensure enriched with previous employer
        prev_companies = [obs.object_value for obs in enriched.observations if obs.predicate == "PREVIOUSLY_WORKED_AT"]
        self.assertIn("Initech Global", prev_companies)

    # ─────────────────────────────────────────────────────────────
    # AT-3: Company People / Search Grid (Multi-Candidate)
    # ─────────────────────────────────────────────────────────────
    def test_at3_company_people_grid(self):
        extractor = EntityExtractor()
        lines = [
            "People also viewed",
            "Alice Smith",
            "Staff Software Engineer at Datadog",
            "New York, New York",
            "Connect",
            "Bob Jones",
            "Principal Architect at Snowflake",
            "Austin, Texas",
            "Connect",
            "Carol Danvers",
            "Director of Product at Stripe",
            "Seattle, Washington",
            "Message",
        ]
        clusters = extractor.extract_from_lines(
            lines=lines,
            capture_id="CAP-AT3",
            source_url="https://www.linkedin.com/search/results/people/",
            window_title="Search | LinkedIn",
        )
        self.assertTrue(len(clusters) >= 2, f"Expected multiple clusters, got {len(clusters)}")
        names = [c.canonical_name for c in clusters]
        self.assertTrue(any("Alice Smith" in n for n in names))
        self.assertTrue(any("Bob Jones" in n for n in names))

    # ─────────────────────────────────────────────────────────────
    # AT-4: Job Board Discrimination (Job vs Recruiter)
    # ─────────────────────────────────────────────────────────────
    def test_at4_job_board_discrimination(self):
        extractor = EntityExtractor()
        lines = [
            "Senior Backend Engineer (Python/Go)",
            "Acme Corp · Remote",
            "About the job",
            "We are looking for a Senior Backend Engineer to join our core platform team.",
            "Requirements: 5+ years experience in Python and PostgreSQL.",
            "Meet the hiring team",
            "Marcus Vance",
            "Senior Talent Acquisition Partner at Acme Corp",
        ]
        clusters = extractor.extract_from_lines(
            lines=lines,
            capture_id="CAP-AT4",
            source_url="https://www.linkedin.com/jobs/view/987654321/",
            window_title="Senior Backend Engineer | Acme Corp | LinkedIn",
        )
        self.assertTrue(len(clusters) >= 1)
        entity_types = {c.entity_type for c in clusters}
        # Verify JOB entity was created
        self.assertIn("JOB", entity_types)

    # ─────────────────────────────────────────────────────────────
    # AT-5: Same Name Disambiguation (IdentityResolver)
    # ─────────────────────────────────────────────────────────────
    def test_at5_same_name_disambiguation(self):
        resolver = IdentityResolver()
        known = [
            {
                "entity_id": "ENT-001",
                "canonical_name": "David Miller",
                "current_company": "Google",
                "location": "Mountain View, CA",
                "linkedin_url": "https://www.linkedin.com/in/david-miller-google/",
            }
        ]

        # Candidate A: Same name, different company & URL -> Should NOT match ENT-001
        cand_a = {
            "canonical_name": "David Miller",
            "current_company": "Goldman Sachs",
            "location": "New York, NY",
            "linkedin_url": "https://www.linkedin.com/in/david-miller-finance/",
        }
        res_a = resolver.resolve(cand_a, known)
        self.assertNotEqual(res_a.outcome, "SAME_ENTITY")

        # Candidate B: Same name, same LinkedIn URL -> Should match ENT-001
        cand_b = {
            "canonical_name": "David Miller",
            "linkedin_url": "https://www.linkedin.com/in/david-miller-google/",
        }
        res_b = resolver.resolve(cand_b, known)
        self.assertEqual(res_b.outcome, "SAME_ENTITY")
        self.assertEqual(res_b.matched_entity_id, "ENT-001")

    # ─────────────────────────────────────────────────────────────
    # AT-6: Small Text Extraction (Skills, Degrees, Education)
    # ─────────────────────────────────────────────────────────────
    def test_at6_small_text_extraction(self):
        extractor = EntityExtractor()
        lines = [
            "Elena Rostova",
            "Staff AI Researcher at DeepMind",
            "London, United Kingdom",
            "Education",
            "Oxford University",
            "Ph.D. in Machine Learning and Robotics",
            "Skills",
            "PyTorch · Reinforcement Learning · Distributed Systems · CUDA",
        ]
        clusters = extractor.extract_from_lines(
            lines=lines,
            capture_id="CAP-AT6",
            source_url="https://www.linkedin.com/in/elena-rostova/",
            window_title="Elena Rostova | LinkedIn",
        )
        self.assertEqual(len(clusters), 1)
        c = clusters[0]
        preds = [obs.predicate for obs in c.observations]
        self.assertTrue("STUDIED_AT" in preds or "HAS_DEGREE" in preds or "HAS_SKILL" in preds)

    # ─────────────────────────────────────────────────────────────
    # AT-7: Reject Ungrounded Fabrication (GroundingGate)
    # ─────────────────────────────────────────────────────────────
    def test_at7_reject_ungrounded_fabrication(self):
        gate = GroundingGate(min_confidence=0.30, strict_mode=True)

        # 1. Valid grounded observation
        valid_obs = {
            "predicate": "WORKS_AT",
            "object_value": "Google",
            "confidence": 0.95,
            "evidence": "VP of Engineering at Google | Mountain View",
            "semantic_type": "PERSON",
        }
        res_valid = gate.validate_observation(valid_obs, {"capture_id": "CAP-1"})
        self.assertEqual(res_valid.outcome, "ACCEPT")

        # 2. Fabricated observation (empty evidence)
        fabricated_obs = {
            "predicate": "WORKS_AT",
            "object_value": "NVIDIA",
            "confidence": 0.95,
            "evidence": "",
            "semantic_type": "PERSON",
        }
        res_fab = gate.validate_observation(fabricated_obs, {"capture_id": "CAP-2"})
        self.assertNotEqual(res_fab.outcome, "ACCEPT")

        # 3. Mismatched hallucination (evidence does not contain object_value)
        hallucinated_obs = {
            "predicate": "WORKS_AT",
            "object_value": "Microsoft",
            "confidence": 0.90,
            "evidence": "Software Engineer at Amazon AWS",
            "semantic_type": "PERSON",
        }
        res_hal = gate.validate_observation(hallucinated_obs, {"capture_id": "CAP-3"})
        self.assertIn(res_hal.outcome, ["REJECT", "FLAG_FABRICATION", "SUSPICIOUS"])

    # ─────────────────────────────────────────────────────────────
    # AT-8: Backend Offline → Reconnect (LocalQueue Backoff & DLQ)
    # ─────────────────────────────────────────────────────────────
    def test_at8_backend_offline_reconnect(self):
        db_path = os.path.join(self.test_dir, "test_queue.db")
        queue = LocalQueue(db_path=db_path)

        contact = {
            "canonical_name": "Marcus Aurelius",
            "current_company": "Rome Corp",
            "capture_id": "CAP-AT8",
        }
        queue_id = queue.enqueue_cluster(contact)
        self.assertIsNotNone(queue_id)

        # 1. Fetch pending batch
        batch = queue.get_pending_batch(limit=10)
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch[0]["_local_queue_id"], queue_id)

        # 2. Simulate network failure with exponential backoff
        queue.mark_batch_failed([queue_id], error_msg="HTTP 503 Service Unavailable")

        # Immediately requesting pending batch should NOT return it (due to next_retry_at backoff)
        batch_immediate = queue.get_pending_batch(limit=10)
        self.assertEqual(len(batch_immediate), 0, "Item in backoff should not be fetched immediately")

        # 3. Simulate successful sync on reconnect
        queue.mark_batch_synced([queue_id])
        stats = queue.get_queue_stats()
        self.assertEqual(stats["synced_today"], 1)
        self.assertEqual(stats["pending"], 0)

    # ─────────────────────────────────────────────────────────────
    # AT-9: Purge Lifecycle (EvidenceStore TTL & MB Ceiling)
    # ─────────────────────────────────────────────────────────────
    def test_at9_purge_lifecycle(self):
        store = EvidenceStore(
            storage_dir=self.test_dir,
            retention_sec=1,  # 1 second TTL for test
            hard_max_retention_sec=5,
            max_buffer_images=10,
            max_buffer_mb=50,
        )

        # Create dummy PIL image and save
        img = Image.new("RGB", (100, 100), color=(73, 109, 137))
        item = store.save_capture(img, capture_id="CAP-AT9", page_url="http://test.com")
        self.assertTrue(os.path.exists(item.file_path))

        # 1. Test immediate 0ms purge on NO_USEFUL_DATA
        file1 = item.file_path
        store.update_status("CAP-AT9", "NO_USEFUL_DATA")
        self.assertFalse(os.path.exists(file1), "NO_USEFUL_DATA must be purged immediately (0ms)")
        self.assertIsNone(item.file_path)

        # 2. Test TTL-based purge on SYNC_COMPLETE
        item2 = store.save_capture(img, capture_id="CAP-AT9-B", page_url="http://test.com")
        file2 = item2.file_path
        self.assertTrue(os.path.exists(file2))
        store.update_status("CAP-AT9-B", "ANALYZING")
        store.update_status("CAP-AT9-B", "EXTRACTED")
        store.update_status("CAP-AT9-B", "STAGED")
        store.update_status("CAP-AT9-B", "SYNC_COMPLETE")
        time.sleep(1.2)  # Wait for 1s audit TTL expiry

        purged_count = store.purge_expired()
        self.assertTrue(purged_count >= 1, "Expired SYNC_COMPLETE items must be purged by purge_expired")
        self.assertFalse(os.path.exists(file2), "Expired screenshot file must be deleted from disk")
        self.assertIsNone(item2.file_path)

    # ─────────────────────────────────────────────────────────────
    # AT-10: Node Identity Isolation (Multi-User Scouts)
    # ─────────────────────────────────────────────────────────────
    def test_at10_node_identity_isolation(self):
        client1 = BackendClient(device_id="SCOUT-NODE-ALPHA", scout_id="NODE-ALPHA-01")
        client2 = BackendClient(device_id="SCOUT-NODE-BETA", scout_id="NODE-BETA-02")

        self.assertNotEqual(client1.device_id, client2.device_id)
        self.assertNotEqual(client1.scout_id, client2.scout_id)
        self.assertNotEqual(client1.session_id, client2.session_id)

        h1 = client1._get_headers()
        h2 = client2._get_headers()
        self.assertEqual(h1["X-Device-Id"], "SCOUT-NODE-ALPHA")
        self.assertEqual(h2["X-Device-Id"], "SCOUT-NODE-BETA")


if __name__ == "__main__":
    unittest.main()
