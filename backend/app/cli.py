"""Operational commands.

    python -m app.cli create-admin --email admin@example.com --name "System Admin"
    python -m app.cli export-openapi ../frontend/src/api/openapi.json

`create-admin` reads the password from COMS_ADMIN_PASSWORD, or prompts for it.
"""

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select

from app.core.db import SessionLocal
from app.modules.audit.actions import ActorType
from app.modules.users import service as users_service
from app.modules.users.models import Role, User
from app.modules.users.rbac import RoleCode
from app.modules.users.schemas import UserCreate


def create_admin(email: str, name: str) -> int:
    password = os.environ.get("COMS_ADMIN_PASSWORD") or getpass.getpass(
        "Password for the new administrator: "
    )
    try:
        data = UserCreate(email=email, full_name=name, password=password, role_codes=[RoleCode.ADMIN])
    except ValidationError as exc:
        print(f"Invalid input:\n{exc}", file=sys.stderr)
        return 1
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == data.email)) is not None:
            print(f"A user with e-mail {data.email} already exists.", file=sys.stderr)
            return 1
        admin_role = db.scalar(select(Role).where(Role.code == RoleCode.ADMIN))
        if admin_role is None:
            print("Roles are not seeded. Run `alembic upgrade head` first.", file=sys.stderr)
            return 1
        users_service.create_user(db, data, actor_id=None, actor_type=ActorType.SYSTEM)
    print(f"Administrator {data.email} created.")
    return 0


def export_openapi(target: str | None) -> int:
    from app.main import create_app

    document = json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n"
    if target:
        Path(target).write_text(document, encoding="utf-8", newline="\n")
        print(f"OpenAPI document written to {target}")
    else:
        sys.stdout.write(document)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    admin = commands.add_parser("create-admin", help="Create the first administrator account.")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True)

    openapi = commands.add_parser(
        "export-openapi", help="Write the OpenAPI document (used for frontend types)."
    )
    openapi.add_argument("target", nargs="?", help="Output file; stdout when omitted.")

    args = parser.parse_args(argv)
    if args.command == "create-admin":
        return create_admin(args.email, args.name)
    return export_openapi(args.target)


if __name__ == "__main__":
    raise SystemExit(main())
