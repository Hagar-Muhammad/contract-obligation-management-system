"""Contracts (FR-CON-01..06, FR-PARTY-03, FR-PROP-01; BR-02, BR-03, BR-07; decisions D-06, D-09, D-17)."""

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.core.pagination import PageParams, paginate
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction, TargetType
from app.modules.auth.dependencies import CurrentUser
from app.modules.contracts.models import Contract, ContractParty, ContractStatus, ContractType
from app.modules.contracts.schemas import (
    ENDED_STATUSES,
    INITIAL_STATUSES,
    STATUS_TRANSITIONS,
    ContractCounts,
    ContractCreate,
    ContractPartyIn,
    ContractSort,
    ContractUpdate,
    ContractView,
    StatusCode,
)
from app.modules.contracts.scope import contract_in_scope
from app.modules.parties.models import Party
from app.modules.properties import service as properties_service
from app.modules.properties.models import Property
from app.modules.users.rbac import DataScope

_SORTS: dict[ContractSort, tuple[Any, ...]] = {
    ContractSort.END_DATE: (Contract.end_date.asc().nulls_last(),),
    ContractSort.END_DATE_DESC: (Contract.end_date.desc().nulls_last(),),
    ContractSort.START_DATE: (Contract.start_date.asc(),),
    ContractSort.START_DATE_DESC: (Contract.start_date.desc(),),
    ContractSort.NUMBER: (Contract.contract_number.asc(),),
    ContractSort.TITLE: (Contract.title.asc(),),
    ContractSort.UPDATED_DESC: (Contract.updated_at.desc(),),
}


def _today() -> date:
    return datetime.now(UTC).date()


def _field_error(field: str, message: str) -> BusinessRuleError:
    return BusinessRuleError(message, details=[{"field": f"body.{field}", "message": message}])


# --- lookups ------------------------------------------------------------------------------------------------


def list_types(db: Session) -> list[ContractType]:
    return list(
        db.scalars(select(ContractType).where(ContractType.is_active).order_by(ContractType.sort_order))
    )


def list_statuses(db: Session) -> list[ContractStatus]:
    return list(db.scalars(select(ContractStatus).order_by(ContractStatus.sort_order)))


def _active_type(db: Session, code: str) -> ContractType:
    found = db.scalar(select(ContractType).where(ContractType.code == code, ContractType.is_active))
    if found is None:
        raise _field_error("type_code", "Choose one of the contract types in the list.")  # FR-CON-06
    return found


def _status(db: Session, code: StatusCode) -> ContractStatus:
    found = db.scalar(select(ContractStatus).where(ContractStatus.code == code))
    if found is None:  # pragma: no cover - statuses are seeded by migration
        raise _field_error("status_code", "Unknown status.")
    return found


# --- validation ---------------------------------------------------------------------------------------------


def _check_dates(start: date, end: date | None) -> None:
    if end is not None and end < start:
        raise _field_error("end_date", "End date can't be earlier than the start date.")  # BR-03


def _check_value(amount: Any, currency: str | None) -> None:
    if amount is not None and currency is None:
        raise _field_error("currency", "Currency is required when a value is entered.")
    if amount is None and currency is not None:
        raise _field_error("value_amount", "Enter the value for this currency, or clear the currency.")


def _check_number_free(db: Session, number: str, *, except_id: uuid.UUID | None = None) -> None:
    stmt = select(Contract.title).where(Contract.contract_number == number)
    if except_id is not None:
        stmt = stmt.where(Contract.id != except_id)
    existing = db.scalar(stmt)
    if existing is not None:
        raise ConflictError(
            "This contract number is already used.",
            details=[{"field": "body.contract_number", "message": f"Already used by “{existing}”."}],
        )


def _parties(db: Session, items: Sequence[ContractPartyIn]) -> list[tuple[Party, str]]:
    """BR-02: at least one party, each listed once, and each must exist."""
    if not items:
        raise _field_error("parties", "Add at least one party.")
    ids = [item.party_id for item in items]
    if len(set(ids)) != len(ids):
        raise _field_error("parties", "Each party can be added only once.")
    found = {p.id: p for p in db.scalars(select(Party).where(Party.id.in_(ids)))}
    if len(found) != len(ids):
        raise _field_error("parties", "One of the parties no longer exists.")
    return [(found[item.party_id], item.role.value) for item in items]


def _links(
    parties: Sequence[tuple[Party, str]], existing: Sequence[ContractParty] = ()
) -> list[ContractParty]:
    """Contract-party rows for `parties`, reusing existing rows so their keys do not clash."""
    by_party = {link.party_id: link for link in existing}
    links = []
    for party, role in parties:
        link = by_party.get(party.id) or ContractParty(party_id=party.id, party=party)
        link.role = role
        links.append(link)
    return links


def _properties(db: Session, current: CurrentUser, ids: Sequence[uuid.UUID]) -> list[Property]:
    """Only properties the user can see; a Property Manager's contract must be on one of their properties."""
    props = properties_service.get_visible(db, current, ids)
    if len(props) != len(set(ids)):
        raise _field_error("property_ids", "One of the properties is not available to you.")
    if current.data_scope == DataScope.ASSIGNED_PROPERTIES and not props:
        raise _field_error("property_ids", "Link at least one of the properties assigned to you.")
    return props


def _snapshot(contract: Contract) -> dict[str, Any]:
    """JSON-friendly values for audit records."""
    return {
        "contract_number": contract.contract_number,
        "title": contract.title,
        "contract_type": contract.contract_type.code,
        "status": contract.status.code,
        "description": contract.description,
        "start_date": contract.start_date.isoformat(),
        "end_date": contract.end_date.isoformat() if contract.end_date else None,
        "value_amount": f"{contract.value_amount:.2f}" if contract.value_amount is not None else None,
        "currency": contract.currency,
        "renewal_date": contract.renewal_date.isoformat() if contract.renewal_date else None,
        "parties": sorted(f"{link.party.display_name} ({link.role})" for link in contract.parties),
        "properties": sorted(prop.code for prop in contract.properties),
    }


def _record(
    db: Session,
    action: AuditAction,
    contract: Contract,
    current: CurrentUser,
    changes: dict[str, Any] | None = None,
) -> None:
    audit.record(
        db,
        action,
        target_type=TargetType.CONTRACT,
        target_id=contract.id,
        target_label=f"{contract.contract_number} · {contract.title}",
        actor_id=current.id,
        changes=changes,
    )


# --- reading ------------------------------------------------------------------------------------------------


def _status_in(codes: Sequence[StatusCode]) -> ColumnElement[bool]:
    return Contract.status_id.in_(select(ContractStatus.id).where(ContractStatus.code.in_(list(codes))))


def _view_filter(view: ContractView | None) -> ColumnElement[bool]:
    not_archived = Contract.archived_at.is_(None)
    match view:
        case None:
            return not_archived  # BR-07: archived contracts only when asked for
        case ContractView.ACTIVE:
            return and_(not_archived, _status_in([StatusCode.ACTIVE]))
        case ContractView.DRAFT:
            return and_(not_archived, _status_in([StatusCode.DRAFT]))
        case ContractView.EXPIRING:
            today = _today()
            horizon = today + timedelta(days=get_settings().expiring_soon_days)
            return and_(
                not_archived, _status_in([StatusCode.ACTIVE]), Contract.end_date.between(today, horizon)
            )
        case ContractView.ENDED:
            return and_(not_archived, _status_in(sorted(ENDED_STATUSES)))
        case ContractView.ARCHIVED:
            return Contract.archived_at.is_not(None)


def list_contracts(
    db: Session,
    current: CurrentUser,
    params: PageParams,
    *,
    view: ContractView | None = None,
    q: str | None = None,
    type_code: str | None = None,
    party_id: uuid.UUID | None = None,
    property_id: uuid.UUID | None = None,
    term_from: date | None = None,
    term_to: date | None = None,
    sort: ContractSort = ContractSort.END_DATE,
) -> tuple[list[Contract], int]:
    stmt = select(Contract).where(contract_in_scope(current), _view_filter(view))
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Contract.contract_number.ilike(pattern),
                Contract.title.ilike(pattern),
                Contract.parties.any(ContractParty.party.has(Party.display_name.ilike(pattern))),
                Contract.properties.any(or_(Property.name.ilike(pattern), Property.code.ilike(pattern))),
            )
        )
    if type_code:
        stmt = stmt.where(Contract.contract_type.has(ContractType.code == type_code))
    if party_id is not None:
        stmt = stmt.where(Contract.parties.any(ContractParty.party_id == party_id))
    if property_id is not None:
        stmt = stmt.where(Contract.properties.any(Property.id == property_id))
    # Contracts whose term overlaps [term_from, term_to].
    if term_to is not None:
        stmt = stmt.where(Contract.start_date <= term_to)
    if term_from is not None:
        stmt = stmt.where(or_(Contract.end_date.is_(None), Contract.end_date >= term_from))
    stmt = stmt.order_by(*_SORTS[sort], Contract.contract_number)
    return paginate(db, stmt, params)


def count_by_view(db: Session, current: CurrentUser) -> ContractCounts:
    def count(view: ContractView) -> int:
        stmt = (
            select(func.count()).select_from(Contract).where(contract_in_scope(current), _view_filter(view))
        )
        return db.scalar(stmt) or 0

    return ContractCounts(**{view.value: count(view) for view in ContractView})


def get_contract(db: Session, current: CurrentUser, contract_id: uuid.UUID) -> Contract:
    """Out-of-scope contracts are reported as not found, so their existence is not revealed."""
    contract = db.scalar(select(Contract).where(Contract.id == contract_id, contract_in_scope(current)))
    if contract is None:
        raise NotFoundError("Contract not found.")
    return contract


def next_number(db: Session) -> str:
    """Suggest PREFIX-YEAR-NNNN after the highest number used this year. A suggestion only: numbers stay unique."""
    prefix = f"{get_settings().contract_number_prefix}-{_today().year}-"
    used = db.scalars(select(Contract.contract_number).where(Contract.contract_number.startswith(prefix)))
    highest = max((int(n[len(prefix) :]) for n in used if n[len(prefix) :].isdigit()), default=0)
    return f"{prefix}{highest + 1:04d}"


# --- writing ------------------------------------------------------------------------------------------------


def create_contract(db: Session, current: CurrentUser, data: ContractCreate) -> Contract:
    _check_number_free(db, data.contract_number)
    contract_type = _active_type(db, data.type_code)
    if data.status_code not in INITIAL_STATUSES:
        raise _field_error("status_code", "A new contract starts as draft or active.")
    _check_dates(data.start_date, data.end_date)
    _check_value(data.value_amount, data.currency)
    contract = Contract(
        id=uuid.uuid4(),
        contract_number=data.contract_number,
        title=data.title,
        contract_type=contract_type,
        status=_status(db, data.status_code),
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
        value_amount=data.value_amount,
        currency=data.currency,
        renewal_date=data.renewal_date,
        parties=_links(_parties(db, data.parties)),
        properties=_properties(db, current, data.property_ids),
        created_by_id=current.id,
        updated_by_id=current.id,
    )
    db.add(contract)
    _record(
        db,
        AuditAction.CONTRACT_CREATED,
        contract,
        current,
        {field: [None, value] for field, value in _snapshot(contract).items() if value not in (None, [])},
    )
    db.commit()
    db.refresh(contract)
    return contract


def update_contract(
    db: Session, current: CurrentUser, contract_id: uuid.UUID, data: ContractUpdate
) -> Contract:
    contract = get_contract(db, current, contract_id)
    if contract.archived_at is not None:
        raise BusinessRuleError("Archived contracts cannot be edited. Restore the contract first.")
    sent = data.model_dump(exclude_unset=True)
    for required in ("contract_number", "title", "type_code", "status_code", "start_date", "parties"):
        if required in sent and sent[required] is None:
            raise _field_error(required, "This field is required.")

    # Check and look up everything first; the contract changes only once the whole edit is acceptable.
    def new(field: str) -> Any:
        return sent[field] if field in sent else getattr(contract, field)

    if new("contract_number") != contract.contract_number:
        _check_number_free(db, sent["contract_number"], except_id=contract.id)
    contract_type = contract.contract_type
    if "type_code" in sent and sent["type_code"] != contract_type.code:
        contract_type = _active_type(db, sent["type_code"])
    status = contract.status
    if "status_code" in sent and sent["status_code"] != status.code:
        target = StatusCode(sent["status_code"])
        if target not in STATUS_TRANSITIONS[StatusCode(status.code)]:
            raise _field_error(
                "status_code", f"A {status.name_en.lower()} contract cannot become {target.value}."
            )
        status = _status(db, target)
    _check_dates(new("start_date"), new("end_date"))
    _check_value(new("value_amount"), new("currency"))
    parties = _parties(db, data.parties) if data.parties is not None else None
    properties = _properties(db, current, data.property_ids) if data.property_ids is not None else None

    before = _snapshot(contract)
    contract.contract_type = contract_type
    contract.status = status
    for field in (
        "contract_number",
        "title",
        "description",
        "start_date",
        "end_date",
        "value_amount",
        "currency",
        "renewal_date",
    ):
        if field in sent:
            setattr(contract, field, sent[field])
    if parties is not None:
        contract.parties = _links(parties, contract.parties)
    if properties is not None:
        contract.properties = properties

    changes = audit.changes_between(before, _snapshot(contract))
    if status_change := changes.pop("status", None):
        _record(db, AuditAction.CONTRACT_STATUS_CHANGED, contract, current, {"status": status_change})
    if changes:
        _record(db, AuditAction.CONTRACT_UPDATED, contract, current, changes)
    if changes or status_change:
        contract.updated_by_id = current.id
    db.commit()
    db.refresh(contract)
    return contract


def set_archived(db: Session, current: CurrentUser, contract_id: uuid.UUID, archived: bool) -> Contract:
    """Archive (FR-CON-05) or restore. Archiving hides the contract from standard lists (BR-07); status is kept."""
    contract = get_contract(db, current, contract_id)
    if (contract.archived_at is not None) == archived:
        raise BusinessRuleError(
            "This contract is already archived." if archived else "This contract is not archived."
        )
    contract.archived_at = datetime.now(UTC) if archived else None
    contract.archived_by_id = current.id if archived else None
    contract.updated_by_id = current.id
    _record(
        db, AuditAction.CONTRACT_ARCHIVED if archived else AuditAction.CONTRACT_RESTORED, contract, current
    )
    db.commit()
    db.refresh(contract)
    return contract
