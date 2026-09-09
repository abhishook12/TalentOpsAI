"""
TalentOps Scout 2.0 - Connectors Package
"""

from .base import BaseConnector
from .linkedin import LinkedInConnector

__all__ = ["BaseConnector", "LinkedInConnector"]
