import asyncio
import json
import logging
import re
import os
import random
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import SessionLocal
from app.models.models import Recruiter, Company, DomainIntelligence, EnrichmentAudit
from app.models.sentinel_state import SentinelPhase4State
from app.services.scraper import is_human_name
from app.services.mailintel_engine import extract_domain
from app.services.parquet_writer import parquet_writer
from app.services.recruiter_store import recruiter_store

logger = logging.getLogger("sentinel")

# ─── INTELLIGENCE MODULES ───

import math

def is_nan(val):
    if val is None: return True
    if isinstance(val, float) and math.isnan(val): return True
    return False

def normalize_email(email):
    if is_nan(email): return None
    email = str(email).strip().lower()
    if email in ('n/a', 'null', 'none', '-', 'unknown', 'test', 'nan'): return None
    if re.match(r"^(info|admin|sales|careers|contact|test)@", email):
        return {"value": email, "issue": "role_based"}
    if "missing.local" in email or "example.com" in email:
        return {"value": email, "issue": "fake_domain"}
    return {"value": email, "issue": None}

def normalize_phone(phone):
    if is_nan(phone): return None
    phone = str(phone)
    if phone.lower() in ('n/a', 'null', 'none', '-', 'unknown', 'test', 'nan'): return None
    cleaned = re.sub(r'[^\d\+]', '', phone)
    if len(cleaned) < 7:
        return {"value": phone, "issue": "invalid_length"}
    return {"value": cleaned, "issue": None}

def normalize_name(name):
    if is_nan(name): return None
    name = str(name)
    if name.lower() in ('n/a', 'null', 'none', '-', 'unknown', 'test', 'nan'): return None
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

def calculate_completeness(r_dict: dict, comp_dict: dict):
    score = 0
    total_fields = 10
    missing = []
    
    fields = [
        ("Name", r_dict.get('recruiter_name')),
        ("Company", comp_dict.get('company_name')),
        ("Title", r_dict.get('title')),
        ("Primary email", r_dict.get('email')),
        ("Phone", r_dict.get('phone')),
        ("LinkedIn", r_dict.get('linkedin')),
        ("City", r_dict.get('normalized_city')),
        ("State", r_dict.get('state')),
        ("Specialization", r_dict.get('specialization')),
        ("Company website", comp_dict.get('website'))
    ]
    for fname, val in fields:
        if val and str(val).strip() and "missing.local" not in str(val).lower() and val not in ('n/a', 'null', 'none', '-'):
            if fname == "Name" and is_non_human_name_heuristic(str(val)):
                missing.append("Name (Non-Human)")
            else:
                score += 1
        else:
            missing.append(fname)
    pct = int((score / total_fields) * 100)
    return pct, missing

def calculate_quality(missing_fields: dict):
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

class SentinelEngine:
    def __init__(self):
        self.running = False
        self.batch_size = 100
        self.sleep_interval = 0.5
        self.companies_cache = {} # id -> dict

    def start(self):
        self.running = True
        asyncio.create_task(self.run_loop())

    def stop(self):
        self.running = False

    def log_audit(self, db: Session, recruiter_id: int, field: str, old: str, new: str, reason: str, confidence: float = 1.0):
        if old != new:
            ea = EnrichmentAudit(
                recruiter_id=recruiter_id, enrichment_type=field,
                original_value=str(old) if old else None,
                proposed_value=str(new) if new else None,
                final_value=str(new) if new else None,
                source="Sentinel Phase IV", confidence_score=int(confidence*100),
                action="update", reason=reason, run_id="sentinel_phase_4"
            )
            db.add(ea)
            return True
        return False

    def get_company(self, db, company_id):
        if not company_id: return {}
        if company_id in self.companies_cache:
            return self.companies_cache[company_id]
        comp = db.query(Company).filter(Company.company_id == company_id).first()
        if comp:
            res = {"company_name": comp.company_name, "website": comp.website, "industry": comp.industry}
        else:
            res = {}
        if len(self.companies_cache) > 5000:
            self.companies_cache.clear()
        self.companies_cache[company_id] = res
        return res

    def _sync_audit(self):
        """Phase 1: Run the full audit query against Parquet"""
        logger.info("[Phase IV] Running Full Database Audit...")
        try:
            recruiter_store._ensure_loaded()
            conn = recruiter_store._conn
            if not conn: return
            
            # Global metrics
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN email IS NULL OR email = '' OR email ILIKE '%missing.local%' THEN 1 ELSE 0 END) as no_email,
                    SUM(CASE WHEN phone IS NULL OR phone = '' THEN 1 ELSE 0 END) as no_phone,
                    SUM(CASE WHEN linkedin IS NULL OR linkedin = '' THEN 1 ELSE 0 END) as no_li,
                    SUM(CASE WHEN company_id IS NULL THEN 1 ELSE 0 END) as no_company,
                    COUNT(DISTINCT company_id) as total_companies,
                    SUM(CASE WHEN completeness_score < 50 THEN 1 ELSE 0 END) as below_50,
                    SUM(CASE WHEN completeness_score > 90 THEN 1 ELSE 0 END) as above_90,
                    AVG(completeness_score) as avg_comp,
                    AVG(quality_score) as avg_qual
                FROM recruiters
            """).fetchone()
            
            db = SessionLocal()
            state = db.query(SentinelPhase4State).first()
            if not state:
                state = SentinelPhase4State()
                db.add(state)
            
            state.total_recruiters = int(stats[0])
            state.missing_emails = int(stats[1])
            state.missing_phones = int(stats[2])
            state.missing_linkedin = int(stats[3])
            state.unknown_companies = int(stats[4])
            state.total_companies = int(stats[5] or 0)
            state.profiles_below_50 = int(stats[6])
            state.profiles_above_90 = int(stats[7])
            state.avg_completeness = int(stats[8] or 0)
            state.avg_confidence = int(stats[9] or 0)
            
            state.status = "Auditing"
            db.commit()
            db.close()
            logger.info(f"[Phase IV] Audit Complete. Total Profiles: {stats[0]}")
        except Exception as e:
            logger.error(f"[Phase IV] Audit failed: {e}")

    def _process_phase4(self):
        """Process one bounded batch of unscanned recruiters.

        Parquet is immutable, so every write rewrites its containing file. Keeping
        this batch bounded prevents the old nested company/state loop from holding
        a database session and a stale DuckDB connection for an entire dataset run.
        """
        try:
            db = SessionLocal()
            state = db.query(SentinelPhase4State).first()
            if not state:
                db.close(); return False
                
            if state.status == "Paused":
                db.close(); return False
                
            state.status = "Running"
            db.commit()
            
            recruiter_store._ensure_loaded()
            conn = recruiter_store._conn
            if not conn: db.close(); return False

            df = conn.execute("""
                SELECT * FROM recruiters
                WHERE COALESCE(sentinel_status, '') != 'Completed'
                ORDER BY recruiter_id
                LIMIT ?
            """, [self.batch_size]).fetchdf()

            if df.empty:
                state.status = "Idle"
                db.commit()
                db.close()
                self._sync_audit()
                return False

            batch_updates = []
            completed_company_ids = set()
            for _, row in df.iterrows():
                if not self.running:
                    break
                r_dict = row.to_dict()
                rid = r_dict["recruiter_id"]
                c_id = r_dict.get("company_id")
                c_dict = self.get_company(db, c_id)
                state.current_company_id = c_id
                state.current_company_name = c_dict.get("company_name", f"Company #{c_id}" if c_id else "Unassigned")
                state.current_state = r_dict.get("state") or "Unknown"
                completed_company_ids.add(c_id)

                if r_dict.get("email"):
                    res = normalize_email(r_dict["email"])
                    new_val = res["value"] if res else None
                    if new_val != r_dict["email"]:
                        self.log_audit(db, rid, "email", r_dict["email"], new_val, "Normalized via Phase IV Engine")
                        r_dict["email"] = new_val

                if r_dict.get("phone"):
                    res = normalize_phone(r_dict["phone"])
                    new_val = res["value"] if res else None
                    if new_val != r_dict["phone"]:
                        self.log_audit(db, rid, "phone", r_dict["phone"], new_val, "Normalized via Phase IV Engine")
                        r_dict["phone"] = new_val

                if r_dict.get("recruiter_name"):
                    new_name = normalize_name(r_dict["recruiter_name"])
                    if new_name != r_dict["recruiter_name"]:
                        self.log_audit(db, rid, "recruiter_name", r_dict["recruiter_name"], new_name, "Capitalized")
                        r_dict["recruiter_name"] = new_name

                score, _ = calculate_completeness(r_dict, c_dict)
                missing_dict = {
                    "primary_email": not bool(r_dict.get("email")) or "missing.local" in str(r_dict.get("email") or ""),
                    "primary_phone": not bool(r_dict.get("phone")), "linkedin": not bool(r_dict.get("linkedin")),
                    "company": not bool(c_id), "location": not bool(r_dict.get("location")),
                    "title": not bool(r_dict.get("title")), "specialization": not bool(r_dict.get("specialization"))
                }
                r_dict["completeness_score"] = score
                r_dict["quality_score"] = calculate_quality(missing_dict)
                r_dict["sentinel_status"] = "Completed"
                r_dict["last_scan_at"] = datetime.now(timezone.utc).isoformat()
                batch_updates.append(r_dict)

            if not batch_updates:
                db.close()
                return False

            # Persist Parquet first; audit and progress state are committed only if
            # the actual recruiter changes were safely written.
            parquet_writer.update_records(batch_updates)
            state.recruiters_completed += len(batch_updates)
            state.companies_completed += len(completed_company_ids - {None})
            state.current_batch_count = len(batch_updates)
            db.commit()
            db.close()
            return True
            
        except Exception as e:
            logger.error(f"SENTINEL Phase IV Engine Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def run_loop(self):
        logger.info("SENTINEL Engine Phase IV Started")
        await asyncio.to_thread(self._sync_audit)
        while self.running:
            processed = await asyncio.to_thread(self._process_phase4)
            if not processed:
                await asyncio.sleep(300)
            else:
                await asyncio.sleep(2)

sentinel_engine = SentinelEngine()
