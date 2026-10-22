"""Party directory (FR-PARTY-01, FR-PARTY-02).

Who sees parties: users whose data scope is all records, and users who manage parties (they pick parties for
contracts). Other users see none until contracts exist; module 4 adds the parties of contracts in their scope.
"""

import uuid
from typing import Any

from sqlalchemy import Select, false, or_, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.core.pagination import PageParams, paginate
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction, TargetType
from app.modules.auth.dependencies import CurrentUser
from app.modules.parties.models import Party
from app.modules.parties.schemas import PartyCreate, PartyType, PartyUpdate
from app.modules.users.rbac import DataScope, Perm

AUDITED_FIELDS = (
    "party_type",
    "display_name",
    "national_id",
    "passport_no",
    "registration_no",
    "tax_no",
    "email",
    "phone",
    "address",
    "notes",
)
_TYPE_ONLY_FIELDS = {
    PartyType.INDIVIDUAL: ("national_id", "passport_no"),
    PartyType.ORGANIZATION: ("registration_no", "tax_no"),
}
_UNIQUE_FIELDS = ("national_id", "passport_no", "registration_no")


def _in_scope(stmt: Select[Party], current: CurrentUser) -> Select[Party]:
    if current.data_scope == DataScope.ALL or current.has(Perm.PARTY_MANAGE):
        return stmt
    return stmt.where(false())


def _snapshot(party: Party) -> dict[str, Any]:
    return {field: getattr(party, field) for field in AUDITED_FIELDS}


def _check_type_fields(party_type: PartyType, values: dict[str, Any]) -> None:
    """Reject identifiers that belong to the other party type, naming each offending field."""
    other = PartyType.ORGANIZATION if party_type == PartyType.INDIVIDUAL else PartyType.INDIVIDUAL
    wrong = [field for field in _TYPE_ONLY_FIELDS[other] if values.get(field) is not None]
    if wrong:
        raise BusinessRuleError(
            f"These fields do not apply to an {party_type.value} party.",
            details=[
                {"field": f"body.{field}", "message": f"Not used for {party_type.value} parties."}
                for field in wrong
            ],
        )


def _check_unique(db: Session, values: dict[str, Any], *, except_id: uuid.UUID | None = None) -> None:
    for field in _UNIQUE_FIELDS:
        value = values.get(field)
        if value is None:
            continue
        stmt = select(Party.display_name).where(getattr(Party, field) == value)
        if except_id is not None:
            stmt = stmt.where(Party.id != except_id)
        existing = db.scalar(stmt)
        if existing is not None:
            raise ConflictError(
                f"{existing} already has this number.",
                details=[{"field": f"body.{field}", "message": f"Already recorded for {existing}."}],
            )


def list_parties(
    db: Session,
    current: CurrentUser,
    params: PageParams,
    *,
    q: str | None = None,
    party_type: PartyType | None = None,
) -> tuple[list[Party], int]:
    """Alphabetical. `q` matches name, e-mail or phone, or an official number exactly."""
    stmt = _in_scope(select(Party), current).order_by(Party.display_name, Party.id)
    if q:
        pattern = f"%{q.strip()}%"
        number = "".join(q.split()).upper()
        stmt = stmt.where(
            or_(
                Party.display_name.ilike(pattern),
                Party.email.ilike(pattern),
                Party.phone.ilike(pattern),
                Party.national_id == number,
                Party.passport_no == number,
                Party.registration_no == number,
                Party.tax_no == number,
            )
        )
    if party_type is not None:
        stmt = stmt.where(Party.party_type == party_type)
    return paginate(db, stmt, params)


def get_party(db: Session, current: CurrentUser, party_id: uuid.UUID) -> Party:
    """Out-of-scope parties are reported as not found, so their existence is not revealed."""
    party = db.scalar(_in_scope(select(Party), current).where(Party.id == party_id))
    if party is None:
        raise NotFoundError("Party not found.")
    return party


def create_party(db: Session, current: CurrentUser, data: PartyCreate) -> Party:
    values = data.model_dump()
    _check_type_fields(data.party_type, values)
    _check_unique(db, values)
    party = Party(id=uuid.uuid4(), **values, created_by_id=current.id, updated_by_id=current.id)
    db.add(party)
    audit.record(
        db,
        AuditAction.PARTY_CREATED,
        target_type=TargetType.PARTY,
        target_id=party.id,
        target_label=party.display_name,
        actor_id=current.id,
        changes={field: [None, value] for field, value in _snapshot(party).items() if value is not None},
    )
    db.commit()
    db.refresh(party)
    return party


def update_party(db: Session, current: CurrentUser, party_id: uuid.UUID, data: PartyUpdate) -> Party:
    party = get_party(db, current, party_id)
    sent = data.model_dump(exclude_unset=True)
    if "display_name" in sent and sent["display_name"] is None:
        raise BusinessRuleError(
            "A party needs a name.", details=[{"field": "body.display_name", "message": "Required."}]
        )
    _check_type_fields(PartyType(party.party_type), sent)
    _check_unique(db, sent, except_id=party.id)

    before = _snapshot(party)
    for field, value in sent.items():
        setattr(party, field, value)
    if changes := audit.changes_between(before, _snapshot(party)):
        audit.record(
            db,
            AuditAction.PARTY_UPDATED,
            target_type=TargetType.PARTY,
            target_id=party.id,
            target_label=party.display_name,
            actor_id=current.id,
            changes=changes,
        )
        party.updated_by_id = current.id
    db.commit()
    db.refresh(party)
    return party
