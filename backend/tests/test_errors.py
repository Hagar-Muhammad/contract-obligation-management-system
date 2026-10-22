"""Error envelope conventions (docs/api-standards.md)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import BusinessRuleError, register_error_handlers


class _Payload(BaseModel):
    name: str
    amount: int


def _app_with_probe_routes() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.post("/validate")
    def validate(payload: _Payload) -> _Payload:
        return payload

    @app.get("/rule")
    def rule() -> None:
        raise BusinessRuleError("End date must not be earlier than start date.")

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("SELECT * FROM secret_table -- connection string here")

    return app


@pytest.fixture
def probe_client() -> TestClient:
    return TestClient(_app_with_probe_routes(), raise_server_exceptions=False)


@pytest.mark.req("NFR-MAIN-01", "NFR-UX-02")
def test_validation_errors_list_every_invalid_field(probe_client: TestClient) -> None:
    response = probe_client.post("/validate", json={"amount": "not-a-number"})
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_error"
    assert {d["field"] for d in body["details"]} == {"body.name", "body.amount"}


@pytest.mark.req("NFR-MAIN-01")
def test_business_rule_errors_use_the_envelope(probe_client: TestClient) -> None:
    response = probe_client.get("/rule")
    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "business_rule_violation",
            "message": "End date must not be earlier than start date.",
        }
    }


@pytest.mark.req("NFR-MAIN-01")
def test_unknown_route_returns_not_found_envelope(probe_client: TestClient) -> None:
    response = probe_client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.req("NFR-REL-02")
def test_unhandled_errors_do_not_leak_implementation_details(probe_client: TestClient) -> None:
    response = probe_client.get("/boom")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "An unexpected error occurred."}
    }
    assert "secret_table" not in response.text
