"""
migrate_dev_db_intelligence.py — Migrates intelligence models and scout tables into backend/dev.db.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import create_engine, inspect
from app.database import Base
# Import all models so they register with Base.metadata
import app.models.models
import app.models.auth_models
import app.models.extension_models
import app.models.staging_models
import app.models.intelligence_models
import app.models.knowledge_models
import app.models.update_models

def migrate():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "dev.db"))
    print(f"Connecting to SQLite database: {db_path}")
    engine = create_engine(f"sqlite:///{db_path}")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Successfully synced DB! Total tables now in dev.db: {len(tables)}")
    
    intelligence_tables = [
        "source_connectors", "oauth_scope_registry", "ingestion_runs",
        "raw_signals", "entity_registry", "persons", "companies_v2",
        "jobs_v2", "posts_v2", "skills_v2", "technologies_v2",
        "relationships", "signal_events", "derived_intents",
        "evidence_ledger", "career_velocities"
    ]
    
    print("\nVerifying 16 Knowledge Graph Intelligence tables:")
    for t in intelligence_tables:
        if t in tables:
            print(f"  [OK] {t}")
        else:
            print(f"  [MISSING] {t}")

if __name__ == "__main__":
    migrate()
