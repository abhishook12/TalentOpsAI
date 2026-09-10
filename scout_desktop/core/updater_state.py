"""
updater_state.py — Typed Autonomous Update State Machine for TalentOps Scout.

Lifecycle:
UP_TO_DATE
     ↓
UPDATE_AVAILABLE
     ↓
DOWNLOADING
     ↓
DOWNLOADED
     ↓
VERIFYING
     ↓
APPLYING
     ↓
HEALTH_CHECK
     ↓
SUCCESS

Failure Paths:
DOWNLOADING  → DOWNLOAD_FAILED
VERIFYING    → VERIFICATION_FAILED
APPLYING     → APPLY_FAILED
HEALTH_CHECK → ROLLBACK

Rollback Path:
ROLLBACK
     ↓
RESTORE_PREVIOUS
     ↓
HEALTH_CHECK
     ↓
STABLE
"""

import os
import json
import time
import logging
from enum import Enum
from typing import Optional, Dict, Any, Set, List
from .paths import get_state_dir

logger = logging.getLogger("scout.updater_state")


class UpdateState(str, Enum):
    UP_TO_DATE = "UP_TO_DATE"
    UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
    DOWNLOADING = "DOWNLOADING"
    READY_TO_INSTALL = "READY_TO_INSTALL"
    INSTALLING = "INSTALLING"
    HEALTH_CHECK = "HEALTH_CHECK"
    UPDATED = "UPDATED"
    FAILED = "FAILED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    REQUIRED_UPDATE = "REQUIRED_UPDATE"

    # Legacy & Granular Compatibility Aliases
    DOWNLOADED = "READY_TO_INSTALL"
    APPLYING = "INSTALLING"
    SUCCESS = "UPDATED"
    ROLLBACK = "ROLLING_BACK"
    RESTORE_PREVIOUS = "ROLLING_BACK"
    STABLE = "UP_TO_DATE"
    DOWNLOAD_FAILED = "FAILED"
    VERIFICATION_FAILED = "FAILED"
    APPLY_FAILED = "FAILED"
    HEALTH_CHECK_FAILED = "FAILED"
    VERIFYING = "DOWNLOADING"


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal state machine transition is attempted."""
    pass


VALID_TRANSITIONS: Dict[UpdateState, Set[UpdateState]] = {
    UpdateState.UP_TO_DATE: {
        UpdateState.UPDATE_AVAILABLE,
        UpdateState.REQUIRED_UPDATE,
        UpdateState.DOWNLOADING,
        UpdateState.UP_TO_DATE,
    },
    UpdateState.UPDATE_AVAILABLE: {
        UpdateState.DOWNLOADING,
        UpdateState.READY_TO_INSTALL,
        UpdateState.UP_TO_DATE,
        UpdateState.REQUIRED_UPDATE,
    },
    UpdateState.REQUIRED_UPDATE: {
        UpdateState.DOWNLOADING,
        UpdateState.READY_TO_INSTALL,
        UpdateState.INSTALLING,
        UpdateState.UP_TO_DATE,
    },
    UpdateState.DOWNLOADING: {
        UpdateState.READY_TO_INSTALL,
        UpdateState.FAILED,
    },
    UpdateState.READY_TO_INSTALL: {
        UpdateState.INSTALLING,
        UpdateState.FAILED,
        UpdateState.UP_TO_DATE,
    },
    UpdateState.INSTALLING: {
        UpdateState.HEALTH_CHECK,
        UpdateState.FAILED,
        UpdateState.ROLLING_BACK,
    },
    UpdateState.HEALTH_CHECK: {
        UpdateState.UPDATED,
        UpdateState.FAILED,
        UpdateState.ROLLING_BACK,
    },
    UpdateState.UPDATED: {
        UpdateState.UP_TO_DATE,
        UpdateState.UPDATE_AVAILABLE,
    },
    UpdateState.FAILED: {
        UpdateState.DOWNLOADING,
        UpdateState.UPDATE_AVAILABLE,
        UpdateState.UP_TO_DATE,
        UpdateState.ROLLING_BACK,
    },
    UpdateState.ROLLING_BACK: {
        UpdateState.ROLLED_BACK,
        UpdateState.HEALTH_CHECK,
        UpdateState.FAILED,
    },
    UpdateState.ROLLED_BACK: {
        UpdateState.UP_TO_DATE,
        UpdateState.UPDATE_AVAILABLE,
    },
}


class UpdateStateMachine:
    """Manages updater state transitions, persistence, and telemetry audit history."""

    def __init__(self, initial_state: UpdateState = UpdateState.UP_TO_DATE):
        self._state: UpdateState = initial_state
        self._history: List[Dict[str, Any]] = []
        self._last_error: Optional[str] = None
        self._target_version: Optional[str] = None
        self._state_file = os.path.join(get_state_dir(), "update_state.json")
        self._load_persisted_state()

    @property
    def current_state(self) -> UpdateState:
        return self._state

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @property
    def target_version(self) -> Optional[str]:
        return self._target_version

    def set_target_version(self, version: str):
        self._target_version = version

    def transition(
        self,
        new_state: UpdateState,
        context: Optional[str] = None,
        target_version: Optional[str] = None,
        strict: bool = True,
    ) -> UpdateState:
        """
        Executes a validated transition to new_state.
        Raises InvalidStateTransitionError if transition is invalid and strict=True.
        """
        if target_version:
            self._target_version = target_version

        allowed = VALID_TRANSITIONS.get(self._state, set())

        if new_state not in allowed:
            msg = f"Illegal updater transition from {self._state.value} -> {new_state.value}."
            if strict:
                logger.error(msg)
                raise InvalidStateTransitionError(msg)
            else:
                logger.warning("%s (Permitted due to non-strict mode)", msg)

        prev = self._state
        self._state = new_state
        timestamp = time.time()

        if "FAILED" in new_state.value or new_state == UpdateState.ROLLBACK:
            self._last_error = context or f"Failed during {prev.value}"

        entry = {
            "from_state": prev.value,
            "to_state": new_state.value,
            "target_version": self._target_version,
            "timestamp": timestamp,
            "context": context,
        }
        self._history.append(entry)

        logger.info(
            "[STATE] Update Transition: %s -> %s %s",
            prev.value,
            new_state.value,
            f"({context})" if context else "",
        )

        self._persist_state()
        return self._state

    def is_in_progress(self) -> bool:
        return self._state in {
            UpdateState.DOWNLOADING,
            UpdateState.DOWNLOADED,
            UpdateState.VERIFYING,
            UpdateState.APPLYING,
            UpdateState.HEALTH_CHECK,
            UpdateState.ROLLBACK,
            UpdateState.RESTORE_PREVIOUS,
        }

    def is_failed(self) -> bool:
        return self._state in {
            UpdateState.DOWNLOAD_FAILED,
            UpdateState.VERIFICATION_FAILED,
            UpdateState.APPLY_FAILED,
            UpdateState.HEALTH_CHECK_FAILED,
        }

    def reset_to_stable(self, error_message: Optional[str] = None):
        """Safely resets state machine back to STABLE / UP_TO_DATE following error or rollback."""
        if self._state == UpdateState.ROLLBACK or self._state == UpdateState.RESTORE_PREVIOUS:
            self.transition(UpdateState.STABLE, context=error_message, strict=False)
        self.transition(UpdateState.UP_TO_DATE, context=error_message, strict=False)

    def _persist_state(self):
        try:
            os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
            payload = {
                "current_state": self._state.value,
                "target_version": self._target_version,
                "last_error": self._last_error,
                "updated_at": time.time(),
                "history": self._history[-20:],  # keep last 20 events
            }
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logger.debug("Could not persist update state: %s", e)

    def _load_persisted_state(self):
        if not os.path.exists(self._state_file):
            return
        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            saved_state_str = data.get("current_state")
            if saved_state_str and saved_state_str in UpdateState._value2member_map_:
                self._state = UpdateState(saved_state_str)
                self._target_version = data.get("target_version")
                self._last_error = data.get("last_error")
                self._history = data.get("history", [])
        except Exception as e:
            logger.debug("Could not load persisted update state: %s", e)
