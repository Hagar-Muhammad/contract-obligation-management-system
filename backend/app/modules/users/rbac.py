"""Default roles and permissions: SRS 2.3 and the 3.2 matrix (docs/roles-and-permissions.md).

This catalog is the reference the seed migration was written from, and the test suite checks that the
database matches it. The database is authoritative at runtime; change both via a new migration.
"""

from collections.abc import Iterable
from enum import StrEnum


class Perm(StrEnum):
    CONTRACT_VIEW = "contract:view"
    CONTRACT_CREATE = "contract:create"
    CONTRACT_EDIT = "contract:edit"
    CONTRACT_ARCHIVE = "contract:archive"
    DOCUMENT_VIEW = "document:view"
    DOCUMENT_UPLOAD = "document:upload"
    EXTRACTION_RUN = "extraction:run"
    EXTRACTION_CONFIRM = "extraction:confirm"
    OBLIGATION_VIEW = "obligation:view"
    OBLIGATION_CREATE = "obligation:create"
    OBLIGATION_UPDATE = "obligation:update"
    PARTY_MANAGE = "party:manage"
    PROPERTY_MANAGE = "property:manage"
    REPORT_VIEW = "report:view"
    REPORT_EXPORT = "report:export"
    USER_MANAGE = "user:manage"
    ROLE_MANAGE = "role:manage"
    AUDIT_VIEW = "audit:view"


PERMISSION_DESCRIPTIONS: dict[Perm, str] = {
    Perm.CONTRACT_VIEW: "View contracts",
    Perm.CONTRACT_CREATE: "Create contracts",
    Perm.CONTRACT_EDIT: "Edit contracts",
    Perm.CONTRACT_ARCHIVE: "Archive and restore contracts",
    Perm.DOCUMENT_VIEW: "View and download contract documents",
    Perm.DOCUMENT_UPLOAD: "Upload contract documents",
    Perm.EXTRACTION_RUN: "Start extraction on a document",
    Perm.EXTRACTION_CONFIRM: "Review and confirm extracted data",
    Perm.OBLIGATION_VIEW: "View obligations",
    Perm.OBLIGATION_CREATE: "Create obligations",
    Perm.OBLIGATION_UPDATE: "Update obligations and their status",
    Perm.PARTY_MANAGE: "Create and update parties",
    Perm.PROPERTY_MANAGE: "Create and update properties and assignments",
    Perm.REPORT_VIEW: "View dashboards and reports",
    Perm.REPORT_EXPORT: "Export report data",
    Perm.USER_MANAGE: "Manage user accounts and their roles",
    Perm.ROLE_MANAGE: "Change role permissions",
    Perm.AUDIT_VIEW: "Read the audit log",
}


class DataScope(StrEnum):
    """Which records a role can see (applied in services, docs/roles-and-permissions.md)."""

    ALL = "all"
    ASSIGNED_PROPERTIES = "assigned_properties"
    ASSIGNED_OBLIGATIONS = "assigned_obligations"


# Widest first. A user holding several roles gets the widest scope among them.
_SCOPE_ORDER = (DataScope.ALL, DataScope.ASSIGNED_PROPERTIES, DataScope.ASSIGNED_OBLIGATIONS)


def widest_scope(scopes: Iterable[str]) -> DataScope:
    present = set(scopes)
    return next((scope for scope in _SCOPE_ORDER if scope in present), DataScope.ASSIGNED_OBLIGATIONS)


class RoleCode(StrEnum):
    ADMIN = "admin"
    CONTRACT_MANAGER = "contract_manager"
    LEGAL = "legal"
    PROPERTY_MANAGER = "property_manager"
    EMPLOYEE = "employee"
    MANAGEMENT = "management"


ROLE_DEFINITIONS: dict[RoleCode, tuple[str, str, DataScope]] = {
    RoleCode.ADMIN: (
        "Administrator",
        "Manage users, roles, permissions, and system settings.",
        DataScope.ALL,
    ),
    RoleCode.CONTRACT_MANAGER: (
        "Contract Manager",
        "Manage contracts, parties, documents, and obligations.",
        DataScope.ALL,
    ),
    RoleCode.LEGAL: (
        "Legal User",
        "Review contract information, extracted data, and obligations.",
        DataScope.ALL,
    ),
    RoleCode.PROPERTY_MANAGER: (
        "Property Manager",
        "Manage contracts and obligations related to assigned properties.",
        DataScope.ASSIGNED_PROPERTIES,
    ),
    RoleCode.EMPLOYEE: (
        "Employee / Responsible User",
        "View and complete assigned obligations and update status.",
        DataScope.ASSIGNED_OBLIGATIONS,
    ),
    RoleCode.MANAGEMENT: (
        "Management",
        "View dashboards, reports, contract status, and obligation summaries.",
        DataScope.ALL,
    ),
}

P = Perm

# SRS 3.2. "Allowed" cells are granted and listed again in PENDING_CONFIRMATION below.
ROLE_PERMISSIONS: dict[RoleCode, frozenset[Perm]] = {
    RoleCode.ADMIN: frozenset(Perm),
    RoleCode.CONTRACT_MANAGER: frozenset(
        {
            P.CONTRACT_VIEW,
            P.CONTRACT_CREATE,
            P.CONTRACT_EDIT,
            P.CONTRACT_ARCHIVE,
            P.DOCUMENT_VIEW,
            P.DOCUMENT_UPLOAD,
            P.EXTRACTION_RUN,
            P.EXTRACTION_CONFIRM,
            P.OBLIGATION_VIEW,
            P.OBLIGATION_CREATE,
            P.OBLIGATION_UPDATE,
            P.PARTY_MANAGE,
            P.PROPERTY_MANAGE,
            P.REPORT_VIEW,
            P.REPORT_EXPORT,
        }
    ),
    RoleCode.LEGAL: frozenset(
        {
            P.CONTRACT_VIEW,
            P.CONTRACT_CREATE,
            P.CONTRACT_EDIT,
            P.CONTRACT_ARCHIVE,
            P.DOCUMENT_VIEW,
            P.DOCUMENT_UPLOAD,
            P.EXTRACTION_RUN,
            P.EXTRACTION_CONFIRM,
            P.OBLIGATION_VIEW,
            P.OBLIGATION_CREATE,
            P.OBLIGATION_UPDATE,
            P.PARTY_MANAGE,
            P.REPORT_VIEW,
            P.REPORT_EXPORT,
        }
    ),
    RoleCode.PROPERTY_MANAGER: frozenset(
        {
            P.CONTRACT_VIEW,
            P.CONTRACT_CREATE,
            P.CONTRACT_EDIT,
            P.CONTRACT_ARCHIVE,
            P.DOCUMENT_VIEW,
            P.DOCUMENT_UPLOAD,
            P.EXTRACTION_RUN,
            P.EXTRACTION_CONFIRM,
            P.OBLIGATION_VIEW,
            P.OBLIGATION_CREATE,
            P.OBLIGATION_UPDATE,
            P.PARTY_MANAGE,
            P.REPORT_VIEW,
        }
    ),
    RoleCode.EMPLOYEE: frozenset(
        {
            P.CONTRACT_VIEW,
            P.DOCUMENT_VIEW,
            P.DOCUMENT_UPLOAD,
            P.EXTRACTION_RUN,
            P.OBLIGATION_VIEW,
            P.OBLIGATION_CREATE,
            P.OBLIGATION_UPDATE,
            P.REPORT_VIEW,
        }
    ),
    RoleCode.MANAGEMENT: frozenset(
        {P.CONTRACT_VIEW, P.DOCUMENT_VIEW, P.OBLIGATION_VIEW, P.REPORT_VIEW, P.REPORT_EXPORT}
    ),
}

# Cells marked "Allowed" in SRS 3.2: granted now, to be confirmed by the business (decision D-01).
PENDING_CONFIRMATION: dict[RoleCode, frozenset[Perm]] = {
    RoleCode.CONTRACT_MANAGER: frozenset({P.CONTRACT_ARCHIVE}),
    RoleCode.LEGAL: frozenset({P.CONTRACT_CREATE, P.CONTRACT_EDIT, P.CONTRACT_ARCHIVE}),
    RoleCode.PROPERTY_MANAGER: frozenset(
        {P.CONTRACT_VIEW, P.CONTRACT_CREATE, P.CONTRACT_EDIT, P.CONTRACT_ARCHIVE, P.EXTRACTION_CONFIRM}
    ),
    RoleCode.EMPLOYEE: frozenset({P.CONTRACT_VIEW, P.DOCUMENT_UPLOAD, P.OBLIGATION_CREATE}),
}
