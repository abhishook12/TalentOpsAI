"""
search_xray_harvester.py — Autonomous Search Engine Recruiter X-Ray Harvester.
Programmatically queries public search engine indexes for recruiter profiles,
extracts structured candidate identities, resolves corporate emails with live SMTP verification,
and pushes them safely into discovery_staging.
"""

import os
import re
import time
import logging
import urllib.parse
import hashlib
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import SessionLocal
from ..models.staging_models import DiscoveryStaging
from ..models.models import Company, Recruiter
from ..models.auth_models import User
from ..services.email_intelligence_service import email_intelligence, SEEDED_COMPANY_PATTERNS
from ..services.smtp_prober import smtp_prober
from ..services.geographic_classifier import geo_classifier, GeoClassification
from ..services.geo_quota_tracker import GeoQuotaTracker

logger = logging.getLogger("talentops.search_xray")

DORK_TITLES = [
    "Technical Recruiter",
    "Talent Acquisition",
    "Senior Recruiter",
    "Recruiting Manager",
    "Lead Sourcer",
    "Head of Talent",
    "Talent Acquisition Manager",
    "Talent Acquisition Director",
    "VP Talent Acquisition",
    "Head of Recruiting",
    "Director of Talent",
    "Staffing Manager",
    "Head of People",
    "VP People Operations",
    "Chief People Officer",
    # Expanded titles — mid-level & specialist roles (common on LinkedIn)
    "IT Recruiter",
    "Campus Recruiter",
    "Executive Recruiter",
    "Sourcing Specialist",
    "Recruitment Consultant",
    "Talent Partner",
    "People Operations Manager",
    "Staffing Specialist",
    "Contract Recruiter",
    "Recruiting Coordinator",
]

# Geographic location qualifiers appended to dork queries for NA-biased discovery
GEO_DORK_QUALIFIERS = [
    '"United States"',
    '"New York"',
    '"San Francisco"',
    '"Chicago"',
    '"Texas"',
    '"California"',
    '"Canada"',
    '"London"',
    '"United Kingdom"',
]


class SearchXRayHarvester:
    """
    Mines real, active recruiter and talent acquisition profiles
    from public search engine caches via structured boolean dorks.
    Uses a warm persistent browser pool to avoid cold-start overhead.
    """

    def __init__(self):
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        self.stats = {
            "total_dorks_executed": 0,
            "profiles_discovered": 0,
            "profiles_staged": 0,
            "emails_smtp_verified": 0,
            "errors": 0,
        }
        # ── Zero-Browser TLS-Impersonated HTTP Engine (0 MB Chrome RAM, 0 Subprocesses) ──
        import threading
        self._thread_local = threading.local()
        self._cache_lock = threading.Lock()
        # ── Dork Result Cache (Speed Optimization) ──
        self._dork_cache: Dict[str, tuple] = {}  # query_hash → (results_list, timestamp)
        self._dork_cache_ttl = 7200  # 2 hours in seconds

    def _shutdown_browser(self):
        """No-op compatibility hook (SearchXRayHarvester now uses 100% zero-browser HTTP)."""
        pass

    def _flush_stale_cache(self):
        """Removes expired entries from dork cache."""
        now = time.time()
        stale_keys = [k for k, v in self._dork_cache.items() if now - v[1] > self._dork_cache_ttl]
        for k in stale_keys:
            self._dork_cache.pop(k, None)

    def _clean_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def parse_snippet_profile(self, card_text: str, link: str, target_company: str) -> Optional[Dict[str, Any]]:
        """
        Extracts candidate name, title, and location from a search result card.
        Example card text:
        'Justin Carey - Senior Technical Recruiter at Insight Global ...'
        """
        if not link or not card_text:
            return None

        # Hard LinkedIn Candidate Gate: ONLY accept individual LinkedIn profile URLs
        if "linkedin.com/in/" not in link:
            return None

        clean = self._clean_text(card_text)

        # Split card text by raw newlines first to isolate the main headline
        raw_lines = [
            l.strip() for l in card_text.splitlines()
            if l.strip() and not l.startswith("http") and l.lower() not in ("linkedin", "view profile")
        ]
        if not raw_lines:
            return None

        headline = ""
        for line in raw_lines:
            if " - " in line or " | " in line or " – " in line or " — " in line:
                headline = line
                break
        if not headline:
            headline = raw_lines[0]

        # Pattern: Name - Title at Company ...
        parts = re.split(r"\s+[-–—|•]\s+", headline)
        if len(parts) < 2:
            parts = re.split(r"[-|]", headline)

        if len(parts) < 2:
            return None

        raw_name = parts[0].strip()
        # Clean out any brackets or emojis
        raw_name = re.sub(r"\(.*?\)", "", raw_name)
        raw_name = re.sub(r"[^\w\s\.\'-]", "", raw_name).strip()

        # Sanity check name (must be 2-4 words, no numbers, not a generic word)
        name_tokens = raw_name.split()
        if len(name_tokens) < 2 or len(name_tokens) > 4:
            return None

        # Gate with strict human name validation and anti-noise checks
        from ..utils.normalizer import validate_human_name, is_company_name, is_platform_name, is_ui_action
        if is_platform_name(raw_name) or is_ui_action(raw_name) or is_company_name(raw_name):
            return None

        is_valid_human, clean_h_name, _ = validate_human_name(raw_name)
        if not is_valid_human:
            return None
        raw_name = clean_h_name

        # Check against blacklist
        blacklist = {"linkedin", "login", "signup", "jobs", "directory", "profile", "view"}
        if any(t.lower() in blacklist for t in raw_name.lower().split()):
            return None

        # Check against spam, adult, and blackhat SEO patterns
        spam_phrases = {"gái gọi", "viet nam", "việt nam", "casino", "poker", "escort", "massage", "bắn cá", "kèo nhà cái", "soi cầu", "seo agency", "porn", "sex"}
        lower_raw = raw_name.lower()
        if any(sp in lower_raw for sp in spam_phrases):
            return None

        # Verify genuine human name against dictionary
        try:
            from .scraper import is_human_name
            if not is_human_name(raw_name, target_company):
                return None
        except Exception:
            pass

        clean_title = parts[1].strip()
        # Remove trailing "at Company ..." or "..."
        clean_title = re.sub(r"\s*\.{2,}.*", "", clean_title)
        clean_title = re.sub(r"\s*\|\s*LinkedIn.*", "", clean_title, flags=re.I).strip()
        
        # Check for location cues in the rest of the text
        raw_location = None
        loc_match = re.search(r"(Greater [A-Za-z ]+ Area|[A-Za-z ]+,\s*[A-Z]{2}|[A-Za-z ]+,\s*United States)", clean)
        if loc_match:
            raw_location = loc_match.group(1).strip()

        # Extract genuine employer company from headline cues (e.g. "Recruiter at Google", "Talent Lead @ Meta")
        extracted_company = None
        comp_match = re.search(
            r"(?:^|[\s,–—-])(?:at|@|with)\s+([A-Za-z0-9&.,' -]+?)(?:\s*\(|\s*\[|\s*–|\s*—|\s*\||\s*\.|$)",
            clean_title,
            re.IGNORECASE
        )
        if comp_match:
            cand_comp = comp_match.group(1).strip(" .,-–—")
            generic_words = {"startups", "scaleups", "home", "remote", "confidential", "stealth", "freelance", "contract"}
            if cand_comp.lower() not in generic_words and len(cand_comp) > 1:
                extracted_company = cand_comp
                # Strip company part from title
                clean_title = re.sub(
                    r"\s*(?:at|@|with)\s+" + re.escape(cand_comp),
                    "",
                    clean_title,
                    flags=re.IGNORECASE
                ).strip(" .,-–—")

        # Disambiguate company: prioritize extracted company if target_company was generic or doesn't match
        final_company = extracted_company or target_company

        return {
            "name": raw_name,
            "title": clean_title if clean_title else "Recruiter",
            "company": final_company,
            "extracted_company": extracted_company,
            "profile_url": link,
            "location": raw_location,
            "snippet": clean[:250],
        }

    def execute_dork(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Executes search dork using 100% Zero-Browser TLS-Impersonated HTTP (curl_cffi)
        and in-memory result cache. Consumes 0 MB of Chrome RAM and spawns 0 subprocesses.
        """
        query_key = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
        now = time.time()

        with self._cache_lock:
            self._flush_stale_cache()
            if query_key in self._dork_cache:
                cached_results, timestamp = self._dork_cache[query_key]
                if now - timestamp < self._dork_cache_ttl:
                    logger.info("[SEARCH_XRAY] Dork cache HIT for '%s' (0ms)", query)
                    self.stats["total_dorks_executed"] += 1
                    return cached_results[:max_results]
                else:
                    self._dork_cache.pop(query_key, None)

        results = []
        url = f"https://search.yahoo.com/search?p={urllib.parse.quote(query)}"

        try:
            from bs4 import BeautifulSoup
            try:
                from curl_cffi import requests as cffi_requests
                r = cffi_requests.get(url, impersonate="chrome124", timeout=8)
                html_text = r.text if r.status_code == 200 else ""
            except Exception:
                import requests
                r = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=8)
                html_text = r.text if r.status_code == 200 else ""

            if html_text:
                soup = BeautifulSoup(html_text, "html.parser")
                cards = soup.select(".algo")
                for c in cards:
                    try:
                        text_val = c.get_text(separator="\n").strip()
                        a_tags = c.find_all("a", href=True)
                        href = ""
                        for a in a_tags:
                            raw_h = a.get("href") or ""
                            unquoted_h = urllib.parse.unquote(raw_h)
                            # Extract clean destination from Yahoo /RU=https://.../RK= wrapper
                            ru_match = re.search(r"/RU=(https?://[^/]+/in/[^/&?\"']+)", unquoted_h)
                            if ru_match:
                                candidate_h = ru_match.group(1)
                            else:
                                candidate_h = unquoted_h
                            if "linkedin.com/in/" in candidate_h:
                                href = candidate_h
                                break
                        if text_val and href and "linkedin.com/in/" in href:
                            results.append({"text": text_val, "link": href})
                            if len(results) >= max_results:
                                break
                    except Exception as err:
                        logger.debug("Card parse error: %s", err)

            if results:
                with self._cache_lock:
                    self._dork_cache[query_key] = (results, time.time())
        except Exception as e:
            logger.debug("[SEARCH_XRAY] Primary HTTP dork note for '%s': %s — trying Bing fallback", query, e)

        if not results:
            results = self._execute_dork_http(query, max_results)
            if results:
                with self._cache_lock:
                    self._dork_cache[query_key] = (results, time.time())

        self.stats["total_dorks_executed"] += 1
        return results

    def _execute_dork_http(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Secondary HTTP search fallback using Bing public search index."""
        import base64
        from bs4 import BeautifulSoup
        results = []
        try:
            url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
            try:
                from curl_cffi import requests as cffi_requests
                r = cffi_requests.get(url, impersonate="chrome124", timeout=8)
            except Exception:
                import requests
                headers = {
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.find_all("li", class_="b_algo")
                for c in cards:
                    try:
                        text_val = c.get_text(separator="\n").strip()
                        a_tags = c.find_all("a", href=True)
                        href = ""
                        for a in a_tags:
                            h = a["href"]
                            if "bing.com/ck/a?" in h and "&u=" in h:
                                try:
                                    u_match = re.search(r'[?&]u=a1([^&]+)', h)
                                    if u_match:
                                        raw_b64 = u_match.group(1)
                                        pad = len(raw_b64) % 4
                                        if pad:
                                            raw_b64 += "=" * (4 - pad)
                                        decoded = base64.urlsafe_b64decode(raw_b64).decode("utf-8", errors="ignore")
                                        if "http" in decoded:
                                            h = decoded
                                except Exception:
                                    pass
                            if "linkedin.com/in/" in h:
                                href = h
                                break
                        if text_val and href and "linkedin.com/in/" in href:
                            results.append({"text": text_val, "link": href})
                            if len(results) >= max_results:
                                break
                    except Exception:
                        pass
        except Exception as e:
            logger.debug("[SEARCH_XRAY] HTTP dork fallback note: %s", e)
        return results

    def harvest_company(
        self,
        company_name: str,
        domain: str,
        db: Session,
        max_profiles: int = 5,
        owner_user_id: int = 1,
        geo_tracker: Optional['GeoQuotaTracker'] = None,
        num_dorks: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Runs X-Ray dorks for a specific company, extracts profiles,
        runs live Port 25 SMTP checks, applies geographic enforcement,
        and stages verified records.
        """
        logger.info("[SEARCH_XRAY] Starting X-Ray harvest for '%s' (%s)", company_name, domain)
        clean_dom = domain.lower().replace("www.", "").strip()

        # Run 1-3 dork variations per company (default 1 for fast cycle cadence).
        # Each variation is cached for 2h so re-runs don't incur browser cost.
        dork_queries = []
        dork_count = max(1, min(num_dorks, 3))
        for i in range(dork_count):
            title_idx = abs(hash(company_name + str(int(time.time() // 120)) + str(i))) % len(DORK_TITLES)
            geo_idx = abs(hash(company_name + str(int(time.time() // 300)) + str(i))) % len(GEO_DORK_QUALIFIERS)
            target_role = DORK_TITLES[title_idx]
            geo_qualifier = GEO_DORK_QUALIFIERS[geo_idx]
            dork_queries.append(f'site:linkedin.com/in/ "{company_name}" "{target_role}" {geo_qualifier}')

        raw_cards = []
        seen_links: set = set()
        for dork_query in dork_queries:
            cards = self.execute_dork(dork_query, max_results=max_profiles * 2)
            for c in cards:
                link = c.get("link", "")
                if link and link not in seen_links:
                    seen_links.add(link)
                    raw_cards.append(c)
            if len(raw_cards) >= max_profiles * 2:
                break

        discovered_candidates = []
        seen_names = set()

        for card in raw_cards:
            parsed = self.parse_snippet_profile(card["text"], card["link"], company_name)
            if not parsed:
                continue

            name = parsed["name"]
            if name.lower() in seen_names:
                continue

            # Candidate name parsing (skip partial single-letter initials e.g. "William L.")
            tokens = name.split()
            first, last = tokens[0], tokens[-1]
            clean_last = re.sub(r"[^a-zA-Z]", "", last)
            if len(clean_last) <= 1:
                continue

            seen_names.add(name.lower())

            # Determine genuine employer and domain
            cand_company = parsed.get("company") or company_name
            effective_domain = None

            # If snippet company differs from target_company, resolve its genuine domain
            if parsed.get("extracted_company") and parsed["extracted_company"].lower() != company_name.lower():
                effective_domain = email_intelligence.resolve_company_domain(cand_company, db=db)
            else:
                effective_domain = clean_dom

            verified_email = None
            smtp_status = "UNVERIFIED"
            is_deliverable = False
            used_pattern = None
            confidence = 50
            mx_provider = "Unknown"

            if effective_domain:
                # 1. DNS MX Check
                mx_info = email_intelligence.verify_mx(effective_domain)
                mx_provider = mx_info.get("provider", "Unknown")

                if not mx_info["has_mx"]:
                    smtp_status = "MX_UNREACHABLE"
                    confidence = 10
                else:
                    # 2. Known empirical pattern lookup (DB first, then seeded ground truth)
                    known_pattern = None
                    if db:
                        try:
                            from ..models.models import CompanyEmailPattern
                            db_pattern = db.query(CompanyEmailPattern).filter(
                                CompanyEmailPattern.domain == effective_domain,
                                CompanyEmailPattern.active == True
                            ).order_by(
                                CompanyEmailPattern.verified_example_count.desc(),
                                CompanyEmailPattern.confidence_score.desc()
                            ).first()
                            if db_pattern and (db_pattern.verified_example_count or 0) >= 1:
                                known_pattern = db_pattern.pattern
                        except Exception as e:
                            logger.debug("Error querying company email pattern: %s", e)

                    if not known_pattern and effective_domain in SEEDED_COMPANY_PATTERNS:
                        known_pattern = SEEDED_COMPANY_PATTERNS[effective_domain]["pattern"]

                    permutations = email_intelligence.generate_permutations(
                        first=first,
                        last=clean_last,
                        domain=effective_domain,
                        known_pattern=known_pattern
                    )

                    # 3. Live Port 25 SMTP Probing (Top 2 variations)
                    for p in permutations[:2]:
                        candidate_email = p["email"]
                        try:
                            probe = smtp_prober.probe_mailbox(candidate_email)
                            if probe.smtp_code == 250:
                                verified_email = candidate_email
                                smtp_status = "SMTP_VERIFIED"
                                is_deliverable = True
                                used_pattern = p.get("pattern")
                                confidence = 95
                                self.stats["emails_smtp_verified"] += 1
                                break
                            elif probe.smtp_code == 550:
                                smtp_status = "SMTP_BOUNCED"
                                continue
                            elif getattr(probe, "is_catch_all", getattr(probe, "is_catchall", False)):
                                verified_email = candidate_email
                                smtp_status = "CATCH_ALL"
                                is_deliverable = True
                                used_pattern = p.get("pattern")
                                confidence = 80
                                break
                        except Exception as err:
                            logger.debug("SMTP probe error on %s: %s", candidate_email, err)

                    # 4. Pattern Intelligence Fallback (when Port 25 SMTP is blocked/inconclusive)
                    if not verified_email and permutations:
                        best_candidate = permutations[0]
                        verified_email = best_candidate["email"]
                        used_pattern = best_candidate.get("pattern")
                        if known_pattern:
                            # Deliverability verified via learned empirical company pattern
                            smtp_status = "PATTERN_MATCHED"
                            is_deliverable = True
                            confidence = 85
                        else:
                            # Port 25 blocked & pattern unverified: strictly an inferred statistical guess
                            smtp_status = "INFERRED_UNVERIFIED"
                            is_deliverable = False
                            confidence = 45
            else:
                smtp_status = "DOMAIN_UNRESOLVED"
                confidence = 0

            smtp_meta = {
                "smtp_status": smtp_status,
                "is_deliverable": is_deliverable,
                "provider": mx_provider,
                "pattern": used_pattern,
                "confidence": confidence,
            }

            parsed["email"] = verified_email
            parsed["email_status"] = smtp_status
            parsed["domain"] = effective_domain
            parsed["smtp_verification"] = smtp_meta
            discovered_candidates.append(parsed)

            self.stats["profiles_discovered"] += 1
            if len(discovered_candidates) >= max_profiles:
                break

        # Stage discovered profiles into discovery_staging (with geographic enforcement)
        staged_records = []
        geo_rejected = 0
        batch_id = f"xray_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        for cand in discovered_candidates:
            disc_id = f"xray_{uuid.uuid4().hex[:12]}"
            
            # ── Geographic Enforcement Gate ──
            geo_result = geo_classifier.classify(
                raw_location=cand.get("location"),
                raw_name=cand.get("name"),
                raw_email=cand.get("email"),
                raw_phone=None,
                raw_linkedin=cand.get("profile_url"),
                raw_company=cand.get("company"),
            )
            
            # Check geo filter
            if not geo_result.passes_filter:
                geo_rejected += 1
                logger.info(
                    "[SEARCH_XRAY] GEO_REJECTED: '%s' at '%s' — region=%s, confidence=%.2f, reason=%s",
                    cand["name"], cand.get("location", "unknown"),
                    geo_result.region, geo_result.confidence, geo_result.rejection_reason,
                )
                self.stats["geo_rejected"] = self.stats.get("geo_rejected", 0) + 1
                continue
            
            # Check quota if tracker provided
            if geo_tracker and not geo_tracker.should_accept(geo_result.region):
                geo_rejected += 1
                logger.info(
                    "[SEARCH_XRAY] GEO_QUOTA_EXCEEDED: '%s' — region=%s, quota=%s",
                    cand["name"], geo_result.region, geo_tracker.get_stats(),
                )
                self.stats["geo_quota_rejected"] = self.stats.get("geo_quota_rejected", 0) + 1
                continue

            # Build dedup filter
            dedup_conditions = []
            if cand.get("email"):
                dedup_conditions.append(DiscoveryStaging.raw_email == cand["email"])
            dedup_conditions.append(
                (DiscoveryStaging.raw_name == cand["name"]) & (DiscoveryStaging.raw_company == cand["company"])
            )
            existing = db.query(DiscoveryStaging).filter(or_(*dedup_conditions)).first()

            if existing:
                continue

            # Build metadata with geo classification & structured deliverability verification
            metadata = {
                "source": "search_xray",
                "source_domain": cand.get("domain") or clean_dom,
                "smtp_status": cand["email_status"],
                "domain": cand.get("domain") or clean_dom,
                "geo_signals": geo_result.signals,
                "smtp_verification": cand.get("smtp_verification"),
            }

            staged = DiscoveryStaging(
                batch_id=batch_id,
                discovery_id=disc_id,
                device_id="xray_worker_01",
                owner_user_id=owner_user_id,
                raw_name=cand["name"],
                raw_title=cand["title"],
                raw_company=cand["company"],
                raw_email=cand.get("email"),
                raw_linkedin=cand.get("profile_url"),
                raw_location=cand.get("location"),
                source_url=cand.get("profile_url"),
                source_page_title=f"{cand['name']} - {cand['title']}",
                extraction_source="search_xray",
                dom_confidence=95,
                processing_status="pending",
                quality_score=85 if cand.get("smtp_verification", {}).get("is_deliverable") else 60,
                geo_region=geo_result.region,
                geo_confidence=geo_result.confidence,
                metadata_json=json.dumps(metadata),
            )
            db.add(staged)
            staged_records.append(cand)
            self.stats["profiles_staged"] += 1
            
            # Record acceptance for quota tracking
            if geo_tracker:
                geo_tracker.record_accepted(geo_result.region)

        db.commit()
        logger.info(
            "[SEARCH_XRAY] Harvest complete: %d discovered, %d staged, %d geo-rejected",
            len(discovered_candidates), len(staged_records), geo_rejected,
        )
        return staged_records


search_xray_harvester = SearchXRayHarvester()
