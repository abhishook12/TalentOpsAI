"""
core/visual_sampler.py — Autonomous Visual Sampling Engine & Regional Change Detector

Implements:
1. Immediate capture upon window change / startup (zero wait).
2. 1-second active sampling loop during active visual changes.
3. 64x64 downscaled weighted regional difference engine (suppresses cursor, clocks, spinners).
4. Strict 10-Second Idle Rule: Enters IDLE WATCH MODE after 10s of static display.
5. Immediate Wakeup upon window switch, scroll, or visual activity.
"""

import time
import threading
import logging
from typing import Optional, Tuple, Callable
from PIL import Image, ImageGrab
import numpy as np

from .window_tracker import WindowInfo, ensure_interactive_desktop

logger = logging.getLogger("scout.visual_sampler")

DOWNSCALE_WIDTH = 64
DOWNSCALE_HEIGHT = 64
DEFAULT_DELTA_THRESHOLD = 0.035  # 3.5% meaningful regional change
PIXEL_TOLERANCE = 16            # Ignore micro compression noise
IDLE_TIMEOUT_SEC = 10.0         # 10 continuous seconds static -> IDLE WATCH
ACTIVE_INTERVAL_SEC = 1.0       # 1s active sampling
IDLE_POLL_INTERVAL_SEC = 1.5    # Low-power idle poll


def downscale_to_grayscale(img: Image.Image) -> np.ndarray:
    """Downscales image to 64x64 grayscale numpy array."""
    resized = img.resize((DOWNSCALE_WIDTH, DOWNSCALE_HEIGHT), Image.Resampling.BILINEAR)
    gray = resized.convert("L")
    return np.array(gray, dtype=np.int16)


def compute_weighted_regional_delta(pixels_a: np.ndarray, pixels_b: np.ndarray) -> float:
    """
    Algorithm 29: Region-Based Change Detection.
    Main content (middle 75% vertical & 80% horizontal) gets 80% weight.
    Borders/margins (headers, tabs, clocks, spinners) get 20% weight.
    """
    if pixels_a is None or pixels_b is None:
        return 1.0
    if pixels_a.shape != pixels_b.shape:
        return 1.0

    diff = np.abs(pixels_a - pixels_b)
    significant_mask = diff > PIXEL_TOLERANCE

    # Define main content bounding box (y: 8..56, x: 6..58)
    main_y_slice = slice(8, 56)
    main_x_slice = slice(6, 58)

    # Main content mask and total count
    main_sig = np.sum(significant_mask[main_y_slice, main_x_slice])
    total_main_pixels = 48 * 52  # 2496

    # Outer region mask and total count
    total_sig = np.sum(significant_mask)
    outer_sig = total_sig - main_sig
    total_outer_pixels = (DOWNSCALE_WIDTH * DOWNSCALE_HEIGHT) - total_main_pixels  # 1600

    main_ratio = main_sig / total_main_pixels
    outer_ratio = outer_sig / total_outer_pixels

    # Weighted score favoring main content
    weighted_score = (main_ratio * 0.8) + (outer_ratio * 0.2)
    return round(float(weighted_score), 4)


class VisualSampler:
    def __init__(
        self,
        on_meaningful_frame: Optional[Callable[[Image.Image, float, WindowInfo], None]] = None,
        on_state_change: Optional[Callable[[str], None]] = None,
        delta_threshold: float = DEFAULT_DELTA_THRESHOLD,
        idle_timeout_sec: float = IDLE_TIMEOUT_SEC,
    ):
        self.on_meaningful_frame = on_meaningful_frame
        self.on_state_change = on_state_change
        self.delta_threshold = delta_threshold
        self.idle_timeout_sec = idle_timeout_sec

        self._state = "ACTIVE_SAMPLING"  # ACTIVE_SAMPLING | IDLE_WATCH | PAUSED
        self._prev_pixels = None
        self._last_active_time = time.time()
        self._last_capture_time = 0.0
        self._current_window_info = None

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._worker_thread = None
        self._lock = threading.Lock()

        # Telemetry metrics
        self.stats = {
            "total_samples": 0,
            "meaningful_frames": 0,
            "idle_skips": 0,
            "last_delta": 0.0,
            "current_state": "STOPPED",
        }

    @property
    def state(self):
        return self._state

    def _set_state(self, new_state: str):
        if self._state != new_state:
            self._state = new_state
            self.stats["current_state"] = new_state
            logger.info("VisualSampler state transition -> %s", new_state)
            if self.on_state_change:
                try:
                    self.on_state_change(new_state)
                except Exception as e:
                    logger.debug("on_state_change callback error: %s", e)

    def grab_window_or_screen(self, window_info: Optional[WindowInfo] = None) -> Optional[Image.Image]:
        """
        Captures the active window bounding box, or full primary screen as fallback.
        """
        ensure_interactive_desktop()
        try:
            if window_info and window_info.is_valid:
                # Clamp coordinates to non-negative
                left = max(0, window_info.rect[0])
                top = max(0, window_info.rect[1])
                right = window_info.rect[2]
                bottom = window_info.rect[3]
                if right > left + 50 and bottom > top + 50:
                    return ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)

            # Fallback to full screen
            return ImageGrab.grab(all_screens=True)
        except Exception as e:
            logger.debug("Screenshot grab failed: %s", e)
            return None

    def set_current_window(self, window_info: Optional[WindowInfo]):
        """Updates the active window target for visual sampling."""
        with self._lock:
            self._current_window_info = window_info

    def trigger_immediate_capture(self, window_info: WindowInfo, reason: str = "window_switched"):
        """
        Forces an immediate capture (e.g. upon window change or wake event).
        Bypasses idle mode and resets baseline.
        """
        with self._lock:
            self._current_window_info = window_info
            self._last_active_time = time.time()
            self._set_state("ACTIVE_SAMPLING")

            img = self.grab_window_or_screen(window_info)
            if img:
                current_pixels = downscale_to_grayscale(img)
                self._prev_pixels = current_pixels
                self._last_capture_time = time.time()
                self.stats["total_samples"] += 1
                self.stats["meaningful_frames"] += 1
                self.stats["last_delta"] = 1.0

                logger.info("⚡ Immediate capture triggered (%s) for '%s'", reason, window_info.title[:30])
                if self.on_meaningful_frame:
                    try:
                        self.on_meaningful_frame(img, 1.0, window_info)
                    except Exception as e:
                        logger.error("Error in on_meaningful_frame handler: %s", e)

    def start(self, initial_window: Optional[WindowInfo] = None):
        """Starts the autonomous sampling worker thread."""
        self._stop_event.clear()
        self._pause_event.clear()
        if initial_window:
            self._current_window_info = initial_window
        self._set_state("ACTIVE_SAMPLING")
        self._worker_thread = threading.Thread(target=self._run_loop, daemon=True, name="VisualSamplerThread")
        self._worker_thread.start()
        logger.info("VisualSampler autonomous engine started.")

    def pause(self):
        self._pause_event.set()
        self._set_state("PAUSED")

    def resume(self):
        self._pause_event.clear()
        self._last_active_time = time.time()
        self._set_state("ACTIVE_SAMPLING")

    def stop(self):
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        self._set_state("STOPPED")
        logger.info("VisualSampler stopped.")

    def _run_loop(self):
        """
        Core autonomous sampling loop.
        During active mode: samples every 1.0s.
        During idle mode: polls every 1.5s with low-overhead diff only.
        """
        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(0.5)
                continue

            now = time.time()
            time_since_active = now - self._last_active_time

            # Check 10-Second Idle Rule: transition to IDLE WATCH MODE
            if self._state == "ACTIVE_SAMPLING" and time_since_active >= self.idle_timeout_sec:
                self._set_state("IDLE_WATCH")

            # Determine sleep duration based on state
            sleep_duration = IDLE_POLL_INTERVAL_SEC if self._state == "IDLE_WATCH" else ACTIVE_INTERVAL_SEC

            # Perform grab
            win_info = self._current_window_info
            if not win_info or not win_info.is_valid:
                time.sleep(sleep_duration)
                continue

            img = self.grab_window_or_screen(win_info)

            if img:
                current_pixels = downscale_to_grayscale(img)
                self.stats["total_samples"] += 1

                if self._prev_pixels is None:
                    # Initial baseline
                    self._prev_pixels = current_pixels
                    self._last_active_time = now
                    self.stats["meaningful_frames"] += 1
                    self.stats["last_delta"] = 1.0
                    if self.on_meaningful_frame and win_info:
                        try:
                            self.on_meaningful_frame(img, 1.0, win_info)
                        except Exception as e:
                            logger.error("Baseline frame dispatch error: %s", e)
                else:
                    delta = compute_weighted_regional_delta(self._prev_pixels, current_pixels)
                    self.stats["last_delta"] = delta
                    is_meaningful = delta >= self.delta_threshold

                    if is_meaningful:
                        # WAKE UP IMMEDIATELY if in IDLE WATCH
                        self._last_active_time = now
                        self._prev_pixels = current_pixels
                        self._set_state("ACTIVE_SAMPLING")
                        self.stats["meaningful_frames"] += 1

                        if self.on_meaningful_frame and win_info:
                            try:
                                self.on_meaningful_frame(img, delta, win_info)
                            except Exception as e:
                                logger.error("Frame dispatch error: %s", e)
                    else:
                        self.stats["idle_skips"] += 1

            # Sleep until next scheduled sample
            time.sleep(sleep_duration)
