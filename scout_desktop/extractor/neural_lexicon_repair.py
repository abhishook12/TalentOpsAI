"""
extractor/neural_lexicon_repair.py — Lexicon-Guided OCR Error Correction

Provides post-OCR neural/lexicon healing for desktop apps (Microsoft Teams desktop,
legacy ATS software, PDFs) where UI Automation is unavailable and raw OCR produces
anti-aliased glyph substitutions (e.g., '0' for 'O', '1' for 'I', 'rn' for 'm').

Matches candidate titles and corporate entities against verified recruiting lexicons
to repair garbled characters before candidate gate classification.
"""

import re
import difflib
import logging
from typing import Tuple, Optional, List

logger = logging.getLogger("scout.lexicon_repair")

# Canonical verified recruiting titles lexicon
CANONICAL_RECRUITING_TITLES = [
    "Technical Recruiter",
    "Senior Technical Recruiter",
    "Lead Technical Recruiter",
    "Principal Technical Recruiter",
    "Corporate Recruiter",
    "Senior Corporate Recruiter",
    "Executive Recruiter",
    "Senior Executive Recruiter",
    "Talent Acquisition Specialist",
    "Senior Talent Acquisition Specialist",
    "Talent Acquisition Partner",
    "Senior Talent Acquisition Partner",
    "Talent Acquisition Manager",
    "Senior Talent Acquisition Manager",
    "Director of Talent Acquisition",
    "Senior Director of Talent Acquisition",
    "VP of Talent Acquisition",
    "Head of Talent Acquisition",
    "Head of People",
    "Head of People & Talent",
    "Chief People Officer",
    "VP of People",
    "Director of People Operations",
    "People Operations Manager",
    "People Operations Specialist",
    "HR Business Partner",
    "Senior HR Business Partner",
    "Director of Human Resources",
    "HR Director",
    "HR Manager",
    "Talent Sourcer",
    "Senior Talent Sourcer",
    "Lead Talent Sourcer",
    "Recruitment Consultant",
    "Senior Recruitment Consultant",
    "Managing Director of Executive Search",
    "Staffing Specialist",
    "Staffing Consultant",
    "Staffing Manager",
    "Account Manager - Staffing",
    "Account Executive - Staffing",
    "Delivery Manager",
    "Client Partner",
]

# Common OCR character confusion matrix
OCR_CONFUSIONS = [
    (r"\b0\b", "O"),
    (r"(?<=[a-zA-Z])0(?=[a-zA-Z])", "o"),
    (r"(?<=[a-zA-Z])1(?=[a-zA-Z])", "l"),
    (r"(?<=[a-zA-Z])5(?=[a-zA-Z])", "s"),
    (r"(?<=[a-zA-Z])@(?=[a-zA-Z])", "a"),
    (r"\b1(?=[a-z])", "I"),
    (r"(?<=[a-z])\|(?=[a-z])", "l"),
    (r"rn(?=[a-z])", "m"),  # e.g., 'rnanager' -> 'manager'
]


class NeuralLexiconRepair:
    """
    Automatic post-OCR lexicon correction engine.
    Heals corrupted job titles and corporate names.
    """

    def __init__(self):
        self._title_lookup = {t.lower(): t for t in CANONICAL_RECRUITING_TITLES}
        self._title_keys = list(self._title_lookup.keys())

    def pre_clean_ocr_glyphs(self, text: str) -> str:
        """Applies deterministic character confusion matrix substitutions."""
        if not text:
            return ""
        repaired = text
        for pattern, replacement in OCR_CONFUSIONS:
            repaired = re.sub(pattern, replacement, repaired)
        return repaired

    def repair_title(self, raw_title: Optional[str]) -> Tuple[str, float]:
        """
        Repairs an OCR-extracted job title using lexicon matching.

        Returns:
            (repaired_title: str, confidence_score: float)
        """
        if not raw_title or len(raw_title.strip()) < 3:
            return raw_title or "", 0.0

        cleaned = self.pre_clean_ocr_glyphs(raw_title.strip())
        c_lower = cleaned.lower()

        # 1. Exact match in canonical lexicon
        if c_lower in self._title_lookup:
            return self._title_lookup[c_lower], 1.0

        # 2. Fuzzy lexicon match
        matches = difflib.get_close_matches(c_lower, self._title_keys, n=1, cutoff=0.78)
        if matches:
            best_match_key = matches[0]
            similarity = difflib.SequenceMatcher(None, c_lower, best_match_key).ratio()
            canonical = self._title_lookup[best_match_key]
            logger.debug(
                "🎯 Lexicon Repaired Title: '%s' -> '%s' (similarity=%.2f)",
                raw_title, canonical, similarity
            )
            return canonical, round(similarity, 2)

        # 3. Clean fallback
        return cleaned, 0.70

    def repair_company_name(self, raw_company: Optional[str]) -> Tuple[str, float]:
        """
        Normalizes and repairs corporate entity names.
        """
        if not raw_company or len(raw_company.strip()) < 2:
            return raw_company or "", 0.0

        cleaned = self.pre_clean_ocr_glyphs(raw_company.strip())
        # Clean trailing symbols or punctuation
        cleaned = re.sub(r"[\s\.,\-_]+$", "", cleaned).strip()
        return cleaned, 0.85


lexicon_repair = NeuralLexiconRepair()
