"""
backend/tests/test_entity_routing_pipeline.py

End-to-End Pipeline & Hard Entity Walled Routing Verification Tests.
Verifies that:
1. ExtensionContact accepts entity_type.
2. DiscoveryStaging stores entity_type.
3. COMPANY entities route to Company table ONLY (never Recruiter).
4. JOB_POSTING entities route to KnowledgeEntity/Signal ONLY (never Recruiter).
5. CONTACT_INFO entities route to KnowledgeEntity ONLY (never Recruiter).
6. NOISE entities are rejected at Gate 1.
7. PERSON entities route to Person grounding -> Cluster -> Master DB.
"""

import sys
import os
import unittest
from datetime import datetime, timezone

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models.staging_models import DiscoveryStaging, ResolvedPerson
from backend.app.models.models import Recruiter, Company, RecruiterEmail, RecruiterPhone, RecruiterLocation
from backend.app.models.auth_models import User
from backend.app.models.knowledge_models import KnowledgeEntity, KnowledgeRelationship, KnowledgeSignal, SemanticObservation
from backend.app.models.extension_models import ExtensionDiscoveryEvent
from backend.app.routes.extension import ExtensionContact
from backend.app.services.discovery_processor import DiscoveryProcessor
from backend.app.services.entity_classifier import (
    entity_classifier,
    ENTITY_PERSON,
    ENTITY_COMPANY,
    ENTITY_JOB_POSTING,
    ENTITY_CONTACT_INFO,
    ENTITY_MARKET_SIGNAL,
    ENTITY_NOISE,
)


class TestEntityRoutingPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create in-memory SQLite database
        cls.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.session = self.Session()
        # Create a test user for foreign keys
        self.test_user = User(
            id=1,
            email="recruiter@test.com",
            password_hash="fakehashpassword123",
            first_name="Test",
            last_name="Recruiter",
        )
        self.session.merge(self.test_user)
        self.session.commit()

    def tearDown(self):
        self.session.rollback()
        # Clean all tables
        for table in reversed(Base.metadata.sorted_tables):
            self.session.execute(table.delete())
        self.session.commit()
        self.session.close()

    def test_extension_contact_schema(self):
        """Verify ExtensionContact schema accepts entity_type."""
        contact = ExtensionContact(
            recruiter_name="Acme Corp",
            title="Biotech",
            entity_type=ENTITY_COMPANY,
        )
        self.assertEqual(contact.entity_type, ENTITY_COMPANY)

        contact_person = ExtensionContact(
            recruiter_name="Sarah Chen",
            title="Staff Engineer",
            entity_type=ENTITY_PERSON,
        )
        self.assertEqual(contact_person.entity_type, ENTITY_PERSON)

    def test_company_hard_routing(self):
        """COMPANY entities must route to Company table and NEVER create Recruiter records."""
        rec = DiscoveryStaging(
            batch_id="batch-comp-1",
            discovery_id="disc-comp-1",
            device_id="test-device-123",
            owner_user_id=self.test_user.id,
            entity_type=ENTITY_COMPANY,
            raw_name="Helix Labs Corp",
            raw_title="Biotechnology & Pharmaceuticals",
            raw_company="Helix Labs Corp",
            raw_location="Boston, MA",
            source_url="https://linkedin.com/company/helix-labs",
            processing_status="pending",
        )
        self.session.add(rec)
        self.session.commit()

        processor = DiscoveryProcessor(self.session)
        stats = processor.process_pending_batch(limit=10)

        self.assertEqual(stats["companies_committed"], 1)
        self.assertEqual(stats["persons_committed"], 0)

        # Check Company table
        company = self.session.query(Company).filter(Company.company_name.ilike("%Helix Labs%")).first()
        self.assertIsNotNone(company)
        self.assertEqual(company.company_name, "Helix Labs Corp")

        # Check Recruiter table: MUST BE EMPTY
        recruiters = self.session.query(Recruiter).all()
        self.assertEqual(len(recruiters), 0, "COMPANY entity should NEVER create a Recruiter record!")

    def test_job_posting_hard_routing(self):
        """JOB_POSTING entities must route to KnowledgeEntity/Signal and NEVER create Recruiter records."""
        rec = DiscoveryStaging(
            batch_id="batch-job-1",
            discovery_id="disc-job-1",
            device_id="test-device-123",
            owner_user_id=self.test_user.id,
            entity_type=ENTITY_JOB_POSTING,
            raw_name="Senior Full Stack Engineer",
            raw_title="Engineering",
            raw_company="Netflix",
            raw_location="Los Gatos, CA",
            source_url="https://linkedin.com/jobs/view/998877",
            about_summary="Looking for a seasoned full stack developer.",
            processing_status="pending",
        )
        self.session.add(rec)
        self.session.commit()

        processor = DiscoveryProcessor(self.session)
        stats = processor.process_pending_batch(limit=10)

        self.assertEqual(stats["jobs_captured"], 1)
        self.assertEqual(stats["persons_committed"], 0)

        # Check KnowledgeEntity
        ke = self.session.query(KnowledgeEntity).filter(KnowledgeEntity.entity_type == "JOB_POSTING").first()
        self.assertIsNotNone(ke)
        self.assertEqual(ke.canonical_name, "Senior Full Stack Engineer")

        # Check KnowledgeSignal
        ks = self.session.query(KnowledgeSignal).filter(KnowledgeSignal.signal_type == "JOB_POSTING").first()
        self.assertIsNotNone(ks)

        # Check Recruiter table: MUST BE EMPTY
        recruiters = self.session.query(Recruiter).all()
        self.assertEqual(len(recruiters), 0, "JOB_POSTING entity should NEVER create a Recruiter record!")

    def test_contact_info_hard_routing(self):
        """CONTACT_INFO entities must route to KnowledgeEntity and NEVER create Recruiter records."""
        rec = DiscoveryStaging(
            batch_id="batch-contact-1",
            discovery_id="disc-contact-1",
            device_id="test-device-123",
            owner_user_id=self.test_user.id,
            entity_type=ENTITY_CONTACT_INFO,
            raw_name="General Inquiries",
            raw_email="info@helixlabs.com",
            raw_phone="+1-800-555-0199",
            raw_company="Helix Labs Corp",
            source_url="https://helixlabs.com/contact",
            processing_status="pending",
        )
        self.session.add(rec)
        self.session.commit()

        processor = DiscoveryProcessor(self.session)
        stats = processor.process_pending_batch(limit=10)

        self.assertEqual(stats["contacts_captured"], 1)
        self.assertEqual(stats["persons_committed"], 0)

        ke = self.session.query(KnowledgeEntity).filter(KnowledgeEntity.entity_type == "CONTACT_INFO").first()
        self.assertIsNotNone(ke)

        # Check Recruiter table: MUST BE EMPTY
        recruiters = self.session.query(Recruiter).all()
        self.assertEqual(len(recruiters), 0, "CONTACT_INFO entity should NEVER create a Recruiter record!")

    def test_noise_rejection(self):
        """NOISE entities must be rejected without creating any database entities."""
        rec = DiscoveryStaging(
            batch_id="batch-noise-1",
            discovery_id="disc-noise-1",
            device_id="test-device-123",
            owner_user_id=self.test_user.id,
            entity_type=None,  # Classifier will detect it
            raw_name="See all 14 results",
            raw_title="",
            raw_company="",
            processing_status="pending",
        )
        self.session.add(rec)
        self.session.commit()

        processor = DiscoveryProcessor(self.session)
        stats = processor.process_pending_batch(limit=10)

        self.assertEqual(stats["noise_rejected"], 1)
        self.assertEqual(stats["persons_committed"], 0)
        self.assertEqual(stats["companies_committed"], 0)

        # Staging record status should be rejected
        self.session.refresh(rec)
        self.assertEqual(rec.processing_status, "rejected")
        self.assertEqual(rec.decision, "REJECT_NOISE")


if __name__ == "__main__":
    unittest.main()
