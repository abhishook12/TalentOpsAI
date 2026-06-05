import os
from dotenv import load_dotenv
load_dotenv()
from app.database import SessionLocal
from app.models.models import PlatformUpdate, FeatureVerification
from sqlalchemy import text

def seed_updates():
    db = SessionLocal()
    
    # Check if updates already exist, optionally clear them
    db.execute(text("DELETE FROM feature_verifications;"))
    db.execute(text("DELETE FROM platform_updates;"))
    
    u1 = PlatformUpdate(
        version="v1.1.0",
        title="High-Performance Data Architecture & Scalability",
        developer="System Engineer"
    )
    db.add(u1)
    db.flush()

    f1 = FeatureVerification(
        update_id=u1.update_id,
        feature_name="B-Tree Database Indexing for O(log n) instantaneous search scaling across 8 distinct contact fields.",
        status="Verified & Operational",
        tester="System Engineer"
    )
    f2 = FeatureVerification(
        update_id=u1.update_id,
        feature_name="Client-side React DOM pagination limits (50-rows max) in Paste & Parse to eliminate browser memory lag.",
        status="Verified & Operational",
        tester="System Engineer"
    )
    f3 = FeatureVerification(
        update_id=u1.update_id,
        feature_name="4-Contact Structural Alignment (4 Emails + 4 Phones per agent) integrated natively into backend Models, Analytics, and APIs.",
        status="Verified & Operational",
        tester="System Engineer"
    )
    db.add_all([f1, f2, f3])
    
    u2 = PlatformUpdate(
        version="v1.0.5",
        title="ETL Adaptive Ingestion Engine",
        developer="System Engineer"
    )
    db.add(u2)
    db.flush()

    f4 = FeatureVerification(
        update_id=u2.update_id,
        feature_name="Dynamic JSON Metadata Extraction mapping fallback properties directly into relational structures.",
        status="Verified & Operational",
        tester="System Engineer"
    )
    f5 = FeatureVerification(
        update_id=u2.update_id,
        feature_name="Multi-sheet XLSX support and CSV heuristic detection system.",
        status="Verified & Operational",
        tester="System Engineer"
    )
    db.add_all([f4, f5])

    try:
        db.commit()
        print("Successfully seeded platform updates!")
    except Exception as e:
        db.rollback()
        print("Error:", e)

if __name__ == "__main__":
    seed_updates()
