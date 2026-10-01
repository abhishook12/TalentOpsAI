"""
tests/test_frontiers_2_and_5.py

Test Suite for:
- Frontier 5: Self-Evolving Code (Self-Healing DOM & Extraction Reflexes via AdaptiveReflexEngine)
- Frontier 2: Zero-Cost Multi-Surface Waterfall OSINT Engine (WaterfallOsintEngine)
"""

import os
import json
import pytest
from scout_desktop.extractor.adaptive_reflex_engine import AdaptiveReflexEngine
from backend.app.services.waterfall_osint_engine import WaterfallOsintEngine, CandidateDossier
from backend.app.database import SessionLocal
from backend.app.models.models import Recruiter


class TestFrontier5AdaptiveReflexEngine:
    def test_01_reflex_synthesis_from_unfamiliar_layout(self, tmp_path):
        rules_file = str(tmp_path / "test_adaptive_rules.json")
        engine = AdaptiveReflexEngine(rules_path=rules_file)

        # Simulated unfamiliar DOM lines from a redesigned layout
        # (e.g. Profile banner changed, name is line 2, title is line 4 with weird punctuation)
        unfamiliar_lines = [
            "Search or jump to...",
            "Notifications",
            "Elena Rostova",                         # Line 2: Name
            "Open to work badge",
            "Lead Technical Sourcer at OpenAI",      # Line 4: Title @ Company
            "San Francisco, California",
            "500+ connections",
        ]

        healed = engine.heal_frame(
            ocr_lines=unfamiliar_lines,
            window_title="Elena Rostova | Talent Profile",
            platform="custom_ats",
        )

        assert healed is not None
        assert healed["canonical_name"] == "Elena Rostova"
        assert "Technical Sourcer" in healed["title"] or "Sourcer" in healed["title"]
        assert healed.get("is_adaptive_healed") is True
        assert engine.get_metrics()["rules_count"] == 1

        # Second test: Re-running on similar lines should hit the learned reflex rule immediately!
        healed_cached = engine.heal_frame(
            ocr_lines=unfamiliar_lines,
            window_title="Elena Rostova | Talent Profile",
            platform="custom_ats",
        )
        assert healed_cached is not None
        assert healed_cached["canonical_name"] == "Elena Rostova"
        # Hit count should now be 2
        assert engine.get_metrics()["heals_performed"] >= 2

    def test_02_noise_lines_not_synthesized_as_name(self, tmp_path):
        rules_file = str(tmp_path / "test_adaptive_noise.json")
        engine = AdaptiveReflexEngine(rules_path=rules_file)

        noise_lines = [
            "Home",
            "My Network",
            "Jobs",
            "Messaging",
            "Notifications",
            "Overview",
        ]

        healed = engine.heal_frame(
            ocr_lines=noise_lines,
            window_title="LinkedIn Feed",
            platform="linkedin",
        )
        assert healed is None


class TestFrontier2WaterfallOsintEngine:
    def test_01_gravatar_hash_beacon(self):
        engine = WaterfallOsintEngine()
        # Gravatar probe on a known email hash or format
        dossier = engine.enrich_candidate_data(
            name="Linus Torvalds",
            company="Linux Foundation",
            domain="linuxfoundation.org",
            existing_email="torvalds@linux-foundation.org"
        )
        assert dossier is not None
        assert dossier.recruiter_name == "Linus Torvalds"
        assert "gravatar_beacon" in dossier.surfaces_checked
        assert "duckduckgo_xray" in dossier.surfaces_checked

    def test_02_phone_regex_and_email_extraction(self):
        engine = WaterfallOsintEngine()
        sample_html = """
        <html>
            <body>
                Contact Sarah Connor at (415) 555-0199 or mobile +1 415-555-0188.
                Email us at sarah.connor@cyberdyne.com or personal sarahc99@gmail.com
            </body>
        </html>
        """
        # Test phone regex directly
        from backend.app.services.waterfall_osint_engine import PHONE_REGEX, EMAIL_REGEX
        phones = []
        for m in PHONE_REGEX.finditer(sample_html):
            area = m.group(1) or m.group(2)
            p1 = m.group(3)
            p2 = m.group(4)
            phones.append(f"+1 ({area}) {p1}-{p2}")

        assert len(phones) >= 2
        assert "+1 (415) 555-0199" in phones
        assert "+1 (415) 555-0188" in phones

        emails = EMAIL_REGEX.findall(sample_html)
        assert "sarah.connor@cyberdyne.com" in emails
        assert "sarahc99@gmail.com" in emails

    def test_03_db_recruiter_enrichment(self):
        engine = WaterfallOsintEngine()
        with SessionLocal() as db:
            # Create a test recruiter
            test_rec = Recruiter(
                recruiter_name="Alexander Hamilton",
                email="alexander.hamilton.test@example.com",
                title="Lead Recruiter",
                data_source="unit_test"
            )
            db.add(test_rec)
            db.commit()
            rec_id = test_rec.recruiter_id

            try:
                dossier = engine.enrich_recruiter(db, rec_id)
                assert dossier is not None
                assert dossier.recruiter_id == rec_id

                # Query refreshed record from DB
                refreshed = db.query(Recruiter).filter(Recruiter.recruiter_id == rec_id).first()
                assert refreshed is not None
                assert "OSINT Waterfall" in (refreshed.notes or "")

            finally:
                db.query(Recruiter).filter(Recruiter.recruiter_id == rec_id).delete()
                db.commit()
