"""
harness/command_engine.py — Natural Command & Task Execution Engine
===================================================================

Enables the user to control, command, and request tasks across all connected platforms
(Teams, Outlook, Vitel, TalentOps Web Site, and dynamic plugins).

Supports both structured commands and natural keyword requests:
- outreach <name> [email] [phone] [company]
- email <to> <subject> <body> [--send]
- sms <phone> <message>
- chat <email> [message]
- call <email_or_phone>
- check_inbox [limit]
- check_calls [limit]
- staged_candidates [limit]
- focus <app>
- status
- register_app <key> <name> <category>
"""

import re
import shlex
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("harness.commands")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [COMMAND_ENGINE] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class CommandEngine:
    """Interprets and executes cross-platform tasks across the Harness Hub."""

    def __init__(self, hub=None):
        if hub is None:
            from harness.hub import harness_hub
            self.hub = harness_hub
        else:
            self.hub = hub

    def execute(self, command_line: str) -> Dict[str, Any]:
        """
        Parses and executes a command string.
        Returns a structured dictionary with 'success': bool, 'command': str, 'result': Any, and 'timestamp'.
        """
        raw_cmd = command_line.strip()
        if not raw_cmd:
            return {
                "success": False,
                "command": "",
                "error": "Empty command provided.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        logger.info("Executing command: %s", raw_cmd)

        # 1. Natural Language Normalization
        normalized_cmd, params = self._normalize_command(raw_cmd)

        try:
            handler = getattr(self, f"_handle_{normalized_cmd}", None)
            if handler:
                result = handler(params)
                return {
                    "success": True,
                    "command": normalized_cmd,
                    "raw_input": raw_cmd,
                    "result": result,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            else:
                return {
                    "success": False,
                    "command": normalized_cmd,
                    "raw_input": raw_cmd,
                    "error": f"Unknown command '{normalized_cmd}'. Type 'help' for available commands.",
                    "available_commands": self.get_help_topics(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as e:
            logger.error("Error executing command '%s': %s", raw_cmd, e, exc_info=True)
            return {
                "success": False,
                "command": normalized_cmd,
                "raw_input": raw_cmd,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # =========================================================================
    # PARSING & NORMALIZATION
    # =========================================================================

    def _normalize_command(self, raw: str) -> (str, Dict[str, Any]):
        """Translates free-form requests or CLI commands into standard actions and parameters."""
        raw_lower = raw.lower()

        # Status
        if raw_lower in ["status", "health", "check status", "system status", "show status"]:
            return "status", {}

        # Help
        if raw_lower in ["help", "?", "commands", "list commands"]:
            return "help", {}

        # Check Inbox / Emails
        if "inbox" in raw_lower or "check email" in raw_lower or "read email" in raw_lower:
            limit = 5
            match = re.search(r"\b(\d+)\b", raw)
            if match:
                limit = int(match.group(1))
            return "check_inbox", {"limit": limit}

        # Check Calls / Vitel History
        if "check call" in raw_lower or "call log" in raw_lower or "vitel log" in raw_lower:
            limit = 5
            match = re.search(r"\b(\d+)\b", raw)
            if match:
                limit = int(match.group(1))
            return "check_calls", {"limit": limit}

        # Staged Candidates
        if "staged" in raw_lower or "recent candidates" in raw_lower or "pipeline" in raw_lower:
            limit = 5
            match = re.search(r"\b(\d+)\b", raw)
            if match:
                limit = int(match.group(1))
            return "staged_candidates", {"limit": limit}

        # Focus window
        if raw_lower.startswith("focus ") or raw_lower.startswith("open "):
            parts = raw.split(maxsplit=1)
            target = parts[1].strip() if len(parts) > 1 else ""
            return "focus", {"app": target}

        # Parse CLI tokens for structured commands
        try:
            tokens = shlex.split(raw)
        except Exception:
            tokens = raw.split()

        cmd = tokens[0].lower() if tokens else ""
        args = tokens[1:]

        # Structured command dispatch
        if cmd == "outreach":
            params = {}
            if len(args) >= 1:
                params["name"] = args[0]
            if len(args) >= 2:
                params["email"] = args[1]
            if len(args) >= 3:
                params["phone"] = args[2]
            if len(args) >= 4:
                params["company"] = args[3]
            return "outreach", params

        if cmd == "email":
            params = {
                "to": args[0] if len(args) >= 1 else "",
                "subject": args[1] if len(args) >= 2 else "TalentOps Outreach",
                "body": args[2] if len(args) >= 3 else "",
                "send_now": "--send" in args or "-s" in args,
            }
            return "email", params

        if cmd == "sms":
            params = {
                "phone": args[0] if len(args) >= 1 else "",
                "message": " ".join(args[1:]) if len(args) >= 2 else "",
            }
            return "sms", params

        if cmd == "chat":
            params = {
                "email": args[0] if len(args) >= 1 else "",
                "message": " ".join(args[1:]) if len(args) >= 2 else None,
            }
            return "chat", params

        if cmd == "call":
            params = {
                "target": args[0] if len(args) >= 1 else "",
                "with_video": "--video" in args or "-v" in args,
            }
            return "call", params

        if cmd == "register_app":
            params = {
                "key": args[0] if len(args) >= 1 else "",
                "name": args[1] if len(args) >= 2 else "",
                "category": args[2] if len(args) >= 3 else "General",
                "description": args[3] if len(args) >= 4 else "",
            }
            return "register_app", params

        # Default fallback
        return cmd, {"args": args}

    # =========================================================================
    # COMMAND HANDLERS
    # =========================================================================

    def _handle_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns the full status matrix."""
        return self.hub.get_status_matrix()

    def _handle_help(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns help documentation on all available commands."""
        return {
            "title": "TalentOps Harness Command Console Help",
            "commands": self.get_help_topics()
        }

    def _handle_outreach(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches correlated cross-platform candidate outreach."""
        name = params.get("name", "Candidate")
        candidate_data = {
            "canonical_name": name,
            "email": params.get("email", ""),
            "phone": params.get("phone", ""),
            "company_name": params.get("company", "Organization"),
            "title": params.get("title", "Professional"),
        }
        return self.hub.dispatch_candidate_flow(candidate_data)

    def _handle_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Drafts or sends an email via Outlook connector."""
        outlook = self.hub.get_connector("outlook")
        if not outlook:
            raise RuntimeError("Outlook connector is not registered.")
        
        success = outlook.create_email(
            to_email=params.get("to", ""),
            subject=params.get("subject", ""),
            body_html=f"<p>{params.get('body', '')}</p>",
            send_now=params.get("send_now", False)
        )
        return {
            "action": "email",
            "success": success,
            "recipient": params.get("to"),
            "mode": "sent" if params.get("send_now") else "drafted_in_outlook",
        }

    def _handle_sms(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Stages an SMS outreach via Vitel connector."""
        vitel = self.hub.get_connector("vitel")
        if not vitel:
            raise RuntimeError("Vitel connector is not registered.")
        
        return vitel.prepare_sms(
            phone_number=params.get("phone", ""),
            message=params.get("message", "")
        )

    def _handle_chat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Opens a direct 1-on-1 Teams chat with prefilled message."""
        teams = self.hub.get_connector("teams")
        if not teams:
            raise RuntimeError("Teams connector is not registered.")
        
        success = teams.open_chat(
            recipient_email=params.get("email", ""),
            message=params.get("message")
        )
        return {"action": "chat", "success": success, "recipient": params.get("email")}

    def _handle_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Starts a call in Teams (if email) or Vitel (if phone number)."""
        target = params.get("target", "")
        if "@" in target:
            teams = self.hub.get_connector("teams")
            success = teams.start_call(target, with_video=params.get("with_video", False))
            return {"action": "call", "platform": "teams", "target": target, "success": success}
        else:
            vitel = self.hub.get_connector("vitel")
            success = vitel.dial_number(target)
            return {"action": "call", "platform": "vitel", "target": target, "success": success}

    def _handle_check_inbox(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Reads recent incoming emails from Outlook Inbox."""
        outlook = self.hub.get_connector("outlook")
        if not outlook:
            raise RuntimeError("Outlook connector is not registered.")
        
        emails = outlook.get_recent_emails(limit=params.get("limit", 5))
        return {"count": len(emails), "emails": emails}

    def _handle_check_calls(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Reads recent calls and messages from Vitel event database."""
        vitel = self.hub.get_connector("vitel")
        if not vitel:
            raise RuntimeError("Vitel connector is not registered.")
        
        logs = vitel.get_call_logs(limit=params.get("limit", 5))
        return {"count": len(logs), "call_logs": logs}

    def _handle_staged_candidates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Reads recently staged candidate observations from the TalentOps Web Platform."""
        site = self.hub.get_connector("site")
        if not site:
            raise RuntimeError("Site connector is not registered.")
        
        candidates = site.get_staged_candidates(limit=params.get("limit", 5))
        return {"count": len(candidates), "staged_candidates": candidates}

    def _handle_focus(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Brings an application window to the foreground."""
        app_name = params.get("app", "").lower()
        success = self.hub.bring_to_front(app_name)
        return {"action": "focus", "app": app_name, "success": success}

    def _handle_register_app(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Registers an upcoming app definition."""
        key = params.get("key", "").lower()
        if not key:
            raise ValueError("App key is required.")
        metadata = {
            "name": params.get("name", key.capitalize()),
            "category": params.get("category", "General"),
            "description": params.get("description", ""),
            "status": "planned"
        }
        self.hub.register_upcoming_app(key, metadata)
        return {"action": "register_app", "registered": key, "metadata": metadata}

    def get_help_topics(self) -> Dict[str, str]:
        """Returns command syntax reference."""
        return {
            "status": "Check health & running state of all connected apps and upcoming plugins.",
            "outreach <name> <email> <phone> <company>": "Run unified multi-app outreach across Teams, Outlook, and Vitel.",
            "email <to> <subject> <body> [--send]": "Draft or send an email directly via Microsoft Outlook COM.",
            "sms <phone> <message>": "Format and stage an SMS outreach message in Vitel Global.",
            "chat <email> [message]": "Open a direct 1-on-1 Teams chat with prefilled message.",
            "call <target> [--video]": "Trigger a call via Teams (email) or Vitel (phone number).",
            "check_inbox [limit]": "Read recent incoming emails and candidate replies from Outlook Inbox.",
            "check_calls [limit]": "Read recent call and messaging history from Vitel local database.",
            "staged_candidates [limit]": "Read recently staged candidates from TalentOps Web Platform.",
            "focus <teams|outlook|vitel|site>": "Bring application window to the front.",
            "register_app <key> <name> <category> [description]": "Dynamically register an upcoming app.",
        }


# Singleton instance
command_engine = CommandEngine()
