"""
harness/connectors/__init__.py — Registry of all Platform Connectors
"""
from harness.connectors.base_connector import BaseConnector
from harness.connectors.teams_connector import TeamsConnector, teams_connector
from harness.connectors.outlook_connector import OutlookConnector, outlook_connector
from harness.connectors.vitel_connector import VitelConnector, vitel_connector
from harness.connectors.site_connector import SiteConnector, site_connector

__all__ = [
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
