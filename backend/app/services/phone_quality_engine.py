"""
phone_quality_engine.py — E.164 Standardization, Line Type & Phone Quality Engine.

Features:
1. Robust E.164 International Normalization (NANP +1, UK +44, India +91, Australia +61, etc.)
2. Country Code & Area Code Resolution
3. Line Type Classification (MOBILE, LANDLINE, VOIP, TOLL_FREE, INVALID)
4. Outbound Outreach Deliverability & Quality Scoring
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

# Known NANP Toll-Free Area Codes
TOLL_FREE_AREA_CODES = {"800", "888", "877", "866", "855", "844", "833"}

# Known NANP Personal/VoIP prefixes
NANP_VOIP_CODES = {"500", "521", "522", "533", "544", "566", "577", "588"}

# Country dialing codes
COUNTRY_CODES = {
    "1": "US/CA",
    "44": "GB",
    "91": "IN",
    "61": "AU",
    "49": "DE",
    "33": "FR",
    "81": "JP",
    "65": "SG",
    "353": "IE",
    "34": "ES",
    "39": "IT",
    "31": "NL",
    "41": "CH",
    "46": "SE",
    "55": "BR",
    "52": "MX",
    "48": "PL",
    "63": "PH",
    "971": "AE",
}


class PhoneQualityEngine:
    """
    Validates, standardizes, and scores telephone contact points.
    Prevents corrupt and undeliverable numbers from entering outreach campaigns.
    """

    @classmethod
    def clean_digits(cls, text: Optional[str]) -> str:
        if not text:
            return ""
        return re.sub(r"\D", "", str(text))

    @classmethod
    def validate_and_format(
        cls,
        raw_phone: Optional[str],
        default_country_code: str = "1",
    ) -> Dict[str, Any]:
        """
        Parses and standardizes any raw phone number string into an E.164 representation.
        Returns detailed forensic metadata including line type and confidence.
        """
        result: Dict[str, Any] = {
            "raw": raw_phone or "",
            "e164": None,
            "country_code": None,
            "national_number": None,
            "line_type": "INVALID",
            "is_valid": False,
            "is_mobile": False,
            "confidence": 0.0,
            "error": None,
        }

        if not raw_phone or not str(raw_phone).strip():
            result["error"] = "Empty phone string"
            return result

        raw = str(raw_phone).strip()

        # Handle extensions (e.g. 555-123-4567 ext 123)
        ext_match = re.search(r"(?:ext|x|extension)[.\s]*(\d+)", raw, re.IGNORECASE)
        extension = ext_match.group(1) if ext_match else None
        clean_raw = re.sub(r"(?:ext|x|extension)[.\s]*\d+", "", raw, flags=re.IGNORECASE).strip()

        digits = cls.clean_digits(clean_raw)

        if len(digits) < 7:
            result["error"] = f"Too few digits ({len(digits)})"
            return result

        if len(digits) > 15:
            result["error"] = f"Too many digits ({len(digits)}) - exceeds E.164 max"
            return result

        # Check for bogus repetitions (e.g. 0000000000, 1111111111, 1234567890)
        if len(set(digits)) <= 2:
            result["error"] = "Suspicious repeating digit sequence"
            return result

        has_plus = clean_raw.startswith("+")
        country_code = None
        national_number = None

        if has_plus:
            # Try matching international prefix
            matched_cc = None
            for cc in sorted(COUNTRY_CODES.keys(), key=lambda k: -len(k)):
                if digits.startswith(cc):
                    matched_cc = cc
                    break
            if matched_cc:
                country_code = matched_cc
                national_number = digits[len(matched_cc):]
            else:
                country_code = digits[:2]
                national_number = digits[2:]
        else:
            if len(digits) == 10:
                country_code = default_country_code
                national_number = digits
            elif len(digits) == 11 and digits.startswith("1"):
                country_code = "1"
                national_number = digits[1:]
            elif len(digits) == 12 and digits.startswith("91"):
                country_code = "91"
                national_number = digits[2:]
            elif len(digits) == 11 and digits.startswith("44"):
                country_code = "44"
                national_number = digits[2:]
            else:
                # Default to assuming NANP or default country
                country_code = default_country_code
                national_number = digits

        if not national_number or len(national_number) < 6:
            result["error"] = "Invalid national number length"
            return result

        # Check for invalid NANP area codes
        if country_code == "1":
            if len(national_number) != 10:
                result["error"] = f"NANP requires 10 national digits (got {len(national_number)})"
                return result

            area_code = national_number[:3]
            prefix = national_number[3:6]

            # NANP area code cannot begin with 0 or 1
            if area_code[0] in ("0", "1") or prefix[0] in ("0", "1"):
                result["error"] = f"Invalid NANP area code ({area_code}) or prefix ({prefix})"
                return result

            # Line type classification
            if area_code in TOLL_FREE_AREA_CODES:
                line_type = "TOLL_FREE"
                conf = 0.40
                is_mobile = False
            elif area_code in NANP_VOIP_CODES:
                line_type = "VOIP"
                conf = 0.65
                is_mobile = False
            else:
                # Standard NANP number - typically mobile or landline
                line_type = "MOBILE"
                conf = 0.95
                is_mobile = True
        else:
            # International numbers
            if country_code == "91":
                # Indian mobile numbers typically start with 6, 7, 8, 9 and are 10 digits
                if len(national_number) == 10 and national_number[0] in ("6", "7", "8", "9"):
                    line_type = "MOBILE"
                    is_mobile = True
                    conf = 0.95
                else:
                    line_type = "LANDLINE"
                    is_mobile = False
                    conf = 0.85
            elif country_code == "44":
                # UK mobile numbers start with 7
                if national_number.startswith("7"):
                    line_type = "MOBILE"
                    is_mobile = True
                    conf = 0.95
                else:
                    line_type = "LANDLINE"
                    is_mobile = False
                    conf = 0.85
            else:
                line_type = "MOBILE"
                is_mobile = True
                conf = 0.88

        e164 = f"+{country_code}{national_number}"

        result.update({
            "e164": e164,
            "country_code": f"+{country_code}",
            "national_number": national_number,
            "extension": extension,
            "line_type": line_type,
            "is_valid": True,
            "is_mobile": is_mobile,
            "confidence": conf,
            "error": None,
        })
        return result
