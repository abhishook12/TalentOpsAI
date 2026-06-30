"""App configuration from environment variables."""
import os
import logging

logger = logging.getLogger("talentops")

from dotenv import load_dotenv
load_dotenv()

ENV = os.getenv("ENV", "development").lower()
IS_RENDER = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID") or os.getenv("RENDER_EXTERNAL_URL"))
IS_STAGING = ENV == "staging"
IS_PRODUCTION = (ENV in ("production", "prod") or IS_RENDER) and not IS_STAGING

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-jwt-key-talentops")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1012")
APP_PASSWORD = os.getenv("APP_PASSWORD") or ADMIN_PASSWORD
FREE_ADMIN_MODE = os.getenv("FREE_ADMIN_MODE", "true").lower() in ("1", "true", "yes", "on")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
TAVILY_API_KEYS = [k.strip() for k in os.environ.get("TAVILY_API_KEYS", "").split(",") if k.strip()]
HUNTER_API_KEY = os.environ.get("HUNTER_API_KEY")

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "https://talent-ops-ai.vercel.app,https://talent-ops-ai-staging.vercel.app,http://localhost:5173,http://127.0.0.1:5173,https://94334d6e-bbcd-4b1a-91a7-46d8884e20ea.lovableproject.com",
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
if FREE_ADMIN_MODE:
    logger.warning("FREE_ADMIN_MODE is enabled: admin endpoints are temporarily open without auth.")
