"""Pure OPEX / quad-witching computation — no I/O, no wall clock.

Monthly equity/index option expiration is the 3rd Friday; quad-witching is the
3rd Friday of Mar/Jun/Sep/Dec. When that Friday is a market holiday the
expiration shifts to the preceding Thursday — deterministic once the holiday set
is known, which is why this takes `holidays` as an argument rather than fetching."""
from datetime import date, timedelta

_QUAD_MONTHS = {3, 6, 9, 12}


def third_friday(year: int, month: int) -> date:
    """The 3rd Friday of (year, month)."""
    first = date(year, month, 1)
    # weekday(): Mon=0 .. Sun=6; Friday=4. Days from the 1st to the first Friday:
    offset = (4 - first.weekday()) % 7
    return first + timedelta(days=offset + 14)


def opex_dates(year: int, holidays: set) -> list:
    """One (iso_date, kind) per month for `year`. kind='quad_witching' for
    Mar/Jun/Sep/Dec else 'opex'. A 3rd Friday that is a market holiday shifts to
    the preceding Thursday."""
    out = []
    for month in range(1, 13):
        d = third_friday(year, month)
        if d.isoformat() in holidays:
            d = d - timedelta(days=1)   # preceding Thursday
        kind = "quad_witching" if month in _QUAD_MONTHS else "opex"
        out.append((d.isoformat(), kind))
    return out
