"""
TalentOps Scout 2.0 - Base Connector Architecture
Defines the standard contract for scope-aware edge connectors.
Ensures zero unauthorized scraping, strict boundary adherence,
and normalized entity extraction.
"""

from __future__ import annotations

import abc
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("scout.connectors.base")


class BaseConnector(abc.ABC):
    """
    Standard interface for Scout 2.0 observation connectors.
    Connectors inspect authorized window/browser contexts, filter by allowed scopes,
    and yield structured, normalized observations.
    """

    def __init__(self, name: str, allowed_domains: Optional[list[str]] = None) -> None:
        self.name = name
        self.allowed_domains = allowed_domains or []
        self._enabled = True

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @abc.abstractmethod
    def is_scope_authorized(self, context: dict[str, Any]) -> bool:
        """
        Verify if the given browser/window context is strictly authorized
        under the connector's enterprise policy and domain scope.
        """
        pass

    @abc.abstractmethod
    def discover(self, context: dict[str, Any]) -> bool:
        """
        Fast evaluation: returns True if this connector handles the context.
        """
        pass

    @abc.abstractmethod
    def capture_and_extract(self, context: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        Extract normalized observation data from context.
        Returns None if no actionable intelligence is discovered.
        """
        pass

    @abc.abstractmethod
    def checkpoint(self) -> dict[str, Any]:
        """
        Return connector state metrics (e.g. observations count, errors, last seen).
        """
        pass
