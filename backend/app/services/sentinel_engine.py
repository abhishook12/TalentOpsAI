import asyncio
import json
import logging
import re
import random
from datetime import datetime, timezone
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import text, func, desc

from app.database import SessionLocal
from app.models.models import Recruiter, Company, DomainIntelligence, EnrichmentAudit
from app.models.sentinel_state import SentinelState
from app.services.scraper import auto_enhance_recruiter_data, is_human_name
from app.services.enrichment_service import jit_enrichment_service
from app.services.mailintel_engine import extract_domain

logger = logging.getLogger("sentinel")

# ─── INTELLIGENCE MODULES ───

def normalize_email(email: str):
    if not email: return None
    email = email.strip().lower()
    if re.match(r"^(info|admin|sales|careers|contact|test)@", email):
        return {"value": email, "issue": "role_based"}
    if "missing.local" in email or "example.com" in email:
        return {"value": email, "issue": "fake_domain"}
    return {"value": email, "issue": None}

def normalize_phone(phone: str):
    if not phone: return None
    cleaned = re.sub(r'[^\d\+]', '', phone)
    if len(cleaned) < 7:
        return {"value": phone, "issue": "invalid_length"}
    return {"value": cleaned, "issue": None}

def normalize_name(name: str):
    if not name: return None
    words = name.split()
    normalized = " ".join([w.capitalize() for w in words])
    return normalized

def is_non_human_name_heuristic(name: str) -> bool:
    if not name: return False
    lower_name = name.lower().strip()
    non_human_keywords = {"sales", "info", "admin", "contact", "marketing", "support", "billing", "careers", "hello", "team", "hr", "recruitment"}
    for kw in non_human_keywords:
        if kw == lower_name or f"{kw} team" in lower_name or f" {kw}" in lower_name:
            return True
    return False

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

FREEMAIL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com", "msn.com", "live.com"}

def calculate_completeness_score(r: Recruiter, c: Company):
    score = 0
    total_fields = 15
    missing = []
    fields = [
        ("Name", r.recruiter_name), ("Company", c.company_name if c else None),
        ("Title", r.title), ("Primary email", r.email), ("Secondary email", r.email2),
        ("Phone", r.phone), ("LinkedIn", r.linkedin), ("City", r.normalized_city),
        ("State", r.state), ("Country", r.location), ("Skills", r.tags),
        ("Department", r.taxonomy_category), ("Specialization", r.specialization),
        ("Company logo", None), ("Company website", c.website if c else None)
    ]
    for fname, val in fields:
        if val and str(val).strip() and "missing.local" not in str(val).lower():
            if fname == "Name" and is_non_human_name_heuristic(str(val)):
                missing.append("Name (Non-Human)")
            else:
                score += 1
        else:
            missing.append(fname)
    pct = int((score / total_fields) * 100)
    return pct, missing

def infer_company_from_domain(db, domain: str, recruiter: Recruiter):
    if domain in FREEMAIL_DOMAINS:
        return None, 0, "Personal email domain (freemail)"
    di = db.query(DomainIntelligence).filter(DomainIntelligence.domain == domain).first()
    if not di:
        di = DomainIntelligence(
            domain=domain, is_personal=False, confidence_score=50,
            evidence=json.dumps({"source": "Extracted from recruiter email", "recruiter_id": recruiter.recruiter_id})
        )
        db.add(di)
        db.flush()
    if di.company_id:
        return di.company_id, di.confidence_score, f"Inferred from DomainIntelligence mapping for {domain}"
    c = db.query(Company).filter((Company.website.ilike(f"%{domain}%")) | (Company.email_pattern == domain)).order_by(Company.trust_score.desc()).first()
    if c:
        di.company_id = c.company_id
        di.company_name = c.company_name
        di.confidence_score = 90
        di.evidence = json.dumps({"source": "Matched existing canonical company", "company_id": c.company_id})
        db.flush()
        return c.company_id, 90, f"Matched existing company ({domain})"
    new_company_name = domain.split('.')[0].capitalize()
    new_comp = Company(
        company_name=new_company_name, website=f"https://www.{domain}",
        email_pattern=domain, data_source="sentinel_inference", trust_score=80
    )
    db.add(new_comp)
    db.flush()
    di.company_id = new_comp.company_id
    di.company_name = new_company_name
    di.confidence_score = 80
    di.evidence = json.dumps({"source": "Auto-created from domain", "company_id": new_comp.company_id})
    db.flush()
    return new_comp.company_id, 80, f"Auto-created company '{new_company_name}' from domain {domain}"

def detect_and_merge_duplicates(db: Session, recruiter: Recruiter):
    # Rule 7: Duplicate Intelligence
    # Returns (merged_recruiter_id, was_merged_and_deleted)
    if not recruiter.email or "missing.local" in recruiter.email:
        return recruiter.recruiter_id, False
        
    dupes = db.query(Recruiter).filter(
        Recruiter.email == recruiter.email,
        Recruiter.recruiter_id != recruiter.recruiter_id
    ).all()
    
    if not dupes:
        return recruiter.recruiter_id, False
        
    # High confidence merge logic: Merge into the oldest record (canonical)
    canonical = min(dupes + [recruiter], key=lambda x: x.recruiter_id)
    duplicates_to_delete = [d for d in dupes + [recruiter] if d.recruiter_id != canonical.recruiter_id]
    
    for d in duplicates_to_delete:
        # Transfer data to canonical if missing
        for attr in ['phone', 'linkedin', 'title', 'location', 'company_id']:
            if getattr(d, attr) and not getattr(canonical, attr):
                setattr(canonical, attr, getattr(d, attr))
                
        # Log merge
        audit = EnrichmentAudit(
            recruiter_id=canonical.recruiter_id,
            enrichment_type="merge",
            original_value=str(d.recruiter_id),
            proposed_value="merged",
            final_value="merged",
            source="Sentinel Deduplication",
            confidence_score=100,
            action="merge_duplicate",
            reason=f"Merged duplicate {d.recruiter_id} sharing email {canonical.email}",
            run_id="sentinel_dedup"
        )
        db.add(audit)
        db.delete(d)
        
    db.flush()
    return canonical.recruiter_id, (recruiter.recruiter_id != canonical.recruiter_id)

class SentinelEngine:
    def __init__(self):
        self.running = False
        self.batch_size = 50
        self.sleep_interval = 2.0

    def start(self):
        self.running = True
        asyncio.create_task(self.run_loop())

    def stop(self):
        self.running = False

    def log_audit(self, db: Session, recruiter_id: int, field: str, old: str, new: str, reason: str, confidence: float = 1.0):
        if old != new:
            # Also write to EnrichmentAudit for Rule 14
            ea = EnrichmentAudit(
                recruiter_id=recruiter_id, enrichment_type=field,
                original_value=str(old) if old else None,
                proposed_value=str(new) if new else None,
                final_value=str(new) if new else None,
                source="Sentinel Background", confidence_score=int(confidence*100),
                action="update", reason=reason, run_id="sentinel_loop"
            )
            db.add(ea)
            return True
        return False

    def _process_batch(self):
        try:
            db = SessionLocal()
            state = db.query(SentinelState).first()
            if not state:
                state = SentinelState(status="Running", last_processed_id=0)
                db.add(state)
                db.commit()
            if state.status != "Running":
                db.close()
                return False # skip

            state.current_task_description = f"Processing priority batch starting at ID {state.last_processed_id}"
            db.commit()
            
            recruiters = db.query(Recruiter).options(
                selectinload(Recruiter.structured_emails),
                selectinload(Recruiter.structured_phones),
                selectinload(Recruiter.company)
            ).filter(
                (Recruiter.sentinel_status == 'Pending') | (Recruiter.sentinel_status == None)
            ).order_by(
                Recruiter.recruiter_id.asc()
            ).limit(self.batch_size).all()
            
            if not recruiters:
                # Reset all to Pending if we want continuous scanning, or just sleep
                db.execute(text("UPDATE recruiters SET sentinel_status = 'Pending' WHERE last_scan_at < NOW() - INTERVAL '7 days'"))
                db.commit()
                state.current_task_description = "Waiting for new records..."
                db.commit()
                db.close()
                return False # sleep long

            repaired_count = 0
            for r in recruiters:
                try:
                    modifications = 0
                    
                    # 0. Deduplication (Rule 7)
                    canonical_id, was_deleted = detect_and_merge_duplicates(db, r)
                    if was_deleted:
                        continue # This record was merged and deleted
                    
                    # Refresh r if it was canonical but had updates
                    if r.recruiter_id != canonical_id:
                        r = db.query(Recruiter).get(canonical_id)

                    # 1-3. Emails, Phones, CSVs
                    for email_field in ["email", "email2", "email3", "email4"]:
                        val = getattr(r, email_field)
                        if val:
                            res = normalize_email(val)
                            if res["value"] != val:
                                self.log_audit(db, r.recruiter_id, email_field, val, res["value"], "Normalized email")
                                setattr(r, email_field, res["value"])
                                modifications += 1

                    for phone_field in ["phone", "phone2", "phone3", "phone4"]:
                        val = getattr(r, phone_field)
                        if val:
                            res = normalize_phone(val)
                            if res["value"] != val:
                                self.log_audit(db, r.recruiter_id, phone_field, val, res["value"], "Normalized phone")
                                setattr(r, phone_field, res["value"])
                                modifications += 1

                    # 4. Structured Entities
                    for se in r.structured_emails:
                        if se.email:
                            res = normalize_email(se.email)
                            if res["value"] != se.email:
                                self.log_audit(db, r.recruiter_id, f"structured_email_{se.id}", se.email, res["value"], "Normalized")
                                se.email = res["value"]
                                modifications += 1
                            if res["issue"] == "role_based" and se.status != "invalid":
                                se.status = "invalid"
                                modifications += 1

                    for sp in r.structured_phones:
                        if sp.phone_number:
                            res = normalize_phone(sp.phone_number)
                            if res["value"] != sp.phone_number:
                                self.log_audit(db, r.recruiter_id, f"structured_phone_{sp.id}", sp.phone_number, res["value"], "Normalized")
                                sp.phone_number = res["value"]
                                modifications += 1

                    # 5. Company Normalization
                    if r.company:
                        if r.company.company_name:
                            new_cname = normalize_name(r.company.company_name)
                            if new_cname != r.company.company_name:
                                self.log_audit(db, r.recruiter_id, f"company_name", r.company.company_name, new_cname, "Capitalized")
                                r.company.company_name = new_cname
                                modifications += 1
                        if r.company.website:
                            clean_web = r.company.website.strip().lower()
                            if not clean_web.startswith("http") and clean_web:
                                clean_web = "https://" + clean_web
                            if clean_web != r.company.website:
                                self.log_audit(db, r.recruiter_id, f"company_website", r.company.website, clean_web, "Normalized URL")
                                r.company.website = clean_web
                                modifications += 1

                    # 6. Recruiter Name
                    if r.recruiter_name:
                        new_name = normalize_name(r.recruiter_name)
                        if new_name != r.recruiter_name:
                            self.log_audit(db, r.recruiter_id, "recruiter_name", r.recruiter_name, new_name, "Capitalized")
                            r.recruiter_name = new_name
                            modifications += 1

                    # 7. Location Intelligence (Rule 6)
                    if r.location and not r.state:
                        parts = [p.strip() for p in r.location.split(',')]
                        if len(parts) >= 2:
                            inferred_city = parts[0]
                            inferred_state = parts[1][:2].upper() # naive mapping
                            self.log_audit(db, r.recruiter_id, "state", r.state, inferred_state, "Inferred from location string")
                            r.normalized_city = inferred_city
                            r.state = inferred_state
                            modifications += 1

                    # 8. Phase II Company Inference (Rules 3, 4, 5)
                    old_company_id = r.company_id
                    if not r.company_id and r.email:
                        domain = extract_domain(r.email)
                        if domain:
                            comp_id, conf, reason = infer_company_from_domain(db, domain, r)
                            if comp_id:
                                r.company_id = comp_id
                                r.company_confidence = conf
                                r.company_reasoning = reason
                                ea = EnrichmentAudit(
                                    recruiter_id=r.recruiter_id, enrichment_type="company_inference",
                                    original_value=str(old_company_id), proposed_value=str(comp_id),
                                    final_value=str(comp_id), source="Sentinel Domain Inference",
                                    confidence_score=conf, action="assigned", reason=reason, run_id="sentinel_phase_2"
                                )
                                db.add(ea)
                                modifications += 1
                    if not old_company_id and r.company_id:
                        db.flush()
                        db.refresh(r)

                    # 9. Omnipresent Enrichment (JIT) - We handle this mostly synchronously now since we are already in a thread
                    enrichment_triggered = False
                    if r.company and r.company.company_name and is_human_name(r.recruiter_name, r.company.company_name, r.email):
                        missing_critical = not r.email or "missing.local" in r.email or not r.phone or not r.linkedin or not r.location
                        if missing_critical:
                            if not r.linkedin or not r.location:
                                try:
                                    success = jit_enrichment_service.enrich_recruiter_sync(db, r)
                                    if success: modifications += 1; enrichment_triggered = True
                                except Exception: pass
                            if not r.email or "missing.local" in r.email or not r.phone:
                                try:
                                    # Since auto_enhance_recruiter_data is async, we can run it in a new event loop or just skip it here 
                                    # for simplicity, but wait, we are in a thread, we can use asyncio.run
                                    res = asyncio.run(auto_enhance_recruiter_data(r.recruiter_name, r.company.company_name, r.company.website))
                                    if res.get('email') and (not r.email or "missing.local" in r.email):
                                        self.log_audit(db, r.recruiter_id, "email", r.email, res['email'], "Tavily")
                                        r.email = res['email']; modifications += 1; enrichment_triggered = True
                                    if res.get('phone') and not r.phone:
                                        self.log_audit(db, r.recruiter_id, "phone", r.phone, res['phone'], "Tavily")
                                        r.phone = res['phone']; modifications += 1; enrichment_triggered = True
                                except Exception: pass
                    
                    if enrichment_triggered:
                        import time as _time
                        _time.sleep(random.uniform(2.5, 4.5))

                    # 10. Missing Fields & Scoring
                    c = r.company
                    score, missing_list = calculate_completeness_score(r, c)
                    missing_dict = {
                        "primary_email": not bool(r.email) or "missing.local" in r.email,
                        "primary_phone": not bool(r.phone), "linkedin": not bool(r.linkedin),
                        "company": not bool(r.company_id), "location": not bool(r.location),
                        "title": not bool(r.title), "specialization": not bool(r.specialization)
                    }
                    r.missing_fields = json.dumps(missing_list)
                    r.completeness_score = score
                    r.quality_score = calculate_quality_score(r, missing_dict)

                    # 11. Review Queue Rules (Rule 11)
                    if r.company_confidence and r.company_confidence < 70:
                        r.needs_review = True
                        r.review_reason = f"Low confidence company match ({r.company_confidence}%)"
                    critical_fields_missing = []
                    if "Primary email" in missing_list: critical_fields_missing.append("Email")
                    if "Phone" in missing_list: critical_fields_missing.append("Phone")
                    if "City" in missing_list and "State" in missing_list and "Country" in missing_list: critical_fields_missing.append("Location")
                    if "Name (Non-Human)" in missing_list: critical_fields_missing.append("Valid Human Name")

                    if critical_fields_missing:
                        r.needs_review = True
                        r.review_reason = f"Missing critical fields: {', '.join(critical_fields_missing)}"
                    elif is_non_human_name_heuristic(r.recruiter_name):
                        r.needs_review = True
                        r.review_reason = "Non-human name detected"
                        
                    # Finalize
                    r.sentinel_status = "Completed"
                    r.last_scan_at = datetime.now(timezone.utc)
                    r.last_verified_at = datetime.now(timezone.utc)
                    if modifications > 0: repaired_count += 1
                    
                    db.commit() # Commit per recruiter to preserve partial progress
                    state.last_processed_id = r.recruiter_id
                    
                except Exception as e:
                    logger.error(f"Error processing recruiter {r.recruiter_id}: {e}")
                    db.rollback()

            # Batch complete
            state.profiles_analyzed += len(recruiters)
            state.profiles_repaired += repaired_count
            db.commit()
            db.close()
            return True
            
        except Exception as e:
            logger.error(f"SENTINEL Engine Loop Error: {e}")
            return False

    async def run_loop(self):
        logger.info("SENTINEL Engine v2 Started")
        while self.running:
            processed = await asyncio.to_thread(self._process_batch)
            if not processed:
                await asyncio.sleep(10)
            else:
                await asyncio.sleep(self.sleep_interval)

sentinel_engine = SentinelEngine()
