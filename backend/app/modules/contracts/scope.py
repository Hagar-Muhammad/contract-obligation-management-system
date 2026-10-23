"""Which contracts a user may see (docs/roles-and-permissions.md, data scope).

Other modules derive their own scope from this one: the parties, properties, documents and obligations of visible
contracts.
"""

import uuid

from sqlalchemy import ColumnElement, Select, or_, select, true

from app.modules.auth.dependencies import CurrentUser
from app.modules.contracts.models import Contract, contract_properties
from app.modules.obligations.models import Obligation
from app.modules.properties.models import property_assignments
from app.modules.users.rbac import DataScope


def _with_my_obligations(current: CurrentUser) -> ColumnElement[bool]:
    """Contracts of the obligations assigned to the user."""
    return Contract.id.in_(select(Obligation.contract_id).where(Obligation.responsible_user_id == current.id))


def contract_in_scope(current: CurrentUser) -> ColumnElement[bool]:
    match current.data_scope:
        case DataScope.ALL:
            return true()
        case DataScope.ASSIGNED_PROPERTIES:
            # Contracts on a property assigned to the user, and contracts of obligations assigned to them.
            on_my_property = Contract.id.in_(
                select(contract_properties.c.contract_id)
                .join(
                    property_assignments,
                    property_assignments.c.property_id == contract_properties.c.property_id,
                )
                .where(property_assignments.c.user_id == current.id)
            )
            return or_(on_my_property, _with_my_obligations(current))
        case _:
            return _with_my_obligations(current)


def visible_contract_ids(current: CurrentUser) -> Select[uuid.UUID]:
    return select(Contract.id).where(contract_in_scope(current))


def obligation_in_scope(current: CurrentUser) -> ColumnElement[bool]:
    """Employees see the obligations assigned to them; Property Managers also those of their contracts."""
    match current.data_scope:
        case DataScope.ALL:
            return true()
        case DataScope.ASSIGNED_PROPERTIES:
            return or_(
                Obligation.contract_id.in_(visible_contract_ids(current)),
                Obligation.responsible_user_id == current.id,
            )
        case _:
            return Obligation.responsible_user_id == current.id
