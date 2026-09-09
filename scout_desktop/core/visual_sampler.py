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
DEFAULT_DELTA_THRESHOLD = 0.048  # 4.8% meaningful regional change (filters typing/blinking cursor)
PIXEL_TOLERANCE = 18            # Ignore micro compression noise
IDLE_TIMEOUT_SEC = 6.0          # 6 continuous seconds static -> IDLE WATCH
ACTIVE_INTERVAL_SEC = 1.0       # 1s active sampling
IDLE_POLL_INTERVAL_SEC = 2.0    # Low-power idle poll (2.0s)
DEFAULT_AUTONOMOUS_SCAN_SEC = 30.0 # 30s periodic scan when static (prevents CPU spikes)


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
    delta, _ = compute_weighted_regional_delta_and_box(pixels_a, pixels_b)
    return delta


def compute_weighted_regional_delta_and_box(
    pixels_a: np.ndarray, pixels_b: np.ndarray, orig_w: int = 0, orig_h: int = 0
) -> Tuple[float, Optional[Tuple[int, int, int, int]]]:
    """
    Computes regional weighted difference score AND identifies the bounding box
    of the visually altered region (scaled to original image dimensions).
    """
    if pixels_a is None or pixels_b is None:
        return 1.0, None
    if pixels_a.shape != pixels_b.shape:
        return 1.0, None

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
    score = round(float(weighted_score), 4)

    # Compute changed bounding box if change detected
    bbox = None
    if total_sig > 10 and orig_w > 0 and orig_h > 0:
        y_indices, x_indices = np.where(significant_mask)
        if len(y_indices) > 0 and len(x_indices) > 0:
            min_y_ratio = max(0.0, float(np.min(y_indices)) / DOWNSCALE_HEIGHT - 0.05)
            max_y_ratio = min(1.0, float(np.max(y_indices)) / DOWNSCALE_HEIGHT + 0.05)
            min_x_ratio = max(0.0, float(np.min(x_indices)) / DOWNSCALE_WIDTH - 0.05)
            max_x_ratio = min(1.0, float(np.max(x_indices)) / DOWNSCALE_WIDTH + 0.05)

            # Ensure box isn't trivial
            if (max_y_ratio - min_y_ratio) > 0.15 and (max_x_ratio - min_x_ratio) > 0.15:
                bbox = (
                    int(min_x_ratio * orig_w),
                    int(min_y_ratio * orig_h),
                    int(max_x_ratio * orig_w),
                    int(max_y_ratio * orig_h),
                )

    return score, bbox



class VisualSampler:
    def __init__(
        self,
        on_meaningful_frame: Optional[Callable[[Image.Image, float, WindowInfo], None]] = None,
        on_state_change: Optional[Callable[[str], None]] = None,
        delta_threshold: float = DEFAULT_DELTA_THRESHOLD,
        idle_timeout_sec: float = IDLE_TIMEOUT_SEC,
        autonomous_scan_interval_sec: float = DEFAULT_AUTONOMOUS_SCAN_SEC,
        active_interval_sec: float = ACTIVE_INTERVAL_SEC,
        idle_poll_interval_sec: float = IDLE_POLL_INTERVAL_SEC,
    ):
        self.on_meaningful_frame = on_meaningful_frame
        self.on_state_change = on_state_change
        self.delta_threshold = delta_threshold
        self.idle_timeout_sec = idle_timeout_sec
        self.autonomous_scan_interval_sec = autonomous_scan_interval_sec
        self.active_interval_sec = active_interval_sec
        self.idle_poll_interval_sec = idle_poll_interval_sec

        self._state = "RESTING_NON_TARGET"  # ACTIVE_SAMPLING | IDLE_WATCH | PAUSED | RESTING_NON_TARGET
        self._is_target_allowed = False
        self._prev_pixels = None
        self._last_active_time = time.time()
        self._last_capture_time = 0.0
        self._last_autonomous_scan_time = 0.0
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
            "autonomous_scans": 0,
            "last_delta": 0.0,
            "current_state": "RESTING_NON_TARGET",
        }

    @property
    def is_target_allowed(self) -> bool:
        return self._is_target_allowed

    def set_target_allowed(self, allowed: bool):
        """Sets whether the currently active window is on the strict target allowlist."""
        with self._lock:
            self._is_target_allowed = allowed
            if not allowed:
                self._prev_pixels = None
                self._set_state("RESTING_NON_TARGET")
            else:
                if self._state == "RESTING_NON_TARGET":
                    now = time.time()
                    self._last_active_time = now
                    self._last_autonomous_scan_time = now
                    self._set_state("ACTIVE_SAMPLING")

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
        Strictly gated: Only executes if active window is an allowed target.
        """
        with self._lock:
            if not self._is_target_allowed:
                logger.debug("Immediate capture skipped: Window outside strict allowlist (%s)", reason)
                return

            self._current_window_info = window_info
            now = time.time()
            self._last_active_time = now
            self._last_autonomous_scan_time = now
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
                    threading.Thread(
                        target=self._dispatch_frame_async,
                        args=(img, 1.0, window_info),
                        daemon=True,
                        name="ImmediateCaptureWorker"
                    ).start()

    def _dispatch_frame_async(self, img: Image.Image, delta: float, window_info: WindowInfo, bbox: Optional[Tuple[int, int, int, int]] = None):
        """Executes heavy frame analysis, OCR, and extraction on a worker thread to keep Qt GUI responsive."""
        try:
            if self.on_meaningful_frame:
                import inspect
                sig = inspect.signature(self.on_meaningful_frame)
                if len(sig.parameters) >= 4 and bbox is not None:
                    self.on_meaningful_frame(img, delta, window_info, bbox)
                else:
                    self.on_meaningful_frame(img, delta, window_info)
        except Exception as e:
            logger.error("Error in on_meaningful_frame worker handler: %s", e)

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

            # Strict Whitelist Rule: If current window is outside allowlist, rest completely (0% CPU)
            if not self._is_target_allowed:
                if self._state != "RESTING_NON_TARGET":
                    self._set_state("RESTING_NON_TARGET")
                time.sleep(1.0)
                continue

            now = time.time()
            time_since_active = now - self._last_active_time

            # Check 10-Second Idle Rule: transition to IDLE WATCH MODE
            if self._state == "ACTIVE_SAMPLING" and time_since_active >= self.idle_timeout_sec:
                self._set_state("IDLE_WATCH")

            # Determine sleep duration based on state
            sleep_duration = self.idle_poll_interval_sec if self._state == "IDLE_WATCH" else self.active_interval_sec

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
                    delta, bbox = compute_weighted_regional_delta_and_box(
                        self._prev_pixels, current_pixels, img.width, img.height
                    )
                    self.stats["last_delta"] = delta
                    is_meaningful = delta >= self.delta_threshold
                    is_autonomous_scan = (now - self._last_autonomous_scan_time) >= self.autonomous_scan_interval_sec

                    if is_meaningful or is_autonomous_scan:
                        # WAKE UP IMMEDIATELY if in IDLE WATCH or trigger autonomous scan
                        self._last_active_time = now
                        self._last_autonomous_scan_time = now
                        self._prev_pixels = current_pixels
                        self._set_state("ACTIVE_SAMPLING")
                        self.stats["meaningful_frames"] += 1
                        if is_autonomous_scan and not is_meaningful:
                            self.stats["autonomous_scans"] = self.stats.get("autonomous_scans", 0) + 1

                        effective_delta = delta if is_meaningful else 0.05
                        if self.on_meaningful_frame and win_info:
                            try:
                                import inspect
                                sig = inspect.signature(self.on_meaningful_frame)
                                if len(sig.parameters) >= 4:
                                    self.on_meaningful_frame(img, effective_delta, win_info, bbox)
                                else:
                                    self.on_meaningful_frame(img, effective_delta, win_info)
                            except Exception as e:
                                logger.error("Frame dispatch error: %s", e)
                    else:
                        self.stats["idle_skips"] += 1

            # Sleep until next scheduled sample
            time.sleep(sleep_duration)
