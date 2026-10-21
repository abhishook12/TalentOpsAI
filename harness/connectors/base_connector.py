"""
harness/connectors/base_connector.py — Base Abstract Connector for TalentOps Harness
===================================================================================

Defines the standard interface that all platform connectors (Teams, Outlook, Vitel,
TalentOps Site, and future plugins) must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("harness.base")


class BaseConnector(ABC):
    """Abstract Base Class for all Harness Connectors."""

    def __init__(self, app_name: str, display_name: str):
        self.app_name = app_name
        self.display_name = display_name
        self.logger = logging.getLogger(f"harness.{app_name}")

    @abstractmethod
    def is_running(self) -> bool:
        """Returns True if the application process or service is currently active."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Returns a dictionary summarizing the application's runtime status,
        connectivity, active accounts, and capabilities.
        """
        pass

    @abstractmethod
    def bring_to_front(self) -> bool:
        """Restores and focuses the application's main window."""
        pass

    @abstractmethod
    def execute_action(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a platform-specific command or workflow action.
        Returns a result dictionary with 'success': bool and action details.
        """
        pass
