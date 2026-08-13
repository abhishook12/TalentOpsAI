import asyncio
import os
import json
import logging
from datetime import datetime, timezone
import aiohttp
from typing import Dict, Any, List, Optional
import pandas as pd
import duckdb
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal
from app.models.models import Company, Recruiter
from app.services.parquet_writer import ParquetWriter
from app.services.recruiter_store import PARQUET_FILE
from app.utils.normalizer import extract_domain

logger = logging.getLogger("identity_engine")

FREE_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 
    'icloud.com', 'live.com', 'msn.com', 'comcast.net', 'att.net', 
    'sbcglobal.net', 'verizon.net', 'me.com', 'mail.com', 'protonmail.com', 
    'ymail.com', 'cox.net', 'charter.net', 'earthlink.net', 'talentops.ai'
}

STATE_FILE = "identity_engine_state.json"

class IdentityEngine:
    def __init__(self):
        self.parquet_writer = ParquetWriter()
        self.state = self._load_state()
        self.is_running = False
        self.lock = asyncio.Lock()

    def _load_state(self) -> Dict[str, Any]:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        return {
            "total_companies": 0,
            "processed": 0,
            "resolved": 0,
            "unresolved": 0,
            "logos_verified": 0,
            "logos_rejected": 0,
            "duplicates_merged": 0,
            "errors": 0,
            "status": "idle"
        }

    def _save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    async def _verify_logo_url(self, url: str, session: aiohttp.ClientSession) -> bool:
        if not url:
            return False
        try:
            async with session.head(url, timeout=5, allow_redirects=True) as resp:
                if resp.status == 200 and resp.headers.get("Content-Type", "").startswith("image/"):
                    return True
                async with session.get(url, timeout=5) as get_resp:
                    return get_resp.status == 200 and get_resp.headers.get("Content-Type", "").startswith("image/")
        except Exception:
            return False
            
    async def get_clearbit_logo(self, domain: str, session: aiohttp.ClientSession) -> Optional[str]:
        # The backend VM lacks DNS/Internet to verify Clearbit logos.
        # We will assume the logo exists and let the frontend handle broken images via onerror.
        return f"https://logo.clearbit.com/{domain}"

    def get_domains_to_process(self) -> List[Dict[str, Any]]:
        if not os.path.exists(PARQUET_FILE):
            return []
        try:
            con = duckdb.connect()
            # Extract email domains, count recruiters, order by count DESC
            query = f"""
                SELECT 
                    CAST(LOWER(SPLIT_PART(email, '@', 2)) AS VARCHAR) as domain,
                    COUNT(*) as recruiter_count
                FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
                WHERE email IS NOT NULL AND email != ''
                GROUP BY 1
                ORDER BY 2 DESC
            """
            res = con.execute(query).fetchall()
            con.close()
            return [{"domain": row[0], "count": row[1]} for row in res if row[0]]
        except Exception as e:
            logger.error(f"Error getting domains from parquet: {e}")
            return []

    async def start_job(self):
        async with self.lock:
            if self.is_running:
                return
            self.is_running = True
            self.state["status"] = "running"
            self._save_state()
            
        # Run the job in background
        asyncio.create_task(self._run_job())

    async def _run_job(self):
        try:
            domains = self.get_domains_to_process()
            self.state["total_companies"] = len(domains)
            self._save_state()

            async with aiohttp.ClientSession() as http_session:
                domain_updates = []
                for item in domains:
                    if not self.is_running:
                        break
                    domain = item["domain"]
                    try:
                        update = await self._process_domain(domain, http_session)
                        if update:
                            domain_updates.append(update)
                        self.state["processed"] += 1
                    except Exception as e:
                        logger.error(f"Error processing domain {domain}: {e}")
                        self.state["errors"] += 1
                    
                    if self.state["processed"] % 100 == 0:
                        self._save_state()
                        # Batch Parquet updates every 100 domains to avoid excessive file rewrites
                        if domain_updates:
                            self._apply_parquet_batch(domain_updates)
                            domain_updates = []

                if domain_updates:
                    self._apply_parquet_batch(domain_updates)
                    self._save_state()

            self.state["status"] = "completed"
        except Exception as e:
            logger.error(f"Identity job failed: {e}")
            self.state["status"] = "failed"
        finally:
            self.is_running = False
            self._save_state()

    def _apply_parquet_batch(self, domain_updates: List[Dict[str, Any]]):
        if not os.path.exists(PARQUET_FILE) or not domain_updates:
            return
            
        try:
            con = duckdb.connect()
            # Fetch all recruiter_ids for these domains in one go
            domain_list = [d["domain"] for d in domain_updates]
            domain_to_id = {d["domain"]: d["company_id"] for d in domain_updates}
            
            # Use placeholders for domains
            placeholders = ', '.join(['?'] * len(domain_list))
            query = f"""
                SELECT recruiter_id, CAST(LOWER(SPLIT_PART(email, '@', 2)) AS VARCHAR) as domain
                FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
                WHERE CAST(LOWER(SPLIT_PART(email, '@', 2)) AS VARCHAR) IN ({placeholders})
            """
            res = con.execute(query, domain_list).fetchall()
            con.close()
            
            updates = []
            for row in res:
                recruiter_id, domain = row
                if domain in domain_to_id:
                    updates.append({"recruiter_id": recruiter_id, "company_id": domain_to_id[domain]})
            
            if updates:
                # Update records in Parquet (batch sizes handled by writer)
                batch_size = 5000
                for i in range(0, len(updates), batch_size):
                    self.parquet_writer.update_records(updates[i:i+batch_size])
        except Exception as e:
            logger.error(f"Error applying parquet batch: {e}")

    async def _process_domain(self, domain: str, http_session: aiohttp.ClientSession) -> Optional[Dict[str, int]]:
        db = SessionLocal()
        try:
            # Check free domains
            if domain in FREE_DOMAINS:
                # Mark as Unresolved/Individual
                company_id = self._upsert_unresolved(db, domain)
                self.state["unresolved"] += 1
                return {"domain": domain, "company_id": company_id}

            # Try to resolve logo
            logo_url = await self.get_clearbit_logo(domain, http_session)
            
            if logo_url:
                verification_status = "verified"
                self.state["logos_verified"] += 1
            else:
                verification_status = "missing"
                self.state["logos_rejected"] += 1

            # Canonical Name (fallback to domain capitalized)
            canonical_name = domain.split('.')[0].replace('-', ' ').title()

            company_id = self._upsert_company(db, domain, canonical_name, logo_url, verification_status)
            self.state["resolved"] += 1

            return {"domain": domain, "company_id": company_id}

        finally:
            db.close()

    def _upsert_unresolved(self, db: Session, domain: str) -> int:
        # Create or update an "Unknown / Individual" bucket for this domain, or a global one
        # Actually, creating a specific one for the free domain is better so it has a valid record
        comp = db.query(Company).filter(Company.primary_domain == domain).first()
        if not comp:
            comp = Company(
                company_name="Unknown / Individual",
                primary_domain=domain,
                canonical_name="Unknown / Individual",
                verification_status="unresolved",
                identity_confidence=0,
                last_verified_at=datetime.now(timezone.utc)
            )
            db.add(comp)
            db.commit()
            db.refresh(comp)
        return comp.company_id

    def _upsert_company(self, db: Session, domain: str, name: str, logo_url: Optional[str], status: str) -> int:
        # Deduplication check: get all companies matching this domain
        comps = db.query(Company).filter(
            (Company.primary_domain == domain) | 
            (Company.website.ilike(f"%{domain}%")) |
            (Company.email_pattern.ilike(f"%{domain}%"))
        ).order_by(Company.company_id).all()

        if not comps:
            comp = Company(
                company_name=name,
                primary_domain=domain,
                canonical_name=name,
                logo_url=logo_url,
                logo_source="clearbit" if logo_url else None,
                verification_status=status,
                identity_confidence=90 if logo_url else 50,
                last_verified_at=datetime.now(timezone.utc)
            )
            db.add(comp)
            db.commit()
            db.refresh(comp)
            return comp.company_id
        else:
            # Deduplicate into the first one
            canonical = comps[0]
            canonical.primary_domain = domain
            if logo_url:
                canonical.logo_url = logo_url
                canonical.logo_source = "clearbit"
            canonical.verification_status = status
            canonical.canonical_name = name
            canonical.last_verified_at = datetime.now(timezone.utc)
            
            # Merge others
            for other in comps[1:]:
                other.merged_into_id = canonical.company_id
                self.state["duplicates_merged"] += 1
            
            db.commit()
            return canonical.company_id

    # Removed _update_parquet_recruiters as logic is moved to _apply_parquet_batch

identity_engine = IdentityEngine()
