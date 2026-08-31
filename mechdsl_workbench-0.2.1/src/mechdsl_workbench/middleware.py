"""Small HTTP middleware used by the standalone workbench."""

from __future__ import annotations

from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, mathjax_url: str) -> None:
        super().__init__(app)
        external_origin = _external_origin(mathjax_url)
        script_sources = " ".join(filter(None, ("'self'", external_origin)))
        font_sources = " ".join(filter(None, ("'self'", "data:", external_origin)))
        self._csp = "; ".join(
            (
                "default-src 'self'",
                f"script-src {script_sources}",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data:",
                f"font-src {font_sources}",
                "connect-src 'self'",
                "object-src 'none'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
            )
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", self._csp)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response


class ContentLengthLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        raw = request.headers.get("content-length")
        if raw is not None:
            try:
                length = int(raw)
            except ValueError:
                return JSONResponse(
                    {
                        "ok": False,
                        "diagnostic": {
                            "severity": "error",
                            "stage": "http",
                            "category": "InvalidContentLength",
                            "message": "Content-Length must be an integer",
                        },
                    },
                    status_code=400,
                )
            if length < 0:
                return JSONResponse(
                    {
                        "ok": False,
                        "diagnostic": {
                            "severity": "error",
                            "stage": "http",
                            "category": "InvalidContentLength",
                            "message": "Content-Length must not be negative",
                        },
                    },
                    status_code=400,
                )
            if length > self.max_bytes:
                return JSONResponse(
                    {
                        "ok": False,
                        "diagnostic": {
                            "severity": "error",
                            "stage": "http",
                            "category": "RequestTooLarge",
                            "message": (
                                f"Request body is {length} bytes; the configured limit is "
                                f"{self.max_bytes} bytes"
                            ),
                        },
                    },
                    status_code=413,
                )
        return await call_next(request)


def _external_origin(url: str) -> str:
    if not url:
        return ""
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"
