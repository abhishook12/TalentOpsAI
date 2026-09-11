"""
extractor/stability_detector.py — Screen Stability & Frame Settling Engine

Ensures Scout only extracts structured data when the screen is settled and static.
Prevents extracting during:
- Continuous mouse wheel scrolling
- Browser page loading / dynamic DOM hydration
- Quick tab cycling

Implements:
SCREEN CHANGING -> WAIT -> SCREEN STABLE -> EXTRACT
"""

from __future__ import annotations
import time
import hashlib
import logging
from typing import Optional, Tuple
from PIL import Image
import numpy as np

logger = logging.getLogger("scout.stability_detector")


class ScreenStabilityDetector:
    """
    Monitors visual deltas across successive frames to detect when a screen has
    settled and is safe for high-precision deep extraction.
    """

    def __init__(self, settling_window_sec: float = 0.6, max_stable_cache_sec: float = 60.0):
        self.settling_window_sec = settling_window_sec
        self.max_stable_cache_sec = max_stable_cache_sec

        self._last_change_time = 0.0
        self._last_delta = 1.0
        self._stable_since = 0.0
        self._is_settled = False
        self._last_processed_hash: Optional[str] = None
        self._last_processed_time = 0.0

    def compute_frame_hash(self, img: Image.Image, win_title: str = "") -> str:
        """
        Computes a resilient 64x64 perceptual content hash.
        Combines spatial luminance grid with sanitized window title.
        """
        try:
            small = img.resize((32, 32), Image.Resampling.BILINEAR).convert("L")
            pixel_bytes = small.tobytes()
            h = hashlib.sha256()
            h.update(pixel_bytes)
            if win_title:
                h.update(win_title.strip().encode("utf-8", errors="ignore"))
            return h.hexdigest()[:24]
        except Exception:
            return f"FALLBACK-{int(time.time())}"

    def update_frame(
        self,
        img: Image.Image,
        delta: float,
        window_title: str = "",
        force_settle: bool = False,
    ) -> Tuple[bool, str, str]:
        """
        Evaluates current visual frame stability.

        Returns:
            (is_ready_for_extraction: bool, state: str, frame_hash: str)
            state is one of: 'STABLE_READY', 'SCREEN_CHANGING', 'SETTLING_WAIT', 'DUPLICATE_VIEW'
        """
        now = time.time()
        frame_hash = self.compute_frame_hash(img, window_title)

        if force_settle:
            self._is_settled = True
            self._last_processed_hash = frame_hash
            self._last_processed_time = now
            return True, "STABLE_READY", frame_hash

        # Meaningful change threshold (e.g. > 4.5% visual difference)
        is_changing = delta > 0.045

        if is_changing:
            self._last_change_time = now
            self._stable_since = 0.0
            self._is_settled = False
            return False, "SCREEN_CHANGING", frame_hash

        # Screen is not changing right now. Has it settled long enough?
        if self._stable_since == 0.0:
            self._stable_since = now

        settle_duration = now - self._stable_since

        if settle_duration < self.settling_window_sec:
            # Still within debounce settling window
            return False, "SETTLING_WAIT", frame_hash

        # Screen is confirmed stable!
        # Check if we already processed this EXACT stable screen recently
        if self._last_processed_hash == frame_hash and (now - self._last_processed_time) < self.max_stable_cache_sec:
            return False, "DUPLICATE_VIEW", frame_hash

        # Mark as processed and trigger extraction
        self._is_settled = True
        self._last_processed_hash = frame_hash
        self._last_processed_time = now
        logger.debug("Screen stability confirmed: settled for %.2fs, hash=%s", settle_duration, frame_hash[:8])
        return True, "STABLE_READY", frame_hash

    def reset(self):
        """Resets stability state (e.g. on window switch)."""
        self._last_change_time = time.time()
        self._stable_since = 0.0
        self._is_settled = False
        self._last_processed_hash = None
        self._last_processed_time = 0.0
