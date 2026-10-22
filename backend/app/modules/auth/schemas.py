import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.users.models import User


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Not EmailStr: a malformed address is simply a failed login, not a validation hint for attackers.
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    preferred_language: str
    roles: list[str]
    permissions: list[str]
    data_scopes: list[str]

    @classmethod
    def from_user(cls, user: User) -> "MeResponse":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            preferred_language=user.preferred_language,
            roles=user.role_codes,
            permissions=sorted(user.permission_codes),
            data_scopes=sorted(user.data_scopes),
        )


class AuthOptions(BaseModel):
    self_signup_enabled: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 (OAuth token type, not a secret)
    expires_in: int = Field(description="Access token lifetime in seconds.")
    user: MeResponse
