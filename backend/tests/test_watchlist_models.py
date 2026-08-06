from datetime import datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.asset import Asset
from app.models.enums import MarketType
from app.models.oauth_account import OAuthAccount
from app.models.telegram_account import TelegramAccount
from app.models.user import User
from app.models.user_session import UserSession
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem

# `User` declares ORM relationships (sessions/oauth_accounts/telegram_account,
# cascade="all, delete-orphan") to tables unrelated to Watchlists - deleting a
# User still touches them, so they must exist even though this test never
# populates them (same requirement `test_user_models.py` already documents).
_TABLES = [
    User.__table__,
    UserSession.__table__,
    OAuthAccount.__table__,
    TelegramAccount.__table__,
    Asset.__table__,
    Watchlist.__table__,
    WatchlistItem.__table__,
]


def _sqlite_engine_with_fk_enforcement() -> Engine:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture
def session() -> Session:
    engine = _sqlite_engine_with_fk_enforcement()
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


def _make_user(session: Session) -> User:
    user = User(email="trader@example.com", username="trader", password_hash="hashed")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _make_asset(session: Session) -> Asset:
    asset = Asset(
        symbol="EURUSD",
        name="Euro / US Dollar",
        market_type=MarketType.FOREX,
        base_currency="EUR",
        quote_currency="USD",
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _make_watchlist(session: Session, user: User) -> Watchlist:
    watchlist = Watchlist(user_id=user.id, name="My Forex List")
    session.add(watchlist)
    session.commit()
    session.refresh(watchlist)
    return watchlist


def test_watchlist_defaults(session: Session) -> None:
    user = _make_user(session)
    watchlist = _make_watchlist(session, user)

    assert watchlist.name == "My Forex List"
    assert isinstance(watchlist.created_at, datetime)


def test_watchlist_item_unique_per_watchlist_and_asset(session: Session) -> None:
    user = _make_user(session)
    watchlist = _make_watchlist(session, user)
    asset = _make_asset(session)

    session.add(WatchlistItem(watchlist_id=watchlist.id, asset_id=asset.id))
    session.commit()

    with pytest.raises(IntegrityError):
        session.add(WatchlistItem(watchlist_id=watchlist.id, asset_id=asset.id))
        session.flush()


def test_watchlist_items_cascade_delete_with_watchlist(session: Session) -> None:
    user = _make_user(session)
    watchlist = _make_watchlist(session, user)
    asset = _make_asset(session)

    session.add(WatchlistItem(watchlist_id=watchlist.id, asset_id=asset.id))
    session.commit()

    session.delete(watchlist)
    session.commit()
    session.expunge_all()

    assert session.query(WatchlistItem).count() == 0


def test_watchlists_cascade_delete_with_user(session: Session) -> None:
    user = _make_user(session)
    watchlist = _make_watchlist(session, user)
    asset = _make_asset(session)
    session.add(WatchlistItem(watchlist_id=watchlist.id, asset_id=asset.id))
    session.commit()

    session.delete(user)
    session.commit()
    session.expunge_all()

    assert session.query(Watchlist).count() == 0
    assert session.query(WatchlistItem).count() == 0
