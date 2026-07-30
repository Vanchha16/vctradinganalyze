import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.system_setting import SystemSetting
from app.repositories.system_setting_repository import SystemSettingRepository


def test_create_and_get_by_key() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[SystemSetting.__table__])

    with Session(engine) as session:
        session.add(SystemSetting(key="maintenance_mode", value="false", description="Toggle"))
        session.commit()

        repo = SystemSettingRepository(session)
        found = repo.get_by_key("maintenance_mode")

        assert found is not None
        assert found.value == "false"
        assert found.description == "Toggle"
        assert found.created_at is not None
        assert found.updated_at is not None


def test_get_by_key_returns_none_when_missing() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[SystemSetting.__table__])

    with Session(engine) as session:
        repo = SystemSettingRepository(session)
        assert repo.get_by_key("does_not_exist") is None


def test_key_uniqueness_rolls_back_via_transaction() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[SystemSetting.__table__])

    with Session(engine) as session:
        repo = SystemSettingRepository(session)
        session.add(SystemSetting(key="dup", value="1"))
        session.commit()

        with pytest.raises(IntegrityError):
            with repo.transaction():
                session.add(SystemSetting(key="dup", value="2"))
                session.flush()

        session.rollback()
        assert repo._count(repo._query()) == 1
