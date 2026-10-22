"""What the audit trail records (FR-AUD-01).

Actions are named `<target>.<verb>`. Each module adds its own members here; the database column is plain text,
so a new action needs no migration. docs/api-standards.md §8 says which changes must be audited.
"""

from enum import StrEnum


class AuditAction(StrEnum):
    AUTH_LOGIN = "auth.login"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_LOGOUT = "auth.logout"
    AUTH_REFRESH_TOKEN_REUSED = "auth.refresh_token_reused"  # noqa: S105 (action name, not a secret)
    USER_CREATED = "user.created"
    USER_REGISTERED = "user.registered"
    USER_UPDATED = "user.updated"
    USER_PASSWORD_RESET = "user.password_reset"  # noqa: S105 (action name, not a secret)
    USER_DEACTIVATED = "user.deactivated"
    USER_ACTIVATED = "user.activated"
    PARTY_CREATED = "party.created"
    PARTY_UPDATED = "party.updated"
    PROPERTY_CREATED = "property.created"
    PROPERTY_UPDATED = "property.updated"


class ActorType(StrEnum):
    USER = "user"
    # Scheduled jobs, operational commands and automatic security responses.
    SYSTEM = "system"
    # Someone who has not proven who they are, e.g. a failed sign-in.
    ANONYMOUS = "anonymous"


class TargetType(StrEnum):
    USER = "user"
    PARTY = "party"
    PROPERTY = "property"
