"""TalentOps AI - Autonomous Security & Self-Healing Sentinel.

Runs 100% server-side with zero manual maintenance required.
Automatically blocks malicious web scanners, exploit probes, and brute-force attacks,
recording alerts directly to Sentry and auto-reviving healthy states.
"""

import time
import logging
from typing import Dict, Set, Tuple
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .sentry import capture_security_alert

logger = logging.getLogger("talentops.security_sentinel")

# Malicious path and scanner patterns
BLOCKED_PATH_PATTERNS = (
    "/.env", "/.git", "/wp-admin", "/wp-login", "/phpmyadmin", "/xmlrpc.php",
    "/.aws", "/id_rsa", "/etc/passwd", "/win.ini", "/cgi-bin", "/.well-known/security.txt",
    "/telescope", "/actuator/health", "/boaform"
)

# Attack signatures in query strings or paths
BLOCKED_PAYLOAD_SIGNATURES = (
    "../", "..\\", "union select", "<script", "onload=", "onerror=",
    "cmd.exe", "/bin/sh", "/bin/bash", "eval(", "base64_decode("
)

class SecuritySentinel:
    def __init__(self):
        # ip -> ban_expiry_timestamp
        self._banned_ips: Dict[str, float] = {}
        # ip -> list of failed attempt timestamps
        self._login_failures: Dict[str, list] = {}
        # Metrics for autonomous tracking
        self.stats = {
            "probes_blocked": 0,
            "brute_force_blocked": 0,
            "active_bans": 0,
            "started_at": time.time(),
        }

    def is_ip_banned(self, ip: str) -> bool:
        """Check if an IP is actively banned; clean up if expired."""
        now = time.time()
        expiry = self._banned_ips.get(ip)
        if expiry:
            if now < expiry:
                return True
            else:
                del self._banned_ips[ip]
        return False

    def ban_ip(self, ip: str, duration_seconds: int = 900, reason: str = "malicious_activity"):
        """Ban an IP for a specified duration (default: 15 minutes)."""
        if ip in ("127.0.0.1", "localhost", "::1"):
            # Never ban local development host
            return
        self._banned_ips[ip] = time.time() + duration_seconds
        self.stats["active_bans"] = len(self._banned_ips)
        logger.warning("🚨 [SECURITY SENTINEL] Auto-banned IP %s for %ds. Reason: %s", ip, duration_seconds, reason)
        capture_security_alert(
            f"Autonomous IP Ban: {ip}",
            details={"ip": ip, "duration": duration_seconds, "reason": reason}
        )

    def record_login_failure(self, ip: str) -> bool:
        """Track login failures. Ban if > 5 failures in 300 seconds."""
        now = time.time()
        failures = self._login_failures.setdefault(ip, [])
        # Keep only failures in last 300s (5 minutes)
        failures = [t for t in failures if now - t < 300]
        failures.append(now)
        self._login_failures[ip] = failures

        if len(failures) >= 5:
            self.stats["brute_force_blocked"] += 1
            self.ban_ip(ip, duration_seconds=1800, reason="excessive_login_failures")
            return True
        return False

    def inspect_request(self, ip: str, path: str, query: str) -> Tuple[bool, str]:
        """Inspect request against attack signatures. Returns (is_malicious, reason)."""
        # 1. Check if IP is already banned
        if self.is_ip_banned(ip):
            return True, "IP is actively banned by security sentinel"

        path_lower = path.lower()
        query_lower = query.lower() if query else ""

        # 2. Check for scanner probe paths
        for blocked_path in BLOCKED_PATH_PATTERNS:
            if blocked_path in path_lower:
                self.stats["probes_blocked"] += 1
                self.ban_ip(ip, duration_seconds=900, reason=f"scanner_probe: {blocked_path}")
                return True, f"Blocked vulnerability probe: {blocked_path}"

        # 3. Check for attack signatures
        full_req = f"{path_lower}?{query_lower}"
        for sig in BLOCKED_PAYLOAD_SIGNATURES:
            if sig in full_req:
                self.stats["probes_blocked"] += 1
                self.ban_ip(ip, duration_seconds=1800, reason=f"exploit_signature: {sig}")
                return True, f"Blocked attack signature: {sig}"

        return False, ""

    def get_status(self) -> dict:
        now = time.time()
        active_bans = [ip for ip, exp in self._banned_ips.items() if exp > now]
        return {
            "status": "operational",
            "uptime_seconds": int(now - self.stats["started_at"]),
            "probes_blocked_count": self.stats["probes_blocked"],
            "brute_force_blocked_count": self.stats["brute_force_blocked"],
            "active_banned_ips_count": len(active_bans),
        }

# Global autonomous instance
security_sentinel = SecuritySentinel()

class AutonomousSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from .limiter import get_client_ip
        client_ip = get_client_ip(request)
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""

        # Autonomous inspection
        is_malicious, reason = security_sentinel.inspect_request(client_ip, path, query)
        if is_malicious:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "detail": "Request rejected by TalentOps Autonomous Security Sentinel",
                    "reason": reason
                }
            )

        response = await call_next(request)
        return response
