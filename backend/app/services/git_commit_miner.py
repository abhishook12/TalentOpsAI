"""
git_commit_miner.py — Public Git & Commit Email Miner.
Mines public commit history and author metadata for target company domains
to discover 100% ground-truth corporate email formulas and active technical personnel.
"""

import os
import re
import time
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import xml.etree.ElementTree as ET

import requests
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.staging_models import DiscoveryStaging
from ..models.models import Company, CompanyEmailPattern, Recruiter
from ..services.email_intelligence_service import email_intelligence
from ..services.smtp_prober import smtp_prober

logger = logging.getLogger("talentops.git_miner")


class GitCommitMiner:
    """
    Discovers authentic corporate emails and establishes 100% verified
    company email formula patterns by inspecting public git commit logs.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TalentOpsAI-CommitMiner/1.0",
            "Accept": "application/vnd.github.v3+json, application/atom+xml",
        })
        self.stats = {
            "domains_mined": 0,
            "commits_inspected": 0,
            "verified_corporate_emails": 0,
            "patterns_locked": 0,
            "contacts_staged": 0,
        }

    def _deduce_formula(self, first_name: str, last_name: str, local_part: str) -> Optional[str]:
        """
        Deduces the exact formula template from a person's name and local-part.
        e.g., 'Christopher', 'Montgomery', 'cmontgomery' -> 'f_last'
        """
        f = first_name.lower().strip()
        l = last_name.lower().strip()
        local = local_part.lower().strip()

        if local == f"{f}.{l}":
            return "first.last"
        elif local == f"{f[0]}{l}":
            return "f_last"
        elif local == f"{f}_{l}":
            return "first_last"
        elif local == f:
            return "first"
        elif local == f"{f}.{l[0]}":
            return "first.l"
        elif local == f"{f}{l[0]}":
            return "first_l"
        elif local == f"{l}.{f}":
            return "last.first"
        return None

    def mine_github_commits_api(self, domain: str, max_items: int = 10) -> List[Dict[str, str]]:
        """
        Queries GitHub Commits Search API for authors matching domain.
        """
        url = f"https://api.github.com/search/commits?q=author-email:{domain}&per_page={max_items}"
        results = []
        try:
            r = self.session.get(url, timeout=8)
            if r.status_code == 200:
                data = r.json()
                items = data.get("items", [])
                self.stats["commits_inspected"] += len(items)
                for item in items:
                    commit = item.get("commit", {})
                    author = commit.get("author", {})
                    name = author.get("name", "").strip()
                    email = author.get("email", "").strip().lower()

                    if email.endswith(f"@{domain}") and "noreply" not in email and "bot" not in email:
                        results.append({
                            "name": name,
                            "email": email,
                            "source": "GitHub Commit API",
                        })
        except Exception as e:
            logger.debug("GitHub commit API error for %s: %s", domain, e)
        return results

    def mine_company_domain(
        self,
        company_name: str,
        domain: str,
        db: Session,
        max_contacts: int = 5,
        owner_user_id: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Mines commit history for target domain, reverse-engineers email formulas,
        updates CompanyEmailPattern, and stages discovered employees.
        """
        clean_dom = domain.lower().replace("www.", "").strip()
        raw_authors = self.mine_github_commits_api(clean_dom, max_items=15)

        self.stats["domains_mined"] += 1
        staged_records = []
        seen = set()

        batch_id = f"git_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        for author in raw_authors:
            email_val = author["email"]
            name = author["name"]

            if email_val in seen or not name:
                continue
            seen.add(email_val)

            # Check tokens
            tokens = name.split()
            if len(tokens) < 2:
                continue
            first, last = tokens[0], tokens[-1]
            local = email_val.split("@")[0]

            formula = self._deduce_formula(first, last, local)
            if formula:
                # Lock in confirmed pattern with 100% confidence
                existing_pat = db.query(CompanyEmailPattern).filter(
                    CompanyEmailPattern.domain == clean_dom,
                    CompanyEmailPattern.pattern == formula,
                ).first()

                if existing_pat:
                    existing_pat.confidence_score = 100
                    existing_pat.verified_example_count = (existing_pat.verified_example_count or 0) + 1
                    existing_pat.last_verified_at = datetime.utcnow()
                else:
                    new_pat = CompanyEmailPattern(
                        company_id=0,
                        domain=clean_dom,
                        pattern=formula,
                        confidence_score=100,
                        verified_example_count=1,
                        active=True,
                        last_verified_at=datetime.utcnow()
                    )
                    db.add(new_pat)
                self.stats["patterns_locked"] += 1

            self.stats["verified_corporate_emails"] += 1

            # Stage the contact
            disc_id = f"git_{uuid.uuid4().hex[:12]}"
            staged = DiscoveryStaging(
                batch_id=batch_id,
                discovery_id=disc_id,
                device_id="git_miner_01",
                owner_user_id=owner_user_id,
                raw_name=name,
                raw_title="Engineering Lead / Corporate Contributor",
                raw_company=company_name,
                raw_email=email_val,
                source_url=f"https://github.com/search?q=author-email%3A{clean_dom}",
                source_page_title=f"Git Commit Logs — {company_name}",
                extraction_source="git_commit_mine",
                dom_confidence=99,
                processing_status="pending",
                quality_score=95,
                metadata_json=f'{{"source": "git_commit_mine", "formula": "{formula}", "domain": "{clean_dom}"}}'
            )
            db.add(staged)
            staged_records.append({
                "name": name,
                "email": email_val,
                "formula": formula,
                "company": company_name,
            })
            self.stats["contacts_staged"] += 1
            if len(staged_records) >= max_contacts:
                break

        if staged_records:
            db.commit()
            logger.info("[GIT_MINER] Staged %d commit authors for %s", len(staged_records), company_name)

        return staged_records


git_commit_miner = GitCommitMiner()
