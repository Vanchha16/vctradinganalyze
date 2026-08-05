"""One-off, operator-run bootstrap: creates the very first Super Admin
account (Phase 8E, docs/59 §9/§12, ADR-123). Public self-registration is
closed (`settings.allow_public_registration=False`), so this is the only
way the platform's first account comes into existence - every account
after this one is created through `POST /admin/users` (`AdminUserService`).

Deliberately not automatic/env-var-driven (ADR-123 explicitly rejected
that option) - this script must be run once, manually, by an operator.
Refuses to run again once any `super_admin` row exists, so it cannot be
used to mint a second bootstrap account by accident.

Usage: python scripts/create_admin.py
"""

import getpass
import sys

from app.database.session import SessionLocal
from app.exceptions import AppException
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService

_EMAIL_PATTERN_HINT = "must look like name@example.com"


def _prompt_email() -> str:
    while True:
        value = input("Email: ").strip()
        if "@" in value and "." in value.split("@")[-1]:
            return value
        print(f"  Invalid email - {_EMAIL_PATTERN_HINT}")


def _prompt_username() -> str:
    while True:
        value = input("Username: ").strip()
        if 3 <= len(value) <= 50:
            return value
        print("  Username must be 3-50 characters.")


def _prompt_password() -> str:
    while True:
        password = getpass.getpass("Password (input hidden): ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("  Passwords do not match - try again.")
            continue
        return password


def main() -> int:
    session = SessionLocal()
    try:
        user_repository = UserRepository(session)

        existing_super_admins = user_repository.count_by_role(UserRole.SUPER_ADMIN)
        if existing_super_admins > 0:
            print(
                "A Super Admin account already exists - bootstrap has already run. "
                "Use `POST /admin/users` (as an existing admin) to create additional accounts."
            )
            return 1

        print("=== ClaudeTrading AI - First Super Admin Setup ===")
        print("This creates the platform's first account. It can only run once.\n")

        email = _prompt_email()
        username = _prompt_username()
        password = _prompt_password()

        user_service = UserService(user_repository)
        try:
            user = user_service.register_user(
                email=email,
                username=username,
                password=password,
                role=UserRole.SUPER_ADMIN,
                must_change_password=False,
                created_by_admin_id=None,
            )
        except AppException as exc:
            print(f"\nFailed: {exc.message}")
            return 1

        print("\nSuper Admin account created successfully:")
        print(f"  id:       {user.id}")
        print(f"  email:    {user.email}")
        print(f"  username: {user.username}")
        print(f"  role:     {user.role.value}")
        print(f"  created:  {user.created_at}")
        print("\n(Password not shown - it was set exactly as entered above.)")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
