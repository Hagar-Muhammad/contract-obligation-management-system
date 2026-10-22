"""Role-based permissions: FR-AUTH-03, NFR-SEC-02, SRS 2.3 / 3.2."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.models import Permission, Role
from app.modules.users.rbac import (
    PENDING_CONFIRMATION,
    PERMISSION_DESCRIPTIONS,
    ROLE_DEFINITIONS,
    ROLE_PERMISSIONS,
    Perm,
    RoleCode,
)


@pytest.mark.req("FR-AUTH-03", "NFR-SEC-02")
def test_TC_AUTH_03_seeded_roles_and_permissions_match_the_srs_matrix(db: Session) -> None:
    assert {p.code for p in db.scalars(select(Permission))} == {str(p) for p in Perm}

    roles = {r.code: r for r in db.scalars(select(Role))}
    assert set(roles) == {str(r) for r in RoleCode}
    for code, expected in ROLE_PERMISSIONS.items():
        role = roles[code]
        assert {p.code for p in role.permissions} == {str(p) for p in expected}, code
        name, _, scope = ROLE_DEFINITIONS[code]
        assert (role.name, role.data_scope) == (name, scope)


@pytest.mark.req("FR-AUTH-03")
@pytest.mark.parametrize("role", list(RoleCode))
def test_TC_AUTH_03_users_receive_exactly_their_roles_permissions(
    client: TestClient, auth_headers: Callable[..., dict[str, str]], role: RoleCode
) -> None:
    me = client.get("/api/v1/auth/me", headers=auth_headers(role))

    assert me.status_code == 200
    assert set(me.json()["permissions"]) == {str(p) for p in ROLE_PERMISSIONS[role]}
    assert me.json()["data_scopes"] == [str(ROLE_DEFINITIONS[role][2])]


@pytest.mark.req("FR-AUTH-03")
def test_TC_AUTH_03_multiple_roles_grant_the_union_of_permissions(
    client: TestClient, auth_headers: Callable[..., dict[str, str]]
) -> None:
    me = client.get("/api/v1/auth/me", headers=auth_headers("employee", "management")).json()

    expected = ROLE_PERMISSIONS[RoleCode.EMPLOYEE] | ROLE_PERMISSIONS[RoleCode.MANAGEMENT]
    assert set(me["permissions"]) == {str(p) for p in expected}
    assert me["roles"] == ["employee", "management"]


def test_srs_matrix_details_are_encoded() -> None:
    """Spot checks against the 3.2 table, so an accidental edit of the catalog is caught."""
    assert Perm.USER_MANAGE in ROLE_PERMISSIONS[RoleCode.ADMIN]
    assert all(
        Perm.USER_MANAGE not in perms for role, perms in ROLE_PERMISSIONS.items() if role != RoleCode.ADMIN
    )
    # "Update assigned obligations: View" for Management -> read-only.
    assert Perm.OBLIGATION_UPDATE not in ROLE_PERMISSIONS[RoleCode.MANAGEMENT]
    assert Perm.OBLIGATION_VIEW in ROLE_PERMISSIONS[RoleCode.MANAGEMENT]
    # Employees cannot create/edit/archive contracts or confirm extraction.
    assert (
        not {Perm.CONTRACT_CREATE, Perm.CONTRACT_EDIT, Perm.CONTRACT_ARCHIVE, Perm.EXTRACTION_CONFIRM}
        & (ROLE_PERMISSIONS[RoleCode.EMPLOYEE])
    )
    # Every "Allowed" cell is granted.
    for role, pending in PENDING_CONFIRMATION.items():
        assert pending <= ROLE_PERMISSIONS[role], role
    assert set(PERMISSION_DESCRIPTIONS) == set(Perm)


def test_roles_endpoint_lists_roles_with_permissions(
    client: TestClient, auth_headers: Callable[..., dict[str, str]]
) -> None:
    response = client.get("/api/v1/roles", headers=auth_headers("admin"))

    assert response.status_code == 200
    by_code = {r["code"]: r for r in response.json()}
    assert set(by_code) == {str(r) for r in RoleCode}
    assert by_code["property_manager"]["data_scope"] == "assigned_properties"
    assert "contract:view" in by_code["employee"]["permissions"]
