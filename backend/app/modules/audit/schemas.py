import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.audit.actions import ActorType, AuditAction, TargetType


class AuditActor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str


class ActivityRead(BaseModel):
    """A record's history as its viewers see it: who did what and what changed (no request id or IP)."""

    model_config = ConfigDict(from_attributes=True)

    occurred_at: datetime
    actor_type: ActorType
    actor: AuditActor | None
    action: AuditAction
    target_type: TargetType
    target_label: str | None
    changes: dict[str, list[Any]] | None


class AuditLogRead(BaseModel):
    """One audit record (FR-AUD-02): who did what, to what, when, and what changed."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    occurred_at: datetime
    actor_type: ActorType
    actor: AuditActor | None = Field(description="The user who acted; null for system and anonymous actions.")
    action: AuditAction
    target_type: TargetType
    target_id: uuid.UUID | None
    target_label: str | None = Field(description="The target's name when the action happened.")
    changes: dict[str, list[Any]] | None = Field(description="Changed fields as {field: [old, new]}.")
    request_id: str | None
    ip_address: str | None
