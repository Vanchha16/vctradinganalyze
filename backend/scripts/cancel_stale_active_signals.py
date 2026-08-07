"""One-off operator script (Phase 9E, ADR-137 §6): marks every currently
`ACTIVE` signal `CANCELLED`.

Deploying ADR-137's entry-confirmation logic changes what `ACTIVE` means -
pre-deploy `ACTIVE` signals were never entry-confirmed, and under the new
logic would be treated as pending orders at levels the market may have
long since passed. `CANCELLED` already exists in `SignalStatus` and was
otherwise unused (BACKLOG.md §21).

Idempotent: re-running after the first `--confirm` run finds zero
remaining `ACTIVE` rows and reports that, since every affected row is
already `CANCELLED`. Dry-run by default - reports the row count it would
change and does nothing until `--confirm` is passed explicitly.

Usage:
    python scripts/cancel_stale_active_signals.py            # dry run
    python scripts/cancel_stale_active_signals.py --confirm   # writes
"""

import argparse
import sys

from app.database.session import SessionLocal
from app.models.enums import SignalStatus
from app.repositories.signal_repository import SignalRepository


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually cancel the rows. Without this flag, only reports the count.",
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        signal_repository = SignalRepository(session)
        active_count = signal_repository.count_filtered(status=SignalStatus.ACTIVE)

        if active_count == 0:
            print("No ACTIVE signals found - nothing to do.")
            return 0

        if not args.confirm:
            print(f"Would cancel {active_count} ACTIVE signal(s). Re-run with --confirm to apply.")
            return 0

        signals = signal_repository.find_paginated(status=SignalStatus.ACTIVE, limit=active_count)
        for signal in signals:
            signal.status = SignalStatus.CANCELLED
        session.commit()
        print(f"Cancelled {len(signals)} ACTIVE signal(s).")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
