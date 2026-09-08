import os
import sys
import re
import json
import hashlib
import threading
import subprocess
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict

logger = logging.getLogger("scout.ocr_engine")


@dataclass
class TextDiffResult:
    added_lines: List[str]
    removed_lines: List[str]
    overlap_count: int
    overlap_ratio: float
    is_scroll: bool
    has_meaningful_new_text: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OcrEngine:
    def __init__(self, helper_path: Optional[str] = None):
        self.helper_path = helper_path or os.path.join(os.path.dirname(__file__), "ocr_helper.ps1")
        self._ocr_cache: Dict[str, List[str]] = {}
        self._last_lines: List[str] = []
        self._lock = threading.Lock()

    def _file_hash(self, path: str) -> str:
        """Computes quick SHA256 of file header/stat to avoid re-OCR identical screenshots."""
        try:
            st = os.stat(path)
            return f"{st.st_size}_{st.st_mtime}"
        except Exception:
            return path

    def extract_text_from_image(self, image_path: str) -> List[str]:
        """
        Runs Windows Media OCR on the given image file path completely silently.
        Guaranteed ZERO console window popups via CREATE_NO_WINDOW and SW_HIDE.
        Prevents concurrent subprocess pile-ups via execution lock.
        """
        if not os.path.exists(image_path):
            return []

        cache_key = self._file_hash(image_path)
        if cache_key in self._ocr_cache:
            return list(self._ocr_cache[cache_key])

        # Prevent concurrent PowerShell executions piling up
        acquired = self._lock.acquire(blocking=False)
        if not acquired:
            logger.debug("OCR already running; returning cached/empty lines to prevent pileup.")
            return list(self._last_lines)

        try:
            cmd = [
                "powershell",
                "-WindowStyle", "Hidden",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-File", self.helper_path,
                "-ImagePath", image_path,
            ]

            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=8.0,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
            stdout = result.stdout.strip()
            if stdout.startswith("{") and stdout.endswith("}"):
                clean_stdout = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", stdout)
                data = json.loads(clean_stdout, strict=False)
                raw_lines = data.get("lines", [])
                clean_lines = [
                    re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", l).strip()
                    for l in raw_lines
                    if l and len(re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", l).strip()) > 1
                ]
                self._ocr_cache[cache_key] = clean_lines
                self._last_lines = clean_lines
                # Keep cache bounded to 30 items
                if len(self._ocr_cache) > 30:
                    oldest_key = next(iter(self._ocr_cache))
                    del self._ocr_cache[oldest_key]
                return clean_lines
            elif "ERROR:" in stdout:
                logger.debug("Windows OCR reported: %s", stdout)
        except subprocess.TimeoutExpired:
            logger.debug("Windows OCR timed out on %s", image_path)
        except Exception as e:
            logger.debug("Windows OCR exception: %s", e)
        finally:
            self._lock.release()

        return []

    def compute_text_diff(self, previous_lines: List[str], current_lines: List[str]) -> TextDiffResult:
        """
        Compares two sets of OCR text lines to detect new information, overlap,
        and scroll continuation events.
        """
        if not previous_lines:
            return TextDiffResult(
                added_lines=list(current_lines),
                removed_lines=[],
                overlap_count=0,
                overlap_ratio=0.0,
                is_scroll=False,
                has_meaningful_new_text=bool(current_lines),
            )

        prev_set: Set[str] = set(previous_lines)
        curr_set: Set[str] = set(current_lines)

        added = [line for line in current_lines if line not in prev_set]
        removed = [line for line in previous_lines if line not in curr_set]
        overlap = [line for line in current_lines if line in prev_set]

        total_unique = len(prev_set | curr_set)
        overlap_ratio = len(overlap) / max(total_unique, 1)

        # A scroll is characterized by moderate-to-high overlap (e.g. >= 30%) with newly added lines
        is_scroll = bool(overlap_ratio >= 0.25 and len(added) > 0 and len(removed) > 0)
        has_meaningful_new_text = len(added) > 0

        return TextDiffResult(
            added_lines=added,
            removed_lines=removed,
            overlap_count=len(overlap),
            overlap_ratio=overlap_ratio,
            is_scroll=is_scroll,
            has_meaningful_new_text=has_meaningful_new_text,
        )
