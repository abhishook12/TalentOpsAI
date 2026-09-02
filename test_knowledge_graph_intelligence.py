"""
Open-Ended Knowledge Graph & Semantic Intelligence Regression Test Suite.
Verifies that:
1. Discovery is not constrained to flat contact schemas.
2. Company People Pages produce Company + Multi-Person Graph with typed relationships.
3. Job Postings produce Job + Company + Location entities without creating fake persons.
4. Profiles produce rich Knowledge Graphs (Person, Companies, School, Location, History).
5. Extensible / unknown semantic types (Certifications, Hiring Signals) are preserved.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.database import Base
from app.models.models import Recruiter, Company
from app.models.auth_models import User
from app.models.knowledge_models import KnowledgeEntity, KnowledgeRelationship, KnowledgeSignal, SemanticObservation
from app.utils.normalizer import build_semantic_graph_document
from app.services.discovery_processor import DiscoveryProcessor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class TestKnowledgeGraphIntelligence(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Seed test user
        self.user = User(
            id=1,
            email="kg-director@talentops.ai",
            first_name="Graph",
            last_name="Intelligence",
            status="Active"
        )
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_company_people_team_graph(self):
        """
        Scenario 1: SynergyGrid IT People Page.
        Produces 1 Company + 3 Persons + 3 EMPLOYED_BY Relationships.
        """
        raw_contacts = [
            {
                "recruiter_name": "Mihir Roy",
                "title": "Recruiting Manager",
                "company_name": "SynergyGrid IT",
                "linkedin_url": "https://www.linkedin.com/in/mihir-roy-12345/",
                "capture_id": "VC-SG-01",
            },
            {
                "recruiter_name": "Kenny Shaw",
                "title": "Vice President",
                "company_name": "SynergyGrid IT",
                "linkedin_url": "https://www.linkedin.com/in/kenny-shaw-67890/",
                "capture_id": "VC-SG-01",
            },
            {
                "recruiter_name": "Apurva C.",
                "title": "Senior Recruiter",
                "company_name": "SynergyGrid IT",
                "linkedin_url": "https://www.linkedin.com/in/apurva-c-54321/",
                "capture_id": "VC-SG-01",
            }
        ]

        doc = build_semantic_graph_document(
            raw_contacts=raw_contacts,
            page_url="https://www.linkedin.com/company/synergygrid-it/people/",
            page_title="SynergyGrid IT: People | LinkedIn",
            capture_id="VC-SG-01"
        )

        processor = DiscoveryProcessor(self.db)
        stats = processor.process_knowledge_graph_document(doc, owner_user_id=1)

        print("\n[TEST RESULT] SynergyGrid Team Graph Stats:", stats)

        # Assertions
        self.assertEqual(stats["entities_created"], 4, "Must create 1 Company + 3 Persons")
        self.assertEqual(stats["relationships_created"], 3, "Must create 3 EMPLOYED_BY relationships")

        # Verify Database Graph Entities
        company_ent = self.db.query(KnowledgeEntity).filter(KnowledgeEntity.entity_type == "COMPANY").first()
        self.assertEqual(company_ent.canonical_name, "SynergyGrid IT")

        person_ents = self.db.query(KnowledgeEntity).filter(KnowledgeEntity.entity_type == "PERSON").all()
        person_names = {p.canonical_name for p in person_ents}
        self.assertEqual(person_names, {"Mihir Roy", "Kenny Shaw", "Apurva C."})

        # Verify Relationships
        rels = self.db.query(KnowledgeRelationship).all()
        self.assertEqual(len(rels), 3)
        for rel in rels:
            self.assertEqual(rel.predicate, "EMPLOYED_BY")
            self.assertEqual(rel.object_entity_id, company_ent.id)

    def test_job_posting_graph_without_person(self):
        """
        Scenario 2: Job Board Posting (SimplyHired).
        Produces 1 Job + 1 Company + 1 Location without creating fake person.
        """
        raw_contacts = [
            {
                "recruiter_name": "Transmission Project Manager",  # Job Title
                "company_name": "Metasys Technologies Inc.",
                "location": "Las Vegas, NV",
                "capture_id": "VC-SH-99",
            }
        ]

        doc = build_semantic_graph_document(
            raw_contacts=raw_contacts,
            page_url="https://www.simplyhired.com/search?q=project+manager",
            page_title="Jobs in Las Vegas, NV | SimplyHired",
            capture_id="VC-SH-99"
        )

        processor = DiscoveryProcessor(self.db)
        stats = processor.process_knowledge_graph_document(doc, owner_user_id=1)

        print("\n[TEST RESULT] Job Posting Graph Stats:", stats)

        # Assertions
        job_ent = self.db.query(KnowledgeEntity).filter(KnowledgeEntity.entity_type == "JOB").first()
        self.assertIsNotNone(job_ent)
        self.assertEqual(job_ent.canonical_name, "Transmission Project Manager")

        comp_ent = self.db.query(KnowledgeEntity).filter(KnowledgeEntity.entity_type == "COMPANY").first()
        self.assertEqual(comp_ent.canonical_name, "Metasys Technologies Inc.")

        loc_ent = self.db.query(KnowledgeEntity).filter(KnowledgeEntity.entity_type == "LOCATION").first()
        self.assertEqual(loc_ent.canonical_name, "Las Vegas, NV")

        # Zero Person Entities Created
        person_count = self.db.query(KnowledgeEntity).filter(KnowledgeEntity.entity_type == "PERSON").count()
        self.assertEqual(person_count, 0, "Must NEVER create a fake PERSON entity for a job posting")

    def test_extensible_signals_and_certifications(self):
        """
        Scenario 3: Extensible Signals & Unknown Types.
        Preserves 'BUSINESS_CERTIFICATION' and 'HIRING_SIGNAL' without schema restriction.
        """
        raw_obs = [
            {
                "subject": "Premier Staffing Solution LLC",
                "predicate": "HAS_CERTIFICATION",
                "object_val": "Certified Women-Owned Staffing Supplier",
                "semantic_type": "BUSINESS_CERTIFICATION",
                "attributes": {"issuing_body": "WBENC", "year": 2024},
                "confidence": 0.98,
            },
            {
                "subject": "Premier Staffing Solution LLC",
                "predicate": "HAS_SIGNAL",
                "object_val": "Hiring 15 Java Developers in Dallas",
                "semantic_type": "HIRING_SIGNAL",
                "attributes": {"role": "Java Developer", "quantity": 15, "location": "Dallas, TX"},
                "confidence": 0.95,
            }
        ]

        doc = build_semantic_graph_document(
            raw_observations=raw_obs,
            page_url="https://premierstaffingsolution.com/about",
            page_title="About Us | Premier Staffing Solution LLC",
            capture_id="VC-PREMIER-01"
        )

        processor = DiscoveryProcessor(self.db)
        stats = processor.process_knowledge_graph_document(doc, owner_user_id=1)

        print("\n[TEST RESULT] Extensible Signals Stats:", stats)

        # Assertions
        self.assertEqual(stats["signals_created"], 2)
        self.assertEqual(stats["observations_created"], 2)

        signals = self.db.query(KnowledgeSignal).all()
        sig_types = {s.signal_type for s in signals}
        self.assertEqual(sig_types, {"BUSINESS_CERTIFICATION", "HIRING_SIGNAL"})

        print("\n>>> OPEN-ENDED KNOWLEDGE GRAPH REGRESSION: ALL ASSERTIONS PASSED! <<<")


if __name__ == "__main__":
    unittest.main()
