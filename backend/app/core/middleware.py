from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.core.config import Settings

HSTS_MAX_AGE_SECONDS = 63072000  # two years


def add_security_headers(app: FastAPI, settings: Settings) -> None:
    """Baseline browser hardening; HSTS only in production, where the app is served over HTTPS (NFR-SEC-04)."""

    @app.middleware("http")
    async def _security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", f"max-age={HSTS_MAX_AGE_SECONDS}; includeSubDomains"
            )
        return response
