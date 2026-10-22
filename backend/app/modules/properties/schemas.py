import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from app.core.fields import CleanText


class PropertyType(StrEnum):
    RESIDENTIAL = "residential"
    RETAIL = "retail"
    OFFICE = "office"
    INDUSTRIAL = "industrial"
    LAND = "land"
    MIXED_USE = "mixed_use"
    OTHER = "other"


def _code(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


PropertyCode = Annotated[
    str, BeforeValidator(_code), Field(min_length=1, max_length=50, pattern=r"^[A-Z0-9][A-Z0-9 ._/-]*$")
]
PropertyName = Annotated[str, CleanText, Field(min_length=1, max_length=200)]
# Constraints apply to the value only; null (clear the field) is always accepted.
ShortText = Annotated[Annotated[str, Field(max_length=100)] | None, CleanText]
LongText = Annotated[Annotated[str, Field(max_length=2000)] | None, CleanText]
Area = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)] | None


class PropertyFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: LongText = None
    city: ShortText = None
    country: ShortText = None
    area_sqm: Area = Field(None, description="Floor or land area in square metres.")
    notes: LongText = None


class PropertyCreate(PropertyFields):
    code: PropertyCode = Field(description='Business reference, e.g. "WM-G14". Stored upper-cased; unique.')
    name: PropertyName
    property_type: PropertyType
    manager_ids: list[uuid.UUID] = Field(
        default_factory=list, description="Property Managers assigned to this property (their data scope)."
    )


class PropertyUpdate(PropertyFields):
    """Partial update: only the fields sent change; send null to clear an optional one."""

    code: PropertyCode | None = None
    name: PropertyName | None = None
    property_type: PropertyType | None = None
    manager_ids: list[uuid.UUID] | None = Field(
        None, description="Replaces the whole list of assigned managers."
    )


class PropertyManagerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str


class PropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    property_type: PropertyType
    address: str | None
    city: str | None
    country: str | None
    area_sqm: Decimal | None
    notes: str | None
    managers: list[PropertyManagerRead]
    created_at: datetime
    updated_at: datetime
