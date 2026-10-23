"""Which contracts a user may see (docs/roles-and-permissions.md, data scope).

Other modules derive their own scope from this one: the parties and properties of visible contracts, and later the
documents and obligations of visible contracts.
"""

import uuid

from sqlalchemy import ColumnElement, Select, false, select, true

from app.modules.auth.dependencies import CurrentUser
from app.modules.contracts.models import Contract, contract_properties
from app.modules.properties.models import property_assignments
from app.modules.users.rbac import DataScope


def contract_in_scope(current: CurrentUser) -> ColumnElement[bool]:
    match current.data_scope:
        case DataScope.ALL:
            return true()
        case DataScope.ASSIGNED_PROPERTIES:
            # Contracts on at least one property assigned to the user.
            return Contract.id.in_(
                select(contract_properties.c.contract_id)
                .join(
                    property_assignments,
                    property_assignments.c.property_id == contract_properties.c.property_id,
                )
                .where(property_assignments.c.user_id == current.id)
            )
        case _:
            # Employees: the contracts of obligations assigned to them, from module 6 (obligations).
            return false()


def visible_contract_ids(current: CurrentUser) -> Select[uuid.UUID]:
    return select(Contract.id).where(contract_in_scope(current))
