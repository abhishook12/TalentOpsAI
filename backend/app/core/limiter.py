from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

def get_client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

# A more robust key function that accounts for reverse proxies
def get_ip_address(request: Request) -> str:
    return get_client_ip(request)

# Redefine limiter with the custom key function
limiter = Limiter(key_func=get_ip_address, default_limits=["200/minute"])
