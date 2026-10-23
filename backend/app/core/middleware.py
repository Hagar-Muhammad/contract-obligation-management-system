from collections.abc import Awaitable, Callable
from http import HTTPStatus

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.errors import error_body

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


# Room for the multipart envelope around an uploaded file.
MULTIPART_OVERHEAD = 64 * 1024


class BodySizeLimitMiddleware:
    """Refuse request bodies above the upload limit before they are read into memory or onto disk (FR-DOC-04).

    A declared Content-Length over the limit gets 413 at once; a body without one is counted as it arrives and cut
    off when it passes the limit. The largest legitimate body is a document upload, so one limit fits every route.
    """

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    @property
    def limit(self) -> int:
        return self.settings.upload_max_bytes + MULTIPART_OVERHEAD

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = self.limit
        declared = Headers(scope=scope).get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            await self._too_large(scope, receive, send)
            return

        received = 0
        rejected = False

        async def counting_receive() -> Message:
            nonlocal received, rejected
            if rejected:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    # Answer now and tell the app the client is gone, so it stops reading the body.
                    rejected = True
                    await self._too_large(scope, receive, send)
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: Message) -> None:
            if not rejected:  # the 413 has already been sent; drop whatever the app answers
                await send(message)

        await self.app(scope, counting_receive, guarded_send)

    @staticmethod
    async def _too_large(scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            error_body("payload_too_large", "The file is larger than the size limit."),
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        )
        await response(scope, receive, send)
