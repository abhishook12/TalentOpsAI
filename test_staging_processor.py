import os
import sys
import unittest
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.models import Recruiter, Company
from app.models.auth_models import User
from app.models.staging_models import DiscoveryStaging, ResolvedPerson
from app.models.extension_models import ExtensionDiscoveryEvent
from app.services.discovery_processor import DiscoveryProcessor, run_batch_processor

class TestDiscoveryProcessor(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Seed test user
        self.test_user = User(
            id=1,
            email="abhishekjadon824@gmail.com",
            first_name="Abhishek",
            last_name="Jadon",
            password_hash="test_pw_hash",
        )
        self.db.add(self.test_user)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_john_smith_multi_observation_accumulation_and_job_change(self):
        """
        Key Test Case:
        5 separate observations of John Smith captured at different frames:
        - Observation 1: John Smith / Recruiter / Apex Systems / (no email) / LinkedIn: /in/john-smith-talent
        - Observation 2: John Smith 1st / Senior Recruiter / Apex Systems / (no email) / phone: +1-555-0199
        - Observation 3: John Smith / Lead Talent Partner / Insight Global (Job changed!) / email: john.smith@insightglobal.com / LinkedIn: /in/john-smith-talent
        - Observation 4: John Smith / Lead Talent Partner / Insight Global / phone: +1-555-0199 / location: Austin, TX
        - Observation 5: Duplicate frame of Observation 4

        The system MUST:
        1. Cluster all 5 observations into 1 single ResolvedPerson.
        2. Recognize the job transition (Apex Systems -> Insight Global).
        3. Consolidate contact channels (email, phone, LinkedIn, location).
        4. Commit as ONE clean master Recruiter record.
        """
        processor = DiscoveryProcessor(self.db)

        # Insert 5 staged observations
        obs1 = DiscoveryStaging(
            batch_id="BATCH-TEST-1",
            discovery_id="DISC-001",
            device_id="dev-1",
            owner_user_id=1,
            raw_name="John Smith",
            raw_title="Recruiter",
            raw_company="Apex Systems",
            raw_linkedin="https://www.linkedin.com/in/john-smith-talent/",
            processing_status="pending"
        )
        obs2 = DiscoveryStaging(
            batch_id="BATCH-TEST-1",
            discovery_id="DISC-002",
            device_id="dev-1",
            owner_user_id=1,
            raw_name="John Smith 1st degree connection",
            raw_title="Senior Recruiter",
            raw_company="Apex Systems",
            raw_phone="+1-555-0199",
            raw_linkedin="https://www.linkedin.com/in/john-smith-talent",
            processing_status="pending"
        )
        obs3 = DiscoveryStaging(
            batch_id="BATCH-TEST-1",
            discovery_id="DISC-003",
            device_id="dev-1",
            owner_user_id=1,
            raw_name="John Smith",
            raw_title="Lead Talent Partner",
            raw_company="Insight Global",
            raw_email="john.smith@insightglobal.com",
            raw_linkedin="https://www.linkedin.com/in/john-smith-talent/",
            processing_status="pending"
        )
        obs4 = DiscoveryStaging(
            batch_id="BATCH-TEST-1",
            discovery_id="DISC-004",
            device_id="dev-1",
            owner_user_id=1,
            raw_name="John Smith",
            raw_title="Lead Talent Partner",
            raw_company="Insight Global",
            raw_phone="+1-555-0199",
            raw_location="Austin, TX",
            raw_linkedin="https://www.linkedin.com/in/john-smith-talent/",
            processing_status="pending"
        )
        obs5 = DiscoveryStaging(
            batch_id="BATCH-TEST-1",
            discovery_id="DISC-005",
            device_id="dev-1",
            owner_user_id=1,
            raw_name="John Smith",
            raw_title="Lead Talent Partner",
            raw_company="Insight Global",
            raw_email="john.smith@insightglobal.com",
            raw_phone="+1-555-0199",
            raw_location="Austin, TX",
            raw_linkedin="https://www.linkedin.com/in/john-smith-talent/",
            processing_status="pending"
        )

        self.db.add_all([obs1, obs2, obs3, obs4, obs5])
        self.db.commit()

        # Run Batch Processing
        stats = processor.process_pending_batch()
        print("\n[TEST RESULT] Batch Processor Stats:", stats)

        # Assertions
        self.assertEqual(stats['processed'], 5)
        self.assertEqual(stats['new'], 1)  # Only ONE master recruiter created!

        # Check ResolvedPerson in DB
        resolved_persons = self.db.query(ResolvedPerson).all()
        self.assertEqual(len(resolved_persons), 1)

        rp = resolved_persons[0]
        print(f"[TEST RESULT] Resolved Person: {rp.canonical_name}")
        print(f"  Current Company: {rp.current_company}")
        print(f"  Previous Company: {rp.previous_company}")
        print(f"  Primary Email: {rp.primary_email}")
        print(f"  Primary Phone: {rp.primary_phone}")
        print(f"  LinkedIn: {rp.linkedin_url}")
        print(f"  Observations: {rp.observation_count}")
        print(f"  Identity Confidence: {rp.identity_confidence}")

        self.assertEqual(rp.canonical_name, "John Smith")
        self.assertEqual(rp.current_company, "Insight Global")
        self.assertEqual(rp.previous_company, "Apex Systems")
        self.assertEqual(rp.primary_email, "john.smith@insightglobal.com")
        self.assertEqual(rp.primary_phone, "+1-555-0199")
        self.assertEqual(rp.observation_count, 5)
        self.assertGreaterEqual(rp.identity_confidence, 0.80)

        # Check Master Recruiter in DB
        recruiters = self.db.query(Recruiter).all()
        self.assertEqual(len(recruiters), 1)
        r = recruiters[0]
        self.assertEqual(r.recruiter_name, "John Smith")
        self.assertEqual(r.email, "john.smith@insightglobal.com")
        self.assertEqual(r.phone, "+1-555-0199")
        self.assertEqual(r.location, "Austin, TX")

        # Check all 5 staging records marked committed
        staged_all = self.db.query(DiscoveryStaging).all()
        self.assertEqual(len(staged_all), 5)
        for s in staged_all:
            self.assertEqual(s.processing_status, "committed")
            self.assertEqual(s.decision, "NEW")

    def test_enrichment_of_existing_recruiter(self):
        """
        Verify that discovering new fields for an existing recruiter triggers ENRICH,
        not a duplicate entry or new person.
        """
        # Create existing master recruiter
        comp = Company(company_name="Google", canonical_name="Google", primary_domain="google.com")
        self.db.add(comp)
        self.db.flush()

        existing = Recruiter(
            user_id=1,
            recruiter_name="Sarah Connor",
            email="sarah.connor@google.com",
            title="Senior Technical Recruiter",
            company_id=comp.company_id,
            linkedin="https://www.linkedin.com/in/sarah-connor-talent",
            phone=None, # Missing phone!
            location=None, # Missing location!
        )
        self.db.add(existing)
        self.db.commit()

        # Staged observation with newly discovered phone and location
        stg = DiscoveryStaging(
            batch_id="BATCH-ENRICH-1",
            discovery_id="DISC-ENRICH-01",
            device_id="dev-1",
            owner_user_id=1,
            raw_name="Sarah Connor",
            raw_email="sarah.connor@google.com",
            raw_phone="+1-555-9876",
            raw_location="San Francisco, CA",
            raw_linkedin="https://www.linkedin.com/in/sarah-connor-talent",
            raw_company="Google",
            processing_status="pending",
        )
        self.db.add(stg)
        self.db.commit()

        processor = DiscoveryProcessor(self.db)
        stats = processor.process_pending_batch()
        print("\n[TEST RESULT] Enrichment Stats:", stats)

        self.assertEqual(stats['enriched'], 1)
        self.assertEqual(stats['new'], 0)

        # Verify existing recruiter was enriched in place
        self.db.refresh(existing)
        self.assertEqual(existing.phone, "+1-555-9876")
        self.assertEqual(existing.location, "San Francisco, CA")

    def test_conflict_detection(self):
        """
        Verify that conflicting corporate email domains or LinkedIn profiles route to CONFLICT / REVIEW.
        """
        comp = Company(company_name="Meta", canonical_name="Meta", primary_domain="meta.com")
        self.db.add(comp)
        self.db.flush()

        existing = Recruiter(
            user_id=1,
            recruiter_name="Alex Mercer",
            email="alex@meta.com",
            linkedin="https://www.linkedin.com/in/alex-mercer-meta",
            company_id=comp.company_id,
        )
        self.db.add(existing)
        self.db.commit()

        # Contradictory observation: same name, but completely different LinkedIn
        stg = DiscoveryStaging(
            batch_id="BATCH-CONF-1",
            discovery_id="DISC-CONF-01",
            device_id="dev-1",
            owner_user_id=1,
            raw_name="Alex Mercer",
            raw_linkedin="https://www.linkedin.com/in/alex-mercer-different-person",
            raw_company="Meta",
            processing_status="pending",
        )
        self.db.add(stg)
        self.db.commit()

        processor = DiscoveryProcessor(self.db)
        stats = processor.process_pending_batch()
        print("\n[TEST RESULT] Conflict Detection Stats:", stats)

        self.assertEqual(stats['conflict'], 1)
        self.assertEqual(stats['review'], 1)
        self.assertEqual(stats['new'], 0)
        self.assertEqual(stats['enriched'], 0)

        # Staging record should be in review status
        self.db.refresh(stg)
        self.assertEqual(stg.processing_status, "review")
        self.assertEqual(stg.decision, "CONFLICT")

if __name__ == "__main__":
    unittest.main()
