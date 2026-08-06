"""E2E seed script (Phase 9C, docs/60 §7). Targets a dedicated `e2e.db`,
never `dev.db` - see `e2e_db.py`, which this script shares with
`run_dev.py --e2e-db`.

**Idempotent by full reset, not upsert.** Every run drops and recreates
every table, then reseeds from scratch - so the E2E suite always starts
from the exact same known state regardless of what a previous run's
tests (watchlist create/rename/delete, admin user create/edit, ...)
mutated. This mirrors `seed_dev_data.py`'s spirit (safe to re-run) but
goes further, since `dev.db` is meant to accumulate manual-verification
state across phases while `e2e.db` deliberately must not.

**Safety requirement (build spec §2):** refuses to run against anything
that isn't obviously the local `e2e.db` SQLite file - see
`e2e_db.assert_safe_e2e_target`, tested in
`tests/test_seed_e2e_data_safety.py`. Test credentials are obviously
fake (`*.invalid` domain, per RFC 2606) and never derived from or read
out of `backend/.env`.

Usage: python scripts/seed_e2e_data.py
"""

import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from e2e_db import E2E_DATABASE_URL, assert_safe_e2e_target  # noqa: E402

# Must happen before any `app.*` import - same constraint `local_env.py`
# documents for `apply_safe_overrides()`. `Settings()` is only ever
# constructed once (`lru_cache`), so this is a no-op if some earlier
# import already built it from a different value.
os.environ["DATABASE_URL"] = E2E_DATABASE_URL
assert_safe_e2e_target(os.environ["DATABASE_URL"])

from app import models  # noqa: E402,F401  (populates Base.metadata)
from app.core.security import hash_password  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.models.asset import Asset  # noqa: E402
from app.models.enums import MarketType, Timeframe, UserRole  # noqa: E402
from app.models.user import User  # noqa: E402
from app.repositories.price_candle_repository import PriceCandleRepository  # noqa: E402
from app.services.market_data.candle_validator import CandleValidator  # noqa: E402
from app.services.market_data.providers.mock import MockMarketDataProvider  # noqa: E402
from app.services.market_data_service import MarketDataService  # noqa: E402

#: `*.invalid` (RFC 2606) - can never resolve to a real mailbox, so these
#: can't be mistaken for or collide with a real account. Password is a
#: fixed, obviously-fake, test-only string - never read from `.env`,
#: never reused for anything real.
E2E_ADMIN_EMAIL = "e2e-admin@example.invalid"
E2E_ADMIN_USERNAME = "e2e_admin"
E2E_NON_ADMIN_EMAIL = "e2e-user@example.invalid"
E2E_NON_ADMIN_USERNAME = "e2e_user"
E2E_TEST_PASSWORD = "E2E-Test-Password9"

ASSETS = [
    ("EURUSD", "Euro / US Dollar", MarketType.FOREX, "EUR", "USD"),
    ("XAUUSD", "Gold / US Dollar", MarketType.METAL, "XAU", "USD"),
]
TIMEFRAMES = [Timeframe.H1, Timeframe.D1]


def main() -> None:
    print(f"Seeding E2E database: {E2E_DATABASE_URL}")

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    session = SessionLocal()
    try:
        admin = User(
            email=E2E_ADMIN_EMAIL,
            username=E2E_ADMIN_USERNAME,
            password_hash=hash_password(E2E_TEST_PASSWORD),
            full_name="E2E Admin",
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True,
        )
        non_admin = User(
            email=E2E_NON_ADMIN_EMAIL,
            username=E2E_NON_ADMIN_USERNAME,
            password_hash=hash_password(E2E_TEST_PASSWORD),
            full_name="E2E User",
            role=UserRole.REGISTERED,
            is_active=True,
            is_verified=True,
        )
        session.add_all([admin, non_admin])
        session.commit()
        print(f"created admin: {admin.email} ({admin.role.value})")
        print(f"created non-admin: {non_admin.email} ({non_admin.role.value})")

        candle_repo = PriceCandleRepository(session)
        service = MarketDataService(
            providers=[MockMarketDataProvider()],
            candle_validator=CandleValidator(),
            price_candle_repository=candle_repo,
        )

        end = datetime.now(UTC)
        start = end - timedelta(days=30)

        for symbol, name, market_type, base_ccy, quote_ccy in ASSETS:
            asset = Asset(
                symbol=symbol,
                name=name,
                market_type=market_type,
                base_currency=base_ccy,
                quote_currency=quote_ccy,
                is_active=True,
            )
            session.add(asset)
            session.commit()
            session.refresh(asset)
            print(f"created asset {symbol}")

            for timeframe in TIMEFRAMES:
                result = service.collect(asset, timeframe, start=start, end=end)
                print(f"  {symbol} {timeframe.value}: persisted={result.persisted}")

        session.commit()
        print("E2E seed complete.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
