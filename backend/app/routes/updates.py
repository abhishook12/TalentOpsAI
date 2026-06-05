from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.exc import ProgrammingError
from typing import List
from datetime import datetime
from sqlalchemy import text

from ..database import get_db
from ..models.models import PlatformUpdate, FeatureVerification
from ..routes.admin import verify_admin

router = APIRouter(prefix="/updates", tags=["updates"])


@router.post("/seed")
def seed_initial_updates(db: Session = Depends(get_db)):
    try:
        # Remove old updates
        db.execute(text("DELETE FROM feature_verifications;"))
        db.execute(text("DELETE FROM platform_updates;"))

        u1 = PlatformUpdate(
            version="v1.1.0",
            title="High-Performance Data Architecture & Scalability",
            developer="System Engineer"
        )
        db.add(u1)
        db.flush()

        f1 = FeatureVerification(update_id=u1.update_id, feature_name="B-Tree Database Indexing for O(log n) instantaneous search scaling across 8 distinct contact fields.", status="Verified & Operational", tester="System Engineer")
        f2 = FeatureVerification(update_id=u1.update_id, feature_name="Client-side React DOM pagination limits (50-rows max) in Paste & Parse to eliminate browser memory lag.", status="Verified & Operational", tester="System Engineer")
        f3 = FeatureVerification(update_id=u1.update_id, feature_name="4-Contact Structural Alignment (4 Emails + 4 Phones per agent) integrated natively into backend Models, Analytics, and APIs.", status="Verified & Operational", tester="System Engineer")
        db.add_all([f1, f2, f3])
        
        u2 = PlatformUpdate(
            version="v1.0.5",
            title="ETL Adaptive Ingestion Engine",
            developer="System Engineer"
        )
        db.add(u2)
        db.flush()

        f4 = FeatureVerification(update_id=u2.update_id, feature_name="Dynamic JSON Metadata Extraction mapping fallback properties directly into relational structures.", status="Verified & Operational", tester="System Engineer")
        f5 = FeatureVerification(update_id=u2.update_id, feature_name="Multi-sheet XLSX support and CSV heuristic detection system.", status="Verified & Operational", tester="System Engineer")
        db.add_all([f4, f5])

        db.commit()
        return {"status": "seeded"}
    except ProgrammingError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Updates tables not initialized. Enable RUN_STARTUP_MIGRATIONS once or run migrations.")

@router.get("/status")
def get_current_status(db: Session = Depends(get_db)):
    """
    Gets the latest update and its overall status.
    """
    try:
        latest_update = db.query(PlatformUpdate).order_by(desc(PlatformUpdate.created_at)).first()
        if not latest_update:
            return {"version": "v1.0.0", "status": "Operational", "date": datetime.utcnow().isoformat(), "features": []}

        features = db.query(FeatureVerification).filter(FeatureVerification.update_id == latest_update.update_id).all()
    except ProgrammingError:
        # Deployments may not have run migrations yet. Keep UI stable.
        db.rollback()
        return {"version": "v1.0.0", "status": "No Data Available", "date": None, "features": []}
    
    # Calculate overall status
    if not features:
        overall_status = "Operational"
    else:
        statuses = [f.status for f in features]
        if "Failed Verification" in statuses:
            overall_status = "Failed Verification"
        elif "Pending Verification" in statuses:
            overall_status = "Pending Verification"
        else:
            overall_status = "Verified & Operational"

    return {
        "version": latest_update.version,
        "date": latest_update.created_at.isoformat() if latest_update.created_at else None,
        "status": overall_status,
        "features": [{"id": f.feature_id, "name": f.feature_name, "status": f.status} for f in features]
    }

@router.get("/changelog")
def get_changelog(db: Session = Depends(get_db)):
    """
    Gets all updates.
    """
    try:
        updates = db.query(PlatformUpdate).order_by(desc(PlatformUpdate.created_at)).all()
    except ProgrammingError:
        db.rollback()
        return []
    result = []
    for u in updates:
        features = db.query(FeatureVerification).filter(FeatureVerification.update_id == u.update_id).all()
        
        if not features:
            status = "Operational"
        else:
            statuses = [f.status for f in features]
            if "Failed Verification" in statuses:
                status = "Failed Verification"
            elif "Pending Verification" in statuses:
                status = "Pending Verification"
            else:
                status = "Verified"
                
        result.append({
            "id": u.update_id,
            "version": u.version,
            "title": u.title,
            "developer": u.developer,
            "date": u.created_at.isoformat() if u.created_at else None,
            "status": status,
            "features": [{"id": f.feature_id, "name": f.feature_name, "status": f.status, "tester": f.tester, "last_tested": f.last_tested.isoformat() if f.last_tested else None, "result": f.result} for f in features]
        })
    return result

@router.get("/features")
def get_all_features(_=Depends(verify_admin), db: Session = Depends(get_db)):
    """
    Gets all features for the admin verification panel.
    """
    features = db.query(FeatureVerification).order_by(desc(FeatureVerification.feature_id)).all()
    return [{
        "id": f.feature_id,
        "name": f.feature_name,
        "status": f.status,
        "last_tested": f.last_tested.isoformat() if f.last_tested else None,
        "tester": f.tester,
        "result": f.result
    } for f in features]

@router.post("/verify/{feature_id}")
def verify_feature(feature_id: int, payload: dict, _=Depends(verify_admin), db: Session = Depends(get_db)):
    """
    Updates the status of a feature.
    """
    feature = db.query(FeatureVerification).filter(FeatureVerification.feature_id == feature_id).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
        
    status = payload.get("status")
    tester = payload.get("tester", "Admin")
    result_text = payload.get("result", "")
    
    if status not in ["Verified", "Pending Verification", "Failed Verification"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    feature.status = status
    feature.tester = tester
    feature.result = result_text
    feature.last_tested = datetime.utcnow()
    
    db.commit()
    return {"status": "ok", "feature_id": feature_id, "new_status": status}
