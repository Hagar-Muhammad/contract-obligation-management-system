import itertools

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.users.models import Role, User

DEFAULT_PASSWORD = "Correct-Horse-9"

# Hashing is deliberately slow; reuse one hash for every factory user with the default password.
_DEFAULT_HASH = hash_password(DEFAULT_PASSWORD)
_sequence = itertools.count(1)


class UserFactory:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *roles: str,
        email: str | None = None,
        full_name: str | None = None,
        password: str | None = None,
        is_active: bool = True,
    ) -> User:
        n = next(_sequence)
        role_codes = roles or ("employee",)
        user = User(
            email=(email or f"user{n}@example.com").lower(),
            full_name=full_name or f"Test User {n}",
            password_hash=hash_password(password) if password else _DEFAULT_HASH,
            is_active=is_active,
            roles=list(self.db.scalars(select(Role).where(Role.code.in_(role_codes)))),
        )
        assert len(user.roles) == len(set(role_codes)), f"unknown role in {role_codes}"
        self.db.add(user)
        self.db.commit()
        return user
