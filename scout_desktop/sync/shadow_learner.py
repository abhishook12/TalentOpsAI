"""
scout_desktop/sync/shadow_learner.py — Shadow Learning & Ambiguity Harvesting Engine

Autonomously identifies ambiguous entities, borderline classifications (confidence 0.30 - 0.85),
and unconfirmed candidate extractions, buffering them with rich surrounding screen context
for asynchronous cloud adjudication by the AI Teacher.
"""

import time
import hashlib
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("scout.shadow_learner")


class ShadowLearner:
    """
    Edge buffer for ambiguous extractions.
    Gathers local context window and submits to the backend AI teacher.
    """

    def __init__(self, max_buffer_size: int = 100):
        self._buffer: List[Dict[str, Any]] = []
        self._seen_hashes: set = set()
        self._max_buffer = max_buffer_size

    def inspect_and_buffer(
        self,
        candidate_text: str,
        entity_type: str,
        confidence: float,
        context_lines: Optional[List[str]] = None,
        source_url: Optional[str] = None,
        window_title: Optional[str] = None,
        line_idx: Optional[int] = None,
    ) -> bool:
        """
        Determines if an observation falls in the ambiguity learning window (0.30 - 0.85 or UNKNOWN).
        If ambiguous and not previously buffered, captures surrounding context.
        """
        if not candidate_text or not isinstance(candidate_text, str):
            return False

        text_clean = candidate_text.strip()
        if len(text_clean) < 2 or len(text_clean) > 80:
            return False

        # Ambiguity threshold criteria:
        is_ambiguous = (
            entity_type == "UNKNOWN"
            or (0.30 <= confidence <= 0.85)
            or (entity_type == "COMPANY" and confidence < 0.90)
            or (entity_type == "PERSON" and confidence < 0.90)
        )

        if not is_ambiguous:
            return False

        # Deduplication hash based on text and context window
        ctx = context_lines or []
        ctx_str = " ".join(ctx[:5])
        content_hash = hashlib.sha256(f"{text_clean.lower()}|{ctx_str.lower()}|{source_url or ''}".encode("utf-8")).hexdigest()[:16]

        if content_hash in self._seen_hashes:
            return False

        self._seen_hashes.add(content_hash)

        item = {
            "content_hash": content_hash,
            "candidate_text": text_clean,
            "provisional_type": entity_type,
            "provisional_confidence": round(confidence, 3),
            "context_lines": ctx[:8],
            "line_index": line_idx,
            "source_url": source_url or "",
            "window_title": window_title or "",
            "captured_at": time.time(),
        }

        self._buffer.append(item)
        if len(self._buffer) > self._max_buffer:
            self._buffer.pop(0)

        logger.debug("ShadowLearner buffered ambiguous entity '%s' (conf=%.2f, type=%s)", text_clean, confidence, entity_type)
        return True

    def get_pending_batch(self, max_items: int = 25) -> List[Dict[str, Any]]:
        """Retrieves items ready to be flushed to the backend AI teacher."""
        return self._buffer[:max_items]

    def remove_flushed(self, count: int):
        """Removes successfully flushed items from the buffer."""
        self._buffer = self._buffer[count:]

    def clear(self):
        """Clears in-memory buffer."""
        self._buffer.clear()
        self._seen_hashes.clear()

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)


# Global singleton instance
shadow_learner = ShadowLearner()
