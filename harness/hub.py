"""
harness/hub.py — Unified Controller & Extensible Multi-Platform Harness Hub
===========================================================================

Coordinates all local application connectors (Teams, Outlook, Vitel, TalentOps Web Site)
and provides an extensible registry for upcoming platform integrations.

Features:
1. Dynamic Connector Registry: Register any future app without modifying core engine.
2. Status Matrix: One-call health inspection across all connected desktop platforms.
3. Unified Multi-App Workflow: Executes correlated candidate outreach across
   Site -> Teams -> Outlook -> Vitel in a single flow.
"""

import os
import sys
import logging
import urllib.parse
from typing import Dict, Any, List, Optional

from harness.connectors.base_connector import BaseConnector
from harness.connectors.teams_connector import teams_connector, TeamsConnector
from harness.connectors.outlook_connector import outlook_connector, OutlookConnector
from harness.connectors.vitel_connector import vitel_connector, VitelConnector
from harness.connectors.site_connector import site_connector, SiteConnector

logger = logging.getLogger("harness.hub")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [HARNESS_HUB] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class HarnessHub:
    """Central Controller and Extensible Orchestrator for all Local Platform Connectors."""

    def __init__(self):
        # Register core native connectors
        self._connectors: Dict[str, BaseConnector] = {
            "teams": teams_connector,
            "outlook": outlook_connector,
            "vitel": vitel_connector,
            "site": site_connector,
        }

        # Registry for upcoming platforms
        self._upcoming_apps: Dict[str, Dict[str, Any]] = {
            "whatsapp": {
                "name": "WhatsApp Business",
                "category": "Messaging",
                "status": "planned",
                "description": "Desktop WhatsApp for candidate instant messaging via whatsapp:// protocol.",
            },
            "ringcentral": {
                "name": "RingCentral",
                "category": "VoIP / Calling",
                "status": "planned",
                "description": "Softphone dialer integration via rcapp:// protocol.",
            },
            "slack": {
                "name": "Slack Desktop",
                "category": "Team Collaboration",
                "status": "planned",
                "description": "Channel notifications & recruiter huddle dispatch via slack:// protocol.",
            },
        }

    # =========================================================================
    # 1. EXTENSIBLE CONNECTOR REGISTRY
    # =========================================================================

    def register_connector(self, name: str, connector: BaseConnector) -> None:
        """Registers a new connector dynamically at runtime."""
        if not isinstance(connector, BaseConnector):
            raise TypeError("Connector must inherit from BaseConnector")
        self._connectors[name.lower()] = connector
        if name.lower() in self._upcoming_apps:
            del self._upcoming_apps[name.lower()]
        logger.info("Registered new connector: '%s' (%s)", name, connector.display_name)

    def register_upcoming_app(self, key: str, metadata: Dict[str, Any]) -> None:
        """Adds an upcoming application specification to the harness roadmap."""
        self._upcoming_apps[key.lower()] = metadata
        logger.info("Registered upcoming app: '%s'", metadata.get("name", key))

    def get_connector(self, name: str) -> Optional[BaseConnector]:
        """Returns the connector for the specified platform."""
        return self._connectors.get(name.lower())

    def list_connectors(self) -> List[str]:
        """Returns all registered connector names."""
        return list(self._connectors.keys())

    # =========================================================================
    # 2. STATUS MATRIX (ONE-CALL HEALTH CHECK)
    # =========================================================================

    def get_status_matrix(self) -> Dict[str, Any]:
        """
        Gathers live status, running state, and capabilities for every
        connected app, the local site, and upcoming planned integrations.
        """
        connected_status = {}
        for name, connector in self._connectors.items():
            try:
                connected_status[name] = connector.get_status()
            except Exception as e:
                connected_status[name] = {
                    "app_name": name,
                    "display_name": connector.display_name,
                    "is_running": False,
                    "error": str(e),
                }

        total_active = sum(1 for s in connected_status.values() if s.get("is_running", False))

        return {
            "summary": {
                "total_connected_apps": len(self._connectors),
                "active_apps_count": total_active,
                "upcoming_apps_count": len(self._upcoming_apps),
            },
            "apps": connected_status,
            "upcoming": self._upcoming_apps,
        }

    # =========================================================================
    # 3. UNIFIED CROSS-APP WORKFLOW
    # =========================================================================

    def dispatch_candidate_flow(
        self,
        candidate_data: Dict[str, Any],
        targets: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Executes a correlated multi-app outreach flow for a candidate:
        - Teams: Publishes Candidate Dossier Card to channel or generates recruiter chat.
        - Outlook: Drafts personalized pitch email in Outlook Drafts.
        - Vitel: Prepares SMS outreach payload.
        - Site: Verifies staging status.
        """
        targets = targets or ["teams", "outlook", "vitel"]
        name = candidate_data.get("canonical_name") or candidate_data.get("recruiter_name") or "Candidate"
        email = candidate_data.get("email") or candidate_data.get("primary_email") or ""
        phone = candidate_data.get("phone") or candidate_data.get("primary_phone") or ""
        title = candidate_data.get("title") or "Professional"
        company = candidate_data.get("company_name") or candidate_data.get("company") or "Global Tech"

        flow_results = {
            "candidate": name,
            "company": company,
            "actions": {},
            "success": True,
        }

        # 1. Teams Action
        if "teams" in targets and "teams" in self._connectors:
            try:
                teams_conn: TeamsConnector = self._connectors["teams"]  # type: ignore
                card_ready = teams_conn.send_candidate_card(
                    candidate_data=candidate_data,
                    webhook_url=os.getenv("TEAMS_WEBHOOK_URL", "")
                )
                flow_results["actions"]["teams"] = {
                    "action": "candidate_card",
                    "success": True,
                    "note": "Card dispatched" if card_ready else "Card generated (No webhook URL set, deep-link ready)",
                    "chat_link": f"msteams:/l/chat/0/0?users={email}&message=Review+{urllib.parse.quote(name)}+from+{urllib.parse.quote(company)}" if email else None
                }
            except Exception as e:
                flow_results["actions"]["teams"] = {"success": False, "error": str(e)}

        # 2. Outlook Action
        if "outlook" in targets and "outlook" in self._connectors and email:
            try:
                outlook_conn: OutlookConnector = self._connectors["outlook"]  # type: ignore
                subject = f"Exciting Opportunity for {name} ({title} @ {company})"
                body_html = f"""
                <p>Hi {name.split()[0] if name else 'there'},</p>
                <p>I came across your background as {title} at {company} through our TalentOps network.</p>
                <p>We are currently representing an opportunity that closely matches your profile. Would you be open to connecting?</p>
                <p>Best regards,<br>TalentOps Recruitment Team</p>
                """
                drafted = outlook_conn.create_email(
                    to_email=email,
                    subject=subject,
                    body_html=body_html,
                    send_now=False
                )
                flow_results["actions"]["outlook"] = {
                    "action": "draft_email",
                    "success": drafted,
                    "recipient": email,
                    "subject": subject
                }
            except Exception as e:
                flow_results["actions"]["outlook"] = {"success": False, "error": str(e)}

        # 3. Vitel Action
        if "vitel" in targets and "vitel" in self._connectors and phone:
            try:
                vitel_conn: VitelConnector = self._connectors["vitel"]  # type: ignore
                sms_text = f"Hi {name.split()[0]}, this is TalentOps following up regarding an open {title} opportunity."
                sms_res = vitel_conn.prepare_sms(phone_number=phone, message=sms_text)
                flow_results["actions"]["vitel"] = {
                    "action": "prepare_sms",
                    "success": sms_res.get("success", False),
                    "recipient": sms_res.get("recipient"),
                    "message": sms_text
                }
            except Exception as e:
                flow_results["actions"]["vitel"] = {"success": False, "error": str(e)}

        logger.info("Unified candidate outreach flow completed for '%s'", name)
        return flow_results

    # =========================================================================
    # 4. FOCUS MANAGEMENT
    # =========================================================================

    def bring_to_front(self, app_name: str) -> bool:
        """Restores and focuses the specified application window."""
        connector = self.get_connector(app_name)
        if connector:
            return connector.bring_to_front()
        return False


# Singleton instance
harness_hub = HarnessHub()
