import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.exceptions import DuplicateUserException, ResourceNotFoundException, WeakPasswordException
from app.models.audit_log import AuditLog
from app.models.oauth_account import OAuthAccount
from app.models.user import User
from app.models.user_session import UserSession
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService

_TABLES = [
    User.__table__,
    UserSession.__table__,
    OAuthAccount.__table__,
    AuditLog.__table__,
]

_STRONG_PASSWORD = "Correct-Horse9"


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


@pytest.fixture
def user_service(session: Session) -> UserService:
    return UserService(UserRepository(session))


def test_register_user_success(user_service: UserService, session: Session) -> None:
    user = user_service.register_user(
        email="trader@example.com", username="trader", password=_STRONG_PASSWORD
    )

    assert user.email == "trader@example.com"
    assert user.password_hash != _STRONG_PASSWORD
    session.commit()


@pytest.mark.parametrize(
    "password",
    [
        "short1A!",  # too short
        "alllowercase123!",  # no uppercase
        "ALLUPPERCASE123!",  # no lowercase
        "NoNumbersHere!!",  # no digit
        "NoSpecialChar123",  # no special character
    ],
)
def test_register_user_rejects_weak_password(user_service: UserService, password: str) -> None:
    with pytest.raises(WeakPasswordException):
        user_service.register_user(email="trader@example.com", username="trader", password=password)


def test_register_user_rejects_duplicate_email(user_service: UserService, session: Session) -> None:
    user_service.register_user(
        email="trader@example.com", username="trader", password=_STRONG_PASSWORD
    )
    session.commit()

    with pytest.raises(DuplicateUserException):
        user_service.register_user(
            email="trader@example.com", username="other", password=_STRONG_PASSWORD
        )


def test_register_user_rejects_duplicate_username(
    user_service: UserService, session: Session
) -> None:
    user_service.register_user(
        email="trader@example.com", username="trader", password=_STRONG_PASSWORD
    )
    session.commit()

    with pytest.raises(DuplicateUserException):
        user_service.register_user(
            email="other@example.com", username="trader", password=_STRONG_PASSWORD
        )


def test_get_user_by_id_success(user_service: UserService, session: Session) -> None:
    created = user_service.register_user(
        email="trader@example.com", username="trader", password=_STRONG_PASSWORD
    )
    session.commit()

    found = user_service.get_user_by_id(created.id)
    assert found.id == created.id


def test_get_user_by_id_raises_when_missing(user_service: UserService) -> None:
    with pytest.raises(ResourceNotFoundException):
        user_service.get_user_by_id(uuid.uuid4())


def test_get_user_by_email_raises_when_missing(user_service: UserService) -> None:
    with pytest.raises(ResourceNotFoundException):
        user_service.get_user_by_email("nobody@example.com")
