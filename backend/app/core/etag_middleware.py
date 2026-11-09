import hashlib
import logging

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
    b"text/event-stream",
    b"application/octet-stream",
    b"application/vnd.microsoft.portable-executable",
    b"application/zip",
)

PUBLIC_CACHE_PATHS = {
    "/ping",
    "/version",
    "/api/v1/version",
    "/health",
    "/api/ping",
    "/api/version",
    "/api/health",
    "/api/scout/version",
    "/scout/updates/latest",
}


class ETagMiddleware:
    """
    Pure ASGI HTTP ETag and Conditional 304 Middleware.
    Aggressively reduces Render egress bandwidth and eliminates all BaseHTTPMiddleware
    task-group deadlocks (Starlette #1012, #1157, #1271).

    1. Returns 304 Not Modified (0 bytes body) when If-None-Match matches.
    2. Sets Vercel Edge-friendly Cache-Control (s-maxage) on public endpoints so Vercel edge
       caches responses and avoids hitting Render entirely.
    3. Sets private, no-cache + ETag on API read endpoints so browsers cache locally and
       revalidate with 0-byte payloads.
    4. Operates 100% at the ASGI protocol level with zero threadpool or taskgroup overhead.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        if method not in ("GET", "HEAD"):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        for bypass in BYPASS_PATHS:
            if path.startswith(bypass):
                await self.app(scope, receive, send)
                return

        # Extract client If-None-Match header
        client_if_none_match = None
        for k, v in scope.get("headers", []):
            if k.lower() == b"if-none-match":
                client_if_none_match = v.decode("latin1", errors="ignore")
                break

        response_start = {}
        body_chunks = []
        is_bypassed = False

        async def custom_send(message):
            nonlocal is_bypassed
            msg_type = message.get("type")

            if msg_type == "http.response.start":
                response_start.update(message)
                # Check for streaming/binary bypass in content-type
                headers = message.get("headers", [])
                for hk, hv in headers:
                    if hk.lower() == b"content-type":
                        hv_lower = hv.lower()
                        for bct in BYPASS_CONTENT_TYPES:
                            if bct in hv_lower:
                                is_bypassed = True
                                break
                        break
                if is_bypassed:
                    await send(message)
                return

            elif msg_type == "http.response.body":
                if is_bypassed:
                    await send(message)
                    return

                body = message.get("body", b"")
                more_body = message.get("more_body", False)
                body_chunks.append(body)

                if more_body:
                    # If response is chunked streaming with more_body=True, don't buffer infinitely
                    # If total buffered exceeds 1MB, bypass to prevent memory ballooning
                    total_len = sum(len(c) for c in body_chunks)
                    if total_len > 1_000_000:
                        is_bypassed = True
                        await send(response_start)
                        for c in body_chunks:
                            await send({"type": "http.response.body", "body": c, "more_body": True})
                        body_chunks.clear()
                    return

                # End of response body reached
                status_code = response_start.get("status", 200)
                raw_headers = response_start.get("headers", [])
                header_dict = {k.lower(): (k, v) for k, v in raw_headers}

                if status_code == 200:
                    full_body = b"".join(body_chunks)
                    digest = hashlib.sha256(full_body).hexdigest()[:16]
                    etag_val = f'"{digest}"'.encode("latin1")

                    # Set ETag
                    header_dict[b"etag"] = (b"etag", etag_val)

                    # Optimal Cache-Control headers
                    if b"cache-control" not in header_dict:
                        if path in PUBLIC_CACHE_PATHS:
                            # Edge CDN caches for 2 minutes, serves stale up to 5 minutes
                            header_dict[b"cache-control"] = (
                                b"cache-control",
                                b"public, max-age=30, s-maxage=120, stale-while-revalidate=300"
                            )
                        else:
                            # Client must revalidate with ETag; 0 bytes if unmodified
                            header_dict[b"cache-control"] = (b"cache-control", b"private, no-cache")

                    # Check client conditional request (If-None-Match)
                    if client_if_none_match:
                        client_tags = [
                            t.strip().lstrip("W/").strip('"')
                            for t in client_if_none_match.split(",")
                        ]
                        if digest in client_tags or "*" in client_tags:
                            # 304 Not Modified: strip body framing headers, send empty body
                            header_dict.pop(b"content-length", None)
                            header_dict.pop(b"content-type", None)
                            header_dict.pop(b"content-encoding", None)
                            out_headers = [pair for pair in header_dict.values()]
                            await send({
                                "type": "http.response.start",
                                "status": 304,
                                "headers": out_headers,
                            })
                            await send({
                                "type": "http.response.body",
                                "body": b"",
                                "more_body": False,
                            })
                            return

                    # Normal 200 OK: accurately update Content-Length
                    header_dict.pop(b"content-encoding", None)
                    header_dict.pop(b"transfer-encoding", None)
                    header_dict[b"content-length"] = (b"content-length", str(len(full_body)).encode("latin1"))

                    out_headers = [pair for pair in header_dict.values()]
                    await send({
                        "type": "http.response.start",
                        "status": status_code,
                        "headers": out_headers,
                    })
                    await send({
                        "type": "http.response.body",
                        "body": full_body,
                        "more_body": False,
                    })
                    return

                # Non-200 responses: send through untouched
                out_headers = [pair for pair in header_dict.values()]
                await send({
                    "type": "http.response.start",
                    "status": status_code,
                    "headers": out_headers,
                })
                for idx, c in enumerate(body_chunks):
                    await send({
                        "type": "http.response.body",
                        "body": c,
                        "more_body": idx < len(body_chunks) - 1,
                    })
                return

            else:
                await send(message)

        await self.app(scope, receive, custom_send)
