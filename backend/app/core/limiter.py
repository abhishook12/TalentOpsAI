import os
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

logger = logging.getLogger("talentops.limiter")

def get_client_ip(request: Request) -> str:
    """Extract the real client IP, accounting for reverse proxies (Render, Vercel, Cloudflare, etc).
    
    Priority order:
    1. CF-Connecting-IP (set by Cloudflare proxy — authoritative client IP)
    2. X-Vercel-Forwarded-For (set by Vercel edge proxy — the real user IP)
    3. X-Real-IP (set by Render's reverse proxy)
    4. First IP in X-Forwarded-For chain (standard proxy header)
    5. Direct client host (local dev)
    """
    # Cloudflare edge proxy provides the genuine visitor IP
    cf_ip = request.headers.get("cf-connecting-ip") or request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    # Vercel edge proxy sets this to the original user's IP
    vercel_fwd = request.headers.get("x-vercel-forwarded-for")
    if vercel_fwd:
        return vercel_fwd.split(",")[0].strip()
    
    # Render sets X-Real-IP to the actual client IP
    real_ip = request.headers.get("x-real-ip") or request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    fwd = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

# A more robust key function that accounts for reverse proxies
def get_ip_address(request: Request) -> str:
    # Exempt CORS preflight OPTIONS from rate limiting by assigning a shared
    # "phantom" key that has its own generous bucket (won't eat real user quota).
    if request.method == "OPTIONS":
        return "__cors_preflight__"
    return get_client_ip(request)

# Support Upstash Redis or local memory storage
_redis_url = os.getenv("UPSTASH_REDIS_URL") or os.getenv("REDIS_URL", "").strip()

if _redis_url:
    try:
        limiter = Limiter(
            key_func=get_ip_address,
            default_limits=["600/minute"],        # 10 req/sec per real IP — generous for SPA
            application_limits=["3000/minute"],   # Global ceiling across all IPs
            storage_uri=_redis_url,
            enabled=True,
        )
        logger.info("🛡️ Distributed Rate Limiter connected to Upstash Redis: %s", _redis_url.split("@")[-1] if "@" in _redis_url else "active")
    except Exception as e:
        logger.warning("Failed to connect Rate Limiter to Redis (%s), falling back to in-memory: %s", _redis_url, e)
        limiter = Limiter(
            key_func=get_ip_address,
            default_limits=["600/minute"],
            application_limits=["3000/minute"],
            enabled=True,
        )
else:
    limiter = Limiter(
        key_func=get_ip_address,
        default_limits=["600/minute"],        # 10 req/sec per real IP — generous for SPA
        application_limits=["3000/minute"],   # Global ceiling across all IPs
        enabled=True,
    )


