import hashlib
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

BYPASS_PATHS = (
    "/download",
    "/api/download",
    "/staging/stream",
    "/scout/events/stream",
    "/docs",
    "/redoc",
    "/openapi.json",
)

BYPASS_CONTENT_TYPES = (
    "text/event-stream",
    "application/octet-stream",
    "application/vnd.microsoft.portable-executable",
    "application/zip",
)

PUBLIC_CACHE_PATHS = (
    "/ping",
    "/version",
    "/api/v1/version",
)


class ETagMiddleware(BaseHTTPMiddleware):
    """
    HTTP ETag and Conditional 304 Middleware.
    Aggressively reduces Render egress bandwidth by:
    1. Returning 304 Not Modified (0 bytes body) when If-None-Match matches.
    2. Setting Vercel Edge-friendly Cache-Control (s-maxage) on public endpoints so Vercel edge
       caches responses and avoids hitting Render entirely.
    3. Setting private, no-cache + ETag on API read endpoints so browsers cache locally and
       revalidate with 0-byte payloads.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method not in ("GET", "HEAD"):
            return await call_next(request)

        path = request.url.path

        # Bypass binary downloads and streaming SSE
        for bypass in BYPASS_PATHS:
            if path.startswith(bypass):
                return await call_next(request)

        response = await call_next(request)

        # Only process successful 200 OK responses
        if response.status_code != 200:
            return response

        content_type = response.headers.get("content-type", "")
        for bypass_ct in BYPASS_CONTENT_TYPES:
            if bypass_ct in content_type:
                return response

        try:
            res_body = b""
            async for chunk in response.body_iterator:
                res_body += chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")

            # Compute SHA-256 short hash
            digest = hashlib.sha256(res_body).hexdigest()[:16]
            etag = f'"{digest}"'

            headers = dict(response.headers)
            headers["etag"] = etag

            # Add optimal Cache-Control headers if not already set by the endpoint
            if "cache-control" not in headers:
                if path in PUBLIC_CACHE_PATHS:
                    # Edge CDN caches for 2 minutes, serves stale up to 5 minutes
                    headers["cache-control"] = "public, max-age=30, s-maxage=120, stale-while-revalidate=300"
                else:
                    # Client must revalidate with ETag; 0 bytes if unmodified
                    headers["cache-control"] = "private, no-cache"

            # Check client conditional request (If-None-Match)
            if_none_match = request.headers.get("if-none-match")
            if if_none_match:
                # Extract client tags, stripping W/ and quotes
                client_tags = [
                    t.strip().lstrip("W/").strip('"')
                    for t in if_none_match.split(",")
                ]
                clean_etag = digest

                if clean_etag in client_tags or "*" in client_tags:
                    # 304 Not Modified: zero body egress
                    headers.pop("content-length", None)
                    headers.pop("content-type", None)
                    headers.pop("content-encoding", None)
                    return Response(status_code=304, headers=headers)

            return Response(
                content=res_body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type,
            )
        except Exception as e:
            logger.debug("ETag processing error on %s: %s", path, e)
            return response
