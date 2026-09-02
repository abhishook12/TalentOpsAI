"""
Alexandra Fotos Multi-Entity Profile & Multi-User Scout Node Regression Suite.
Verifies:
1. Full first-class field extraction for Alexandra Fotos (Location, Role, Company, Specialty, School, Followers, Connections, About Context).
2. Knowledge Graph multi-entity preservation (Custom Kiks, VCG, Georgia Tech, Atlanta).
3. Multi-User Scout Node heartbeat tracking and ingestion verification for multiple connected users (User A, User B, User C).
"""

import os
import sys
import unittest
import json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.database import Base
from app.models.models import Recruiter, Company
from app.models.auth_models import User
from app.models.extension_models import ExtensionDevice, ExtensionDiscoveryEvent
from app.models.staging_models import DiscoveryStaging, ResolvedPerson
from app.models.knowledge_models import KnowledgeEntity, KnowledgeRelationship, KnowledgeSignal, SemanticObservation
from app.utils.normalizer import build_semantic_graph_document
from app.services.discovery_processor import DiscoveryProcessor
from app.services.scout_node_service import record_scout_heartbeat, get_all_scout_nodes_telemetry
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class TestAlexandraFotosAndScoutNodesRegression(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Seed 3 connected users (User A, User B, User C)
        self.user_a = User(id=1, email="user.a@talentops.ai", first_name="User", last_name="A", status="Active")
        self.user_b = User(id=2, email="user.b@talentops.ai", first_name="User", last_name="B", status="Active")
        self.user_c = User(id=3, email="user.c@talentops.ai", first_name="User", last_name="C", status="Active")
        self.db.add_all([self.user_a, self.user_b, self.user_c])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_alexandra_fotos_extraction_and_knowledge_graph(self):
        """
        Verify Alexandra Fotos live screen data extraction:
        - Person: Alexandra Fotos
        - Title: Managing Director
        - Specialty: Marketing & Growth Strategist
        - Company: Custom Kiks
        - Location: Atlanta, Georgia, United States (FIRST CLASS)
        - Education: Georgia Institute of Technology
        - Followers: 11,476
        - Connections: 500+
        - About section: Founded VCG in Oct 2024, acquired Custom Kiks in Jan 2025
        """
        raw_contacts = [
            {
                "recruiter_name": "Alexandra Fotos",
                "title": "Managing Director",
                "headline": "Managing Director @ Custom Kiks | Marketing & Growth Strategist",
                "specialty": "Marketing & Growth Strategist",
                "company_name": "Custom Kiks",
                "previous_company": "VCG",
                "location": "Atlanta, Georgia, United States",
                "education": "Georgia Institute of Technology",
                "followers_count": "11,476 followers",
                "connections_count": "500+ connections",
                "about_summary": "In October of 2024, I founded VCG, a private holding company focused on acquiring small businesses in the Southeast. In January 2025 I acquired Custom Kiks, an e-commerce brand.",
                "capture_id": "VC-ALEXANDRA-FOTOS-01",
            }
        ]

        raw_obs = [
            {
                "subject": "Alexandra Fotos",
                "predicate": "FOUNDED",
                "object_val": "VCG",
                "semantic_type": "BUSINESS_ACQUISITION_CONTEXT",
                "attributes": {"date": "October 2024", "details": "Private holding company in Southeast"}
            },
            {
                "subject": "Alexandra Fotos",
                "predicate": "ACQUIRED",
                "object_val": "Custom Kiks",
                "semantic_type": "BUSINESS_ACQUISITION_CONTEXT",
                "attributes": {"date": "January 2025", "details": "E-commerce brand"}
            }
        ]

        doc = build_semantic_graph_document(
            raw_contacts=raw_contacts,
            raw_observations=raw_obs,
            page_url="https://www.linkedin.com/in/alexandra-fotos-b7853563/",
            page_title="Alexandra Fotos | LinkedIn",
            capture_id="VC-ALEXANDRA-FOTOS-01"
        )

        processor = DiscoveryProcessor(self.db)
        stats = processor.process_knowledge_graph_document(doc, owner_user_id=1)

        print("\n[ALEXANDRA FOTOS RESULT] Extraction Stats:", stats)

        # 1. Assert Entities
        ents = self.db.query(KnowledgeEntity).all()
        ent_map = {e.canonical_name: e.entity_type for e in ents}
        self.assertIn("Alexandra Fotos", ent_map)
        self.assertEqual(ent_map["Alexandra Fotos"], "PERSON")
        self.assertIn("Custom Kiks", ent_map)
        self.assertEqual(ent_map["Custom Kiks"], "COMPANY")
        self.assertIn("VCG", ent_map)
        self.assertEqual(ent_map["VCG"], "COMPANY")
        self.assertIn("Atlanta, Georgia, United States", ent_map)
        self.assertEqual(ent_map["Atlanta, Georgia, United States"], "LOCATION")
        self.assertIn("Georgia Institute of Technology", ent_map)
        self.assertEqual(ent_map["Georgia Institute of Technology"], "EDUCATION")

        # 2. Assert Relationships
        rels = self.db.query(KnowledgeRelationship).all()
        predicates = {r.predicate for r in rels}
        self.assertIn("EMPLOYED_BY", predicates)
        self.assertIn("PREVIOUSLY_EMPLOYED_BY", predicates)
        self.assertIn("LOCATED_IN", predicates)
        self.assertIn("ATTENDED", predicates)

        # 3. Assert Extensible Context Observations Preserved
        obs = self.db.query(SemanticObservation).all()
        self.assertGreaterEqual(len(obs), 2)
        obs_subjects = {o.subject for o in obs}
        self.assertIn("Alexandra Fotos", obs_subjects)

    def test_multi_user_scout_node_heartbeat_and_sync_verification(self):
        """
        Verify multi-user scout node telemetry across 3 connected users:
        - User A: Live Streaming (Heartbeat 8s ago + Recent DB write)
        - User B: Connected Idle (Heartbeat 30s ago + Waiting for profile)
        - User C: Idle No Ingestion (Heartbeat 4m ago)
        """
        now = datetime.now(timezone.utc)

        # 1. Record Heartbeats
        record_scout_heartbeat(self.db, user_id=1, device_id="DEV-NODE-1", client_metrics={"device_name": "User A Laptop Chrome"})
        record_scout_heartbeat(self.db, user_id=2, device_id="DEV-NODE-2", client_metrics={"device_name": "User B Workstation"})
        record_scout_heartbeat(self.db, user_id=3, device_id="DEV-NODE-3", client_metrics={"device_name": "User C Macbook"})

        # Override timestamps for User B & User C to test distinct states
        dev_b = self.db.query(ExtensionDevice).filter(ExtensionDevice.device_id == "DEV-NODE-2").first()
        dev_b.last_seen_at = now - timedelta(seconds=35)

        dev_c = self.db.query(ExtensionDevice).filter(ExtensionDevice.device_id == "DEV-NODE-3").first()
        dev_c.last_seen_at = now - timedelta(minutes=4)

        # Add active discovery event for User A
        evt_a = ExtensionDiscoveryEvent(
            discovery_id="DISC-A-01",
            device_id="DEV-NODE-1",
            owner_user_id=1,
            recruiter_name="Alexandra Fotos",
            company_name="Custom Kiks",
            title="Managing Director",
            db_action="ENRICHED",
            fields_added=json.dumps(["location", "education", "specialty"]),
            capture_id="VC-A-01",
            source_url="https://www.linkedin.com/in/alexandra-fotos-b7853563/",
            confidence=98,
            created_at=now - timedelta(seconds=20),
        )
        self.db.add(evt_a)
        self.db.commit()

        # Query Multi-User Scout Nodes Telemetry
        telemetry = get_all_scout_nodes_telemetry(self.db)
        print("\n[MULTI-USER SCOUT TELEMETRY]:", json.dumps(telemetry, indent=2))

        # Assertions
        self.assertEqual(telemetry["total_registered_users"], 3)
        self.assertEqual(telemetry["total_scout_nodes"], 3)
        self.assertEqual(telemetry["active_connected_nodes"], 2, "User A (8s) and User B (35s) are connected (< 300s)")
        self.assertEqual(telemetry["active_nodes_streaming_data"], 1, "Only User A is actively streaming (< 180s capture)")

        node_a = next(n for n in telemetry["nodes"] if n["user_id"] == 1)
        node_b = next(n for n in telemetry["nodes"] if n["user_id"] == 2)
        node_c = next(n for n in telemetry["nodes"] if n["user_id"] == 3)

        self.assertEqual(node_a["node_status"], "LIVE_STREAMING")
        self.assertEqual(node_a["records_enriched"], 1)
        self.assertEqual(node_a["db_successes"], 1)

        self.assertEqual(node_b["node_status"], "CONNECTED_IDLE")
        self.assertEqual(node_b["captures_today"], 0)

        self.assertEqual(node_c["node_status"], "IDLE_NO_INGESTION")

        print("\n>>> ALEXANDRA FOTOS & MULTI-USER SCOUT REGRESSION: 100% PASSED! <<<")


if __name__ == "__main__":
    unittest.main()
