import asyncio
import json
import logging
import re
import random
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import SessionLocal
from app.models.models import Recruiter
from app.models.sentinel_state import SentinelState
from app.models.sentinel_audit import SentinelAuditLog
from app.services.scraper import auto_enhance_recruiter_data, is_human_name
from app.services.enrichment_service import jit_enrichment_service

logger = logging.getLogger("sentinel")

# ─── INTELLIGENCE MODULES ───

def normalize_email(email: str):
    if not email: return None
    email = email.strip().lower()
    # Disposable / fake / role-based heuristics
    if re.match(r"^(info|admin|sales|careers|contact|test)@", email):
        return {"value": email, "issue": "role_based"}
    if "missing.local" in email or "example.com" in email:
        return {"value": email, "issue": "fake_domain"}
    return {"value": email, "issue": None}

def normalize_phone(phone: str):
    if not phone: return None
    # Strip everything except digits and +
    cleaned = re.sub(r'[^\d\+]', '', phone)
    if len(cleaned) < 7:
        return {"value": phone, "issue": "invalid_length"}
    return {"value": cleaned, "issue": None}

def normalize_name(name: str):
    if not name: return None
    # Title Case normalization
    words = name.split()
    normalized = " ".join([w.capitalize() for w in words])
    return normalized

def calculate_quality_score(recruiter: Recruiter, missing_fields: dict):
    score = 100
    
    if missing_fields.get("primary_email"): score -= 20
    if missing_fields.get("primary_phone"): score -= 15
    if missing_fields.get("linkedin"): score -= 15
    if missing_fields.get("company"): score -= 20
    if missing_fields.get("location"): score -= 10
    if missing_fields.get("title"): score -= 10
    if missing_fields.get("specialization"): score -= 5
    
    return max(0, score)

# ─── ENGINE CORE ───

class SentinelEngine:
    def __init__(self):
        self.running = False
        self.batch_size = 50
        self.sleep_interval = 2.0 # Throttle to prevent DB locking

    def start(self):
        self.running = True
        asyncio.create_task(self.run_loop())

    def stop(self):
        self.running = False

    def log_audit(self, db: Session, recruiter_id: int, field: str, old: str, new: str, reason: str, confidence: float = 1.0):
        if old != new:
            log = SentinelAuditLog(
                recruiter_id=recruiter_id,
                field_changed=field,
                previous_value=str(old) if old else None,
                new_value=str(new) if new else None,
                reason=reason,
                confidence=confidence
            )
            db.add(log)
            return True
        return False

    async def run_loop(self):
        logger.info("SENTINEL Engine Started")
        while self.running:
            try:
                db = SessionLocal()
                state = db.query(SentinelState).first()
                
                if not state:
                    state = SentinelState(status="Running")
                    db.add(state)
                    db.commit()
                
                if state.status != "Running":
                    db.close()
                    await asyncio.sleep(5)
                    continue

                # Process batch
                state.current_task_description = f"Processing batch starting at ID {state.last_processed_id}"
                db.commit()
                
                from sqlalchemy.orm import selectinload
                recruiters = db.query(Recruiter).options(
                    selectinload(Recruiter.structured_emails),
                    selectinload(Recruiter.structured_phones),
                    selectinload(Recruiter.company)
                ).filter(Recruiter.recruiter_id > state.last_processed_id).order_by(Recruiter.recruiter_id.asc()).limit(self.batch_size).all()
                
                if not recruiters:
                    # Reached the end, wrap around
                    state.last_processed_id = 0
                    state.current_task_description = "Completed full pass. Restarting..."
                    db.commit()
                    db.close()
                    await asyncio.sleep(10)
                    continue

                repaired_count = 0
                for r in recruiters:
                    modifications = 0
                    
                    # 1. Normalize All Emails (email, email2, email3, email4)
                    for email_field in ["email", "email2", "email3", "email4"]:
                        val = getattr(r, email_field)
                        if val:
                            res = normalize_email(val)
                            if res["value"] != val:
                                self.log_audit(db, r.recruiter_id, email_field, val, res["value"], "Normalized email")
                                setattr(r, email_field, res["value"])
                                modifications += 1

                    # 2. Normalize All Phones (phone, phone2, phone3, phone4)
                    for phone_field in ["phone", "phone2", "phone3", "phone4"]:
                        val = getattr(r, phone_field)
                        if val:
                            res = normalize_phone(val)
                            if res["value"] != val:
                                self.log_audit(db, r.recruiter_id, phone_field, val, res["value"], "Normalized phone format")
                                setattr(r, phone_field, res["value"])
                                modifications += 1

                    # 3. Normalize CSV Fields (alternate_emails, alternate_phones)
                    if r.alternate_emails:
                        emails = [e.strip() for e in r.alternate_emails.split(",") if e.strip()]
                        normalized_emails = []
                        for e in emails:
                            val = normalize_email(e)["value"]
                            if val: normalized_emails.append(val)
                        new_val = ",".join(normalized_emails) if normalized_emails else None
                        if new_val != r.alternate_emails:
                            self.log_audit(db, r.recruiter_id, "alternate_emails", r.alternate_emails, new_val, "Normalized alternate_emails CSV")
                            r.alternate_emails = new_val
                            modifications += 1

                    if r.alternate_phones:
                        phones = [p.strip() for p in r.alternate_phones.split(",") if p.strip()]
                        normalized_phones = []
                        for p in phones:
                            val = normalize_phone(p)["value"]
                            if val: normalized_phones.append(val)
                        new_val = ",".join(normalized_phones) if normalized_phones else None
                        if new_val != r.alternate_phones:
                            self.log_audit(db, r.recruiter_id, "alternate_phones", r.alternate_phones, new_val, "Normalized alternate_phones CSV")
                            r.alternate_phones = new_val
                            modifications += 1

                    # 4. Normalize Structured Entities (RecruiterEmail, RecruiterPhone)
                    for se in r.structured_emails:
                        if se.email:
                            res = normalize_email(se.email)
                            if res["value"] != se.email:
                                self.log_audit(db, r.recruiter_id, f"structured_email_{se.id}", se.email, res["value"], "Normalized relational email")
                                se.email = res["value"]
                                modifications += 1
                            if res["issue"] == "role_based" and se.status != "invalid":
                                se.status = "invalid"
                                modifications += 1

                    for sp in r.structured_phones:
                        if sp.phone_number:
                            res = normalize_phone(sp.phone_number)
                            if res["value"] != sp.phone_number:
                                self.log_audit(db, r.recruiter_id, f"structured_phone_{sp.id}", sp.phone_number, res["value"], "Normalized relational phone")
                                sp.phone_number = res["value"]
                                modifications += 1

                    # 5. Normalize Company Entity
                    if r.company:
                        if r.company.company_name:
                            new_cname = normalize_name(r.company.company_name)
                            if new_cname != r.company.company_name:
                                self.log_audit(db, r.recruiter_id, f"company_name_{r.company.company_id}", r.company.company_name, new_cname, "Capitalization normalization for company")
                                r.company.company_name = new_cname
                                modifications += 1
                        
                        if r.company.website:
                            clean_web = r.company.website.strip().lower()
                            if not clean_web.startswith("http") and clean_web:
                                clean_web = "https://" + clean_web
                            if clean_web != r.company.website:
                                self.log_audit(db, r.recruiter_id, f"company_website_{r.company.company_id}", r.company.website, clean_web, "Normalized company website")
                                r.company.website = clean_web
                                modifications += 1

                    # 6. Normalize Recruiter Name
                    if r.recruiter_name:
                        new_name = normalize_name(r.recruiter_name)
                        if new_name != r.recruiter_name:
                            self.log_audit(db, r.recruiter_id, "recruiter_name", r.recruiter_name, new_name, "Capitalization normalization")
                            r.recruiter_name = new_name
                            modifications += 1
                    # 7. Omnipresent Enrichment
                    enrichment_triggered = False
                    if r.company and r.company.company_name and is_human_name(r.recruiter_name, r.company.company_name, r.email):
                        missing_critical = not r.email or "missing.local" in r.email or not r.phone or not r.linkedin or not r.location
                        
                        if missing_critical:
                            # Try DDG (LinkedIn / Title / Location)
                            if not r.linkedin or not r.location:
                                try:
                                    success = await asyncio.to_thread(jit_enrichment_service.enrich_recruiter_sync, db, r)
                                    if success:
                                        modifications += 1
                                        enrichment_triggered = True
                                        self.log_audit(db, r.recruiter_id, "omnipresent_enrichment", "missing", "enriched", "DDG Enrichment")
                                        
                                        # If location was found, map it to state instantly!
                                        if r.location and (not r.state or r.state == 'US'):
                                            from app.utils.state_mapper import extract_state_detailed
                                            new_state, _ = extract_state_detailed(r.location)
                                            if new_state:
                                                self.log_audit(db, r.recruiter_id, "state", str(r.state), new_state, "DDG Location Inference")
                                                r.state = new_state
                                except Exception as e:
                                    logger.error(f"DDG Enrichment Error in Sentinel: {e}")
                                    
                            # Try Tavily/SMTP (Email / Phone)
                            if not r.email or "missing.local" in r.email or not r.phone:
                                try:
                                    res = await asyncio.to_thread(
                                        auto_enhance_recruiter_data, 
                                        r.recruiter_name, 
                                        r.company.company_name, 
                                        r.company.website or r.company.email_pattern
                                    )
                                    if res.get('email') and (not r.email or "missing.local" in r.email):
                                        self.log_audit(db, r.recruiter_id, "email", r.email, res['email'], "Tavily/SMTP Enrichment")
                                        r.email = res['email']
                                        modifications += 1
                                        enrichment_triggered = True
                                    if res.get('phone') and not r.phone:
                                        self.log_audit(db, r.recruiter_id, "phone", r.phone, res['phone'], "Tavily Enrichment")
                                        r.phone = res['phone']
                                        modifications += 1
                                        enrichment_triggered = True
                                except Exception as e:
                                    logger.error(f"Tavily Enrichment Error in Sentinel: {e}")

                    if enrichment_triggered:
                        # Throttle aggressively to prevent IP bans during active batch enrichment
                        await asyncio.sleep(random.uniform(2.5, 4.5))
                    
                    # 4. Missing Fields & Scoring
                    missing = {
                        "primary_email": not bool(r.email) or "missing.local" in r.email,
                        "primary_phone": not bool(r.phone),
                        "linkedin": not bool(r.linkedin),
                        "company": not bool(r.company_id),
                        "location": not bool(r.location),
                        "title": not bool(r.title),
                        "specialization": not bool(r.specialization)
                    }
                    r.missing_fields = json.dumps(missing)
                    
                    new_score = calculate_quality_score(r, missing)
                    if new_score != r.quality_score:
                        r.quality_score = new_score
                        modifications += 1
                        
                    r.sentinel_status = "Completed"
                    r.last_verified_at = datetime.now(timezone.utc)
                    
                    if modifications > 0:
                        repaired_count += 1
                        
                    state.last_processed_id = r.recruiter_id
                    state.profiles_analyzed += 1

                state.profiles_repaired += repaired_count
                db.commit()
                db.close()
                
            except Exception as e:
                logger.error(f"SENTINEL Engine Error: {e}")
            
            await asyncio.sleep(self.sleep_interval)

sentinel_engine = SentinelEngine()
