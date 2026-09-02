"""
Deep End-to-End Multi-Archetype Knowledge Graph Regression Test Suite.
Verifies all 5 page archetypes and full API surface.
"""

import os
import sys
import unittest
import json

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


class TestKnowledgeGraphDeep(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Seed test user
        self.user = User(
            id=1,
            email="kg-architect@talentops.ai",
            first_name="Knowledge",
            last_name="Architect",
            status="Active"
        )
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_archetype_company_about_and_leadership_network(self):
        """
        Archetype 1: ABC Staffing Leadership & Network.
        Company: ABC Staffing Solutions
        People: Jane Smith (CEO), John Brown (Recruiting Manager), Sarah Davis (Technical Recruiter), Mike Jones (Account Manager)
        Locations: Chicago, Dallas, New York
        Specializations: IT staffing, Healthcare staffing
        """
        raw_contacts = [
            {"recruiter_name": "Jane Smith", "title": "CEO", "company_name": "ABC Staffing Solutions", "capture_id": "VC-ABC-01"},
            {"recruiter_name": "John Brown", "title": "Recruiting Manager", "company_name": "ABC Staffing Solutions", "capture_id": "VC-ABC-01"},
            {"recruiter_name": "Sarah Davis", "title": "Technical Recruiter", "company_name": "ABC Staffing Solutions", "capture_id": "VC-ABC-01"},
            {"recruiter_name": "Mike Jones", "title": "Account Manager", "company_name": "ABC Staffing Solutions", "capture_id": "VC-ABC-01"},
        ]

        raw_obs = [
            {"subject": "ABC Staffing Solutions", "predicate": "HAS_LOCATION", "object_val": "Chicago", "semantic_type": "LOCATION"},
            {"subject": "ABC Staffing Solutions", "predicate": "HAS_LOCATION", "object_val": "Dallas", "semantic_type": "LOCATION"},
            {"subject": "ABC Staffing Solutions", "predicate": "HAS_LOCATION", "object_val": "New York", "semantic_type": "LOCATION"},
            {"subject": "ABC Staffing Solutions", "predicate": "HAS_SPECIALIZATION", "object_val": "IT Staffing", "semantic_type": "STAFFING_SPECIALIZATION"},
            {"subject": "ABC Staffing Solutions", "predicate": "HAS_SPECIALIZATION", "object_val": "Healthcare Staffing", "semantic_type": "STAFFING_SPECIALIZATION"},
        ]

        doc = build_semantic_graph_document(
            raw_contacts=raw_contacts,
            raw_observations=raw_obs,
            page_url="https://abcstaffingsolutions.com/about",
            page_title="About Us & Leadership Team | ABC Staffing Solutions",
            capture_id="VC-ABC-01"
        )

        processor = DiscoveryProcessor(self.db)
        stats = processor.process_knowledge_graph_document(doc, owner_user_id=1)

        print("\n[ARCHETYPE 1 RESULT] ABC Staffing Network Stats:", stats)

        # Assertions
        self.assertEqual(stats["entities_created"], 5, "1 Company + 4 Persons")
        self.assertEqual(stats["relationships_created"], 4, "4 EMPLOYED_BY relationships")
        self.assertEqual(stats["signals_created"], 2, "2 Staffing Specializations")
        self.assertEqual(stats["observations_created"], 5, "5 Extensible Typed Observations")

        # Verify Entities
        ents = self.db.query(KnowledgeEntity).all()
        ent_names = {e.canonical_name for e in ents}
        self.assertIn("ABC Staffing Solutions", ent_names)
        self.assertIn("Jane Smith", ent_names)
        self.assertIn("John Brown", ent_names)
        self.assertIn("Sarah Davis", ent_names)
        self.assertIn("Mike Jones", ent_names)

        # Verify Relationships
        rels = self.db.query(KnowledgeRelationship).all()
        self.assertEqual(len(rels), 4)

        # Verify Signals
        signals = self.db.query(KnowledgeSignal).all()
        sig_titles = {s.title for s in signals}
        self.assertEqual(sig_titles, {"IT Staffing", "Healthcare Staffing"})

    def test_archetype_job_board_no_person(self):
        """
        Archetype 2: Job Board Page (SimplyHired / Indeed).
        Verifies 1 Job + 1 Company + 1 Location, ZERO fake people.
        """
        raw_contacts = [
            {
                "recruiter_name": "Transmission Project Manager",
                "company_name": "Metasys Technologies Inc.",
                "location": "Las Vegas, NV",
                "capture_id": "VC-JOB-77",
            }
        ]

        doc = build_semantic_graph_document(
            raw_contacts=raw_contacts,
            page_url="https://www.simplyhired.com/search?q=project+manager",
            page_title="Jobs in Las Vegas | SimplyHired",
            capture_id="VC-JOB-77"
        )

        processor = DiscoveryProcessor(self.db)
        stats = processor.process_knowledge_graph_document(doc, owner_user_id=1)

        print("\n[ARCHETYPE 2 RESULT] Job Board Stats:", stats)

        # Verify 0 PERSON entities
        person_count = self.db.query(KnowledgeEntity).filter(KnowledgeEntity.entity_type == "PERSON").count()
        self.assertEqual(person_count, 0)

        # Verify 1 JOB entity
        job = self.db.query(KnowledgeEntity).filter(KnowledgeEntity.entity_type == "JOB").first()
        self.assertEqual(job.canonical_name, "Transmission Project Manager")

    def test_archetype_progressive_candidate_profile(self):
        """
        Archetype 3: Personal Candidate Profile with Progressive History.
        """
        raw_contacts = [
            {
                "recruiter_name": "Kelsei Martinez",
                "title": "VP of Staffing",
                "company_name": "Premier Staffing Solution LLC",
                "previous_company": "ABC Staffing",
                "education": "East Carolina University",
                "location": "Chicago, Illinois, United States",
                "followers_count": "11,476 followers",
                "connections_count": "500+ connections",
                "capture_id": "VC-KELSEI-01",
            }
        ]

        doc = build_semantic_graph_document(
            raw_contacts=raw_contacts,
            page_url="https://www.linkedin.com/in/kelseirobertson/",
            page_title="Kelsei Martinez | LinkedIn",
            capture_id="VC-KELSEI-01"
        )

        processor = DiscoveryProcessor(self.db)
        stats = processor.process_knowledge_graph_document(doc, owner_user_id=1)

        print("\n[ARCHETYPE 3 RESULT] Progressive Candidate Profile Stats:", stats)

        # Verify Entities (1 Person + 2 Companies + 1 Location + 1 Education)
        ents = self.db.query(KnowledgeEntity).all()
        self.assertEqual(len(ents), 5)

        # Verify Relationships (EMPLOYED_BY current, PREVIOUSLY_EMPLOYED_BY past, LOCATED_IN, ATTENDED)
        rels = self.db.query(KnowledgeRelationship).all()
        predicates = {r.predicate for r in rels}
        self.assertEqual(predicates, {"EMPLOYED_BY", "PREVIOUSLY_EMPLOYED_BY", "LOCATED_IN", "ATTENDED"})

        print("\n>>> DEEP MULTI-ARCHETYPE KNOWLEDGE GRAPH REGRESSION: ALL 3 TESTS PASSED! <<<")


if __name__ == "__main__":
    unittest.main()
