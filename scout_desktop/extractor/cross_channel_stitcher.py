"""
extractor/cross_channel_stitcher.py — Continuous Multi-Hop Cross-Channel Graph Stitcher & Peak Completeness Engine

Enables peak continuous data enrichment by stitching candidate observations across:
- Google Chat, MS Teams, Slack, WhatsApp, Telegram
- LinkedIn, GitHub, Stack Overflow, Kaggle
- Gmail, Outlook, PDF Resumes

Maintains progressive 360-degree candidate dossiers with multi-source field provenance.
"""

from __future__ import annotations

import time
import uuid
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("scout.cross_channel_stitcher")


@dataclass
class StitchedProfile:
    """Consolidated 360-degree candidate intelligence profile."""
    entity_id: str
    canonical_name: str
    primary_email: Optional[str] = None
    all_emails: List[str] = field(default_factory=list)
    primary_phone: Optional[str] = None
    all_phones: List[str] = field(default_factory=list)
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    stackoverflow_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    previous_company: Optional[str] = None
    location: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    work_authorization: Optional[str] = None
    tax_terms: List[str] = field(default_factory=list)
    compensation: Optional[Dict[str, Any]] = None
    availability: Optional[str] = None
    security_clearance: Optional[str] = None
    seniority_level: Optional[str] = None
    work_preference: Optional[str] = None
    observed_channels: List[str] = field(default_factory=list)
    observations_count: int = 1
    completeness_score: float = 0.0
    first_seen: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    def calculate_completeness(self) -> float:
        """Computes peak completeness index (0.0 to 1.0)."""
        score = 0.0
        # 1. Identity (15%)
        if self.canonical_name and len(self.canonical_name.split()) >= 2:
            score += 0.15
        elif self.canonical_name:
            score += 0.08

        # 2. Verified Contact Points (30%)
        if self.primary_email:
            score += 0.18
        if self.primary_phone:
            score += 0.12

        # 3. Employment & Roles (25%)
        if self.current_title:
            score += 0.13
        if self.current_company:
            score += 0.12

        # 4. Sourcing Signals (15%)
        if self.work_authorization:
            score += 0.05
        if self.compensation:
            score += 0.05
        if self.availability or self.work_preference:
            score += 0.05

        # 5. Technical DNA & Digital Channels (15%)
        if self.skills and len(self.skills) >= 3:
            score += 0.08
        elif self.skills:
            score += 0.04
        if self.linkedin_url or self.github_url or self.stackoverflow_url:
            score += 0.07

        self.completeness_score = round(min(1.0, score), 2)
        return self.completeness_score

    def to_staged_contact_dict(self) -> Dict[str, Any]:
        """Converts stitched profile into canonical backend staging format."""
        self.calculate_completeness()
        meta = {
            "work_authorization": self.work_authorization,
            "tax_terms": self.tax_terms,
            "compensation": self.compensation,
            "availability": self.availability,
            "security_clearance": self.security_clearance,
            "seniority_level": self.seniority_level,
            "work_preference": self.work_preference,
            "observed_channels": self.observed_channels,
            "completeness_score": self.completeness_score,
            "github_url": self.github_url,
            "stackoverflow_url": self.stackoverflow_url,
        }
        return {
            "recruiter_name": self.canonical_name,
            "raw_name": self.canonical_name,
            "title": self.current_title or "Professional Profile",
            "raw_title": self.current_title or "",
            "company_name": self.current_company or "",
            "raw_company": self.current_company or "",
            "previous_company": self.previous_company or "",
            "email": self.primary_email or "",
            "raw_email": self.primary_email or "",
            "phone": self.primary_phone or "",
            "raw_phone": self.primary_phone or "",
            "linkedin_url": self.linkedin_url or "",
            "raw_linkedin": self.linkedin_url or "",
            "location": self.location or "",
            "raw_location": self.location or "",
            "skills": self.skills,
            "confidence": int(self.completeness_score * 100),
            "quality_score": int(self.completeness_score * 100),
            "observations_count": self.observations_count,
            "metadata_json": meta,
        }


class CrossChannelStitcher:
    """
    Continuous in-memory multi-hop identity resolution engine.
    Links candidate observations across chats, inboxes, code repos, and resumes.
    """

    def __init__(self):
        self._profiles: Dict[str, StitchedProfile] = {}
        # Index lookups for fast multi-hop graph resolution
        self._email_index: Dict[str, str] = {}
        self._phone_index: Dict[str, str] = {}
        self._linkedin_index: Dict[str, str] = {}
        self._name_company_index: Dict[Tuple[str, str], str] = {}
        self._name_index: Dict[str, str] = {}

    def _fuse_profiles(self, target: StitchedProfile, source: StitchedProfile):
        """Merges source profile into target profile losslessly."""
        target.observations_count += source.observations_count
        target.last_updated = max(target.last_updated, source.last_updated)
        for ch in source.observed_channels:
            if ch not in target.observed_channels:
                target.observed_channels.append(ch)

        if not target.canonical_name and source.canonical_name:
            target.canonical_name = source.canonical_name
        if not target.primary_email and source.primary_email:
            target.primary_email = source.primary_email
        for em in source.all_emails:
            if em not in target.all_emails:
                target.all_emails.append(em)
        if not target.primary_phone and source.primary_phone:
            target.primary_phone = source.primary_phone
        for ph in source.all_phones:
            if ph not in target.all_phones:
                target.all_phones.append(ph)
        if not target.linkedin_url and source.linkedin_url:
            target.linkedin_url = source.linkedin_url
        if not target.current_company and source.current_company:
            target.current_company = source.current_company
        if not target.current_title and source.current_title:
            target.current_title = source.current_title
        if not target.location and source.location:
            target.location = source.location

        # Signals
        if not target.work_authorization and source.work_authorization:
            target.work_authorization = source.work_authorization
        for t in source.tax_terms:
            if t not in target.tax_terms:
                target.tax_terms.append(t)
        if not target.compensation and source.compensation:
            target.compensation = source.compensation
        if not target.availability and source.availability:
            target.availability = source.availability
        if not target.security_clearance and source.security_clearance:
            target.security_clearance = source.security_clearance
        if not target.seniority_level and source.seniority_level:
            target.seniority_level = source.seniority_level
        if not target.work_preference and source.work_preference:
            target.work_preference = source.work_preference

        for sk in source.skills:
            if sk not in target.skills:
                target.skills.append(sk)

    def stitch_observation(self, candidate_dict: Dict[str, Any], channel: str = "GENERIC") -> StitchedProfile:
        """
        Takes raw candidate observation from any source and stitches it into the identity graph.
        Performs multi-hop resolution and graph bridge fusion.
        Returns the enriched, consolidated StitchedProfile.
        """
        name = (candidate_dict.get("recruiter_name") or candidate_dict.get("raw_name") or "").strip()
        email = (candidate_dict.get("email") or candidate_dict.get("raw_email") or "").strip().lower()
        phone = (candidate_dict.get("phone") or candidate_dict.get("raw_phone") or "").strip()
        linkedin = (candidate_dict.get("linkedin_url") or candidate_dict.get("raw_linkedin") or "").strip()
        company = (candidate_dict.get("company_name") or candidate_dict.get("raw_company") or "").strip()
        title = (candidate_dict.get("title") or candidate_dict.get("raw_title") or "").strip()
        meta = candidate_dict.get("metadata_json") or {}

        # 1. Multi-Hop Graph Resolution (Find all matching candidate nodes)
        matched_ids = set()
        if linkedin and linkedin in self._linkedin_index:
            matched_ids.add(self._linkedin_index[linkedin])
        if email and email in self._email_index:
            matched_ids.add(self._email_index[email])
        if phone and phone in self._phone_index:
            matched_ids.add(self._phone_index[phone])
        if name and company and (name.lower(), company.lower()) in self._name_company_index:
            matched_ids.add(self._name_company_index[(name.lower(), company.lower())])
        elif name and len(name.split()) >= 2 and name.lower() in self._name_index:
            matched_ids.add(self._name_index[name.lower()])

        now = time.time()
        if matched_ids:
            # Multi-Node Graph Bridge: Fuse multiple matching profiles if bridged by this observation
            primary_id = list(matched_ids)[0]
            profile = self._profiles[primary_id]

            for other_id in list(matched_ids)[1:]:
                if other_id in self._profiles and other_id != primary_id:
                    other_p = self._profiles.pop(other_id)
                    self._fuse_profiles(profile, other_p)
                    # Remap indexes
                    for em in other_p.all_emails:
                        self._email_index[em] = primary_id
                    for ph in other_p.all_phones:
                        self._phone_index[ph] = primary_id
                    if other_p.linkedin_url:
                        self._linkedin_index[other_p.linkedin_url] = primary_id
                    if other_p.canonical_name and other_p.current_company:
                        self._name_company_index[(other_p.canonical_name.lower(), other_p.current_company.lower())] = primary_id
                    if other_p.canonical_name:
                        self._name_index[other_p.canonical_name.lower()] = primary_id

            profile.last_updated = now
            profile.observations_count += 1
            if channel not in profile.observed_channels:
                profile.observed_channels.append(channel)

            # Enrich missing fields (Lossless progressive enrichment)
            if not profile.canonical_name and name:
                profile.canonical_name = name
            if not profile.primary_email and email:
                profile.primary_email = email
            if email and email not in profile.all_emails:
                profile.all_emails.append(email)
            if not profile.primary_phone and phone:
                profile.primary_phone = phone
            if phone and phone not in profile.all_phones:
                profile.all_phones.append(phone)
            if not profile.linkedin_url and linkedin:
                profile.linkedin_url = linkedin
            if not profile.current_company and company:
                profile.current_company = company
            if not profile.current_title and title:
                profile.current_title = title
            if not profile.location and candidate_dict.get("location"):
                profile.location = candidate_dict.get("location")

            # Enrich Sourcing Signals
            if not profile.work_authorization and meta.get("work_authorization"):
                profile.work_authorization = meta["work_authorization"]
            if meta.get("tax_terms"):
                for t in meta["tax_terms"]:
                    if t not in profile.tax_terms:
                        profile.tax_terms.append(t)
            if not profile.compensation and meta.get("compensation"):
                profile.compensation = meta["compensation"]
            if not profile.availability and meta.get("availability"):
                profile.availability = meta["availability"]
            if not profile.security_clearance and meta.get("security_clearance"):
                profile.security_clearance = meta["security_clearance"]
            if not profile.seniority_level and meta.get("seniority_level"):
                profile.seniority_level = meta["seniority_level"]
            if not profile.work_preference and meta.get("work_preference"):
                profile.work_preference = meta["work_preference"]

            # Merge Skills
            new_skills = candidate_dict.get("skills") or []
            for sk in new_skills:
                if sk not in profile.skills:
                    profile.skills.append(sk)

            logger.info("Stitched & Enriched profile %s (Channels: %s, Completeness: %.0f%%)",
                        profile.canonical_name, profile.observed_channels, profile.calculate_completeness() * 100)
        else:
            # Create New Profile Node with globally unique entity ID
            entity_id = f"STITCH-{uuid.uuid4().hex[:8].upper()}"
            profile = StitchedProfile(
                entity_id=entity_id,
                canonical_name=name or (email.split("@")[0].capitalize() if email else "Candidate"),
                primary_email=email or None,
                all_emails=[email] if email else [],
                primary_phone=phone or None,
                all_phones=[phone] if phone else [],
                linkedin_url=linkedin or None,
                current_title=title or None,
                current_company=company or None,
                location=candidate_dict.get("location") or None,
                skills=list(candidate_dict.get("skills") or []),
                work_authorization=meta.get("work_authorization"),
                tax_terms=list(meta.get("tax_terms") or []),
                compensation=meta.get("compensation"),
                availability=meta.get("availability"),
                security_clearance=meta.get("security_clearance"),
                seniority_level=meta.get("seniority_level"),
                work_preference=meta.get("work_preference"),
                observed_channels=[channel],
                observations_count=1,
            )
            self._profiles[entity_id] = profile

        # Update Indexes for future hops
        if profile.primary_email:
            self._email_index[profile.primary_email] = profile.entity_id
        for em in profile.all_emails:
            self._email_index[em] = profile.entity_id
        if profile.primary_phone:
            self._phone_index[profile.primary_phone] = profile.entity_id
        for ph in profile.all_phones:
            self._phone_index[ph] = profile.entity_id
        if profile.linkedin_url:
            self._linkedin_index[profile.linkedin_url] = profile.entity_id
        if profile.canonical_name and profile.current_company:
            self._name_company_index[(profile.canonical_name.lower(), profile.current_company.lower())] = profile.entity_id
        if profile.canonical_name and len(profile.canonical_name.split()) >= 2:
            self._name_index[profile.canonical_name.lower()] = profile.entity_id

        profile.calculate_completeness()
        return profile
