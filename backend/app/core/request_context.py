"""Per-request correlation data: request id and client IP (NFR-MAIN-03, docs/api-standards.md §8).

Read anywhere during a request (logging, the audit service) without passing the Request object around.
"""

import re
import uuid
from contextvars import ContextVar

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
# A caller-supplied id is kept only if it is short and harmless to write into logs.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_client_ip: ContextVar[str | None] = ContextVar("client_ip", default=None)


def current_request_id() -> str | None:
    return _request_id.get()


def current_client_ip() -> str | None:
    return _client_ip.get()


class RequestContextMiddleware:
    """Give every HTTP request an id (the caller's `X-Request-ID` if valid) and echo it in the response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = MutableHeaders(scope=scope).get(REQUEST_ID_HEADER)
        request_id = incoming if incoming and _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        client = scope.get("client")
        # Not reset afterwards on purpose: each request runs in its own task (its own context), and the
        # outermost unhandled-error handler, which runs after this middleware returns, still needs the id.
        _request_id.set(request_id)
        _client_ip.set(client[0] if client else None)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        await self.app(scope, receive, send_with_request_id)
