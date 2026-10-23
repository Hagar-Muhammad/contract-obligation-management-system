import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from app.core.fields import CleanText
from app.modules.parties.schemas import PartyType
from app.modules.properties.schemas import PropertyType


class StatusCode(StrEnum):
    """Seeded statuses (decision D-17). The codes are fixed; names live in contract_statuses."""

    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    CANCELLED = "cancelled"


# D-17: draft → active → expired / terminated; draft → cancelled. Archiving is separate from status.
STATUS_TRANSITIONS: dict[StatusCode, frozenset[StatusCode]] = {
    StatusCode.DRAFT: frozenset({StatusCode.ACTIVE, StatusCode.CANCELLED}),
    StatusCode.ACTIVE: frozenset({StatusCode.EXPIRED, StatusCode.TERMINATED}),
    StatusCode.EXPIRED: frozenset(),
    StatusCode.TERMINATED: frozenset(),
    StatusCode.CANCELLED: frozenset(),
}
INITIAL_STATUSES = frozenset({StatusCode.DRAFT, StatusCode.ACTIVE})
ENDED_STATUSES = frozenset({StatusCode.EXPIRED, StatusCode.TERMINATED, StatusCode.CANCELLED})


class PartyRole(StrEnum):
    """A party's part in a contract (FR-PARTY-03)."""

    LANDLORD = "landlord"
    TENANT = "tenant"
    SELLER = "seller"
    BUYER = "buyer"
    OWNER = "owner"
    SERVICE_PROVIDER = "service_provider"
    CONTRACTOR = "contractor"
    CONSULTANT = "consultant"
    PARTNER = "partner"
    LICENSOR = "licensor"
    LICENSEE = "licensee"
    OTHER = "other"


class ContractView(StrEnum):
    """The list tabs. Without a view, the list shows every contract that is not archived (BR-07)."""

    ACTIVE = "active"
    DRAFT = "draft"
    EXPIRING = "expiring"
    ENDED = "ended"
    ARCHIVED = "archived"


class ContractSort(StrEnum):
    END_DATE = "end_date"
    END_DATE_DESC = "-end_date"
    START_DATE = "start_date"
    START_DATE_DESC = "-start_date"
    NUMBER = "contract_number"
    TITLE = "title"
    UPDATED_DESC = "-updated_at"


def _upper(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


ContractNumber = Annotated[
    str, BeforeValidator(_upper), Field(min_length=1, max_length=100, pattern=r"^[A-Z0-9][A-Z0-9 ._/-]*$")
]
Title = Annotated[str, CleanText, Field(min_length=1, max_length=300)]
LongText = Annotated[Annotated[str, Field(max_length=5000)] | None, CleanText]
Amount = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)] | None
Currency = Annotated[Annotated[str, Field(pattern=r"^[A-Z]{3}$")] | None, BeforeValidator(_upper)]


class ContractPartyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    party_id: uuid.UUID
    role: PartyRole


class ContractFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: LongText = None
    end_date: date | None = Field(
        None, description="Leave empty for an open-ended contract. Not before start_date."
    )
    value_amount: Amount = None
    currency: Currency = Field(None, description="ISO 4217 code; required when a value is given.")
    renewal_date: date | None = Field(None, description="When renewal notice is due (decision D-09).")


class ContractCreate(ContractFields):
    contract_number: ContractNumber = Field(
        description="Stored upper-cased; unique. See GET /contracts/defaults."
    )
    title: Title
    type_code: str = Field(max_length=50, description="An active code from GET /contract-types.")
    status_code: StatusCode = Field(StatusCode.DRAFT, description="A new contract starts as draft or active.")
    start_date: date
    parties: list[ContractPartyIn] = Field(min_length=1, description="At least one party (BR-02).")
    property_ids: list[uuid.UUID] = Field(default_factory=list)


class ContractUpdate(ContractFields):
    """Partial update: only the fields sent change. `parties` and `property_ids` replace the whole list."""

    contract_number: ContractNumber | None = None
    title: Title | None = None
    type_code: str | None = Field(None, max_length=50)
    status_code: StatusCode | None = Field(None, description="Must follow the allowed transitions (D-17).")
    start_date: date | None = None
    parties: list[ContractPartyIn] | None = Field(None, min_length=1)
    property_ids: list[uuid.UUID] | None = None


class LookupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name_en: str
    name_ar: str


class ContractStatusRead(LookupRead):
    next_codes: list[StatusCode] = Field(description="Statuses this one may change to (D-17).")


class ContractPartyRead(BaseModel):
    id: uuid.UUID
    display_name: str
    party_type: PartyType
    role: PartyRole


class ContractPropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    property_type: PropertyType


class PersonRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str


class ContractRead(BaseModel):
    id: uuid.UUID
    contract_number: str
    title: str
    contract_type: LookupRead
    status: ContractStatusRead
    description: str | None
    start_date: date
    end_date: date | None
    value_amount: Decimal | None
    currency: str | None
    renewal_date: date | None
    parties: list[ContractPartyRead]
    properties: list[ContractPropertyRead]
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    created_by: PersonRef | None
    updated_by: PersonRef | None


class ContractCounts(BaseModel):
    """Number of contracts per list tab, within the caller's data scope."""

    active: int
    draft: int
    expiring: int
    ended: int
    archived: int


class ContractDefaults(BaseModel):
    next_number: str = Field(description="Suggested number for a new contract; the user can change it.")
    default_currency: str
    expiring_soon_days: int = Field(
        description="An active contract ending within this many days is expiring."
    )
