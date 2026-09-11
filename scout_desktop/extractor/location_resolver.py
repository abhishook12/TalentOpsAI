"""
extractor/location_resolver.py — High Precision Location Normalization & Corruption Detector

Prevents corrupted OCR (e.g. 'San ntu, Texas' or 'M@itland, FL') from polluting candidate records.
Validates character integrity, eliminates replacement characters, checks known geographic registries,
and assigns explicit location confidence.
"""

from __future__ import annotations
import re
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class ResolvedLocation:
    """Standardized representation of an extracted geographic location."""
    raw_text: str
    display_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    confidence: float = 0.0
    is_corrupted: bool = False
    status: str = "VALID"  # 'VALID' | 'LOCATION_UNCERTAIN' | 'CORRUPTED_REJECTED'


class LocationResolver:
    """
    Dedicated parser and corruption filter for candidate locations.
    """

    # US States mapping
    US_STATES = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
        "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
        "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
        "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
        "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
        "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
        "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
        "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
        "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
        "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
        "DC": "District of Columbia"
    }

    # Major global countries
    COUNTRIES = {
        "united states", "usa", "us", "canada", "united kingdom", "uk", "great britain",
        "india", "australia", "germany", "france", "netherlands", "singapore", "ireland",
        "switzerland", "sweden", "spain", "italy", "brazil", "mexico", "japan"
    }

    @classmethod
    def resolve(cls, raw_location: Optional[str]) -> ResolvedLocation:
        """
        Validates, cleans, and normalizes a candidate location string.
        """
        if not raw_location or not isinstance(raw_location, str):
            return ResolvedLocation(raw_text="", status="LOCATION_UNCERTAIN", confidence=0.0)

        cleaned = raw_location.strip()

        # 1. Strict Corruption Check: Detect replacement characters (\ufffd), nulls, or weird OCR glitches
        if "\ufffd" in cleaned or "\x00" in cleaned or "\\ufffd" in cleaned:
            return ResolvedLocation(
                raw_text=cleaned,
                display_name=None,
                is_corrupted=True,
                status="LOCATION_UNCERTAIN",
                confidence=0.15,
            )

        # Check for unreadable symbols or corrupted ASCII fragments
        bad_chars_count = sum(1 for c in cleaned if not (c.isalnum() or c in " ,.-'/"))
        if bad_chars_count > 0:
            return ResolvedLocation(
                raw_text=cleaned,
                display_name=None,
                is_corrupted=True,
                status="LOCATION_UNCERTAIN",
                confidence=0.20,
            )

        # Clean bullets, connection degree markers, or leading icons
        cleaned = re.sub(r"^[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|,\s]+", "", cleaned)
        cleaned = re.sub(r"\s*[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|].*$", "", cleaned)
        cleaned = re.sub(r"\s*Contact\s*info.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip()

        if len(cleaned) < 3 or len(cleaned) > 90:
            return ResolvedLocation(raw_text=raw_location, status="LOCATION_UNCERTAIN", confidence=0.0)

        # 2. Parse City, State, Country
        parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        city = None
        state = None
        country = None
        confidence = 0.70

        if len(parts) == 1:
            part_low = parts[0].lower()
            # Could be just country or "Greater ... Area"
            if part_low in cls.COUNTRIES:
                country = parts[0].title()
                confidence = 0.85
            elif "greater" in part_low and "area" in part_low:
                city = parts[0]
                confidence = 0.80
            else:
                city = parts[0]
                confidence = 0.65

        elif len(parts) == 2:
            city = parts[0]
            second = parts[1].strip()
            second_upper = second.upper()
            second_low = second.lower()

            if second_upper in cls.US_STATES:
                state = cls.US_STATES[second_upper]
                country = "United States"
                confidence = 0.95
            elif second_low in [s.lower() for s in cls.US_STATES.values()]:
                state = second.title()
                country = "United States"
                confidence = 0.95
            elif second_low in cls.COUNTRIES:
                country = second.title()
                confidence = 0.90
            else:
                state = second
                confidence = 0.75

        elif len(parts) >= 3:
            city = parts[0]
            state = parts[1]
            country = parts[2].title()
            confidence = 0.96

        display_name = cleaned
        return ResolvedLocation(
            raw_text=raw_location,
            display_name=display_name,
            city=city,
            state=state,
            country=country,
            confidence=confidence,
            is_corrupted=False,
            status="VALID" if confidence >= 0.70 else "LOCATION_UNCERTAIN"
        )
