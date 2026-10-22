"""Property register and Property Manager assignments (SRS 4.6; groundwork for FR-PROP-01/02).

Who sees properties: users whose data scope is all records see every property; Property Managers see the properties
assigned to them; other users see none until contracts and obligations exist (modules 4 and 6 widen this).
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, false, or_, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.core.pagination import PageParams, paginate
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction, TargetType
from app.modules.auth.dependencies import CurrentUser
from app.modules.properties.models import Property, property_assignments
from app.modules.properties.schemas import PropertyCreate, PropertyType, PropertyUpdate
from app.modules.users.models import Role, User
from app.modules.users.rbac import DataScope, RoleCode

AUDITED_FIELDS = ("code", "name", "property_type", "address", "city", "country", "area_sqm", "notes")
ASSIGNABLE_LIMIT = 50


def _in_scope(stmt: Select[Property], current: CurrentUser) -> Select[Property]:
    match current.data_scope:
        case DataScope.ALL:
            return stmt
        case DataScope.ASSIGNED_PROPERTIES:
            return stmt.where(
                Property.id.in_(
                    select(property_assignments.c.property_id).where(
                        property_assignments.c.user_id == current.id
                    )
                )
            )
        case _:
            return stmt.where(false())


def _snapshot(prop: Property) -> dict[str, Any]:
    values = {field: getattr(prop, field) for field in AUDITED_FIELDS}
    # JSON-friendly values for the audit record.
    values["area_sqm"] = f"{prop.area_sqm:.2f}" if prop.area_sqm is not None else None
    values["managers"] = sorted(user.full_name for user in prop.managers)
    return values


def _ensure_code_free(db: Session, code: str, *, except_id: uuid.UUID | None = None) -> None:
    stmt = select(Property.name).where(Property.code == code)
    if except_id is not None:
        stmt = stmt.where(Property.id != except_id)
    existing = db.scalar(stmt)
    if existing is not None:
        raise ConflictError(
            f"{existing} already uses this code.",
            details=[{"field": "body.code", "message": f"Already used by {existing}."}],
        )


def _assignable() -> Select[User]:
    """Active users holding the Property Manager role: the only role whose scope comes from assignments."""
    return (
        select(User)
        .where(User.is_active.is_(True), User.roles.any(Role.code == RoleCode.PROPERTY_MANAGER))
        .order_by(User.full_name, User.email)
    )


def _managers(db: Session, ids: Sequence[uuid.UUID]) -> list[User]:
    wanted = set(ids)
    users = list(db.scalars(_assignable().where(User.id.in_(wanted))))
    if len(users) != len(wanted):
        raise BusinessRuleError(
            "Only active Property Managers can be assigned to a property.",
            details=[
                {
                    "field": "body.manager_ids",
                    "message": "Choose active users with the Property Manager role.",
                }
            ],
        )
    return users


def list_properties(
    db: Session,
    current: CurrentUser,
    params: PageParams,
    *,
    q: str | None = None,
    property_type: PropertyType | None = None,
    manager_id: uuid.UUID | None = None,
) -> tuple[list[Property], int]:
    """Alphabetical by name. `q` matches code, name, city or address."""
    stmt = _in_scope(select(Property), current).order_by(Property.name, Property.code)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Property.code.ilike(pattern),
                Property.name.ilike(pattern),
                Property.city.ilike(pattern),
                Property.address.ilike(pattern),
            )
        )
    if property_type is not None:
        stmt = stmt.where(Property.property_type == property_type)
    if manager_id is not None:
        stmt = stmt.where(Property.managers.any(User.id == manager_id))
    return paginate(db, stmt, params)


def get_property(db: Session, current: CurrentUser, property_id: uuid.UUID) -> Property:
    """Out-of-scope properties are reported as not found, so their existence is not revealed."""
    prop = db.scalar(_in_scope(select(Property), current).where(Property.id == property_id))
    if prop is None:
        raise NotFoundError("Property not found.")
    return prop


def list_assignable_managers(db: Session, *, q: str | None = None) -> list[User]:
    stmt = _assignable()
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))
    return list(db.scalars(stmt.limit(ASSIGNABLE_LIMIT)))


def create_property(db: Session, current: CurrentUser, data: PropertyCreate) -> Property:
    _ensure_code_free(db, data.code)
    prop = Property(
        id=uuid.uuid4(),
        **data.model_dump(exclude={"manager_ids"}),
        managers=_managers(db, data.manager_ids),
        created_by_id=current.id,
        updated_by_id=current.id,
    )
    db.add(prop)
    audit.record(
        db,
        AuditAction.PROPERTY_CREATED,
        target_type=TargetType.PROPERTY,
        target_id=prop.id,
        target_label=f"{prop.code} · {prop.name}",
        actor_id=current.id,
        changes={field: [None, value] for field, value in _snapshot(prop).items() if value not in (None, [])},
    )
    db.commit()
    db.refresh(prop)
    return prop


def update_property(
    db: Session, current: CurrentUser, property_id: uuid.UUID, data: PropertyUpdate
) -> Property:
    prop = get_property(db, current, property_id)
    sent = data.model_dump(exclude_unset=True)
    for required in ("code", "name", "property_type"):
        if required in sent and sent[required] is None:
            raise BusinessRuleError(
                "This field is required.", details=[{"field": f"body.{required}", "message": "Required."}]
            )
    if "code" in sent and sent["code"] != prop.code:
        _ensure_code_free(db, sent["code"], except_id=prop.id)

    before = _snapshot(prop)
    manager_ids = sent.pop("manager_ids", None)
    for field, value in sent.items():
        setattr(prop, field, value)
    if manager_ids is not None:
        prop.managers = _managers(db, manager_ids)
    if changes := audit.changes_between(before, _snapshot(prop)):
        audit.record(
            db,
            AuditAction.PROPERTY_UPDATED,
            target_type=TargetType.PROPERTY,
            target_id=prop.id,
            target_label=f"{prop.code} · {prop.name}",
            actor_id=current.id,
            changes=changes,
        )
        prop.updated_by_id = current.id
    db.commit()
    db.refresh(prop)
    return prop
