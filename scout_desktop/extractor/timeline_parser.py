"""
extractor/timeline_parser.py — Employment Timeline Intelligence Engine

Parses employment history observations into structured, chronologically
sorted records with:
- ISO date normalization ("Jan 2020 - Present" → 2020-01, None)
- Tenure calculation in months
- Employment gap detection (gaps > 3 months)
- Current role identification (must have 'Present' or most recent end date)
- Historical overwrite prevention (never replace current with past)
- Internal promotion detection (multiple roles at same company)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger('scout.timeline_parser')


@dataclass
class EmploymentRecord:
    company: str
    title: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    is_current: bool
    tenure_months: Optional[int]
    location: Optional[str]
    description: Optional[str]
    source_evidence: str
    confidence: float

    def to_dict(self) -> dict:
        return {
            "company": self.company,
            "title": self.title,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "is_current": self.is_current,
            "tenure_months": self.tenure_months,
            "location": self.location,
            "description": self.description,
            "source_evidence": self.source_evidence,
            "confidence": self.confidence,
        }


@dataclass
class GapPeriod:
    start_date: str
    end_date: str
    duration_months: int
    between_companies: tuple[str, str]

    def to_dict(self) -> dict:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "duration_months": self.duration_months,
            "between_companies": self.between_companies,
        }


@dataclass
class PromotionChain:
    company: str
    roles: list[dict]
    total_tenure_months: int

    def to_dict(self) -> dict:
        return {
            "company": self.company,
            "roles": self.roles,
            "total_tenure_months": self.total_tenure_months,
        }


class TimelineParser:
    MONTH_MAP = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'september': 9, 'sept': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }

    def _parse_single_date(self, text: str) -> Optional[str]:
        """
        Parses a single date string into YYYY-MM format.
        """
        text = text.lower().strip()
        if text in ('present', 'current', 'now', 'today'):
            return None
        
        # Try Month Year format
        month_year_match = re.match(r'([a-z]+)\s+(\d{4})', text)
        if month_year_match:
            month_str, year_str = month_year_match.groups()
            month = self.MONTH_MAP.get(month_str[:3], 1)
            for k, v in self.MONTH_MAP.items():
                if month_str == k:
                    month = v
                    break
            return f"{year_str}-{month:02d}"
        
        # Try just Year
        year_match = re.match(r'^(\d{4})$', text)
        if year_match:
            return f"{year_match.group(1)}-01"
        
        return None

    def parse_date_range(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parses a date range string into start and end ISO format strings.
        """
        if not text:
            return None, None
            
        # Try full month/year range
        full_match = re.search(r'([a-z]+\s*\d{4})\s*[-–—to]+\s*([a-z]+\s*\d{4}|present|current|now)', text, re.IGNORECASE)
        if full_match:
            start_str, end_str = full_match.groups()
            return self._parse_single_date(start_str), self._parse_single_date(end_str)
            
        # Try year range
        year_match = re.search(r'(\d{4})\s*[-–—to]+\s*(\d{4}|present|current|now)', text, re.IGNORECASE)
        if year_match:
            start_str, end_str = year_match.groups()
            return self._parse_single_date(start_str), self._parse_single_date(end_str)
            
        # Try single year
        single_year_match = re.search(r'^(\d{4})$', text.strip())
        if single_year_match:
            return self._parse_single_date(text.strip()), None

        return None, None

    def calculate_tenure_months(self, start: str, end: Optional[str]) -> Optional[int]:
        """
        Calculates the tenure in months between two ISO dates.
        """
        if not start:
            return None
            
        try:
            start_year, start_month = map(int, start.split('-'))
            if end:
                end_year, end_month = map(int, end.split('-'))
            else:
                today = date.today()
                end_year, end_month = today.year, today.month
                
            months = (end_year - start_year) * 12 + (end_month - start_month)
            return max(0, months)
        except (ValueError, TypeError, AttributeError):
            return None

    def build_timeline(self, observations: list[dict]) -> list[EmploymentRecord]:
        """
        Builds a chronologically sorted timeline of employment records from observations.
        """
        records = []
        for obs in observations:
            predicate = obs.get("predicate")
            if predicate not in ("WORKS_AT", "PREVIOUSLY_WORKED_AT"):
                continue
                
            company = obs.get("target_entity", "Unknown Company")
            attributes = obs.get("attributes", {})
            title = attributes.get("title")
            date_range = attributes.get("date_range", "")
            location = attributes.get("location")
            description = attributes.get("description")
            source_evidence = obs.get("source_evidence", "")
            confidence = obs.get("confidence", 0.5)
            
            start_date, end_date = self.parse_date_range(date_range)
            is_current = (predicate == "WORKS_AT") or (end_date is None)
            tenure = self.calculate_tenure_months(start_date, end_date)
            
            record = EmploymentRecord(
                company=company,
                title=title,
                start_date=start_date,
                end_date=end_date,
                is_current=is_current,
                tenure_months=tenure,
                location=location,
                description=description,
                source_evidence=source_evidence,
                confidence=confidence
            )
            records.append(record)
            
        # Sort chronologically, most recent first (end_date None first, then by end_date desc, then start_date desc)
        def sort_key(r: EmploymentRecord):
            end = r.end_date or "9999-12"
            start = r.start_date or "0000-01"
            return (end, start)
            
        records.sort(key=sort_key, reverse=True)
        
        # Mark current roles
        for r in records:
            if not r.end_date:
                r.is_current = True
                
        return records

    def detect_gaps(self, timeline: list[EmploymentRecord]) -> list[GapPeriod]:
        """
        Identifies employment gaps > 3 months between consecutive records.
        """
        gaps = []
        # Timeline is sorted most recent first. 
        # So timeline[i+1] is older than timeline[i]
        
        for i in range(len(timeline) - 1):
            newer_role = timeline[i]
            older_role = timeline[i+1]
            
            if newer_role.start_date and older_role.end_date:
                try:
                    ny, nm = map(int, newer_role.start_date.split('-'))
                    oy, om = map(int, older_role.end_date.split('-'))
                    
                    gap_months = (ny - oy) * 12 + (nm - om)
                    if gap_months > 3:
                        gap = GapPeriod(
                            start_date=older_role.end_date,
                            end_date=newer_role.start_date,
                            duration_months=gap_months,
                            between_companies=(older_role.company, newer_role.company)
                        )
                        gaps.append(gap)
                except ValueError:
                    pass
                    
        return gaps

    def detect_promotions(self, timeline: list[EmploymentRecord]) -> list[PromotionChain]:
        """
        Finds consecutive roles at the same company and groups them into promotion chains.
        """
        if not timeline:
            return []
            
        chains = []
        current_chain = []
        
        for i in range(len(timeline)):
            role = timeline[i]
            
            if not current_chain:
                current_chain.append(role)
                continue
                
            # Check if same company (simple normalization)
            last_role = current_chain[-1]
            if role.company.lower().strip() == last_role.company.lower().strip():
                current_chain.append(role)
            else:
                if len(current_chain) > 1:
                    chains.append(self._create_promotion_chain(current_chain))
                current_chain = [role]
                
        if len(current_chain) > 1:
            chains.append(self._create_promotion_chain(current_chain))
            
        return chains
        
    def _create_promotion_chain(self, roles: list[EmploymentRecord]) -> PromotionChain:
        company = roles[0].company
        roles_data = []
        total_tenure = 0
        
        for r in roles:
            roles_data.append({
                "title": r.title,
                "start_date": r.start_date,
                "end_date": r.end_date
            })
            if r.tenure_months:
                total_tenure += r.tenure_months
                
        return PromotionChain(
            company=company,
            roles=roles_data,
            total_tenure_months=total_tenure
        )

    def get_current_role(self, timeline: list[EmploymentRecord]) -> Optional[EmploymentRecord]:
        """
        Returns the current role.
        """
        for role in timeline:
            if role.is_current:
                return role
        return timeline[0] if timeline else None

    def prevent_historical_overwrite(self, current_entity: dict, new_observation: dict) -> bool:
        """
        Prevents overwriting current company with historical employer.
        """
        predicate = new_observation.get("predicate")
        if predicate == "PREVIOUSLY_WORKED_AT":
            new_company = new_observation.get("target_entity", "").lower().strip()
            current_company = current_entity.get("company", "").lower().strip()
            if new_company == current_company:
                return True
        return False

    def get_total_career_months(self, timeline: list[EmploymentRecord]) -> int:
        """
        Calculates total career months.
        """
        return sum((r.tenure_months for r in timeline if r.tenure_months), 0)
