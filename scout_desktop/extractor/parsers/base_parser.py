"""
extractor/parsers/base_parser.py — Base Platform-Specific Parser Interface

All platform-specific parsers (LinkedIn, ZoomInfo, Apollo, GitHub, Indeed, Resume)
inherit from BasePlatformParser and implement layout fingerprinting, page context
classification, and targeted field extraction.
"""

from __future__ import annotations
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple


class BasePlatformParser(ABC):
    """Abstract base class for platform-specific layout parsing."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Name of the platform (e.g. 'LinkedIn', 'ZoomInfo', 'Apollo', etc.)."""
        pass

    @abstractmethod
    def can_handle(self, url: str, platform_hint: str, window_title: str) -> bool:
        """Returns True if this parser is designed for the given URL, platform, or title."""
        pass

    @abstractmethod
    def detect_page_type(self, ocr_text: str, url: str, window_title: str) -> str:
        """
        Classifies page layout into one of:
        - PROFILE_PAGE
        - SEARCH_RESULTS
        - JOB_POSTING
        - COMPANY_PAGE
        - MESSAGING_THREAD
        - DOCUMENT_RESUME
        - UNKNOWN
        """
        pass

    @abstractmethod
    def parse(self, ocr_text: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extracts structured candidate data from the OCR text and context.
        Returns a dict with canonical keys or None if non-candidate layout.
        """
        pass
