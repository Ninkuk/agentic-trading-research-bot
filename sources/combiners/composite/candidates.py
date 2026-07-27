"""Quality-first candidate screen: a read-only report that lists real
businesses currently trading at a dislocation, as raw material for
`research-ticker`. SELECT-only over stocks.db; writes nothing, grades
nothing, recommends nothing.

WHY THIS EXISTS. composite's ticker-grain signals are all microstructure
(short interest, FTDs, RSI, short volume, reddit), so its universe is
empirically a microcap dislocation scanner — measured 2026-07-26, si_spike
fired on 527 tickers of which 10 were above $2B. The research gate then
correctly rejects nearly all of them, because "is this a good business to
own for years?" has one honest answer for an oversold microcap. This screen
enters the funnel from the other end: quality first, dislocation as timing.
Of the names it surfaced on the day it was written, 2 were in composite's
universe and 0 were flagged — the two funnels barely intersect.

WHAT THIS IS NOT. There is no forward-return evidence for this screen and
nothing downstream grades it. It is a reading list, not an opinion, and
deliberately produces no signal_values rows and no flags.

Every gate below encodes a defect measured in stocks.db on 2026-07-26; none
of them are stylistic:
  * ONE ROW PER COMPANY — share classes INHERIT the whole-company marketCap
    (BRK.A $1,059.5B vs BRK.B $1,058.9B; BF.A == BF.B bit-identical), so a
    cap screen counts one company twice. See _COMPANY_KEY below for why the
    key is the US CUSIP issuer number and not `isin`, `cik`, or the
    isPrimaryListing flag.
  * dollarVolume — 305 symbols over $2B "marketCap" are non-primary, 10 of
    them under $100k of daily volume (TAP.A: $7.5B cap, $14,473 traded).
  * ROIC_MAX — roic ranges -23,089%..+12,239% across the table; NTES reads
    376% because net cash ($23.2B) nearly equals equity ($24.6B), collapsing
    invested capital. A bare `roic > 12` admits the artifact, not the quality.
  * FSCORE_MIN — every other gate is a LEVEL, and levels cannot distinguish
    oversold quality from a falling knife. Piotroski is the trend read, and
    it covers 5,594/5,597 symbols. It is what excludes LULU (fScore 4, -43%
    over six months) while keeping ADBE (fScore 7).
  * rsi > 0 — 26 rows carry a non-positive RSI, out of domain for a 0-100
    oscillator. composite/catalog.py guards the same column the same way.
"""

import argparse
import os
import sqlite3
from datetime import UTC, datetime

from sources.combiners.composite.catalog import STOCKS_COMPANY_KEY, STOCKS_PRIMARY_FIRST
from sources.common.clock import phx_date

# Hand-set, documented judgment — not fitted, and deliberately not tuned
# against outcomes (no outcome data for this screen exists). Tune here.
MARKET_CAP_MIN = 2e9
DOLLAR_VOLUME_MIN = 10e6
ROIC_MIN = 12.0
ROIC_MAX = 150.0  # above this for a >$2B company it is a denominator artifact
ROIC5Y_MIN = 10.0
FCF_YIELD_MIN = 4.0
REV_GROWTH_3Y_MIN = 5.0
NET_DEBT_EBITDA_MAX = 3.0
SHARES_YOY_MAX = 2.0  # percent; buybacks are negative
FSCORE_MIN = 5.0
RSI_MAX = 45.0  # the dislocation: timing, not the thesis

# One row per company. Both expressions are imported from catalog.py rather
# than restated here, so this screen and composite's stocks_rsi signal can
# never disagree about what counts as the same business — see the measured
# comparison of isPrimaryListing / cik / CUSIP-issuer keys documented there.
_COMPANY_KEY = STOCKS_COMPANY_KEY
_PRIMARY_FIRST = STOCKS_PRIMARY_FIRST

# All thresholds are on stockanalysis.com's PERCENT scale (roic=27.09 means
# 27.09%), verified against the field distributions — a fraction/percent mixup
# silently turns a gate into a no-op, so a test pins the scale.
#
# NULL POLICY. netDebtEbitda is the sparsest field read here (2,860/5,597
# populated) and is sparse BY NATURE — a debt-free company has no meaningful
# net-debt/EBITDA. Requiring it would silently halve the universe, so absent
# leverage is not disqualifying; present-and-bad is. Every OTHER gated column
# is densely populated, so a NULL there is missing evidence rather than a
# structural absence, and the row drops rather than the screen guessing. Both
# behaviours are pinned by tests.
_SCREEN_SQL = f"""
WITH eligible AS (
    SELECT symbol, sector, marketCap, dollarVolume, roic, roic5y, fcfYield,
           revenueGrowth3Y, netDebtEbitda, sharesYoY, fScore, rsi, ch6m,
           priceDate, isin, isPrimaryListing
    FROM v_latest
    WHERE symbol NOT LIKE '%.PR%'                 -- preferreds are not common equity
      AND marketCap >= {MARKET_CAP_MIN}
      AND dollarVolume >= {DOLLAR_VOLUME_MIN}
      AND roic BETWEEN {ROIC_MIN} AND {ROIC_MAX}
      AND roic5y BETWEEN {ROIC5Y_MIN} AND {ROIC_MAX}
      AND fcfYield >= {FCF_YIELD_MIN}
      AND revenueGrowth3Y >= {REV_GROWTH_3Y_MIN}
      AND sharesYoY < {SHARES_YOY_MAX}
      AND fScore >= {FSCORE_MIN}
      AND rsi > 0 AND rsi < {RSI_MAX}
      AND (netDebtEbitda IS NULL OR netDebtEbitda < {NET_DEBT_EBITDA_MAX})
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY {_COMPANY_KEY}
        ORDER BY {_PRIMARY_FIRST}, dollarVolume DESC, symbol
    ) AS rn
    FROM eligible
)
SELECT symbol, sector, marketCap, dollarVolume, roic, roic5y, fcfYield,
       revenueGrowth3Y, netDebtEbitda, sharesYoY, fScore, rsi, ch6m, priceDate
FROM ranked WHERE rn = 1
ORDER BY fcfYield DESC, roic DESC, symbol
"""

# Positionally zipped onto the final SELECT above; a test pins the mapping so
# a reorder of either list cannot silently print one field under another's name.
_FIELDS = [
    "symbol",
    "sector",
    "marketCap",
    "dollarVolume",
    "roic",
    "roic5y",
    "fcfYield",
    "revenueGrowth3Y",
    "netDebtEbitda",
    "sharesYoY",
    "fScore",
    "rsi",
    "ch6m",
    "priceDate",
]

# One (label, width) per rendered column, so the header and every row are
# built from the SAME widths and cannot drift apart.
_LAYOUT = (
    ("symbol", 6),
    ("sector", 22),
    ("cap$B", 7),
    ("roic", 6),
    ("roic5y", 7),
    ("fcfy", 6),
    ("rev3y", 6),
    ("nde", 6),
    ("fS", 2),
    ("rsi", 5),
    ("ch6m", 7),
)


def connect_ro(path: str) -> sqlite3.Connection:
    """stocks.db opened read-only. This reporter must never be able to write
    to a source DB, so the guarantee is in the connection, not in discipline."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return sqlite3.connect(f"file:{os.path.abspath(path)}?mode=ro", uri=True)


def screen(conn) -> list[dict]:
    """Rows passing every gate, one per company, best free-cash-flow yield
    first. SELECT-only."""
    return [dict(zip(_FIELDS, r, strict=True)) for r in conn.execute(_SCREEN_SQL)]


def snapshot_date(conn) -> str | None:
    """Phoenix calendar date of the stocks.db snapshot behind v_latest, or
    None when the header is unavailable.

    Every consumer needs this, because the screener does not run at weekends:
    a Sunday-night reader is quoting Friday's RSI, and a screen that cannot
    say how old its data is invites the reader to assume it is tonight's."""
    try:
        row = conn.execute(
            "SELECT captured_at FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1"
        ).fetchone()
    except sqlite3.Error:
        return None
    return phx_date(row[0]) if row and row[0] else None


def _num(x, places=1) -> str:
    return "n/a" if x is None else f"{x:.{places}f}"


def _row_cells(r: dict) -> list[str]:
    return [
        r["symbol"],
        (r["sector"] or "?")[:22],
        _num(r["marketCap"] / 1e9),
        _num(r["roic"]),
        _num(r["roic5y"]),
        _num(r["fcfYield"]),
        _num(r["revenueGrowth3Y"]),
        _num(r["netDebtEbitda"], 2),
        _num(r["fScore"], 0),
        _num(r["rsi"]),
        _num(r["ch6m"]),
    ]


def _line(cells) -> str:
    parts = [
        f"{c:<{w}}" if i == 0 or i == 1 else f"{c:>{w}}"
        for i, (c, (_, w)) in enumerate(zip(cells, _LAYOUT, strict=True))
    ]
    return "  " + " | ".join(parts)


def _candidates_section(rows: list[dict]) -> str:
    if not rows:
        return "  no candidates pass the screen today"
    return "\n".join(
        [_line([label for label, _ in _LAYOUT])] + [_line(_row_cells(r)) for r in rows]
    )


def build_report(conn, now_iso: str) -> str:
    rows = screen(conn)
    data_date = snapshot_date(conn)
    # The run date and the DATA date are different facts and diverge every
    # weekend, when stocks.db has not refreshed since Friday.
    source = f"stocks.db snapshot {data_date}" if data_date else "stocks.db snapshot date unknown"
    return "\n".join(
        [
            f"=== Research Candidates — {phx_date(now_iso)} ===",
            "",
            f"Quality first, dislocation as timing. {len(rows)} name(s) pass.  [{source}]",
            "",
            _candidates_section(rows),
            "",
            f"Screen: one row per company, cap >= ${MARKET_CAP_MIN / 1e9:.0f}B,"
            f" ${DOLLAR_VOLUME_MIN / 1e6:.0f}M+ daily volume,",
            f"  roic and roic5y within {ROIC_MIN:.0f}-{ROIC_MAX:.0f}%,"
            f" fcf yield >= {FCF_YIELD_MIN:.0f}%,"
            f" 3y revenue growth >= {REV_GROWTH_3Y_MIN:.0f}%,",
            f"  net debt/ebitda < {NET_DEBT_EBITDA_MAX:.0f} or absent,"
            f" dilution < {SHARES_YOY_MAX:.0f}%/yr,"
            f" fScore >= {FSCORE_MIN:.0f}, rsi < {RSI_MAX:.0f}.",
            "",
            "This is an UNGRADED screen and NOT A RECOMMENDATION. No forward-return",
            "evidence exists for it and nothing downstream scores it. Row order is",
            "fcf yield, not conviction. It is input to research-ticker, which decides",
            "whether any of these is worth owning.",
        ]
    )


def run(db_path: str, now_iso: str | None = None) -> str:
    now_iso = now_iso or datetime.now(UTC).isoformat()
    conn = connect_ro(db_path)
    try:
        return build_report(conn, now_iso)
    finally:
        conn.close()


def main(argv=None) -> None:
    p = argparse.ArgumentParser(
        prog="candidates",
        description="Print a quality-first research candidate screen (reads"
        " stocks.db read-only; writes nothing, recommends nothing)",
    )
    p.add_argument("--db", default="stocks.db")
    a = p.parse_args(argv)
    print(run(a.db))


if __name__ == "__main__":
    main()
