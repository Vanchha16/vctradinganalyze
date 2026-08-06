"""Route tests mirror `test_signal_routes.py`'s in-memory SQLite +
`dependency_overrides` pattern (docs/58 §2.3).

`FastAPI.dependency_overrides` is a single dict on the shared `app`
object, not per-`TestClient` - a test that needs two different
authenticated identities in the same test body must flip the override
immediately before each call via `_as()`, rather than holding two
`TestClient`s constructed with two different baked-in overrides (the
latter silently collapses to whichever override was set last, for both
clients, since they share the same `app`)."""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.asset import Asset
from app.models.enums import MarketType, UserRole
from app.models.user import User
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem

_TABLES = [User.__table__, Asset.__table__, Watchlist.__table__, WatchlistItem.__table__]

_USER_A = User(
    id=uuid.uuid4(),
    email="trader-a@example.com",
    username="trader-a",
    password_hash="hashed",
    role=UserRole.REGISTERED,
)
_USER_B = User(
    id=uuid.uuid4(),
    email="trader-b@example.com",
    username="trader-b",
    password_hash="hashed",
    role=UserRole.REGISTERED,
)


def _as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)

    def override_get_db() -> Generator[Session, None, None]:
        db = Session(engine)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    _as(_USER_A)
    with TestClient(app) as test_client:
        test_client.engine = engine
        yield test_client
    app.dependency_overrides.clear()


def _make_asset(engine: object, symbol: str = "EURUSD") -> Asset:
    with Session(engine) as session:  # type: ignore[arg-type]
        asset = Asset(
            symbol=symbol,
            name="Euro / US Dollar",
            market_type=MarketType.FOREX,
            base_currency="EUR",
            quote_currency="USD",
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        session.expunge(asset)
        return asset


def test_create_list_rename_delete_round_trip(client: TestClient) -> None:
    create_response = client.post("/api/v1/watchlists", json={"name": "My List"})
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["name"] == "My List"
    assert created["item_count"] == 0
    watchlist_id = created["id"]

    list_response = client.get("/api/v1/watchlists")
    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1

    rename_response = client.put(f"/api/v1/watchlists/{watchlist_id}", json={"name": "Renamed"})
    assert rename_response.status_code == 200
    assert rename_response.json()["name"] == "Renamed"

    delete_response = client.delete(f"/api/v1/watchlists/{watchlist_id}")
    assert delete_response.status_code == 204

    final_list = client.get("/api/v1/watchlists")
    assert final_list.json()["items"] == []


def test_add_and_remove_asset(client: TestClient) -> None:
    asset = _make_asset(client.engine)
    watchlist_id = client.post("/api/v1/watchlists", json={"name": "My List"}).json()["id"]

    add_response = client.post(
        f"/api/v1/watchlists/{watchlist_id}/assets", json={"asset_id": str(asset.id)}
    )
    assert add_response.status_code == 200
    assert add_response.json()["symbol"] == "EURUSD"

    detail_response = client.get(f"/api/v1/watchlists/{watchlist_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["assets"]) == 1
    assert detail["assets"][0]["symbol"] == "EURUSD"

    remove_response = client.delete(f"/api/v1/watchlists/{watchlist_id}/assets/{asset.id}")
    assert remove_response.status_code == 204

    detail_after_remove = client.get(f"/api/v1/watchlists/{watchlist_id}").json()
    assert detail_after_remove["assets"] == []


def test_add_duplicate_asset_returns_conflict(client: TestClient) -> None:
    asset = _make_asset(client.engine)
    watchlist_id = client.post("/api/v1/watchlists", json={"name": "My List"}).json()["id"]

    first = client.post(
        f"/api/v1/watchlists/{watchlist_id}/assets", json={"asset_id": str(asset.id)}
    )
    assert first.status_code == 200

    duplicate = client.post(
        f"/api/v1/watchlists/{watchlist_id}/assets", json={"asset_id": str(asset.id)}
    )
    assert duplicate.status_code == 409


def test_add_unknown_asset_returns_404(client: TestClient) -> None:
    watchlist_id = client.post("/api/v1/watchlists", json={"name": "My List"}).json()["id"]

    response = client.post(
        f"/api/v1/watchlists/{watchlist_id}/assets", json={"asset_id": str(uuid.uuid4())}
    )
    assert response.status_code == 404


def test_remove_asset_not_in_watchlist_returns_404(client: TestClient) -> None:
    asset = _make_asset(client.engine)
    watchlist_id = client.post("/api/v1/watchlists", json={"name": "My List"}).json()["id"]

    response = client.delete(f"/api/v1/watchlists/{watchlist_id}/assets/{asset.id}")
    assert response.status_code == 404


def test_user_cannot_read_rename_delete_or_add_asset_to_other_users_watchlist(
    client: TestClient,
) -> None:
    asset = _make_asset(client.engine)

    _as(_USER_A)
    watchlist_id = client.post("/api/v1/watchlists", json={"name": "A's List"}).json()["id"]

    _as(_USER_B)
    assert client.get(f"/api/v1/watchlists/{watchlist_id}").status_code == 404
    assert (
        client.put(f"/api/v1/watchlists/{watchlist_id}", json={"name": "Hijacked"}).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/watchlists/{watchlist_id}/assets", json={"asset_id": str(asset.id)}
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/watchlists/{watchlist_id}").status_code == 404

    # B's rejected attempts never touched A's watchlist.
    _as(_USER_A)
    still_there = client.get(f"/api/v1/watchlists/{watchlist_id}")
    assert still_there.status_code == 200
    assert still_there.json()["name"] == "A's List"


def test_unauthenticated_requests_are_rejected(client: TestClient) -> None:
    watchlist_id = client.post("/api/v1/watchlists", json={"name": "My List"}).json()["id"]
    app.dependency_overrides.pop(get_current_user, None)

    assert client.get("/api/v1/watchlists").status_code in (401, 403)
    assert client.post("/api/v1/watchlists", json={"name": "X"}).status_code in (401, 403)
    assert client.get(f"/api/v1/watchlists/{watchlist_id}").status_code in (401, 403)
