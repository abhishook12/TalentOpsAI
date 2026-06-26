#!/usr/bin/env python
from __future__ import annotations

import sys
import os
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.models import Recruiter, Company
from app.utils.state_mapper import normalize_state, extract_state_detailed

def run_repair():
    print("Starting Full Throttle Database Quality & Repair Worker...")
    db = SessionLocal()
    
    try:
        recruiters = db.query(Recruiter).all()
        print(f"Auditing {len(recruiters)} total recruiter records...")
        
        stats = {
            "audited": len(recruiters),
            "state_fixed": 0,
            "email_quarantined": 0,
            "entity_flagged": 0,
            "offshore_flagged": 0
        }
        
        company_suffixes = ['inc', 'llc', 'ltd', 'global', 'services', 'talent', 'solutions', 'group', 'brands', 'technologies', 'consulting', 'partners', 'staffing', 'corporation', 'corp', 'agency']
        offshore_indicators = ['india', 'uk', 'united kingdom', 'england', 'europe', 'australia', 'philippines', 'mexico', 'brazil', 'pakistan', 'london', 'bengaluru', 'hyderabad', 'pune', 'manila', 'bracknell']
        
        for r in recruiters:
            modified = False
            reasons = []
            
            # 1. Check Entity Name
            name_lower = (r.recruiter_name or "").lower()
            words = name_lower.split()
            if any(s in words for s in company_suffixes):
                if not r.needs_review:
                    r.needs_review = True
                    stats["entity_flagged"] += 1
                reasons.append("Entity Misclassification: Name appears to be a corporate entity or agency.")
                modified = True
                
            # 2. Check Offshore Location
            loc_lower = (r.location or "").lower()
            if any(off in loc_lower for off in offshore_indicators):
                if not r.needs_review:
                    r.needs_review = True
                    r.is_active = False # Deactivate offshore per user rule
                    stats["offshore_flagged"] += 1
                reasons.append(f"Offshore location detected ({r.location}).")
                modified = True
                
            # 3. Missing State Reconstruction
            if not r.state:
                new_state = None
                state_source = None
                state_confidence = None
                state_reason = None
                
                if r.location:
                    res = extract_state_detailed(r.location)
                    if isinstance(res, tuple):
                        new_state, state_reason = res[0], res[1]
                    else:
                        new_state = res
                    if new_state:
                        state_source = "recruiter_location"
                        state_confidence = "high"
                
                if not new_state and r.company_id:
                    comp = db.query(Company).filter(Company.company_id == r.company_id).first()
                    if comp and comp.location:
                        res = extract_state_detailed(comp.location)
                        if isinstance(res, tuple):
                            new_state, state_reason = res[0], res[1]
                        else:
                            new_state = res
                        if new_state:
                            state_source = "company_location"
                            state_confidence = "medium"
                            
                if new_state:
                    r.state = new_state
                    if hasattr(r, 'state_source'): r.state_source = state_source
                    if hasattr(r, 'state_confidence'): r.state_confidence = state_confidence
                    stats["state_fixed"] += 1
                    modified = True
                    
            # 4. Faulty / Dummy Email Quarantine
            email_val = r.email or ""
            if "@missing.local" in email_val or "tavily_discovery" in email_val or "unknown" in email_val or not re.match(r"[^@]+@[^@]+\.[^@]+", email_val):
                if hasattr(r, 'email_status') and r.email_status != "invalid":
                    r.email_status = "invalid"
                    stats["email_quarantined"] += 1
                    modified = True
                    
            # Apply review reasons
            if reasons:
                existing_reason = r.review_reason or ""
                new_reason = " | ".join(reasons)
                if new_reason not in existing_reason:
                    r.review_reason = (existing_reason + " | " + new_reason).strip(" | ")
                    modified = True
                    
            if modified:
                tags = r.tags or ""
                if "full_throttle_repair_2026" not in tags:
                    r.tags = (tags + ",full_throttle_repair_2026").strip(",")
                    
        db.commit()
        print("\nFull Throttle Quality Scan Complete!")
        print(f"Final Repair Statistics:")
        print(f"   - Total Audited: {stats['audited']}")
        print(f"   - Missing States Reconstructed: {stats['state_fixed']}")
        print(f"   - Faulty Emails Quarantined: {stats['email_quarantined']}")
        print(f"   - Corporate Entities Flagged: {stats['entity_flagged']}")
        print(f"   - Offshore Profiles Quarantined: {stats['offshore_flagged']}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during database repair: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_repair()
