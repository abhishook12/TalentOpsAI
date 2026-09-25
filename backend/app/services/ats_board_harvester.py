"""
ats_board_harvester.py — Public ATS Career Board Harvester.
Crawls corporate applicant tracking system endpoints (Greenhouse, Lever, SmartRecruiters)
for target companies to extract active recruiters, hiring managers, and direct contacts.
"""

import os
import re
import time
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

import requests
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.staging_models import DiscoveryStaging
from ..models.models import Company, Recruiter
from ..services.email_intelligence_service import email_intelligence
from ..services.smtp_prober import smtp_prober

logger = logging.getLogger("talentops.ats_harvester")


class ATSBoardHarvester:
    """
    Direct public API harvester for corporate ATS boards (Greenhouse, Lever).
    Extracts hiring leads, recruiters, and contact points from live job requisitions.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })
        self.stats = {
            "boards_scanned": 0,
            "jobs_examined": 0,
            "hiring_contacts_found": 0,
            "contacts_staged": 0,
            "errors": 0,
        }

    def _derive_slugs(self, company_name: str, domain: str) -> List[str]:
        """Generates possible ATS sub-domain / board token slugs."""
        slugs = set()
        clean_name = re.sub(r"[^\w\s-]", "", company_name.lower())
        tokens = clean_name.split()
        if tokens:
            slugs.add(tokens[0])
            slugs.add("".join(tokens))
            slugs.add("-".join(tokens))
        
        # Domain based slug
        clean_dom = domain.lower().replace("www.", "").split(".")[0]
        slugs.add(clean_dom)
        return [s for s in slugs if len(s) >= 3]

    def scan_greenhouse(self, slug: str, domain: str) -> List[Dict[str, Any]]:
        """Queries public Greenhouse API for job requisitions."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        contacts = []
        try:
            r = self.session.get(url, timeout=6)
            if r.status_code == 200:
                data = r.json()
                jobs = data.get("jobs", [])
                self.stats["jobs_examined"] += len(jobs)
                for job in jobs[:15]:
                    title = job.get("title", "")
                    content = job.get("content", "") or ""
                    dept = job.get("departments", [{}])[0].get("name", "Talent Acquisition") if job.get("departments") else "Staffing"
                    
                    # Look for recruiter / hiring manager mentions
                    # e.g., "Contact: Sarah Jenkins" or "Recruiter: John Doe"
                    m = re.search(r"(?:recruiter|talent acquisition partner|hiring lead|point of contact)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)", content, re.I)
                    if m:
                        contacts.append({
                            "name": m.group(1).strip(),
                            "title": f"Recruiter - {dept}",
                            "source": "Greenhouse Requisition",
                            "source_url": job.get("absolute_url") or url,
                        })
                    
                    # Look for email mentions
                    email_m = re.search(r"([a-zA-Z0-9_.+-]+@" + re.escape(domain) + r")", content, re.I)
                    if email_m:
                        raw_email = email_m.group(1).strip()
                        # Extract name from email if possible
                        local = raw_email.split("@")[0]
                        if "." in local:
                            name_guess = " ".join([p.capitalize() for p in local.split(".") if p.isalpha()])
                            if len(name_guess.split()) == 2:
                                contacts.append({
                                    "name": name_guess,
                                    "title": f"Talent Acquisition ({dept})",
                                    "email": raw_email,
                                    "source": "Greenhouse Requisition",
                                    "source_url": job.get("absolute_url") or url,
                                })
        except Exception as err:
            logger.debug("Greenhouse scan error for %s: %s", slug, err)
        return contacts

    def scan_lever(self, slug: str, domain: str) -> List[Dict[str, Any]]:
        """Queries public Lever API for job postings."""
        url = f"https://api.lever.co/v0/postings/{slug}"
        contacts = []
        try:
            r = self.session.get(url, timeout=6)
            if r.status_code == 200:
                postings = r.json()
                if isinstance(postings, list):
                    self.stats["jobs_examined"] += len(postings)
                    for post in postings[:15]:
                        text = post.get("text", "")
                        desc = post.get("descriptionPlain", "") or ""
                        categories = post.get("categories", {})
                        team = categories.get("team", "Talent Acquisition")
                        
                        m = re.search(r"(?:recruiter|hiring manager|contact)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)", desc, re.I)
                        if m:
                            contacts.append({
                                "name": m.group(1).strip(),
                                "title": f"Technical Recruiter - {team}",
                                "source": "Lever Requisition",
                                "source_url": post.get("hostedUrl") or url,
                            })
        except Exception as err:
            logger.debug("Lever scan error for %s: %s", slug, err)
        return contacts

    def harvest_company(
        self,
        company_name: str,
        domain: str,
        db: Session,
        max_profiles: int = 5,
        owner_user_id: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Scans Greenhouse and Lever boards for target company,
        resolves emails, and stages discovered hiring personnel.
        """
        clean_dom = domain.lower().replace("www.", "").strip()
        slugs = self._derive_slugs(company_name, clean_dom)
        
        all_discovered = []
        for s in slugs:
            gh_res = self.scan_greenhouse(s, clean_dom)
            if gh_res:
                all_discovered.extend(gh_res)
                break
            lever_res = self.scan_lever(s, clean_dom)
            if lever_res:
                all_discovered.extend(lever_res)
                break

        self.stats["boards_scanned"] += 1
        staged_records = []
        seen = set()

        batch_id = f"ats_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        for cand in all_discovered:
            name = cand.get("name")
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())

            # Synthesize or verify email
            email_val = cand.get("email")
            smtp_status = "UNVERIFIED"

            if not email_val:
                tokens = name.split()
                if len(tokens) >= 2:
                    perms = email_intelligence.generate_permutations(tokens[0], tokens[-1], clean_dom)
                    if perms:
                        email_val = perms[0]["email"]

            if email_val:
                try:
                    probe = smtp_prober.probe_mailbox(email_val)
                    if probe.smtp_code == 250:
                        smtp_status = "SMTP_VERIFIED"
                except Exception:
                    pass

            disc_id = f"ats_{uuid.uuid4().hex[:12]}"
            staged = DiscoveryStaging(
                batch_id=batch_id,
                discovery_id=disc_id,
                device_id="ats_worker_01",
                owner_user_id=owner_user_id,
                raw_name=name,
                raw_title=cand.get("title", "Talent Acquisition Partner"),
                raw_company=company_name,
                raw_email=email_val,
                source_url=cand.get("source_url"),
                source_page_title=f"ATS Job Board — {company_name}",
                extraction_source="ats_job_board",
                dom_confidence=98,
                processing_status="pending",
                quality_score=90 if smtp_status == "SMTP_VERIFIED" else 80,
                metadata_json=f'{{"source": "ats_job_board", "smtp_status": "{smtp_status}", "domain": "{clean_dom}"}}'
            )
            db.add(staged)
            staged_records.append({
                "name": name,
                "title": cand.get("title"),
                "email": email_val,
                "smtp_status": smtp_status,
                "company": company_name,
            })
            self.stats["contacts_staged"] += 1
            if len(staged_records) >= max_profiles:
                break

        if staged_records:
            db.commit()
            logger.info("[ATS_HARVESTER] Staged %d contacts for %s", len(staged_records), company_name)
        return staged_records


ats_board_harvester = ATSBoardHarvester()
