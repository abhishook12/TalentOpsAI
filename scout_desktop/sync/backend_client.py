"""
sync/backend_client.py — Secure TalentOps Backend REST Integration Client

Communicates with the TalentOps backend:
- Auto-probes local dev backend (http://localhost:8000) with fallback to production.
- Manages device activation & JWT token handling.
- Sends rich heartbeat telemetry to /scout/heartbeat.
- Flushes staged batches to /recruiters/extension/batch with payload optimization.
"""

import os
import sys
import json
import gzip
import logging
import time
import uuid
from typing import Optional, Dict, Any, List, Tuple
import requests

logger = logging.getLogger("scout.backend_client")

DEFAULT_PRODUCTION_API = "https://talentopsai-1.onrender.com"
DEFAULT_LOCAL_API = "http://localhost:8000"


class BackendClient:
    def __init__(
        self,
        api_base: Optional[str] = None,
        device_id: str = "DESKTOP-SCOUT-WIN",
        scout_id: str = "SCOUT-NODE-01",
        config_path: Optional[str] = None,
    ):
        self.device_id = device_id
        self.scout_id = scout_id
        self.user_id = 1
        self.session_id = f"SESS-{uuid.uuid4().hex[:8].upper()}"
        self.config_path = config_path or os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
        self.auth_token: Optional[str] = None
        self.last_request_time: str = "—"
        self.last_response_status: str = "—"
        self.last_db_write_time: str = "—"
        self.last_db_write_result: str = "—"
        self.last_backend_response: Dict[str, Any] = {}

        self.active_api_base = api_base or self._resolve_api_base()
        self.base_url = self.active_api_base
        self.environment_name = "PRODUCTION" if "onrender.com" in self.active_api_base else "LOCAL DEVELOPMENT"

        self._load_token_from_config()

    def set_environment(self, env_type: str):
        """Switches environment between 'PRODUCTION' and 'LOCAL'."""
        if env_type.upper() == "LOCAL":
            self.active_api_base = DEFAULT_LOCAL_API
            self.environment_name = "LOCAL DEVELOPMENT"
        else:
            self.active_api_base = DEFAULT_PRODUCTION_API
            self.environment_name = "PRODUCTION"
        self.base_url = self.active_api_base
        self.auth_token = None
        self._load_token_from_config()
        logger.info("Switched backend target to %s (%s)", self.environment_name, self.active_api_base)

    def _resolve_api_base(self) -> str:
        """Resolves target backend from config (defaults to PRODUCTION)."""
        cfg_env = "PRODUCTION"
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cfg_env = data.get("environment", "PRODUCTION").upper()
                    if cfg_env == "LOCAL":
                        return data.get("local_api_base", DEFAULT_LOCAL_API)
                    elif data.get("api_base"):
                        return data.get("api_base")
            except Exception:
                pass

        return DEFAULT_PRODUCTION_API

    def _load_token_from_config(self):
        """Loads saved auth token if present."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.auth_token = data.get("auth_token") or None
            except Exception:
                pass

    def _save_credentials_to_config(self, token: str, scout_id: Optional[str] = None, user_email: Optional[str] = None, user_name: Optional[str] = None):
        self.auth_token = token
        if scout_id:
            self.scout_id = scout_id
        try:
            data = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["auth_token"] = token
            if scout_id:
                data["scout_id"] = scout_id
            if user_email:
                data["user_email"] = user_email
            if user_name:
                data["user_name"] = user_name
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug("Failed to persist credentials: %s", e)

    def _save_token_to_config(self, token: str):
        self._save_credentials_to_config(token)

    def is_authenticated(self) -> bool:
        """Returns True if device has a stored authentication token."""
        return bool(self.auth_token)

    def activate_with_code(self, activation_code: str, hostname: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Activates this Scout Desktop instance using a short-lived code (TOS-XXXX-XXXX).
        Saves issued JWT token, scout_id, and user metadata to config.
        """
        url = f"{self.active_api_base}/scout/activate"
        host = hostname or os.environ.get("COMPUTERNAME", "Windows Desktop")
        payload = {
            "activation_code": activation_code.strip(),
            "device_id": self.device_id,
            "hostname": host,
            "os_info": sys.platform,
            "scout_version": "2.0.0",
        }

        try:
            res = requests.post(url, json=payload, timeout=10.0)
            data = res.json() if res.content else {}
            if res.status_code == 200 and data.get("access_token"):
                token = data["access_token"]
                scout_id = data.get("scout_id", self.scout_id)
                u_email = data.get("user_email")
                u_name = data.get("user_name")
                self._save_credentials_to_config(token, scout_id=scout_id, user_email=u_email, user_name=u_name)
                logger.info("🎉 Scout Desktop successfully activated via code! scout_id=%s user=%s", scout_id, u_email)
                return True, data
            else:
                err_msg = data.get("detail") or f"Activation failed (HTTP {res.status_code})"
                return False, {"error": err_msg}
        except Exception as e:
            logger.warning("Activation request error: %s", e)
            return False, {"error": f"Connection error: {e}"}

    def ensure_authenticated(self) -> bool:
        """Auto-activates device to acquire valid JWT token if needed."""
        if self.auth_token:
            return True

        url = f"{self.active_api_base}/recruiters/extension/auto-activate"
        payload = {
            "device_id": self.device_id,
            "browser_info": "TalentOps Scout Desktop / Windows Native",
            "extension_version": "2.0.0-desktop",
        }
        try:
            res = requests.post(url, json=payload, timeout=5.0)
            if res.status_code == 200:
                token = res.json().get("access_token")
                if token:
                    self._save_token_to_config(token)
                    logger.info("⚡ Scout Desktop successfully activated with backend!")
                    return True
        except Exception as e:
            logger.warning("Auto-activation request failed: %s", e)
        return False

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-Device-Id": self.device_id,
            "X-Extension-Version": "1.0.0-desktop",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def send_heartbeat(
        self,
        page_url: Optional[str] = None,
        capture_id: Optional[str] = None,
        client_metrics: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Sends heartbeat telemetry to /scout/heartbeat."""
        if not self.ensure_authenticated():
            return False, {"error": "unauthenticated"}

        url = f"{self.active_api_base}/scout/heartbeat"
        metrics = dict(client_metrics or {})
        if status:
            metrics["status"] = status

        payload = {
            "device_id": self.device_id,
            "page_url": page_url,
            "capture_id": capture_id,
            "client_metrics": {
                "scout_id": self.scout_id,
                "version": "2.0.0",
                "platform": sys.platform,
                **metrics,
                "timestamp": time.time(),
            },
        }
        try:
            res = requests.post(url, json=payload, headers=self._get_headers(), timeout=4.0)
            if res.status_code == 401:
                logger.info("Heartbeat received 401; auto-reactivating device...")
                self.auth_token = None
                if self.ensure_authenticated():
                    res = requests.post(url, json=payload, headers=self._get_headers(), timeout=4.0)
            if res.status_code == 200:
                try:
                    return True, res.json()
                except Exception:
                    return True, {"status": "ok"}
            return False, {"error": f"HTTP {res.status_code}"}
        except Exception as e:
            logger.debug("Heartbeat ping failed: %s", e)
            return False, {"error": str(e)}

    def lookup_candidate(
        self,
        name: Optional[str] = None,
        company: Optional[str] = None,
        linkedin: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Queries backend copilot endpoint to check if candidate is already in TalentOps.
        Returns candidate match dict if found or None.
        """
        if not self.ensure_authenticated():
            return None

        url = f"{self.active_api_base}/scout/copilot/lookup"
        params = {}
        if name:
            params["name"] = name
        if company:
            params["company"] = company
        if linkedin:
            params["linkedin"] = linkedin
        if email:
            params["email"] = email

        try:
            res = requests.get(url, params=params, headers=self._get_headers(), timeout=3.5)
            if res.status_code == 200:
                data = res.json()
                if data.get("found"):
                    return data
        except Exception as e:
            logger.debug("Copilot lookup error: %s", e)
        return None

    def sync_staged_batch(
        self,
        contacts: List[Dict[str, Any]],
        session_stats: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Submits candidate batch to /recruiters/extension/batch.
        Uses automatic gzip compression for payloads larger than 8KB.
        Returns (success: bool, response_dict).
        """
        if not contacts:
            return True, {"staged": 0}
        if not self.ensure_authenticated():
            return False, {"error": "unauthenticated"}

        url = f"{self.active_api_base}/scout/ingest/batch"
        fallback_url = f"{self.active_api_base}/recruiters/extension/batch"
        payload = {
            "device_id": self.device_id,
            "contacts": contacts,
            "session_stats": session_stats or {},
        }

        try:
            self.last_request_time = time.strftime("%H:%M:%S")
            headers = self._get_headers()
            raw_data = json.dumps(payload).encode("utf-8")

            # Gzip compress if large
            target_url = url
            if len(raw_data) > 8192:
                compressed_data = gzip.compress(raw_data)
                headers["Content-Encoding"] = "gzip"
                headers["Content-Length"] = str(len(compressed_data))
                res = requests.post(target_url, data=compressed_data, headers=headers, timeout=30.0)
                if res.status_code == 404:
                    target_url = fallback_url
                    res = requests.post(target_url, data=compressed_data, headers=headers, timeout=30.0)
                if res.status_code in [415, 400]:
                    headers.pop("Content-Encoding", None)
                    headers.pop("Content-Length", None)
                    res = requests.post(target_url, json=payload, headers=headers, timeout=30.0)
            else:
                res = requests.post(target_url, json=payload, headers=headers, timeout=30.0)
                if res.status_code == 404:
                    target_url = fallback_url
                    res = requests.post(target_url, json=payload, headers=headers, timeout=30.0)

            if res.status_code == 403:
                logger.warning("🚨 Device access REVOKED by backend (HTTP 403). Disabling auto-retry.")
                self.last_response_status = "REVOKED (HTTP 403)"
                self.last_db_write_result = "ACCESS REVOKED"
                return False, {"error": "device_revoked", "detail": "Device access revoked by administrator"}

            if res.status_code == 401:
                logger.info("Batch staging received 401; auto-reactivating device and retrying...")
                self.auth_token = None
                if self.ensure_authenticated():
                    res = requests.post(target_url, json=payload, headers=self._get_headers(), timeout=30.0)

            if res.status_code == 200:
                data = res.json()
                self.last_response_status = f"{data.get('status', 'SUCCESS')} (HTTP 200)"
                self.last_db_write_time = time.strftime("%H:%M:%S")
                staged = data.get("staged", 0)
                rels = data.get("knowledge_graph_stats", {}).get("relationships_created", 0)
                self.last_db_write_result = f"SUCCESS (Staged: {staged}, Relations: {rels})"
                self.last_backend_response = data
                logger.info("✅ Batch staged to backend successfully (Staged: %s)", staged)
                return True, data
            else:
                self.last_response_status = f"ERROR (HTTP {res.status_code})"
                self.last_db_write_result = f"FAILED: HTTP {res.status_code}"
                logger.warning("Batch upload returned HTTP %d: %s", res.status_code, res.text[:100])
                return False, {"error": f"HTTP_{res.status_code}"}
        except Exception as e:
            self.last_response_status = "NETWORK ERROR"
            self.last_db_write_result = f"FAILED: {e}"
            logger.warning("Batch sync network error: %s", e)
            return False, {"error": str(e)}
