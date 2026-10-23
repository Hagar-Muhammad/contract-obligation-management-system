import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.core.fields import CleanText
from app.modules.parties.schemas import PartyType


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ObligationStatus(StrEnum):
    """What people set (SRS 4.10). Overdue is not set: it follows from the due date (BR-04)."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EffectiveStatus(StrEnum):
    """The status shown everywhere: the stored status, or overdue when the due date has passed (SRS 4.10)."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


OPEN_STATUSES = frozenset({ObligationStatus.PENDING, ObligationStatus.IN_PROGRESS})


class ObligationView(StrEnum):
    """The list's status chips (design screen 7). Without a view: every obligation."""

    OPEN = "open"
    OVERDUE = "overdue"
    DUE_THIS_WEEK = "due_this_week"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ObligationSort(StrEnum):
    DUE_DATE = "due_date"
    DUE_DATE_DESC = "-due_date"
    PRIORITY = "priority"
    TITLE = "title"
    UPDATED_DESC = "-updated_at"


Title = Annotated[str, CleanText, Field(min_length=1, max_length=300)]
Description = Annotated[str, CleanText, Field(min_length=1, max_length=5000)]
LongText = Annotated[Annotated[str, Field(max_length=5000)] | None, CleanText]
Rule = Annotated[Annotated[str, Field(max_length=500)] | None, CleanText]


class ObligationFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    responsible_user_id: uuid.UUID | None = Field(
        None, description="Internal user who follows it up (FR-OBL-03)."
    )
    start_date: date | None = None
    due_date: date | None = Field(
        None, description="Leave empty for an ongoing duty without a deadline (D-07)."
    )
    recurrence_rule: Rule = Field(None, description="RFC 5545 RRULE, e.g. FREQ=MONTHLY;INTERVAL=3 (BR-08).")
    penalty_text: LongText = Field(None, description="Penalty for missing it, as text (D-08).")
    notes: LongText = None


class ObligationCreate(ObligationFields):
    contract_id: uuid.UUID = Field(description="BR-01: every obligation belongs to a contract.")
    title: Title
    description: Description
    responsible_party_id: uuid.UUID = Field(description="One of the contract's parties.")
    priority: Priority = Priority.MEDIUM
    status: ObligationStatus = Field(ObligationStatus.PENDING, description="Pending or in progress.")


class ObligationUpdate(ObligationFields):
    """Partial update of the details. Status changes go through POST /obligations/{id}/status."""

    title: Title | None = None
    description: Description | None = None
    responsible_party_id: uuid.UUID | None = None
    priority: Priority | None = None


class StatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ObligationStatus
    note: Annotated[Annotated[str, Field(max_length=1000)] | None, CleanText] = Field(
        None, description="Kept in the audit trail with the change."
    )


class ContractRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contract_number: str
    title: str


class PartyRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    party_type: PartyType


class UserRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str


class ObligationRead(BaseModel):
    id: uuid.UUID
    contract: ContractRef
    title: str
    description: str
    responsible_party: PartyRef
    responsible_user: UserRef | None
    start_date: date | None
    due_date: date | None
    priority: Priority
    status: ObligationStatus
    effective_status: EffectiveStatus
    recurrence_rule: str | None
    series_id: uuid.UUID | None
    penalty_text: str | None
    notes: str | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    overdue_at: datetime | None
    evidence_count: int
    created_at: datetime
    updated_at: datetime


class ObligationCounts(BaseModel):
    """Number of obligations per status chip, within the caller's data scope."""

    open: int
    overdue: int
    due_this_week: int
    in_progress: int
    pending: int
    completed: int
    cancelled: int
