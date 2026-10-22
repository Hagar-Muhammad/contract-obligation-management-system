"""Every request gets an X-Request-ID that also appears in logs (NFR-MAIN-03, docs/api-standards.md §8)."""

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.logging import RequestIdFilter
from app.core.request_context import REQUEST_ID_HEADER

HEALTH = "/api/v1/health"


@pytest.mark.req("NFR-MAIN-03")
def test_request_id_is_generated_when_absent(client: TestClient) -> None:
    first = client.get(HEALTH).headers[REQUEST_ID_HEADER]
    second = client.get(HEALTH).headers[REQUEST_ID_HEADER]
    assert len(first) == 32
    assert first != second


@pytest.mark.req("NFR-MAIN-03")
def test_valid_caller_request_id_is_kept(client: TestClient) -> None:
    response = client.get(HEALTH, headers={REQUEST_ID_HEADER: "trace-abc.123_X"})
    assert response.headers[REQUEST_ID_HEADER] == "trace-abc.123_X"


@pytest.mark.req("NFR-MAIN-03")
@pytest.mark.parametrize("bad", ["has space", "x" * 65, "line\tbreak", "semi;colon"])
def test_unsafe_caller_request_id_is_replaced(client: TestClient, bad: str) -> None:
    response = client.get(HEALTH, headers={REQUEST_ID_HEADER: bad})
    assert response.headers[REQUEST_ID_HEADER] != bad
    assert len(response.headers[REQUEST_ID_HEADER]) == 32


@pytest.mark.req("NFR-MAIN-03")
def test_error_responses_carry_the_request_id(client: TestClient) -> None:
    assert REQUEST_ID_HEADER in client.get("/api/v1/no-such-route").headers
    assert REQUEST_ID_HEADER in client.get("/api/v1/users").headers  # 401


@pytest.mark.req("NFR-MAIN-03")
def test_unhandled_error_is_logged_with_the_request_id(
    app: FastAPI, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    @app.get("/api/v1/_boom")
    def boom() -> None:
        raise RuntimeError("boom")

    caplog.handler.addFilter(RequestIdFilter())
    with caplog.at_level(logging.ERROR):
        response = client.get("/api/v1/_boom", headers={REQUEST_ID_HEADER: "req-500"})

    assert response.status_code == 500
    assert response.headers[REQUEST_ID_HEADER] == "req-500"
    assert [r.request_id for r in caplog.records] == ["req-500"]  # type: ignore[attr-defined]
