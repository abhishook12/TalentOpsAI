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
DEV_AUTO_VERIFY = os.getenv("DEV_AUTO_VERIFY", "true").lower() in ("1", "true", "yes", "on") and not IS_PRODUCTION

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
TAVILY_API_KEYS = [k.strip() for k in os.environ.get("TAVILY_API_KEYS", "").split(",") if k.strip()]
HUNTER_API_KEY = os.environ.get("HUNTER_API_KEY")

DEVELOPMENT_LOCKDOWN = os.getenv("DEVELOPMENT_LOCKDOWN", "false").lower() in ("1", "true", "yes", "on")
FEATURE_PASTE_IMPORT = os.getenv("FEATURE_PASTE_IMPORT", "false").lower() in ("1", "true", "yes", "on")
FEATURE_CSV_IMPORT = os.getenv("FEATURE_CSV_IMPORT", "false").lower() in ("1", "true", "yes", "on")
FEATURE_EXCEL_IMPORT = os.getenv("FEATURE_EXCEL_IMPORT", "false").lower() in ("1", "true", "yes", "on")
FEATURE_OUTLOOK_LIBRARY = os.getenv("FEATURE_OUTLOOK_LIBRARY", "false").lower() in ("1", "true", "yes", "on")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@talentops.ai")
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "https://talent-ops-ai.vercel.app,https://talent-ops-ai-staging.vercel.app,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175,https://94334d6e-bbcd-4b1a-91a7-46d8884e20ea.lovableproject.com",
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
