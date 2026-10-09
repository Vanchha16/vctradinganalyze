"""A deterministic XAUUSD M5 history that produces one smc-ict-crt-v2 design-A
BUY setup (ADR-185 tests). No randomness: every candle is computed.

Timeline (UTC, all weekdays, gap-free):
- Mon 2026-10-05 00:00 -> Tue 09:55: a quiet zigzag around 2000, with one
  spike to 1990.00 on Monday at 12:00 (the previous day's low - the key level).
- Tue 10:00 hour: the anchor, range 1995.00 - 2030.00.
- Tue 11:00 hour: the raid - low 1990.05 (sweeps the anchor low), high 2010,
  closes 2000 back inside.
- Tue 12:00 onward: M5 rallies; a swing high at 12:10 (2004) and a close above
  it at 12:25 (the MSS); an FVG between 12:00 and 12:10 gives entry 2002.
"""

from datetime import UTC, datetime, timedelta

from app.services.smc_crt.rules import Candle

M5 = timedelta(minutes=5)
START = datetime(2026, 10, 5, 0, 0, tzinfo=UTC)
ANCHOR_T = datetime(2026, 10, 6, 10, 0, tzinfo=UTC)
RAID_T = ANCHOR_T + timedelta(hours=1)
RAID_CLOSE = RAID_T + timedelta(hours=1)
MSS_T = RAID_CLOSE + timedelta(minutes=25)
EXPIRES_AT = RAID_CLOSE + timedelta(hours=3)


def _zigzag(t: datetime, k: int) -> Candle:
    close = 2000.0 + (0.5 if k % 2 else -0.5)
    o = 2000.0 - (0.5 if k % 2 else -0.5)
    low = min(o, close) - 0.5
    if t == datetime(2026, 10, 5, 12, 0, tzinfo=UTC):
        low = 1990.0
    return Candle(t, o, max(o, close) + 0.5, low, close)


_ANCHOR = [  # (open, high, low, close) per 5 minutes
    (2000, 2008, 1999, 2007), (2007, 2018, 2006, 2017), (2017, 2030, 2016, 2028),
    (2028, 2029, 2020, 2021), (2021, 2022, 2012, 2013), (2013, 2014, 2005, 2006),
    (2006, 2007, 1999, 2000), (2000, 2001, 1997, 1998), (1998, 1999, 1995, 1996),
    (1996, 2002, 1996, 2001), (2001, 2004, 2000, 2003), (2003, 2006, 2002, 2005),
]
_RAID = [
    (2005, 2010, 2004, 2008), (2008, 2009, 2001, 2002), (2002, 2003, 1996, 1997),
    (1997, 1998, 1993, 1994), (1994, 1995, 1991, 1992), (1992, 1993, 1990.05, 1991),
    (1991, 1995, 1990.5, 1994), (1994, 1997, 1993, 1996), (1996, 1998, 1995, 1997),
    (1997, 1999, 1996, 1998), (1998, 1999.8, 1997.5, 1999.5), (1999.5, 2000.2, 1999, 2000),
]
_AFTER = [
    (2000, 2001, 1999, 2000.5), (2000.5, 2003, 2000, 2002.5), (2002.5, 2004, 2002, 2003),
    (2003, 2003.5, 2001, 2001.5), (2001.5, 2002, 2000.5, 2001), (2001, 2008, 2001, 2007.5),
]


def history(until: datetime | None = None) -> list[Candle]:
    """Every M5 candle from START up to (excluding) `until`, gap-free.

    After the scripted bars the price drifts up slowly and never returns to
    the entry, so nothing here depends on a fill."""
    out: list[Candle] = []
    t, k = START, 0
    end = until or (EXPIRES_AT + timedelta(hours=2))
    scripted = {ANCHOR_T + i * M5: c for i, c in enumerate(_ANCHOR)}
    scripted |= {RAID_T + i * M5: c for i, c in enumerate(_RAID)}
    scripted |= {RAID_CLOSE + i * M5: c for i, c in enumerate(_AFTER)}
    last = 2007.5
    while t < end:
        if t in scripted:
            o, h, low, c = scripted[t]
            out.append(Candle(t, float(o), float(h), float(low), float(c)))
        elif t < ANCHOR_T:
            out.append(_zigzag(t, k))
        else:
            o = last
            last = last + 0.2
            out.append(Candle(t, o, last + 0.3, o - 0.1, last))
        if t in scripted:
            last = float(scripted[t][3])
        t += M5
        k += 1
    return out
