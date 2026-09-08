"""
core/intelligence_levels.py — 3-Level Cognitive Intelligence Router

Implements the WATCH → UNDERSTAND → RESOLVE intelligence hierarchy:

Level 1 (WATCH):
    Low-cost passive monitoring. Only polls active window identity,
    lightweight perceptual hash comparison, and URL change detection.
    No expensive OCR or AI invoked. Continuous, sub-second cadence.

Level 2 (UNDERSTAND):
    Triggered when meaningful visual change is detected at Level 1.
    Captures full-resolution frame, runs OCR, extracts entities,
    builds observations, and evaluates information value.

Level 3 (RESOLVE):
    Triggered only for high-value or ambiguous observations.
    Performs client-side identity resolution against known entities,
    evaluates completeness and information gaps, determines
    enrichment vs new-entity decisions, and validates evidence grounding.

The IntelligenceRouter determines which level to invoke for each frame
based on signals from the visual sampler, browser tracker, and context memory.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Dict, Any, List

logger = logging.getLogger("scout.intelligence")


class IntelligenceLevel(IntEnum):
    """The three cognitive processing levels for visual intelligence."""
    WATCH = 1       # Cheap monitoring only — window polling + perceptual hash
    UNDERSTAND = 2  # Full capture + OCR + entity extraction
    RESOLVE = 3     # Identity resolution + enrichment decision + grounding validation


@dataclass
class FrameContext:
    """
    Encapsulates all signals available when deciding which intelligence level
    to invoke for a captured frame.
    """
    # Visual change signals
    visual_delta: float = 0.0           # 0.0–1.0 weighted regional difference
    is_window_changed: bool = False     # Active window HWND changed
    is_url_changed: bool = False        # Browser URL changed
    is_page_type_changed: bool = False  # Page type classification changed

    # Content signals
    page_type: str = "UNKNOWN"          # PERSON_PROFILE, COMPANY_PEOPLE, JOB_POSTING, etc.
    platform: str = "UNKNOWN"           # LINKEDIN, INDEED, GLASSDOOR, etc.
    window_title: str = ""
    page_url: str = ""

    # Processing state signals
    current_entity_count: int = 0       # How many entities are currently tracked
    has_pending_gaps: bool = False       # Are there known information gaps to fill?
    frames_since_last_extraction: int = 0  # Frames processed without new extraction
    time_since_last_extraction: float = 0.0  # Seconds since last successful extraction

    # Queue signals
    queue_depth: int = 0                # Pending frames in processing queue
    is_backpressure: bool = False       # Is downstream processing overloaded?

    # Window metadata
    process_name: str = ""
    process_category: str = ""          # BROWSER, PRODUCTIVITY, GENERIC

    timestamp: float = field(default_factory=time.time)


@dataclass
class IntelligenceDecision:
    """
    The routing decision for a single frame, including the selected level
    and the reasoning behind it.
    """
    level: IntelligenceLevel
    reason: str                         # Human-readable explanation
    priority: float = 0.5              # 0.0 (lowest) to 1.0 (highest)
    should_capture: bool = True        # Whether to take a screenshot
    should_skip: bool = False          # Whether to skip processing entirely
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntelligenceRouter:
    """
    Determines which intelligence level to invoke for a given frame.

    The router evaluates multiple signals (visual change, window change,
    page context, processing state) and returns a decision that includes
    the appropriate intelligence level and the reasoning behind it.

    Escalation Rules:
    - Level 1 (WATCH) is always running; it's the baseline.
    - Escalate to Level 2 (UNDERSTAND) when: meaningful visual change,
      window/URL switch, or periodic forced capture.
    - Escalate to Level 3 (RESOLVE) when: multiple entities detected,
      ambiguous identity signals, information gaps exist, or high-value
      page context (e.g., LinkedIn profile with missing fields).

    Backpressure Rules:
    - If queue_depth > MAX_QUEUE_DEPTH: stay at Level 1, don't capture.
    - If time_since_last_extraction < MIN_EXTRACTION_INTERVAL: stay at Level 1.
    """

    # Thresholds
    DELTA_THRESHOLD_UNDERSTAND = 0.035    # 3.5% visual change → escalate to UNDERSTAND
    DELTA_THRESHOLD_HIGH_VALUE = 0.10     # 10% change on high-value page → escalate to RESOLVE
    MIN_EXTRACTION_INTERVAL = 0.5         # Minimum 500ms between extractions
    MAX_QUEUE_DEPTH = 5                   # Maximum pending frames before backpressure
    FORCED_CAPTURE_INTERVAL = 30.0        # Force capture every 30s even if static
    HIGH_VALUE_PAGE_TYPES = {
        "PERSON_PROFILE", "COMPANY_PEOPLE", "JOB_POSTING", "CAREER_PAGE",
    }

    def __init__(self):
        self._last_decision_time = 0.0
        self._last_level = IntelligenceLevel.WATCH
        self._consecutive_watch_count = 0
        self._stats = {
            "total_decisions": 0,
            "level_1_count": 0,
            "level_2_count": 0,
            "level_3_count": 0,
            "backpressure_skips": 0,
        }

    @property
    def stats(self) -> Dict[str, int]:
        """Returns intelligence routing statistics."""
        return dict(self._stats)

    def evaluate(self, ctx: FrameContext) -> IntelligenceDecision:
        """
        Evaluates frame context and returns the appropriate intelligence level.

        Args:
            ctx: FrameContext with all available signals.

        Returns:
            IntelligenceDecision with level, reason, and priority.
        """
        self._stats["total_decisions"] += 1

        # Rule 0: Backpressure guard — if queue is full, don't add more work
        if ctx.is_backpressure or ctx.queue_depth > self.MAX_QUEUE_DEPTH:
            self._stats["backpressure_skips"] += 1
            return IntelligenceDecision(
                level=IntelligenceLevel.WATCH,
                reason="BACKPRESSURE: queue full, staying at WATCH",
                priority=0.0,
                should_capture=False,
                should_skip=True,
            )

        # Rule 1: Window or URL changed — always escalate to UNDERSTAND
        if ctx.is_window_changed or ctx.is_url_changed:
            decision = IntelligenceDecision(
                level=IntelligenceLevel.UNDERSTAND,
                reason=f"{'Window' if ctx.is_window_changed else 'URL'} changed → UNDERSTAND",
                priority=0.9,
                should_capture=True,
            )
            # Further escalate to RESOLVE if it's a high-value page
            if ctx.page_type in self.HIGH_VALUE_PAGE_TYPES and ctx.has_pending_gaps:
                decision.level = IntelligenceLevel.RESOLVE
                decision.reason += " + high-value page with gaps → RESOLVE"
                decision.priority = 1.0
            self._record_decision(decision)
            return decision

        # Rule 2: Page type changed (e.g., from search to profile) — escalate
        if ctx.is_page_type_changed:
            decision = IntelligenceDecision(
                level=IntelligenceLevel.UNDERSTAND,
                reason=f"Page type changed to {ctx.page_type} → UNDERSTAND",
                priority=0.85,
                should_capture=True,
            )
            self._record_decision(decision)
            return decision

        # Rule 3: Meaningful visual change — escalate based on delta magnitude
        if ctx.visual_delta >= self.DELTA_THRESHOLD_UNDERSTAND:
            # High delta on valuable page → RESOLVE
            if (ctx.visual_delta >= self.DELTA_THRESHOLD_HIGH_VALUE
                    and ctx.page_type in self.HIGH_VALUE_PAGE_TYPES):
                decision = IntelligenceDecision(
                    level=IntelligenceLevel.RESOLVE,
                    reason=f"High visual delta ({ctx.visual_delta:.3f}) on {ctx.page_type} → RESOLVE",
                    priority=0.95,
                    should_capture=True,
                )
            else:
                decision = IntelligenceDecision(
                    level=IntelligenceLevel.UNDERSTAND,
                    reason=f"Visual delta ({ctx.visual_delta:.3f}) exceeds threshold → UNDERSTAND",
                    priority=0.7,
                    should_capture=True,
                )
            self._record_decision(decision)
            return decision

        # Rule 4: Information gaps exist and we're on a high-value page — periodic RESOLVE
        if (ctx.has_pending_gaps
                and ctx.page_type in self.HIGH_VALUE_PAGE_TYPES
                and ctx.time_since_last_extraction > 3.0):
            decision = IntelligenceDecision(
                level=IntelligenceLevel.RESOLVE,
                reason=f"Information gaps pending on {ctx.page_type}, re-evaluating → RESOLVE",
                priority=0.6,
                should_capture=True,
            )
            self._record_decision(decision)
            return decision

        # Rule 5: Forced periodic capture (prevent stale baseline)
        if ctx.time_since_last_extraction > self.FORCED_CAPTURE_INTERVAL:
            decision = IntelligenceDecision(
                level=IntelligenceLevel.UNDERSTAND,
                reason=f"Forced capture after {ctx.time_since_last_extraction:.0f}s static → UNDERSTAND",
                priority=0.3,
                should_capture=True,
            )
            self._record_decision(decision)
            return decision

        # Rule 6: Default — stay at WATCH (no capture, no processing)
        self._consecutive_watch_count += 1
        decision = IntelligenceDecision(
            level=IntelligenceLevel.WATCH,
            reason="No significant signals → WATCH",
            priority=0.1,
            should_capture=False,
            should_skip=False,
        )
        self._stats["level_1_count"] += 1
        return decision

    def should_escalate(self, observations: list, completeness_score: float = 0.0) -> bool:
        """
        Post-extraction check: should we escalate from UNDERSTAND to RESOLVE?

        Called after Level 2 extraction produces observations. Returns True
        if the observations warrant deeper identity resolution or enrichment.

        Args:
            observations: List of extracted Observation objects.
            completeness_score: Current entity completeness (0.0–1.0).

        Returns:
            True if escalation to Level 3 is warranted.
        """
        if not observations:
            return False

        # Multiple entities detected → need resolution
        unique_subjects = set()
        for obs in observations:
            if hasattr(obs, 'subject'):
                unique_subjects.add(obs.subject)
        if len(unique_subjects) > 1:
            return True

        # Low completeness → need gap filling
        if completeness_score < 0.5:
            return True

        # Any ambiguous observations → need resolution
        for obs in observations:
            if hasattr(obs, 'confidence') and obs.confidence < 0.6:
                return True

        return False

    def _record_decision(self, decision: IntelligenceDecision):
        """Records decision statistics."""
        self._last_decision_time = time.time()
        self._last_level = decision.level
        self._consecutive_watch_count = 0

        if decision.level == IntelligenceLevel.WATCH:
            self._stats["level_1_count"] += 1
        elif decision.level == IntelligenceLevel.UNDERSTAND:
            self._stats["level_2_count"] += 1
        elif decision.level == IntelligenceLevel.RESOLVE:
            self._stats["level_3_count"] += 1


class FrameQueue:
    """
    Bounded frame queue with backpressure support.

    Holds pending frames for processing with a maximum depth.
    When the queue is full, the oldest unprocessed frame is dropped
    (keep newest strategy) to prevent memory buildup.
    """

    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth
        self._queue: List[Dict[str, Any]] = []
        self._dropped_count = 0
        self._total_enqueued = 0
        import threading
        self._lock = threading.Lock()

    @property
    def depth(self) -> int:
        """Current number of pending frames."""
        with self._lock:
            return len(self._queue)

    @property
    def is_full(self) -> bool:
        """Whether the queue is at capacity."""
        with self._lock:
            return len(self._queue) >= self.max_depth

    @property
    def dropped_count(self) -> int:
        """Total number of frames dropped due to backpressure."""
        return self._dropped_count

    def enqueue(self, frame_data: Dict[str, Any]) -> bool:
        """
        Adds a frame to the queue. If full, drops the oldest frame.

        Args:
            frame_data: Dictionary containing 'image', 'delta', 'window_info',
                       'decision', and 'timestamp'.

        Returns:
            True if the frame was added (possibly after dropping oldest),
            False if the frame itself was rejected.
        """
        with self._lock:
            if len(self._queue) >= self.max_depth:
                # Drop oldest unprocessed frame (keep newest strategy)
                dropped = self._queue.pop(0)
                self._dropped_count += 1
                logger.debug(
                    "Frame queue full (%d/%d), dropped oldest frame from %.1fs ago",
                    len(self._queue), self.max_depth,
                    time.time() - dropped.get("timestamp", 0)
                )

            self._queue.append(frame_data)
            self._total_enqueued += 1
            return True

    def dequeue(self) -> Optional[Dict[str, Any]]:
        """
        Removes and returns the oldest frame from the queue.

        Returns:
            Frame data dict, or None if queue is empty.
        """
        with self._lock:
            if self._queue:
                return self._queue.pop(0)
            return None

    def peek(self) -> Optional[Dict[str, Any]]:
        """Returns the oldest frame without removing it."""
        with self._lock:
            if self._queue:
                return self._queue[0]
            return None

    def clear(self):
        """Clears all pending frames from the queue."""
        with self._lock:
            count = len(self._queue)
            self._queue.clear()
            if count > 0:
                logger.info("Frame queue cleared (%d frames discarded)", count)

    def get_stats(self) -> Dict[str, int]:
        """Returns queue telemetry statistics."""
        with self._lock:
            return {
                "current_depth": len(self._queue),
                "max_depth": self.max_depth,
                "total_enqueued": self._total_enqueued,
                "total_dropped": self._dropped_count,
            }
