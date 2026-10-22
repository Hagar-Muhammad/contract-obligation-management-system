import os
from collections.abc import Callable, Iterator
from pathlib import Path

# Point the app at the test database before any app module reads settings.
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://coms:coms@localhost:5433/coms_test"
)

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import engine, get_db
from app.main import create_app
from tests.factories import DEFAULT_PASSWORD, UserFactory

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def migrated_database() -> None:
    """Fresh schema built by the real migrations, also proving they downgrade cleanly."""
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")


@pytest.fixture
def db(migrated_database: None) -> Iterator[Session]:
    """A session whose work is rolled back after each test, even when the code under test commits."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def app(db: Session) -> FastAPI:
    application = create_app()
    application.dependency_overrides[get_db] = lambda: db
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def users(db: Session) -> UserFactory:
    return UserFactory(db)


@pytest.fixture
def auth_headers(client: TestClient, users: UserFactory) -> Callable[..., dict[str, str]]:
    """auth_headers("employee") -> Authorization header for a fresh user holding that role."""

    def make(*roles: str, **kwargs: object) -> dict[str, str]:
        user = users.create(*roles, **kwargs)  # type: ignore[arg-type]
        response = client.post("/api/v1/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return make
