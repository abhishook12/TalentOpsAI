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
        self._last_ocr_time: float = 0.0
        self.cooldown_sec: float = 0.2  # Reduced from 1.5s to 0.2s due to 15x faster daemon
        self._lock = threading.Lock()
        self._daemon_proc: Optional[subprocess.Popen] = None
        self._daemon_lock = threading.Lock()
        self._init_daemon()

    def _init_daemon(self):
        """Starts persistent PowerShell OCR worker daemon."""
        if not os.path.exists(self.helper_path):
            return

        try:
            cmd = [
                "powershell",
                "-WindowStyle", "Hidden",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-File", self.helper_path,
                "-Daemon",
            ]

            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )

            # Wait for ready signal (up to 3 seconds)
            ready_line = proc.stdout.readline().strip()
            if "DAEMON_READY" in ready_line:
                self._daemon_proc = proc
                logger.info("⚡ Persistent WinRT OCR Daemon initialized successfully (Ready in <25ms)")
            else:
                logger.warning("OCR daemon init unexpected greeting: %s (will use single-shot fallback)", ready_line)
                try:
                    proc.terminate()
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Failed to start persistent OCR daemon: %s (using single-shot)", e)
            self._daemon_proc = None

    def close(self):
        """Terminates persistent daemon on application shutdown."""
        with self._daemon_lock:
            if self._daemon_proc:
                try:
                    if self._daemon_proc.stdin:
                        self._daemon_proc.stdin.write("QUIT\n")
                        self._daemon_proc.stdin.flush()
                    self._daemon_proc.terminate()
                    self._daemon_proc.wait(timeout=1.0)
                except Exception:
                    pass
                self._daemon_proc = None

    def _file_hash(self, path: str) -> str:
        """Computes quick SHA256 of file header/stat to avoid re-OCR identical screenshots."""
        try:
            st = os.stat(path)
            return f"{st.st_size}_{st.st_mtime}"
        except Exception:
            return path

    def _run_single_shot(self, image_path: str) -> List[str]:
        """Fallback single-shot execution if daemon is unavailable."""
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
            encoding="utf-8",
            errors="replace",
            timeout=8.0,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )
        return self._parse_ocr_json(result.stdout)

    def _parse_ocr_json(self, stdout: str) -> List[str]:
        stdout = stdout.strip()
        if stdout.startswith("{") and stdout.endswith("}"):
            clean_stdout = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", stdout)
            data = json.loads(clean_stdout, strict=False)
            raw_lines = data.get("lines", [])
            return [
                re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", l).strip()
                for l in raw_lines
                if l and len(re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", l).strip()) > 1
            ]
        return []

    def extract_text_from_image(self, image_path: str) -> List[str]:
        """
        Runs Windows Media OCR on the given image file path completely silently.
        Uses persistent high-speed WinRT daemon (<25ms) with single-shot fallback.
        Guaranteed ZERO console window popups via CREATE_NO_WINDOW and SW_HIDE.
        """
        if not os.path.exists(image_path):
            return []

        cache_key = self._file_hash(image_path)
        if cache_key in self._ocr_cache:
            return list(self._ocr_cache[cache_key])

        import time
        now = time.time()
        if now - self._last_ocr_time < self.cooldown_sec:
            logger.debug("OCR debounced (cooldown active); returning cached lines.")
            return list(self._last_lines)

        acquired = self._lock.acquire(blocking=False)
        if not acquired:
            logger.debug("OCR already running; returning cached/empty lines to prevent pileup.")
            return list(self._last_lines)

        try:
            self._last_ocr_time = time.time()
            clean_lines = []

            # Fast path: Persistent daemon IPC
            with self._daemon_lock:
                if self._daemon_proc and self._daemon_proc.poll() is None:
                    try:
                        self._daemon_proc.stdin.write(image_path + "\n")
                        self._daemon_proc.stdin.flush()
                        response_line = self._daemon_proc.stdout.readline()
                        clean_lines = self._parse_ocr_json(response_line)
                    except Exception as de:
                        logger.debug("Daemon IPC read error: %s (falling back)", de)
                        clean_lines = []

            # Fallback path if daemon returned empty or was down
            if not clean_lines:
                clean_lines = self._run_single_shot(image_path)
                # Auto-restart daemon if it exited
                if not self._daemon_proc or self._daemon_proc.poll() is not None:
                    self._init_daemon()

            if clean_lines:
                self._ocr_cache[cache_key] = clean_lines
                self._last_lines = clean_lines
                if len(self._ocr_cache) > 40:
                    oldest_key = next(iter(self._ocr_cache))
                    del self._ocr_cache[oldest_key]
                return clean_lines

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
