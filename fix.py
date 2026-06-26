with open("C:/TalentOpsAI/backend/app/routes/recruiters.py", "a", encoding="utf-8") as f:
    f.write("""

@router.post("/{recruiter_id}/report")
def report_recruiter(recruiter_id: int, db: Session = Depends(get_db)):
    from sqlalchemy import text
    try:
        res = db.execute(
            text("UPDATE recruiters SET report_count = report_count + 1 WHERE recruiter_id = :id RETURNING report_count"),
            {"id": recruiter_id}
        ).fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="Recruiter not found")
        count = res[0]
        if count >= 3:
            db.execute(
                text("UPDATE recruiters SET needs_review = true, review_reason = 'Flagged by users 3 times', is_active = false WHERE recruiter_id = :id"),
                {"id": recruiter_id}
            )
        db.commit()
        return {"message": "Report logged successfully", "report_count": count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

from ..services.scraper import auto_enhance_recruiter_data

@router.post("/{recruiter_id}/enhance")
def enhance_recruiter(recruiter_id: int, db: Session = Depends(get_db)):
    recruiter = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter not found")
        
    company_name = None
    company_domain = None
    if recruiter.company_id:
        company = db.query(Company).filter(Company.company_id == recruiter.company_id).first()
        if company:
            company_name = company.company_name
            if company.website:
                company_domain = company.website.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0]
                
    result = auto_enhance_recruiter_data(recruiter.recruiter_name, company_name, company_domain)
    
    updated = []
    if result['email'] and (not recruiter.email or recruiter.email.endswith('@missing.local')):
        recruiter.email = result['email']
        updated.append("email")
    if result['phone'] and not recruiter.phone:
        recruiter.phone = result['phone']
        updated.append("phone")
        
    from sqlalchemy.sql import func
    recruiter.last_scan_at = func.now()
    db.commit()

    if updated:
        return {"message": f"Successfully enhanced {', '.join(updated)}!", "data": result}
    else:
        return {"message": "No new verified data found.", "data": result}

from pydantic import BaseModel
class ChromeExtensionPayload(BaseModel):
    recruiter_name: str
    title: str | None = None
    location: str | None = None
    company_name: str | None = None
    linkedin_url: str | None = None
    source: str | None = None
    scraped_at: str | None = None

import uuid
import json
from ..utils.location_normalization import extract_state_detailed, normalize_text

@router.post("/extension", status_code=201)
def extension_webhook(data: ChromeExtensionPayload, db: Session = Depends(get_db)):
    # 1. Resolve Company
    company_id = None
    if data.company_name:
        norm_comp = normalize_text(data.company_name)
        company = db.query(Company).filter(Company.normalized_company_name == norm_comp).first()
        if company:
            company_id = company.company_id
        else:
            new_comp = Company(
                company_name=data.company_name,
                normalized_company_name=norm_comp,
                is_active=True,
                data_source="chrome_extension"
            )
            db.add(new_comp)
            db.commit()
            db.refresh(new_comp)
            company_id = new_comp.company_id
            
    # 2. Extract state from location if available
    state = None
    state_source = None
    state_confidence = None
    state_reason = None
    if data.location:
        state, state_reason = extract_state_detailed(data.location)
        if state:
            state_source = "extension_location"
            state_confidence = "high"

    # 3. Create placeholder email
    email = f"linkedin_{uuid.uuid4().hex[:8]}@missing.local"

    # 4. Create Recruiter
    new_rec = Recruiter(
        recruiter_name=data.recruiter_name,
        normalized_recruiter_name=normalize_text(data.recruiter_name),
        email=email,
        title=data.title,
        company_id=company_id,
        location=data.location,
        state=state,
        state_source=state_source,
        state_confidence=state_confidence,
        state_reason=state_reason,
        linkedin=data.linkedin_url,
        data_source=data.source or "chrome_extension",
        is_active=True
    )
    db.add(new_rec)
    db.commit()
    db.refresh(new_rec)
    
    return {"message": "Recruiter imported successfully", "recruiter_id": new_rec.recruiter_id}

""")
