import re
import uuid

from app.core.security import hash_password
from app.exceptions import DuplicateUserException, ResourceNotFoundException, WeakPasswordException
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository

_MIN_PASSWORD_LENGTH = 12
_PASSWORD_RULES: dict[str, re.Pattern[str]] = {
    "uppercase": re.compile(r"[A-Z]"),
    "lowercase": re.compile(r"[a-z]"),
    "number": re.compile(r"\d"),
    "special character": re.compile(r"[^A-Za-z0-9]"),
}


def _validate_password_strength(password: str) -> None:
    """Enforce the password policy in docs/23_AUTHENTICATION_AND_RBAC.md §7."""
    if len(password) < _MIN_PASSWORD_LENGTH:
        raise WeakPasswordException(
            f"Password must be at least {_MIN_PASSWORD_LENGTH} characters long."
        )
    for rule_name, pattern in _PASSWORD_RULES.items():
        if not pattern.search(password):
            raise WeakPasswordException(f"Password must contain at least one {rule_name}.")


class UserService:
    """Business rules for user registration and lookup.

    No SQL lives here - all persistence goes through `UserRepository`.
    """

    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    def register_user(
        self,
        *,
        email: str,
        username: str,
        password: str,
        full_name: str | None = None,
        role: UserRole = UserRole.REGISTERED,
        must_change_password: bool = False,
        created_by_admin_id: uuid.UUID | None = None,
    ) -> User:
        """`role`/`must_change_password`/`created_by_admin_id` are additive
        (Phase 8, docs/59 §3.3/ADR-119) - every pre-Phase-8 caller (the
        public register route) omits them and gets the exact prior
        behavior. `AdminUserService.create_user` is the only caller that
        passes them, reusing this method rather than duplicating
        validation/uniqueness logic so the two entry points never drift."""
        _validate_password_strength(password)

        if self._user_repository.get_by_email(email) is not None:
            raise DuplicateUserException("Email is already registered.")
        if self._user_repository.get_by_username(username) is not None:
            raise DuplicateUserException("Username is already taken.")

        user = User(
            email=email,
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
            must_change_password=must_change_password,
            created_by_admin_id=created_by_admin_id,
        )
        self._user_repository.create(user)
        self._user_repository.commit()
        return user

    def get_user_by_id(self, user_id: uuid.UUID) -> User:
        user = self._user_repository.get_by_id(user_id)
        if user is None:
            raise ResourceNotFoundException("User not found.")
        return user

    def get_user_by_email(self, email: str) -> User:
        user = self._user_repository.get_by_email(email)
        if user is None:
            raise ResourceNotFoundException("User not found.")
        return user
