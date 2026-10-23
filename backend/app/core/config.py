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
    # Session length when "Keep me signed in" is not ticked (the cookie also ends when the browser closes).
    unremembered_session_hours: int = Field(default=12, ge=1, le=72)
    refresh_cookie_name: str = "coms_refresh"

    # Self sign-up (change request CR-01, docs/decisions.md D-20). New accounts get this single role.
    self_signup_enabled: bool = True
    self_signup_role: Literal[
        "admin", "contract_manager", "legal", "property_manager", "employee", "management"
    ] = "employee"

    # Contracts (module 4, docs/decisions.md T-26)
    default_currency: str = Field(default="EGP", pattern=r"^[A-Z]{3}$")
    contract_number_prefix: str = Field(default="CT", pattern=r"^[A-Z0-9]{1,10}$")
    expiring_soon_days: int = Field(default=60, ge=1, le=365)

    # Contract documents (module 5, decision D-12). Originals are kept on this disk path, outside the web root.
    storage_dir: str = "storage"
    upload_max_bytes: int = Field(default=20 * 1024 * 1024, ge=1024)
    upload_allowed_types: list[Literal["pdf", "docx", "png", "jpg"]] = ["pdf", "docx", "png", "jpg"]

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
