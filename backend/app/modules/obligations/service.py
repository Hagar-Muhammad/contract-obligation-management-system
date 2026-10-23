"""Obligations (FR-OBL-01..07, BR-01, BR-04, BR-08; decisions D-07, D-08).

Who may do what: viewing follows `obligation_in_scope`; creating needs obligation:create and a contract in scope;
editing details needs obligation:update and a data scope wider than "assigned obligations"; changing status needs
obligation:update on an obligation in scope (an Employee updates the obligations assigned to them).
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ForbiddenError, NotFoundError
from app.core.pagination import PageParams, paginate
from app.modules.audit import service as audit
from app.modules.audit.actions import ActorType, AuditAction, TargetType
from app.modules.auth.dependencies import CurrentUser
from app.modules.contracts import service as contracts_service
from app.modules.contracts.models import Contract, contract_properties
from app.modules.contracts.schemas import ObligationSummary, StatusCode
from app.modules.contracts.scope import obligation_in_scope
from app.modules.documents.models import ContractDocument
from app.modules.obligations import recurrence
from app.modules.obligations.models import Obligation
from app.modules.obligations.schemas import (
    OPEN_STATUSES,
    EffectiveStatus,
    ObligationCounts,
    ObligationCreate,
    ObligationSort,
    ObligationStatus,
    ObligationUpdate,
    ObligationView,
    StatusChange,
)
from app.modules.parties.models import Party
from app.modules.users.models import User
from app.modules.users.rbac import DataScope

_PRIORITY_ORDER = case({"critical": 0, "high": 1, "medium": 2, "low": 3}, value=Obligation.priority, else_=4)
_SORTS: dict[ObligationSort, tuple[Any, ...]] = {
    ObligationSort.DUE_DATE: (Obligation.due_date.asc().nulls_last(),),
    ObligationSort.DUE_DATE_DESC: (Obligation.due_date.desc().nulls_last(),),
    ObligationSort.PRIORITY: (_PRIORITY_ORDER, Obligation.due_date.asc().nulls_last()),
    ObligationSort.TITLE: (Obligation.title.asc(),),
    ObligationSort.UPDATED_DESC: (Obligation.updated_at.desc(),),
}
# How many missed occurrences one run may create for a series that fell behind.
_MAX_ROLL = 12


def today() -> date:
    return datetime.now(UTC).date()


def _now() -> datetime:
    return datetime.now(UTC)


def _field_error(field: str, message: str) -> BusinessRuleError:
    return BusinessRuleError(message, details=[{"field": f"body.{field}", "message": message}])


def is_overdue(obligation: Obligation, on: date | None = None) -> bool:
    """BR-04: the due date has passed and it is neither completed nor cancelled."""
    on = on or today()
    return obligation.due_date is not None and obligation.due_date < on and obligation.status in OPEN_STATUSES


def effective_status(obligation: Obligation, on: date | None = None) -> EffectiveStatus:
    return EffectiveStatus.OVERDUE if is_overdue(obligation, on) else EffectiveStatus(obligation.status)


def _overdue_clause(on: date) -> ColumnElement[bool]:
    return and_(Obligation.due_date < on, Obligation.status.in_([s.value for s in OPEN_STATUSES]))


def _snapshot(obligation: Obligation) -> dict[str, Any]:
    return {
        "title": obligation.title,
        "description": obligation.description,
        "responsible_party": obligation.responsible_party.display_name,
        "responsible_user": obligation.responsible_user.full_name if obligation.responsible_user else None,
        "start_date": obligation.start_date.isoformat() if obligation.start_date else None,
        "due_date": obligation.due_date.isoformat() if obligation.due_date else None,
        "priority": obligation.priority,
        "recurrence_rule": obligation.recurrence_rule,
        "penalty_text": obligation.penalty_text,
        "notes": obligation.notes,
    }


def _record(
    db: Session,
    action: AuditAction,
    obligation: Obligation,
    *,
    actor_id: uuid.UUID | None,
    changes: dict[str, Any] | None = None,
) -> None:
    audit.record(
        db,
        action,
        target_type=TargetType.OBLIGATION,
        target_id=obligation.id,
        target_label=obligation.title,
        actor_id=actor_id,
        actor_type=None if actor_id else ActorType.SYSTEM,
        changes=changes,
    )


# --- reading ------------------------------------------------------------------------------------------------


def _view_filter(view: ObligationView | None, on: date) -> ColumnElement[bool] | None:
    open_values = [s.value for s in OPEN_STATUSES]
    match view:
        case None:
            return None
        case ObligationView.OPEN:
            return Obligation.status.in_(open_values)
        case ObligationView.OVERDUE:
            return _overdue_clause(on)
        case ObligationView.DUE_THIS_WEEK:
            return and_(
                Obligation.status.in_(open_values), Obligation.due_date.between(on, on + timedelta(days=6))
            )
        case ObligationView.IN_PROGRESS:
            # Not "NOT overdue": with no due date that is NULL in SQL and would drop ongoing duties.
            return and_(
                Obligation.status == ObligationStatus.IN_PROGRESS,
                or_(Obligation.due_date.is_(None), Obligation.due_date >= on),
            )
        case ObligationView.PENDING:
            return and_(
                Obligation.status == ObligationStatus.PENDING,
                or_(Obligation.due_date.is_(None), Obligation.due_date >= on),
            )
        case ObligationView.COMPLETED:
            return Obligation.status == ObligationStatus.COMPLETED
        case ObligationView.CANCELLED:
            return Obligation.status == ObligationStatus.CANCELLED


def list_obligations(
    db: Session,
    current: CurrentUser,
    params: PageParams,
    *,
    view: ObligationView | None = None,
    q: str | None = None,
    contract_id: uuid.UUID | None = None,
    property_id: uuid.UUID | None = None,
    party_id: uuid.UUID | None = None,
    responsible_user_id: uuid.UUID | None = None,
    priority: str | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    sort: ObligationSort = ObligationSort.DUE_DATE,
) -> tuple[list[Obligation], int]:
    """FR-OBL-07. `q` matches the title, the contract number or title, or the responsible party."""
    on = today()
    stmt = select(Obligation).where(obligation_in_scope(current))
    if (condition := _view_filter(view, on)) is not None:
        stmt = stmt.where(condition)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Obligation.title.ilike(pattern),
                Obligation.contract.has(
                    or_(Contract.contract_number.ilike(pattern), Contract.title.ilike(pattern))
                ),
                Obligation.responsible_party.has(Party.display_name.ilike(pattern)),
            )
        )
    if contract_id is not None:
        stmt = stmt.where(Obligation.contract_id == contract_id)
    if property_id is not None:  # FR-PROP-02: the obligations of a property's contracts
        stmt = stmt.where(
            Obligation.contract_id.in_(
                select(contract_properties.c.contract_id).where(
                    contract_properties.c.property_id == property_id
                )
            )
        )
    if party_id is not None:
        stmt = stmt.where(Obligation.responsible_party_id == party_id)
    if responsible_user_id is not None:
        stmt = stmt.where(Obligation.responsible_user_id == responsible_user_id)
    if priority:
        stmt = stmt.where(Obligation.priority == priority)
    if due_from is not None:
        stmt = stmt.where(Obligation.due_date >= due_from)
    if due_to is not None:
        stmt = stmt.where(Obligation.due_date <= due_to)
    stmt = stmt.order_by(*_SORTS[sort], Obligation.title, Obligation.id)
    return paginate(db, stmt, params)


def count_by_view(db: Session, current: CurrentUser) -> ObligationCounts:
    on = today()

    def count(view: ObligationView) -> int:
        condition = _view_filter(view, on)
        stmt = select(func.count()).select_from(Obligation).where(obligation_in_scope(current))
        return db.scalar(stmt.where(condition) if condition is not None else stmt) or 0

    return ObligationCounts(**{view.value: count(view) for view in ObligationView})


def get_obligation(db: Session, current: CurrentUser, obligation_id: uuid.UUID) -> Obligation:
    """Out-of-scope obligations are reported as not found, so their existence is not revealed."""
    obligation = db.scalar(
        select(Obligation).where(Obligation.id == obligation_id, obligation_in_scope(current))
    )
    if obligation is None:
        raise NotFoundError("Obligation not found.")
    return obligation


def evidence_counts(db: Session, ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not ids:
        return {}
    rows = db.execute(
        select(ContractDocument.obligation_id, func.count())
        .where(ContractDocument.obligation_id.in_(ids))
        .group_by(ContractDocument.obligation_id)
    )
    return {row[0]: row[1] for row in rows if row[0] is not None}


def contract_summaries(
    db: Session, current: CurrentUser, contract_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, ObligationSummary]:
    """Open and overdue obligations per contract, counting only obligations the user can see."""
    if not contract_ids:
        return {}
    on = today()
    open_values = [s.value for s in OPEN_STATUSES]
    rows = db.execute(
        select(
            Obligation.contract_id,
            func.count().filter(Obligation.status.in_(open_values)),
            func.count().filter(_overdue_clause(on)),
        )
        .where(Obligation.contract_id.in_(contract_ids), obligation_in_scope(current))
        .group_by(Obligation.contract_id)
    )
    found = {row[0]: ObligationSummary(open=row[1], overdue=row[2]) for row in rows}
    return {cid: found.get(cid, ObligationSummary(open=0, overdue=0)) for cid in contract_ids}


# --- writing ------------------------------------------------------------------------------------------------


def _writable_contract(db: Session, current: CurrentUser, contract_id: uuid.UUID) -> Contract:
    try:
        contract = contracts_service.get_contract(db, current, contract_id)
    except NotFoundError:
        raise _field_error("contract_id", "Choose a contract you can see.") from None  # FR-OBL-01
    if contract.archived_at is not None:
        raise BusinessRuleError("The contract is archived. Restore it to change its obligations.")
    return contract


def _check_party(contract: Contract, party_id: uuid.UUID) -> Party:
    for link in contract.parties:
        if link.party_id == party_id:
            return link.party
    raise _field_error("responsible_party_id", "Choose one of the contract's parties.")


def _check_user(db: Session, user_id: uuid.UUID | None) -> User | None:
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _field_error("responsible_user_id", "Choose an active user.")
    return user


def _check_dates(start: date | None, due: date | None) -> None:
    if start is not None and due is not None and due < start:
        raise _field_error("due_date", "Due date can't be earlier than the start date.")


def _check_rule(rule: str | None, due: date | None, first_due: date | None = None) -> str | None:
    if rule is None:
        return None
    if due is None:
        raise _field_error("due_date", "A repeating obligation needs a due date.")
    try:
        return recurrence.normalise(rule, first_due or due)
    except recurrence.InvalidRecurrenceError as exc:
        raise _field_error("recurrence_rule", str(exc)) from None  # BR-08


def create_obligation(db: Session, current: CurrentUser, data: ObligationCreate) -> Obligation:
    contract = _writable_contract(db, current, data.contract_id)
    party = _check_party(contract, data.responsible_party_id)
    user = _check_user(db, data.responsible_user_id)
    if data.status not in OPEN_STATUSES:
        raise _field_error("status", "A new obligation is pending or in progress.")
    _check_dates(data.start_date, data.due_date)
    rule = _check_rule(data.recurrence_rule, data.due_date)
    obligation_id = uuid.uuid4()
    obligation = Obligation(
        id=obligation_id,
        contract=contract,
        title=data.title,
        description=data.description,
        responsible_party=party,
        responsible_user=user,
        start_date=data.start_date,
        due_date=data.due_date,
        priority=data.priority,
        status=data.status,
        recurrence_rule=rule,
        series_id=obligation_id if rule else None,
        penalty_text=data.penalty_text,
        notes=data.notes,
        created_by_id=current.id,
        updated_by_id=current.id,
    )
    db.add(obligation)
    _record(
        db,
        AuditAction.OBLIGATION_CREATED,
        obligation,
        actor_id=current.id,
        changes={k: [None, v] for k, v in _snapshot(obligation).items() if v is not None},
    )
    db.commit()
    db.refresh(obligation)
    return obligation


def update_obligation(
    db: Session, current: CurrentUser, obligation_id: uuid.UUID, data: ObligationUpdate
) -> Obligation:
    obligation = get_obligation(db, current, obligation_id)
    if current.data_scope == DataScope.ASSIGNED_OBLIGATIONS:
        raise ForbiddenError(
            "You can update the status of the obligations assigned to you, not their details."
        )
    contract = _writable_contract(db, current, obligation.contract_id)
    sent = data.model_dump(exclude_unset=True)
    for required in ("title", "description", "responsible_party_id", "priority"):
        if required in sent and sent[required] is None:
            raise _field_error(required, "This field is required.")

    def new(field: str) -> Any:
        return sent[field] if field in sent else getattr(obligation, field)

    party = _check_party(contract, sent["responsible_party_id"]) if "responsible_party_id" in sent else None
    user = _check_user(db, sent["responsible_user_id"]) if "responsible_user_id" in sent else None
    _check_dates(new("start_date"), new("due_date"))
    first_due = None
    if obligation.series_id and obligation.series_id != obligation.id:
        first_due = db.scalar(select(Obligation.due_date).where(Obligation.id == obligation.series_id))
    rule = _check_rule(new("recurrence_rule"), new("due_date"), first_due)

    before = _snapshot(obligation)
    for field in ("title", "description", "start_date", "due_date", "priority", "penalty_text", "notes"):
        if field in sent:
            setattr(obligation, field, sent[field])
    if party is not None:
        obligation.responsible_party = party
    if "responsible_user_id" in sent:
        obligation.responsible_user = user
    obligation.recurrence_rule = rule
    if rule and obligation.series_id is None:
        obligation.series_id = obligation.id
    if obligation.overdue_at is not None and not is_overdue(obligation):
        obligation.overdue_at = None  # moved out of overdue: it may be reported again later
    if changes := audit.changes_between(before, _snapshot(obligation)):
        _record(db, AuditAction.OBLIGATION_UPDATED, obligation, actor_id=current.id, changes=changes)
        obligation.updated_by_id = current.id
    db.commit()
    db.refresh(obligation)
    return obligation


def change_status(
    db: Session, current: CurrentUser, obligation_id: uuid.UUID, data: StatusChange
) -> Obligation:
    """FR-OBL-04. Completing or cancelling an occurrence of a series creates the next one (FR-OBL-06)."""
    obligation = get_obligation(db, current, obligation_id)
    _writable_contract(db, current, obligation.contract_id)
    old = ObligationStatus(obligation.status)
    if data.status == old and not data.note:
        return obligation
    now = _now()
    obligation.status = data.status
    obligation.completed_at = now if data.status == ObligationStatus.COMPLETED else None
    obligation.cancelled_at = now if data.status == ObligationStatus.CANCELLED else None
    if data.status not in OPEN_STATUSES:
        obligation.overdue_at = None
    obligation.updated_by_id = current.id
    changes: dict[str, Any] = {"status": [old.value, data.status.value]} if data.status != old else {}
    if data.note:
        changes["note"] = [None, data.note]
    _record(db, AuditAction.OBLIGATION_STATUS_CHANGED, obligation, actor_id=current.id, changes=changes)
    if obligation.series_id and data.status not in OPEN_STATUSES:
        _roll_series(db, obligation.series_id, today(), actor_id=current.id)
    db.commit()
    db.refresh(obligation)
    return obligation


# --- recurrence and overdue (also run daily by the scheduler) ------------------------------------------------


def _roll_series(db: Session, series_id: uuid.UUID, on: date, *, actor_id: uuid.UUID | None) -> int:
    """Create the next occurrence while the latest one is closed or past its due date. Returns how many."""
    first = db.get(Obligation, series_id)
    if first is None or first.due_date is None:
        return 0
    created = 0
    for _ in range(_MAX_ROLL):
        latest = db.scalar(
            select(Obligation)
            .where(Obligation.series_id == series_id)
            .order_by(Obligation.due_date.desc(), Obligation.created_at.desc())
            .limit(1)
        )
        if latest is None or latest.due_date is None or not latest.recurrence_rule:
            break
        contract = latest.contract
        if contract.archived_at is not None or contract.status.code not in (
            StatusCode.DRAFT,
            StatusCode.ACTIVE,
        ):
            break
        if latest.status in OPEN_STATUSES and latest.due_date >= on:
            break
        following = recurrence.next_due(latest.recurrence_rule, first.due_date, latest.due_date)
        if following is None:
            break  # the series has ended (COUNT / UNTIL)
        occurrence = Obligation(
            id=uuid.uuid4(),
            contract=contract,
            title=latest.title,
            description=latest.description,
            responsible_party=latest.responsible_party,
            responsible_user=latest.responsible_user,
            due_date=following,
            priority=latest.priority,
            status=ObligationStatus.PENDING,
            recurrence_rule=latest.recurrence_rule,
            series_id=series_id,
            penalty_text=latest.penalty_text,
            notes=latest.notes,
            created_by_id=actor_id,
            updated_by_id=actor_id,
        )
        db.add(occurrence)
        db.flush()
        _record(
            db,
            AuditAction.OBLIGATION_CREATED,
            occurrence,
            actor_id=actor_id,
            changes={"due_date": [None, following.isoformat()], "series": [None, first.title]},
        )
        created += 1
    return created


def roll_recurrences(db: Session, on: date | None = None) -> int:
    """Daily: make sure every live series has its next occurrence (FR-OBL-06)."""
    on = on or today()
    series_ids = db.scalars(select(Obligation.series_id).where(Obligation.series_id.is_not(None)).distinct())
    created = sum(
        _roll_series(db, series_id, on, actor_id=None) for series_id in list(series_ids) if series_id
    )
    db.commit()
    return created


def mark_overdue(db: Session, on: date | None = None) -> list[Obligation]:
    """Daily: record obligations that became overdue (FR-OBL-05, BR-04). Notifications build on this (module 8)."""
    on = on or today()
    newly = list(db.scalars(select(Obligation).where(_overdue_clause(on), Obligation.overdue_at.is_(None))))
    now = _now()
    for obligation in newly:
        obligation.overdue_at = now
        _record(
            db,
            AuditAction.OBLIGATION_OVERDUE,
            obligation,
            actor_id=None,
            changes={"due_date": [None, obligation.due_date.isoformat() if obligation.due_date else None]},
        )
    db.commit()
    return newly
