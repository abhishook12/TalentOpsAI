"""
harness/__init__.py — TalentOps Multi-Platform Local Automation Harness
"""
from harness.hub import HarnessHub, harness_hub
from harness.connectors import (
    BaseConnector,
    TeamsConnector,
    teams_connector,
    OutlookConnector,
    outlook_connector,
    VitelConnector,
    vitel_connector,
    SiteConnector,
    site_connector,
)

__all__ = [
    "HarnessHub",
    "harness_hub",
    "BaseConnector",
    "TeamsConnector",
    "teams_connector",
    "OutlookConnector",
    "outlook_connector",
    "VitelConnector",
    "vitel_connector",
    "SiteConnector",
    "site_connector",
]
