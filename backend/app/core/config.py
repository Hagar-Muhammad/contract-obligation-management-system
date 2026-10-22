from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Only for local development and tests. Production refuses to start with it (see _check_production).
DEV_JWT_SECRET = "dev-only-insecure-secret-change-me-0123456789"  # noqa: S105 (public dev default by design)


class Settings(BaseSettings):
    """Application settings, read from environment variables (see .env.example)."""

    # One .env at the repository root serves docker compose and the API; backend/.env can override locally.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ConTrack API"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://coms:coms@localhost:5433/coms"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # Authentication (FR-AUTH-*, NFR-SEC-*)
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = Field(default=15, ge=1, le=120)
    refresh_token_ttl_days: int = Field(default=7, ge=1, le=90)
    refresh_cookie_name: str = "coms_refresh"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cookie_secure(self) -> bool:
        """Cookies are HTTPS-only in production (NFR-SEC-04)."""
        return self.is_production

    @model_validator(mode="after")
    def _check_production(self) -> "Settings":
        if self.is_production and (self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 32):
            raise ValueError(
                "JWT_SECRET must be set to a random value of at least 32 characters in production."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
