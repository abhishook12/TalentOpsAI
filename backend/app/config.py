"""App configuration from environment variables."""
import os
import logging

logger = logging.getLogger("talentops")

ENV = os.getenv("ENV", "development").lower()
IS_RENDER = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID") or os.getenv("RENDER_EXTERNAL_URL"))
IS_PRODUCTION = ENV in ("production", "prod") or IS_RENDER

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-jwt-key-talentops")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1012")
APP_PASSWORD = os.getenv("APP_PASSWORD") or ADMIN_PASSWORD

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "https://talent-ops-ai.vercel.app,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]

if IS_PRODUCTION:
    if not os.getenv("JWT_SECRET") or JWT_SECRET.startswith("super-secret"):
        raise RuntimeError("Set a strong JWT_SECRET in production (Render env vars).")
    if not os.getenv("ADMIN_PASSWORD"):
        raise RuntimeError("Set ADMIN_PASSWORD in production (Render env vars).")
else:
    if JWT_SECRET.startswith("super-secret") or ADMIN_PASSWORD == "1012" or APP_PASSWORD == "1012":
        logger.warning(
            "Using default dev secrets — set JWT_SECRET and ADMIN_PASSWORD in .env before deploying."
        )
