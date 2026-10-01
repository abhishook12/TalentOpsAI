from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

def get_client_ip(request: Request) -> str:
    """Extract the real client IP, accounting for reverse proxies (Render, Vercel, etc).
    
    Priority order:
    1. X-Vercel-Forwarded-For (set by Vercel edge proxy — the real user IP)
    2. X-Real-IP (set by Render's reverse proxy)
    3. First IP in X-Forwarded-For chain (standard proxy header)
    4. Direct client host (local dev)
    
    IMPORTANT: When Vercel rewrites /api/* → Render, all traffic arrives from
    Vercel's edge IPs. Without reading x-vercel-forwarded-for, every user
    appears as the same client and rate limits are exhausted in seconds.
    """
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

limiter = Limiter(
    key_func=get_ip_address,
    default_limits=["600/minute"],        # 10 req/sec per real IP — generous for SPA
    application_limits=["3000/minute"],   # Global ceiling across all IPs
    enabled=True,
)

