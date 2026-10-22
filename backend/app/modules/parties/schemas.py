import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.core.fields import CleanText, Identifier
from app.modules.users.schemas import Email


class PartyType(StrEnum):
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"


# Decision D-05: only the name is required; everything else is optional.
DisplayName = Annotated[str, CleanText, Field(min_length=1, max_length=300)]
# Length and pattern apply to the text only; null (clear the field) is always accepted.
OfficialNumber = Annotated[Annotated[str, Field(max_length=50)] | None, Identifier]
Phone = Annotated[Annotated[str, Field(max_length=50, pattern=r"^[0-9+()\-. /]+$")] | None, CleanText]
LongText = Annotated[Annotated[str, Field(max_length=2000)] | None, CleanText]
OptionalEmail = Annotated[Email | None, CleanText]


class PartyFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    national_id: OfficialNumber = Field(None, description="Individuals only.")
    passport_no: OfficialNumber = Field(None, description="Individuals only.")
    registration_no: OfficialNumber = Field(None, description="Organizations only (commercial registration).")
    tax_no: OfficialNumber = Field(None, description="Organizations only.")
    email: OptionalEmail = None
    phone: Phone = None
    address: LongText = None
    notes: LongText = None


class PartyCreate(PartyFields):
    party_type: PartyType
    display_name: DisplayName = Field(description="Full name of a person, or the company name.")


class PartyUpdate(PartyFields):
    """Partial update: only the fields sent change; send null to clear one. The party type cannot change."""

    display_name: DisplayName | None = None


class PartyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    party_type: PartyType
    display_name: str
    national_id: str | None
    passport_no: str | None
    registration_no: str | None
    tax_no: str | None
    email: str | None
    phone: str | None
    address: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
