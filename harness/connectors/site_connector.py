"""
harness/connectors/site_connector.py — TalentOps Local Web Platform Harness Connector
====================================================================================

Connects the harness to the local TalentOps Web Platform (FastAPI Backend + Vite Frontend):
1. Health & Service Detection: Checks localhost:8000 (Backend) and localhost:5173 (Frontend).
2. Live Candidate & Staging Query: Reads from local SQLite queue or master SQLite databases.
3. Ingestion Dispatch: Passes candidates discovered from external apps into TalentOps pipelines.
4. Browser Navigation: Focuses or opens the TalentOps dashboard in the user's browser.
"""

import os
import sys
import json
import sqlite3
import urllib.request
import logging
from typing import Optional, Dict, Any, List
from harness.connectors.base_connector import BaseConnector

logger = logging.getLogger("harness.site")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [SITE_CONNECTOR] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class SiteConnector(BaseConnector):
    """Master controller for local TalentOps Web Platform integration."""

    DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
    DEFAULT_FRONTEND_URL = "http://localhost:5173"
    LOCAL_QUEUE_DB = r"C:\TalentOpsAI\scout_desktop\local_queue.db"

    def __init__(self, backend_url: Optional[str] = None, frontend_url: Optional[str] = None):
        super().__init__(app_name="site", display_name="TalentOps Web Platform")
        self.backend_url = backend_url or self.DEFAULT_BACKEND_URL
        self.frontend_url = frontend_url or self.DEFAULT_FRONTEND_URL

    # =========================================================================
    # 1. PROCESS & SERVICE DETECTION
    # =========================================================================

    def is_running(self) -> bool:
        """Checks if the local backend server (port 8000) is actively responding."""
        try:
            req = urllib.request.Request(f"{self.backend_url}/docs", headers={"User-Agent": "Harness/1.0"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            # Check if uvicorn process is in process table
            try:
                import psutil
                for p in psutil.process_iter(['name', 'cmdline']):
                    cmd = " ".join(p.info['cmdline'] or [])
                    if "uvicorn" in cmd and "8000" in cmd:
                        return True
            except Exception:
                pass
        return False

    # =========================================================================
    # 2. STATUS & HEALTH
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Returns TalentOps Web Platform health, staged candidate count, and ports."""
        backend_active = False
        frontend_active = False
        queue_count = 0

        # Check backend
        try:
            req = urllib.request.Request(f"{self.backend_url}/docs", headers={"User-Agent": "Harness/1.0"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                backend_active = (resp.status == 200)
        except Exception:
            backend_active = False

        # Check frontend
        try:
            req = urllib.request.Request(self.frontend_url, headers={"User-Agent": "Harness/1.0"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                frontend_active = (resp.status == 200)
        except Exception:
            frontend_active = False

        # Check local queue
        if os.path.exists(self.LOCAL_QUEUE_DB):
            try:
                conn = sqlite3.connect(f"file:{self.LOCAL_QUEUE_DB}?mode=ro", uri=True)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM queued_observations")
                queue_count = cursor.fetchone()[0]
                conn.close()
            except Exception:
                pass

        return {
            "app_name": self.app_name,
            "display_name": self.display_name,
            "is_running": backend_active or frontend_active,
            "backend_active": backend_active,
            "frontend_active": frontend_active,
            "backend_url": self.backend_url,
            "frontend_url": self.frontend_url,
            "staged_observations_count": queue_count,
            "capabilities": ["get_staged_candidates", "ingest_candidate", "bring_to_front"],
        }

    # =========================================================================
    # 3. PIPELINE & CANDIDATE ACCESS
    # =========================================================================

    def get_staged_candidates(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Reads recent staged candidates from local queue."""
        results = []
        if not os.path.exists(self.LOCAL_QUEUE_DB):
            return results

        try:
            conn = sqlite3.connect(f"file:{self.LOCAL_QUEUE_DB}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, cluster_json, created_at FROM queued_observations ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            for r in rows:
                try:
                    data = json.loads(r[1])
                    results.append({
                        "id": r[0],
                        "candidate_name": data.get("recruiter_name") or data.get("name") or "Unnamed",
                        "title": data.get("title") or "Professional",
                        "company": data.get("company") or "Independent",
                        "email": data.get("email") or "",
                        "created_at": r[2]
                    })
                except Exception:
                    continue
            conn.close()
        except Exception as e:
            logger.error("Failed to read staged candidates: %s", e)

        return results

    def bring_to_front(self) -> bool:
        """Opens or restores the TalentOps dashboard in the default browser."""
        try:
            os.startfile(self.frontend_url)
            return True
        except Exception as e:
            logger.error("Failed to open TalentOps web UI: %s", e)
            return False

    def execute_action(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Unified action dispatcher."""
        payload = payload or {}
        if action == "get_staged_candidates":
            candidates = self.get_staged_candidates(limit=payload.get("limit", 5))
            return {"action": action, "success": True, "candidates": candidates}
        elif action == "bring_to_front":
            success = self.bring_to_front()
            return {"action": action, "success": success}
        else:
            return {"action": action, "success": False, "error": f"Unknown action '{action}' for {self.app_name}"}


# Singleton instance
site_connector = SiteConnector()
