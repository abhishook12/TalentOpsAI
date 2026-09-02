"""
Universal Hard Invariant & Semantic Classifier Test Suite.
Exhaustively verifies that:
1. UI actions ('Connect', 'Contact', 'Message', 'Apply', etc.) are NEVER titles or names.
2. Platform names ('LinkedIn', 'Indeed', 'Glassdoor', etc.) are NEVER employer companies.
3. Multi-platform title & company splitting and page-context inheritance works across all sources.
4. Component confidences are computed honestly.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.utils.normalizer import (
    is_ui_action,
    is_platform_name,
    clean_title,
    clean_company,
    split_title_and_company,
    calculate_field_confidences,
    UI_ACTION_TERMS,
    PLATFORM_NAMES,
)
from app.database import Base
from app.models.models import Recruiter, Company
from app.models.auth_models import User
from app.models.staging_models import DiscoveryStaging, ResolvedPerson
from app.services.discovery_processor import DiscoveryProcessor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

class TestUniversalHardInvariants(unittest.TestCase):

    def test_ui_action_rejection(self):
        """Verify all UI action buttons are rejected from titles."""
        test_actions = [
            "Connect", "Contact", "Message", "Follow", "Following", "Pending",
            "See more", "Show all", "View profile", "More", "Save", "Saved",
            "Apply", "Easy Apply", "Apply Now", "Quick Apply", "Submit",
            "Visit website", "Join Now", "Sign In", "Mutual connection"
        ]

        for act in test_actions:
            self.assertTrue(is_ui_action(act), f"'{act}' must be classified as UI action")
            self.assertIsNone(clean_title(act), f"'{act}' must be cleaned to None for title")

    def test_platform_name_rejection(self):
        """Verify platform names are never treated as employer companies."""
        test_platforms = [
            "LinkedIn", "Indeed", "Glassdoor", "ZipRecruiter", "Monster",
            "Dice", "CareerBuilder", "Greenhouse", "Lever", "Workday",
            "Google", "TalentOps", "Wellfound"
        ]

        for plat in test_platforms:
            self.assertTrue(is_platform_name(plat), f"'{plat}' must be classified as platform name")
            # Without page context -> None
            self.assertIsNone(clean_company(plat), f"'{plat}' without context must be None")
            # With page context -> inherited page context
            self.assertEqual(clean_company(plat, "Stripe"), "Stripe", f"'{plat}' with page context 'Stripe' must become 'Stripe'")

    def test_title_and_company_splitting(self):
        """Verify universal title/company extraction and headline splitting."""
        cases = [
            # (raw_title, raw_company, page_context, expected_title, expected_company)
            ("Recruiting Manager at SynergyGrid IT", None, None, "Recruiting Manager", "SynergyGrid IT"),
            ("VP of Talent @ Snowflake | San Mateo", "LinkedIn", None, "VP of Talent", "Snowflake"),
            ("Senior Recruiter", "Indeed", "Akkodis", "Senior Recruiter", "Akkodis"),
            ("Contact", "LinkedIn", "Microsoft", "Professional", "Microsoft"),
            ("Lead Technical Sourcer", None, "Databricks: People | LinkedIn", "Lead Technical Sourcer", "Databricks"),
            ("Apply Now", "Glassdoor", "Apple Inc.", "Professional", "Apple Inc."),
        ]

        for raw_t, raw_c, page_ctx, exp_t, exp_c in cases:
            t, c = split_title_and_company(raw_t, raw_c, page_ctx)
            self.assertEqual(t, exp_t, f"Title mismatch for '{raw_t}': got '{t}', expected '{exp_t}'")
            self.assertEqual(c, exp_c, f"Company mismatch for '{raw_t}': got '{c}', expected '{exp_c}'")

    def test_component_confidences(self):
        """Verify honest component confidence scoring."""
        # 1. Invalid title & company -> low confidence
        bad_conf = calculate_field_confidences(
            name="Mihir Roy",
            title="Contact",      # UI action -> title_conf 0
            company="LinkedIn",   # Platform name -> comp_conf 0
        )
        self.assertEqual(bad_conf["title"], 0, "UI action title must receive 0 title confidence")
        self.assertEqual(bad_conf["company"], 0, "Platform company must receive 0 company confidence")
        self.assertLessEqual(bad_conf["overall"], 50, "Bad record must not get high overall score")

        # 2. Legitimate profile -> high confidence
        good_conf = calculate_field_confidences(
            name="Mihir Roy",
            title="Recruiting Manager",
            company="SynergyGrid IT",
            linkedin="https://www.linkedin.com/in/mihir-roy/"
        )
        self.assertGreaterEqual(good_conf["name"], 90)
        self.assertGreaterEqual(good_conf["title"], 90)
        self.assertGreaterEqual(good_conf["company"], 90)
        self.assertGreaterEqual(good_conf["overall"], 90)

    def test_cross_platform_batch_pipeline(self):
        """Verify batch processor ingests multi-platform records without platform corruption."""
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        user = User(id=1, email="test@talentops.ai", first_name="Test", last_name="User", status="Active")
        db.add(user)
        db.commit()

        # Observations across 4 different platforms
        obs = [
            DiscoveryStaging(
                batch_id="BATCH-MULTI-01",
                discovery_id="DISC-IND-01",
                device_id="DEV-01",
                owner_user_id=1,
                raw_name="Sarah Connor",
                raw_title="Senior Talent Lead",
                raw_company="Indeed", # Platform name -> should inherit Cyberdyne from page
                raw_linkedin="https://www.linkedin.com/in/sarah-connor-talent",
                source_url="https://www.indeed.com/cmp/cyberdyne-systems",
                source_page_title="Cyberdyne Systems Careers",
                processing_status="pending"
            ),
            DiscoveryStaging(
                batch_id="BATCH-MULTI-01",
                discovery_id="DISC-GLS-01",
                device_id="DEV-01",
                owner_user_id=1,
                raw_name="Marcus Wright",
                raw_title="Apply on Company Site", # UI action -> should become Professional
                raw_company="Waymo",
                raw_email="mwright@waymo.com",
                raw_location="Mountain View, CA",
                source_url="https://www.glassdoor.com/job/waymo",
                source_page_title="Waymo: Recruiter Job",
                processing_status="pending"
            )
        ]
        db.add_all(obs)
        db.commit()

        processor = DiscoveryProcessor(db)
        stats = processor.process_pending_batch()

        self.assertEqual(stats["processed"], 2)
        self.assertEqual(stats["new"], 2)

        p1 = db.query(ResolvedPerson).filter(ResolvedPerson.canonical_name == "Sarah Connor").first()
        self.assertIsNotNone(p1)
        self.assertEqual(p1.current_company, "Cyberdyne Systems", "Sarah must inherit Cyberdyne Systems from page context")
        self.assertNotEqual(p1.current_company, "Indeed")

        p2 = db.query(ResolvedPerson).filter(ResolvedPerson.canonical_name == "Marcus Wright").first()
        self.assertIsNotNone(p2)
        self.assertEqual(p2.current_title, "Professional", "UI action 'Apply on Company Site' must be cleaned to 'Professional'")
        self.assertEqual(p2.current_company, "Waymo")

        db.close()

if __name__ == "__main__":
    unittest.main()
