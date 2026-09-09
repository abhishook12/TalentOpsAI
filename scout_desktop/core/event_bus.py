"""
TalentOps Scout 2.0 - Local Event Bus
Thread-safe, typed publish-subscribe engine decoupling capture,
extraction, change detection, local queueing, and telemetry reporting.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger("scout.event_bus")


class EventPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    IGNORE = "IGNORE"


@dataclass
class BaseEvent:
    """Base class for all Scout 2.0 events."""
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: f"EVT-{int(time.time()*1000)}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.__class__.__name__,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
        }


@dataclass
class CaptureEvent(BaseEvent):
    """Fired when visual or textual content is observed from an authorized window."""
    capture_id: str = ""
    window_title: str = ""
    source_url: str = ""
    file_path: Optional[str] = None
    raw_text: str = ""
    platform: str = "linkedin"
    scope_authorized: bool = True

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "capture_id": self.capture_id,
            "window_title": self.window_title,
            "source_url": self.source_url,
            "file_path": self.file_path,
            "raw_text_length": len(self.raw_text),
            "platform": self.platform,
            "scope_authorized": self.scope_authorized,
        })
        return d


@dataclass
class NormalizedObservationEvent(BaseEvent):
    """Fired when an extractor normalizes an observation into structured fields."""
    observation_id: str = ""
    entity_type: str = "PERSON"
    canonical_name: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    skills: list[str] = field(default_factory=list)
    confidence: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "observation_id": self.observation_id,
            "entity_type": self.entity_type,
            "canonical_name": self.canonical_name,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "skills": self.skills,
            "confidence": self.confidence,
        })
        return d


@dataclass
class ChangeDetectedEvent(BaseEvent):
    """Fired when the delta engine identifies an insert, update, or ignore state."""
    entity_id: str = ""
    operation: str = "INSERT"  # INSERT, UPDATE, IGNORE
    changed_fields: list[str] = field(default_factory=list)
    delta: dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.MEDIUM

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "entity_id": self.entity_id,
            "operation": self.operation,
            "changed_fields": self.changed_fields,
            "delta": self.delta,
            "priority": self.priority.value if hasattr(self.priority, "value") else str(self.priority),
        })
        return d


@dataclass
class QueueStatusEvent(BaseEvent):
    """Fired when local queue items transition states."""
    queue_id: int = 0
    status: str = "PENDING"  # PENDING, PROCESSING, SYNCED, RETRY, DLQ
    priority: str = "MEDIUM"
    retry_count: int = 0
    dlq_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "queue_id": self.queue_id,
            "status": self.status,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "dlq_reason": self.dlq_reason,
        })
        return d


@dataclass
class HealthAlertEvent(BaseEvent):
    """Fired on health status change, degradation, or self-healing action."""
    subsystem: str = ""
    status: str = "HEALTHY"  # HEALTHY, DEGRADED, RECOVERING, FAULT
    message: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "subsystem": self.subsystem,
            "status": self.status,
            "message": self.message,
            "metrics": self.metrics,
        })
        return d


@dataclass
class SyncTelemetryEvent(BaseEvent):
    """Fired after synchronization batches to measure network and backend health."""
    batch_size: int = 0
    duration_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    server_status: int = 200

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "batch_size": self.batch_size,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
            "server_status": self.server_status,
        })
        return d


EventHandler = Callable[[BaseEvent], None]


class EventBus:
    """
    Thread-safe publish/subscribe Event Bus for local Scout 2.0 subsystems.
    Allows decoupling capture, extraction, change detection, and sync.
    """

    _instance: Optional[EventBus] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._subscribers: dict[Type[BaseEvent], list[EventHandler]] = {}
        self._any_subscribers: list[EventHandler] = []
        self._history: list[BaseEvent] = []
        self._max_history = 200
        self._bus_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> EventBus:
        """Singleton accessor for application-wide event bus."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def subscribe(self, event_type: Type[BaseEvent], handler: EventHandler) -> None:
        """Register a callback for a specific event type."""
        with self._bus_lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                logger.debug("Subscribed %s to %s", getattr(handler, "__name__", str(handler)), event_type.__name__)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Register a callback that receives every published event."""
        with self._bus_lock:
            if handler not in self._any_subscribers:
                self._any_subscribers.append(handler)

    def unsubscribe(self, event_type: Type[BaseEvent], handler: EventHandler) -> None:
        """Remove a previously registered handler."""
        with self._bus_lock:
            if event_type in self._subscribers and handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)

    def publish(self, event: BaseEvent) -> None:
        """
        Publish an event to all matching subscribers synchronously and safely.
        Exceptions in handlers are caught and logged to avoid breaking the publisher.
        """
        with self._bus_lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history.pop(0)

            handlers: list[EventHandler] = []
            # Specific type handlers
            for evt_cls, sub_list in self._subscribers.items():
                if isinstance(event, evt_cls):
                    handlers.extend(sub_list)
            # Catch-all handlers
            handlers.extend(self._any_subscribers)

        # Dispatch outside the lock to prevent deadlocks
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error("Error in event handler %s for %s: %s", getattr(handler, "__name__", str(handler)), event.__class__.__name__, e, exc_info=True)

    def get_recent_events(self, limit: int = 50) -> list[BaseEvent]:
        """Return the most recent events in FIFO order."""
        with self._bus_lock:
            return list(self._history[-limit:])

    def clear(self) -> None:
        """Reset subscribers and history (useful for test isolation)."""
        with self._bus_lock:
            self._subscribers.clear()
            self._any_subscribers.clear()
            self._history.clear()
