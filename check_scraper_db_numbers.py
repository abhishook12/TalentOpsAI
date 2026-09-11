"""
Audit script to check:
1. Total observations/contacts pulled by the scraper.
2. Number of new records created in master DB by scraper.
3. Number of existing records enriched in master DB by scraper.
4. Total recruiters in the master DB.
5. Exact breakdown and verification of whether numbers match.
"""

import os
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.database import SessionLocal, engine
from sqlalchemy import text
from app.models.models import Recruiter, Company
from app.models.staging_models import DiscoveryStaging, ResolvedPerson
from app.models.extension_models import (
    ExtensionDiscoveryEvent,
    ExtensionSubmissionLog,
    ExtensionDevice,
    ExtensionHeartbeat
)
from app.models.knowledge_models import (
    KnowledgeEntity,
    KnowledgeRelationship,
    KnowledgeSignal,
    SemanticObservation
)


def inspect_scraper_vs_master_db():
    print("=" * 80)
    print("AUDITING LIVE DATABASE: SCRAPER VS MASTER DATABASE")
    print("=" * 80)

    try:
        with SessionLocal() as db:
            # 1. Total in master DB
            total_recruiters = db.query(Recruiter).count()
            extension_recruiters = db.query(Recruiter).filter(Recruiter.data_source == 'extension').count()
            
            # 2. Extension events
            total_events = db.query(ExtensionDiscoveryEvent).count()
            new_discoveries = db.query(ExtensionDiscoveryEvent).filter(ExtensionDiscoveryEvent.db_action == 'NEW_DISCOVERY').count()
            enriched_records = db.query(ExtensionDiscoveryEvent).filter(ExtensionDiscoveryEvent.db_action == 'ENRICHED').count()
            duplicates_seen = db.query(ExtensionDiscoveryEvent).filter(ExtensionDiscoveryEvent.db_action == 'PREVIOUSLY_KNOWN').count()
            
            # 3. Staging and batch layer
            total_staged = db.query(DiscoveryStaging).count()
            staged_committed = db.query(DiscoveryStaging).filter(DiscoveryStaging.processing_status == 'committed').count()
            staged_pending = db.query(DiscoveryStaging).filter(DiscoveryStaging.processing_status == 'pending').count()
            staged_resolved = db.query(ResolvedPerson).count()

            # 4. Knowledge Graph entities
            total_entities = db.query(KnowledgeEntity).count()
            total_relationships = db.query(KnowledgeRelationship).count()
            total_observations = db.query(SemanticObservation).count()

            # 5. Extension devices & logs
            devices = db.query(ExtensionDevice).all()
            total_submissions = db.query(ExtensionSubmissionLog).count()

            # 6. Recent Extension events
            recent_events = db.query(ExtensionDiscoveryEvent).order_by(ExtensionDiscoveryEvent.id.desc()).limit(10).all()

            print(f"\n1. MASTER DATABASE HEADCOUNT:")
            print(f"   - Total Master Recruiters:         {total_recruiters:,}")
            print(f"   - Created by Scraper (New):        {extension_recruiters:,}")

            print(f"\n2. SCRAPER INGESTION & DISCOVERY EVENTS:")
            print(f"   - Total Extension Events Logged:   {total_events:,}")
            print(f"   - New People Created:              {new_discoveries:,}")
            print(f"   - Existing People Enriched:        {enriched_records:,}")
            print(f"   - Duplicate Sightings (Skipped):   {duplicates_seen:,}")

            print(f"\n3. STAGING & RESOLUTION LAYER:")
            print(f"   - Total Staged Observations:       {total_staged:,}")
            print(f"   - Staged Committed to DB:          {staged_committed:,}")
            print(f"   - Staged Pending Batch:            {staged_pending:,}")
            print(f"   - Resolved Person Entities:        {staged_resolved:,}")

            print(f"\n4. KNOWLEDGE GRAPH ENTITIES:")
            print(f"   - Total Graph Entities:            {total_entities:,}")
            print(f"   - Total Graph Relationships:       {total_relationships:,}")
            print(f"   - Semantic Observations:           {total_observations:,}")

            print(f"\n5. CONNECTED SCOUT DEVICES: ({len(devices)})")
            for d in devices:
                print(f"   - Device [{d.device_id}]: Version={d.extension_version}, Submitted={d.total_submitted}, Accepted={d.total_accepted}, LastSeen={d.last_seen_at}")

            print(f"\n6. RECENT SCRAPER DISCOVERIES IN DATABASE:")
            for e in recent_events:
                print(f"   - [{e.db_action}] {e.recruiter_name} | {e.title} @ {e.company_name} | Confidence: {e.confidence}% | Time: {e.created_at}")

            print("\n" + "=" * 80)
            print("MATCH ANALYSIS & VERIFICATION:")
            print("=" * 80)
            if new_discoveries == extension_recruiters:
                print(f"[MATCH] EXACT MATCH: {new_discoveries} new discoveries logged == {extension_recruiters} extension recruiters in master DB.")
            else:
                print(f"[INFO] DIFFERENCE: {new_discoveries} new discoveries logged vs {extension_recruiters} extension recruiters.")
            print(f"[ENRICHMENTS] {enriched_records} existing master records were updated with new fields without altering master headcount.")
            print("=" * 80)

    except Exception as e:
        print(f"Error auditing database: {e}")


if __name__ == "__main__":
    inspect_scraper_vs_master_db()
