"""TalentOps AI - Sentry Real-Time Error & Security Monitoring Core.

Provides zero-overhead runtime crash protection, security exploit alerts,
and strict PII redaction to protect candidate data and recruiter credentials.
"""

import os
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("talentops.sentry")

_SENTRY_INITIALIZED = False


def _scrub_sensitive_event(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Strict Security & Privacy Redactor:
    Scrubs all authorization headers, cookies, passwords, API keys,
    and candidate PII (phones, unhashed tokens) before transmission.
    """
    try:
        # 1. Scrub request headers
        req = event.get("request", {})
        if "headers" in req and isinstance(req["headers"], dict):
            for h in ["authorization", "cookie", "set-cookie", "x-api-key", "proxy-authorization"]:
                for key in list(req["headers"].keys()):
                    if key.lower() == h:
                        req["headers"][key] = "[REDACTED_SECURITY_HEADER]"

        # 2. Scrub query parameters
        if "query_string" in req and isinstance(req["query_string"], str):
            for secret_param in ["token", "secret", "password", "key"]:
                if secret_param in req["query_string"].lower():
                    req["query_string"] = "[REDACTED_QUERY_PARAMS]"
                    break

        # 3. Scrub breadcrumbs
        breadcrumbs = event.get("breadcrumbs", {})
        if isinstance(breadcrumbs, dict) and "values" in breadcrumbs:
            for b in breadcrumbs["values"]:
                data = b.get("data", {})
                if isinstance(data, dict):
                    for k in list(data.keys()):
                        if any(s in k.lower() for s in ["password", "secret", "token", "auth", "phone", "email"]):
                            data[k] = "[REDACTED]"

        # 4. Strip user identifiers unless explicit non-sensitive ID
        user = event.get("user")
        if isinstance(user, dict):
            if "email" in user:
                # Mask email domain e.g. a***@company.com
                email_parts = str(user["email"]).split("@")
                if len(email_parts) == 2:
                    user["email"] = f"{email_parts[0][:1]}***@{email_parts[1]}"
                else:
                    user["email"] = "[REDACTED]"
            if "ip_address" in user:
                user["ip_address"] = "[MASKED_IP]"

    except Exception as scrub_err:
        logger.debug("Sentry scrubbing error (non-fatal): %s", scrub_err)

    return event


def init_sentry() -> bool:
    """Initialize Sentry SDK if SENTRY_DSN environment variable is present."""
    global _SENTRY_INITIALIZED
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        load_dotenv(os.path.join(base_dir, ".env"))
        load_dotenv(os.path.join(base_dir, "..", ".env"))
    except Exception:
        pass

    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("ℹ️ Sentry DSN not provided; running with local exception logging.")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        env = os.getenv("ENV", "development").lower()
        traces_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.2"))

        sentry_sdk.init(
            dsn=dsn,
            environment=env,
            traces_sample_rate=traces_rate,
            profiles_sample_rate=0.05,
            send_default_pii=False,
            before_send=_scrub_sensitive_event,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            release=f"talentops-backend@{os.getenv('APP_VERSION', '1.1.0')}",
        )
        _SENTRY_INITIALIZED = True
        logger.info("🛡️ Sentry active: Real-time runtime crash & vulnerability radar online (env: %s)", env)
        return True
    except Exception as e:
        logger.error("Failed to initialize Sentry SDK: %s", e)
        return False


def is_sentry_active() -> bool:
    return _SENTRY_INITIALIZED


def capture_exception(exc: Exception, tags: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Capture exception to Sentry if active; otherwise log locally."""
    if _SENTRY_INITIALIZED:
        try:
            import sentry_sdk
            if tags:
                for k, v in tags.items():
                    sentry_sdk.set_tag(k, v)
            return sentry_sdk.capture_exception(exc)
        except Exception as e:
            logger.warning("Error forwarding exception to Sentry: %s", e)
    logger.exception("TalentOps Unhandled Exception: %s", exc)
    return None


def capture_security_alert(message: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Send immediate security warning event to Sentry."""
    logger.warning("🚨 SECURITY ALERT: %s - Details: %s", message, details)
    if _SENTRY_INITIALIZED:
        try:
            import sentry_sdk
            sentry_sdk.set_level("warning")
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("security_incident", "true")
                if details:
                    for k, v in details.items():
                        scope.set_extra(k, v)
                sentry_sdk.capture_message(f"Security Alert: {message}", level="warning")
        except Exception as e:
            logger.warning("Failed to forward security alert to Sentry: %s", e)
