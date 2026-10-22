import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.modules.users.rbac import DataScope, RoleCode

Language = Literal["en", "ar"]

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


def _lower(value: str) -> str:
    return value.strip().lower()


Email = Annotated[EmailStr, AfterValidator(_lower)]
FullName = Annotated[str, Field(min_length=1, max_length=200)]
Password = Annotated[str, Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)]


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Email
    full_name: FullName
    password: Password
    role_codes: list[RoleCode] = Field(min_length=1, description="At least one role (FR-USER-01).")
    preferred_language: Language = "en"


class UserUpdate(BaseModel):
    """Partial update. Setting `password` is an administrator reset and ends the user's sessions."""

    model_config = ConfigDict(extra="forbid")

    email: Email | None = None
    full_name: FullName | None = None
    password: Password | None = None
    role_codes: list[RoleCode] | None = Field(default=None, min_length=1)
    preferred_language: Language | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    preferred_language: str
    is_active: bool
    role_codes: list[str]
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RoleRead(BaseModel):
    code: str
    name: str
    description: str
    data_scope: DataScope
    permissions: list[str]
