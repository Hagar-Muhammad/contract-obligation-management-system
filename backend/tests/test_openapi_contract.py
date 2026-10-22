"""The frontend's generated API types come from frontend/src/api/openapi.json; it must match the live API."""

import json
from pathlib import Path

from app.main import create_app

CONTRACT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "api" / "openapi.json"


def test_committed_openapi_document_matches_the_api() -> None:
    committed = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert committed == create_app().openapi(), (
        "The API changed. Run `npm run api:generate` in frontend/ (with the backend venv active) and commit the result."
    )
