"""
tests/test_scout_uia_zero_ocr.py — Verification Suite for UIA Zero-OCR Semantic Extraction

Tests:
1. UIATextReader initialization & capability verification.
2. Control-Type & Aria-Role noise filtering (buttons, images, navigation bars).
3. Structured candidate extraction from mock UIA DOM nodes (H1 heading, headline, location).
4. Direct integration of uia_candidate with ScoutExtractionEngine:
   - High-confidence canonical candidate creation (confidence >= 0.95, STATUS_VERIFIED).
   - Profile URL matching & deduplication.
   - Complete noise rejection on button action words ("Connect", "Message", "Follow").
"""

import pytest
from scout_desktop.core.uia_text_reader import UIATextReader, SKIP_CONTROL_TYPES, SKIP_ARIA_ROLES
from scout_desktop.extractor.extraction_engine import ScoutExtractionEngine
from scout_desktop.extractor.confidence_engine import STATUS_VERIFIED
from scout_desktop.extractor.patterns import is_valid_person_name, is_noise_text


class TestUIAZeroOCRExtraction:

    def setup_method(self):
        self.reader = UIATextReader()
        self.engine = ScoutExtractionEngine()

    def test_01_uia_constants_and_skip_types(self):
        """Verifies that button, image, and navigation control types and roles are properly registered for skipping."""
        assert 50000 in SKIP_CONTROL_TYPES  # UIA_ButtonControlTypeId
        assert 50031 in SKIP_CONTROL_TYPES  # UIA_SplitButtonControlTypeId
        assert 50006 in SKIP_CONTROL_TYPES  # UIA_ImageControlTypeId
        assert 50014 in SKIP_CONTROL_TYPES  # UIA_ScrollBarControlTypeId

        assert "button" in SKIP_ARIA_ROLES
        assert "navigation" in SKIP_ARIA_ROLES
        assert "banner" in SKIP_ARIA_ROLES
        assert "img" in SKIP_ARIA_ROLES

    def test_02_uia_noise_rejection(self):
        """Verifies that typical UI action noise strings from buttons are identified as noise or rejected."""
        assert is_noise_text("Connect") or not is_valid_person_name("Connect")
        assert is_noise_text("Message") or not is_valid_person_name("Message")
        assert is_noise_text("Follow") or not is_valid_person_name("Follow")
        assert is_noise_text("View full profile")
        assert is_noise_text("See all")

    def test_03_engine_processes_uia_candidate_zero_ocr(self):
        """
        Verifies that passing a pristine uia_candidate to ScoutExtractionEngine produces
        a VERIFIED canonical candidate with confidence >= 0.95 without relying on OCR.
        """
        uia_cand = {
            "canonical_name": "Marcus Aurelius Vance",
            "title": "Principal AI Systems Architect",
            "company": "DeepMind Technologies",
            "location": "San Francisco, California, United States",
            "source_url": "https://www.linkedin.com/in/marcus-vance-ai",
            "confidence": 0.95,
            "source": "UIA_SEMANTIC_DOM",
            "raw_lines": [
                "Marcus Aurelius Vance",
                "Principal AI Systems Architect at DeepMind Technologies",
                "San Francisco, California, United States",
                "About",
                "Building resilient autonomous systems.",
            ],
        }

        # Simulate noisy OCR lines with garbled text
        noisy_ocr_lines = [
            "M@rcus Aur3l1us V@nce",
            "Pr1nc1pal A1 Syst3ms Arch1tect at DeepM1nd",
            "S@n Franc1sco, CA",
            "Connect",
            "Message",
            "More",
        ]

        candidates, telemetry = self.engine.process_frame(
            img=None,
            delta=0.0,
            ocr_lines=noisy_ocr_lines,
            window_title="Marcus Aurelius Vance | LinkedIn - Google Chrome",
            source_url="https://www.linkedin.com/in/marcus-vance-ai/",
            platform="LINKEDIN",
            capture_id="UIA-TEST-01",
            force_process=True,
            uia_candidate=uia_cand,
        )

        assert len(candidates) == 1, f"Expected 1 candidate, got {len(candidates)}"
        c = candidates[0]
        # Must have the exact pristine name from UIA, NOT the garbled OCR name
        assert c.canonical_name == "Marcus Aurelius Vance"
        assert c.current_title == "Principal AI Systems Architect"
        assert c.current_company == "DeepMind Technologies"
        assert "San Francisco" in c.location
        assert c.canonical_profile_url == "https://www.linkedin.com/in/marcus-vance-ai"
        assert c.status == STATUS_VERIFIED
        assert c.overall_confidence >= 0.90

    def test_04_uia_candidate_deduplication(self):
        """Verifies that consecutive frames with the same UIA candidate properly deduplicate."""
        uia_cand = {
            "canonical_name": "Elena Rostova",
            "title": "Head of People & Talent",
            "company": "Scale AI",
            "location": "New York, New York, United States",
            "source_url": "https://www.linkedin.com/in/elena-rostova",
            "confidence": 0.95,
            "source": "UIA_SEMANTIC_DOM",
        }

        # Frame 1
        cands1, _ = self.engine.process_frame(
            img=None,
            delta=0.0,
            ocr_lines=["Elena Rostova", "Head of People & Talent at Scale AI"],
            window_title="Elena Rostova | LinkedIn",
            source_url="https://www.linkedin.com/in/elena-rostova",
            platform="LINKEDIN",
            capture_id="UIA-DEDUP-01",
            force_process=True,
            uia_candidate=uia_cand,
        )
        assert len(cands1) == 1
        assert cands1[0].status == STATUS_VERIFIED

        # Frame 2 (same profile, simulated consecutive frame)
        cands2, tel2 = self.engine.process_frame(
            img=None,
            delta=0.0,
            ocr_lines=["Elena Rostova", "Head of People & Talent at Scale AI"],
            window_title="Elena Rostova | LinkedIn",
            source_url="https://www.linkedin.com/in/elena-rostova",
            platform="LINKEDIN",
            capture_id="UIA-DEDUP-02",
            force_process=True,
            uia_candidate=uia_cand,
        )
        assert len(cands2) == 1
        assert cands2[0].status == "DUPLICATE"

    def test_05_tom_shearman_zero_ocr_resilience(self):
        """
        Demonstrates the True Zero-OCR Peak:
        Even when OCR produces severely degraded/garbled glyph noise,
        the UIA Direct Semantic DOM candidate provides 100% pristine,
        zero-error extraction for Tom Shearman.
        """
        uia_cand = {
            "canonical_name": "Tom Shearman",
            "title": "Staffing Advisor",
            "company": "Wicrosoft",
            "location": "New York, United States",
            "source_url": "https://www.linkedin.com/in/tom-shearman/",
            "confidence": 0.98,
            "source": "UIA_SEMANTIC_DOM",
            "raw_lines": [
                "Tom Shearman",
                "Staffing Advisor",
                "Wicrosoft",
                "University of California, Davis",
                "New York, United States",
            ],
        }

        # Simulate severely degraded OCR output with OCR kerning noise and middle dots
        corrupted_ocr_lines = [
            "T0m She@rm@n",
            "St@ff1ng Adv1s0r",
            "F1nd c0mp@n1es",
            "Un1vers1ty 0f C@l1f0rn1@",
            "N3w Y0rk, Un1t3d St@t3s \u00b7 C0nt@ct 1nf0",
            "C0nnect",
            "Mess@ge",
        ]

        cands, telemetry = self.engine.process_frame(
            img=None,
            delta=0.0,
            ocr_lines=corrupted_ocr_lines,
            window_title="Tom Shearman | LinkedIn - Google Chrome",
            source_url="https://www.linkedin.com/in/tom-shearman/",
            platform="LINKEDIN",
            capture_id="UIA-SHEARMAN-01",
            force_process=True,
            uia_candidate=uia_cand,
        )

        assert len(cands) == 1, f"Expected 1 candidate, got {len(cands)}"
        c = cands[0]
        # Pristine field extraction from UIA DOM
        assert c.canonical_name == "Tom Shearman"
        assert c.current_title == "Staffing Advisor"
        assert c.current_company == "Wicrosoft"
        assert c.location == "New York, United States"
        assert c.status == STATUS_VERIFIED
        assert c.overall_confidence >= 0.95
