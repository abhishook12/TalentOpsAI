from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from datetime import datetime

from ..database import get_db
from ..models.models import PlatformUpdate, FeatureVerification
from ..routes.admin import verify_admin

router = APIRouter(prefix="/updates", tags=["updates"])


@router.post("/seed")
def seed_initial_updates(db: Session = Depends(get_db)):
    if db.query(PlatformUpdate).first():
        return {"status": "already seeded"}
        
    u = PlatformUpdate(
        version="v2.8.4",
        title="Core Functionality Pass",
        developer="Antigravity",
    )
    db.add(u)
    db.commit()
    
    f1 = FeatureVerification(update_id=u.update_id, feature_name="AI Search Exports", status="Pending Verification")
    f2 = FeatureVerification(update_id=u.update_id, feature_name="State Directory Sort/Export", status="Pending Verification")
    f3 = FeatureVerification(update_id=u.update_id, feature_name="Recruiter Excel Export", status="Pending Verification")
    f4 = FeatureVerification(update_id=u.update_id, feature_name="Company Excel Export", status="Pending Verification")
    f5 = FeatureVerification(update_id=u.update_id, feature_name="Data Cleanup Logic", status="Pending Verification")
    
    db.add_all([f1, f2, f3, f4, f5])
    db.commit()
    return {"status": "seeded"}

@router.get("/status")
def get_current_status(db: Session = Depends(get_db)):
    \"\"\"
    Gets the latest update and its overall status.
    \"\"\"
    latest_update = db.query(PlatformUpdate).order_by(desc(PlatformUpdate.created_at)).first()
    if not latest_update:
        return {"version": "v1.0.0", "status": "Operational", "date": datetime.utcnow().isoformat(), "features": []}

    features = db.query(FeatureVerification).filter(FeatureVerification.update_id == latest_update.update_id).all()
    
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
    \"\"\"
    Gets all updates.
    \"\"\"
    updates = db.query(PlatformUpdate).order_by(desc(PlatformUpdate.created_at)).all()
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
    \"\"\"
    Gets all features for the admin verification panel.
    \"\"\"
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
    \"\"\"
    Updates the status of a feature.
    \"\"\"
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
