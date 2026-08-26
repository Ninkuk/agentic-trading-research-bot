"""Source drill-down sections — one card per source view family that had no
dashboard presence: dark pools, XBRL fundamentals, the three COT report
families, Treasury curve/auctions/debt, FRED series, fails-to-deliver,
short volume and short interest, unusual options, NY Fed funding, the
calendars, energy and ag inventories, reddit, and EDGAR filings.

All SELECT-only. Leaderboards cap at `_TOP` rows; time series ride as
per-row sparklines (`history`) or tile `history` points, both bounded.
Monitor views (`v_this_week`, `v_next_fomc`, …) filter on the
`calendar_now.today` row their own nightly run set — read-only here, so a
section is as fresh as that run, never fresher.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from dashboard_lib.common import (
    attach_history,
    col,
    fetch,
    histories,
    ro,
    spark_col,
    tile,
    verdict,
)

_TOP = 30
_WEEKS = 26
_DAYS = 90


def _marks(values: list[Any]) -> str:
    """`?,?,?` for an IN list. Empty stays empty — SQLite accepts `IN ()`,
    and running the query anyway keeps the history view in the read set
    the coverage gate observes."""
    return ",".join("?" * len(values))


def _series_tile(
    conn: sqlite3.Connection,
    label: str,
    sql: str,
    *,
    limit: int,
    band: str | None = None,
    tone: str | None = None,
    scale: float = 1.0,
) -> dict[str, Any] | None:
    """A tile whose value is the newest point of `sql` (date, value; oldest
    first) divided by `scale`, and whose history is the last `limit` points.
    None when the series is empty so the caller can skip it."""
    pts = [{"date": d, "value": v} for d, v in conn.execute(sql).fetchall() if v is not None][
        -limit:
    ]
    if not pts:
        return None
    return tile(label, pts[-1]["value"], band or pts[-1]["date"], tone, pts)


# --- FINRA ATS (dark pools) --------------------------------------------------

_DARK_POOL_COLUMNS = [
    col("ats_name", "Venue", numeric=False),
    col("mpid", "MPID", numeric=False),
    col("total_shares", "Shares"),
    col("total_trades", "Trades"),
]


def dark_pools(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT ats_name, mpid, total_shares, total_trades FROM v_top_dark_pools"
        " ORDER BY total_shares DESC",
    )
    agg = conn.execute(
        "SELECT COUNT(*), SUM(total_shares), SUM(total_trades) FROM v_latest_off_exchange"
    ).fetchone()
    tiles = [
        tile("venues reporting", len(rows)),
        tile("symbols with off-exchange volume", agg[0]),
        tile("off-exchange shares", agg[1]),
    ]
    return {
        "tiles": tiles,
        "columns": _DARK_POOL_COLUMNS,
        "rows": rows,
        "empty": "no ATS weekly file loaded yet",
    }


_OFF_EXCHANGE_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("total_shares", "Off-exchange shares"),
    col("total_trades", "Trades"),
    col("venue_count", "Venues"),
    spark_col("history", "Weekly shares"),
]


def off_exchange_leaders(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT symbol, total_shares, total_trades, venue_count FROM v_latest_off_exchange"
        " ORDER BY total_shares DESC LIMIT ?",
        (_TOP,),
    )
    syms = [r["symbol"] for r in rows]
    hist = histories(
        conn,
        "SELECT symbol, SUM(share_quantity) FROM v_symbol_venue_history"
        f" WHERE symbol IN ({_marks(syms)}) GROUP BY symbol, week_start ORDER BY week_start",
        syms,
        limit=_WEEKS,
    )
    attach_history(rows, hist, "symbol")
    return {
        "columns": _OFF_EXCHANGE_COLUMNS,
        "rows": rows,
        "empty": "no ATS weekly file loaded yet",
    }


# --- SEC XBRL fundamentals ---------------------------------------------------

_REVISION_COLUMNS = [
    col("ticker", "Ticker", numeric=False),
    col("tag", "Line item", numeric=False),
    col("period_end", "Period", numeric=False),
    col("form", "Form", numeric=False),
    col("filed", "Filed", numeric=False),
    col("value", "Restated value"),
    col("value_delta", "Change vs prior filing"),
]


def sec_revisions(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT ticker, tag, period_end, form, filed, value, value_delta FROM v_revisions"
        " WHERE ticker IS NOT NULL ORDER BY filed DESC, ABS(value_delta) DESC LIMIT ?",
        (_TOP,),
    )
    return {
        "columns": _REVISION_COLUMNS,
        "rows": rows,
        "empty": "no restated XBRL facts yet",
    }


_SEC_SCREENER_COLUMNS = [
    col("ticker", "Ticker", numeric=False),
    col("name", "Company", numeric=False),
    col("revenues", "Revenue"),
    col("net_income", "Net income"),
    col("net_margin", "Net margin"),
    col("roe", "ROE"),
    col("debt_to_equity", "Debt / equity", direction="down-good"),
    col("eps_diluted", "Diluted EPS"),
]


def sec_screener(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT ticker, name, revenues, net_income, net_margin, roe, debt_to_equity,"
        " eps_diluted FROM v_screener WHERE ticker IS NOT NULL AND revenues IS NOT NULL"
        " ORDER BY revenues DESC LIMIT ?",
        (_TOP,),
    )
    return {
        "columns": _SEC_SCREENER_COLUMNS,
        "rows": rows,
        "empty": "no XBRL company facts loaded yet",
    }


# --- CFTC Commitments of Traders --------------------------------------------


def _cot_section(
    conn: sqlite3.Connection,
    *,
    positioning_view: str,
    extremes_view: str,
    index_view: str,
    net_col: str,
    long_col: str,
    short_col: str,
    chg_long: str,
    chg_short: str,
    secondary: tuple[str, str, str] | None,
    empty: str,
) -> dict[str, Any]:
    """One COT family: positioning rows flagged by the family's extremes
    view, the speculator index history as a sparkline, and (optionally) the
    other side's index joined by contract code."""
    sec_sql = ""
    if secondary:
        view, column, alias = secondary
        sec_sql = f", (SELECT cot_index FROM {view} s WHERE s.code = p.code) AS {alias}"
    rows = fetch(
        conn,
        f"SELECT p.code, p.name, p.asset_class, p.report_date, p.{net_col} AS net,"
        f" p.cot_index, p.{long_col} AS pct_long, p.{short_col} AS pct_short,"
        f" p.{chg_long} AS chg_long, p.{chg_short} AS chg_short, p.chg_oi{sec_sql}"
        f" FROM {positioning_view} p ORDER BY p.asset_class, p.name",
    )
    extreme = {r[0] for r in conn.execute(f"SELECT code FROM {extremes_view}")}
    for r in rows:
        r["extreme"] = r["code"] in extreme
    hist = histories(
        conn,
        f"SELECT code, cot_index FROM {index_view} ORDER BY report_date",
        limit=_WEEKS,
    )
    attach_history(rows, hist, "code")
    for r in rows:
        del r["code"]
    rows.sort(key=lambda r: (not r["extreme"], r["asset_class"] or "", r["name"] or ""))
    n_ext = sum(1 for r in rows if r["extreme"])
    return {
        "verdict": verdict(
            f"{n_ext} contract{'s' if n_ext != 1 else ''} at a positioning extreme",
            "mid" if n_ext else "on",
        )
        if rows
        else None,
        "rows": rows,
        "empty": empty,
    }


def _cot_columns(net_label: str, secondary_label: str | None) -> list[dict[str, Any]]:
    cols = [
        col("name", "Contract", numeric=False),
        col("asset_class", "Class", numeric=False),
        col("report_date", "Report", numeric=False),
        col("net", net_label),
        col("cot_index", "COT index (0–100)", term="COT index"),
        spark_col("history", "Index, 26 weeks"),
    ]
    if secondary_label:
        cols.append(col("secondary_index", secondary_label))
    cols += [
        col("pct_long", "% OI long"),
        col("pct_short", "% OI short"),
        col("chg_long", "Δ long"),
        col("chg_short", "Δ short"),
        col("chg_oi", "Δ open interest"),
        col("extreme", "Extreme?", numeric=False),
    ]
    return cols


def cot_positioning(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    body = _cot_section(
        conn,
        positioning_view="v_positioning",
        extremes_view="v_extremes",
        index_view="v_cot_index",
        net_col="net_noncomm",
        long_col="pct_oi_noncomm_long",
        short_col="pct_oi_noncomm_short",
        chg_long="chg_noncomm_long",
        chg_short="chg_noncomm_short",
        secondary=None,
        empty="no legacy COT report loaded yet",
    )
    return {"columns": _cot_columns("Net speculators", None), **body}


def cot_disaggregated(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    body = _cot_section(
        conn,
        positioning_view="v_disagg_positioning",
        extremes_view="v_managed_money_extremes",
        index_view="v_disagg_cot_index",
        net_col="net_mm",
        long_col="pct_oi_mm_long",
        short_col="pct_oi_mm_short",
        chg_long="chg_mm_long",
        chg_short="chg_mm_short",
        secondary=("v_disagg_cot_index_commercial_latest", "cot_index", "secondary_index"),
        empty="no disaggregated COT report loaded yet",
    )
    return {"columns": _cot_columns("Net managed money", "Commercial index"), **body}


def cot_financial(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    body = _cot_section(
        conn,
        positioning_view="v_leveraged_funds_positioning",
        extremes_view="v_leveraged_funds_extremes",
        index_view="v_tff_cot_index",
        net_col="net_lev",
        long_col="pct_oi_lev_long",
        short_col="pct_oi_lev_short",
        chg_long="chg_lev_long",
        chg_short="chg_lev_short",
        secondary=("v_tff_cot_index_dealer_latest", "cot_index", "secondary_index"),
        empty="no financial-futures COT report loaded yet",
    )
    return {"columns": _cot_columns("Net leveraged funds", "Dealer index"), **body}


# --- Treasury ---------------------------------------------------------------


def yield_curve(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT record_date, mo3, yr2, yr10, spread_2s10s, spread_3m10y, inverted"
        " FROM v_yield_curve_latest"
    ).fetchone()
    if row is None:
        return {"tiles": [], "empty": "no Treasury yield-curve row yet"}
    inv = bool(row["inverted"])
    tiles = [
        tile("3-month", row["mo3"], row["record_date"]),
        tile("2-year", row["yr2"], row["record_date"]),
        tile("10-year", row["yr10"], row["record_date"]),
        tile(
            "10y − 2y spread",
            row["spread_2s10s"],
            "inverted" if inv else "normal",
            "off" if inv else "on",
        ),
        tile(
            "10y − 3m spread",
            row["spread_3m10y"],
            None,
            "off" if row["spread_3m10y"] is not None and row["spread_3m10y"] < 0 else "on",
        ),
    ]
    return {
        "verdict": verdict("curve inverted" if inv else "curve normal", "off" if inv else "on"),
        "tiles": tiles,
    }


_AUCTION_COLUMNS = [
    col("security_term", "Security", numeric=False),
    col("auction_date", "Auction", numeric=False),
    col("latest_btc", "Bid-to-cover", direction="up-good"),
    col("avg_btc", "Typical bid-to-cover"),
    col("vs_avg", "Vs typical", direction="up-good"),
]


def auction_demand(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT security_term, auction_date, latest_btc, avg_btc FROM v_auction_demand"
        " ORDER BY auction_date DESC LIMIT ?",
        (_TOP,),
    )
    for r in rows:
        a, b = r["latest_btc"], r["avg_btc"]
        r["vs_avg"] = None if a is None or b is None else round(a - b, 2)
    weak = sum(1 for r in rows if r["vs_avg"] is not None and r["vs_avg"] < -0.2)
    return {
        "verdict": verdict(
            f"{weak} of the last {len(rows)} auctions drew weak demand", "mid" if weak else "on"
        )
        if rows
        else None,
        "columns": _AUCTION_COLUMNS,
        "rows": rows,
        "empty": "no auction results loaded yet",
    }


_UPCOMING_AUCTION_COLUMNS = [
    col("auction_date", "Auction", numeric=False),
    col("security_type", "Type", numeric=False),
    col("security_term", "Term", numeric=False),
    col("announcement_date", "Announced", numeric=False),
    col("issue_date", "Settles", numeric=False),
]


def upcoming_auctions(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT auction_date, security_type, security_term, announcement_date, issue_date"
        " FROM v_upcoming_auctions ORDER BY auction_date, security_term",
    )
    return {
        "columns": _UPCOMING_AUCTION_COLUMNS,
        "rows": rows,
        "empty": "no auctions announced in the window",
    }


def federal_debt(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    tiles = [
        t
        for t in (
            _series_tile(
                conn,
                "total public debt ($T)",
                "SELECT record_date, tot_pub_debt_out FROM v_debt_trend ORDER BY record_date",
                limit=_DAYS,
                scale=1e12,
            ),
            _series_tile(
                conn,
                "Treasury cash balance ($B)",
                "SELECT record_date, close_balance FROM v_tga_trend ORDER BY record_date",
                limit=_DAYS,
                scale=1e3,
            ),
        )
        if t
    ]
    return {"tiles": tiles, **({"empty": "no debt or TGA rows yet"} if not tiles else {})}


# --- FRED -------------------------------------------------------------------

_FRED_COLUMNS = [
    col("title", "Series", numeric=False),
    col("theme", "Theme", numeric=False),
    col("latest_date", "As of", numeric=False),
    col("latest", "Latest"),
    col("year_ago", "A year ago"),
    col("change_pct", "YoY %"),
    col("zscore", "Z-score vs history", term="Z-score"),
]


def fred_series(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT y.title, y.theme, y.latest_date, y.latest, y.year_ago, y.change_pct, z.zscore"
        " FROM v_yoy_change y LEFT JOIN v_zscore z ON z.series_id = y.series_id"
        " ORDER BY y.theme, y.title",
    )
    sig = conn.execute(
        "SELECT t10y2y, yield_curve_inverted, hy_spread, fed_funds, unemployment"
        " FROM v_regime_signals"
    ).fetchone()
    tiles = []
    if sig is not None:
        inv = bool(sig["yield_curve_inverted"])
        tiles = [
            tile(
                "10y − 2y", sig["t10y2y"], "inverted" if inv else "normal", "off" if inv else "on"
            ),
            tile("high-yield spread", sig["hy_spread"], "% over Treasuries"),
            tile("fed funds", sig["fed_funds"], "%"),
            tile("unemployment", sig["unemployment"], "%"),
        ]
    stretched = sum(1 for r in rows if r["zscore"] is not None and abs(r["zscore"]) >= 2)
    return {
        "verdict": verdict(
            f"{stretched} series more than 2σ from their own history", "mid" if stretched else "on"
        )
        if rows
        else None,
        "tiles": tiles,
        "columns": _FRED_COLUMNS,
        "rows": rows,
        "empty": "no FRED observations yet",
    }


# --- Fails-to-deliver -----------------------------------------------------------

_FTD_SPIKE_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("description", "Security", numeric=False),
    col("settlement_date", "Settled", numeric=False),
    col("quantity", "Fails"),
    col("base", "Typical fails"),
    col("spike_ratio", "× typical"),
]


def _latest_date_rows(
    conn: sqlite3.Connection, sql: str, date_key: str, limit: int
) -> list[dict[str, Any]]:
    """Rows sharing the newest date of a `... ORDER BY <date> DESC, <rank>`
    query, stopping at the first older row. One pass, so an expensive view
    is evaluated once — `WHERE d = (SELECT MAX(d) FROM view)` evaluates it
    twice."""
    rows: list[dict[str, Any]] = []
    newest = None
    for r in conn.execute(sql):
        if newest is None:
            newest = r[date_key]
        if r[date_key] != newest or len(rows) >= limit:
            break
        rows.append(dict(r))
    return rows


def ftd_spikes(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = _latest_date_rows(
        conn,
        "SELECT symbol, description, settlement_date, quantity, base, spike_ratio FROM v_spikes"
        " ORDER BY settlement_date DESC, spike_ratio DESC",
        "settlement_date",
        _TOP,
    )
    return {
        "columns": _FTD_SPIKE_COLUMNS,
        "rows": rows,
        "empty": "no fails-to-deliver spikes on the latest settlement date",
    }


_FTD_LARGEST_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("description", "Security", numeric=False),
    col("settlement_date", "Settled", numeric=False),
    col("quantity", "Fails"),
    col("price", "Price"),
    col("dollar_value", "Dollar value"),
]


def ftd_largest(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT symbol, description, settlement_date, quantity, price, dollar_value"
        " FROM v_latest_fails ORDER BY dollar_value DESC LIMIT ?",
        (_TOP,),
    )
    return {
        "columns": _FTD_LARGEST_COLUMNS,
        "rows": rows,
        "empty": "no fails-to-deliver file loaded yet",
    }


_FTD_STREAK_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("description", "Security", numeric=False),
    col("streak_days", "Days failing"),
    col("streak_start", "Since", numeric=False),
    col("streak_end", "Last", numeric=False),
    col("peak_quantity", "Peak fails"),
]


def ftd_streaks(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT symbol, description, streak_days, streak_start, streak_end, peak_quantity"
        " FROM v_persistent WHERE active = 1 ORDER BY streak_days DESC, peak_quantity DESC"
        " LIMIT ?",
        (_TOP,),
    )
    return {
        "columns": _FTD_STREAK_COLUMNS,
        "rows": rows,
        "empty": "no active fail streaks",
    }


# --- FINRA short volume ---------------------------------------------------------

_SHORT_RATIO_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("date", "Date", numeric=False),
    col("short_ratio", "Short share of volume"),
    col("short_volume", "Short volume"),
    col("total_volume", "Total volume"),
    col("market", "Market", numeric=False),
    spark_col("history", "Ratio, 30 days"),
]


def short_volume_ratio(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT symbol, date, short_ratio, short_volume, total_volume, market"
        " FROM v_high_short_ratio ORDER BY short_ratio DESC LIMIT ?",
        (_TOP,),
    )
    syms = [r["symbol"] for r in rows]
    hist = histories(
        conn,
        f"SELECT symbol, short_ratio FROM v_symbol_history WHERE symbol IN ({_marks(syms)})"
        " ORDER BY date",
        syms,
        limit=30,
    )
    attach_history(rows, hist, "symbol")
    return {
        "columns": _SHORT_RATIO_COLUMNS,
        "rows": rows,
        "empty": "no symbol above the short-ratio threshold today",
    }


_SHORT_STREAK_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("streak_days", "Days elevated"),
    col("streak_start", "Since", numeric=False),
    col("streak_end", "Last", numeric=False),
    col("peak_ratio", "Peak ratio"),
]


def short_volume_streaks(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT symbol, streak_days, streak_start, streak_end, peak_ratio FROM v_short_streaks"
        " WHERE active = 1 ORDER BY streak_days DESC, peak_ratio DESC LIMIT ?",
        (_TOP,),
    )
    return {
        "columns": _SHORT_STREAK_COLUMNS,
        "rows": rows,
        "empty": "no active elevated-short-volume streaks",
    }


# --- FINRA short interest -------------------------------------------------------

_CROWDED_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("settlement_date", "Settled", numeric=False),
    col("days_to_cover", "Days to cover", term="SI days to cover"),
    col("current_short_qty", "Shares short"),
    col("avg_daily_volume", "Avg daily volume"),
    col("change_pct", "Change since prior %"),
    col("market_class", "Market", numeric=False),
    spark_col("history", "Days to cover, 12 reports"),
]


def short_interest_crowded(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT symbol, settlement_date, days_to_cover, current_short_qty, avg_daily_volume,"
        " change_pct, market_class FROM v_high_days_to_cover ORDER BY days_to_cover DESC"
        " LIMIT ?",
        (_TOP,),
    )
    syms = [r["symbol"] for r in rows]
    hist = histories(
        conn,
        f"SELECT symbol, days_to_cover FROM v_symbol_history WHERE symbol IN ({_marks(syms)})"
        " ORDER BY settlement_date",
        syms,
        limit=12,
    )
    attach_history(rows, hist, "symbol")
    return {
        "columns": _CROWDED_COLUMNS,
        "rows": rows,
        "empty": "no short-interest report loaded yet",
    }


# --- Cboe options ---------------------------------------------------------------

_UNUSUAL_COLUMNS = [
    col("underlying", "Underlying", numeric=False),
    col("type", "Type", numeric=False),
    col("expiration", "Expiry", numeric=False),
    col("strike", "Strike"),
    col("volume", "Volume today"),
    col("open_interest", "Open interest"),
    col("vol_oi_ratio", "Volume ÷ OI"),
    col("iv", "Implied vol"),
]


def unusual_options(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = _latest_date_rows(
        conn,
        "SELECT underlying, type, expiration, strike, volume, open_interest, vol_oi_ratio, iv,"
        " snapshot_date FROM v_unusual_activity ORDER BY snapshot_date DESC, vol_oi_ratio DESC",
        "snapshot_date",
        _TOP,
    )
    for r in rows:
        del r["snapshot_date"]
    return {
        "columns": _UNUSUAL_COLUMNS,
        "rows": rows,
        "empty": "no unusual option contracts on the latest snapshot",
    }


# --- Cboe daily statistics -----------------------------------------------------


def options_sentiment(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    tiles: list[dict[str, Any]] = []
    sent = conn.execute(
        "SELECT vix_date, vix_close, pcr_date, equity_pcr, total_pcr, backwardation"
        " FROM v_latest_sentiment"
    ).fetchone()
    if sent is not None:
        v = sent["vix_close"]
        tiles.append(
            tile(
                "VIX",
                v,
                sent["vix_date"],
                None if v is None else "on" if v < 20 else "off" if v >= 25 else "mid",
            )
        )
        tiles.append(tile("equity put/call", sent["equity_pcr"], sent["pcr_date"]))
        tiles.append(tile("total put/call", sent["total_pcr"], sent["pcr_date"]))
    ts = conn.execute(
        "SELECT date, close, vix3m, vix_vix3m_ratio, backwardation FROM v_vix_term_structure"
    ).fetchone()
    if ts is not None:
        back = bool(ts["backwardation"])
        tiles.append(
            tile(
                "VIX ÷ VIX3M",
                ts["vix_vix3m_ratio"],
                "backwardation — near-term fear" if back else "contango — calm",
                "off" if back else "on",
            )
        )
    ex = conn.execute("SELECT date, equity_pcr_pctile, equity_flag FROM v_pcr_extremes").fetchone()
    if ex is not None:
        flag = ex["equity_flag"]
        tiles.append(
            tile(
                "equity put/call percentile",
                None if ex["equity_pcr_pctile"] is None else round(ex["equity_pcr_pctile"] * 100),
                flag or "inside the normal range",
                "mid" if flag else "on",
            )
        )
    return {"tiles": tiles, **({"empty": "no Cboe statistics yet"} if not tiles else {})}


# --- NY Fed ---------------------------------------------------------------------


def funding_markets(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    tiles: list[dict[str, Any]] = []
    sofr = conn.execute(
        "SELECT effective_date, percent_rate, volume_bn, iorb, sofr_iorb_spread FROM v_sofr_latest"
    ).fetchone()
    if sofr is not None:
        spread = sofr["sofr_iorb_spread"]
        tiles += [
            tile("SOFR %", sofr["percent_rate"], sofr["effective_date"]),
            tile("IORB %", sofr["iorb"], sofr["effective_date"]),
            tile(
                "SOFR − IORB",
                spread,
                None if spread is None else "funding stress" if spread > 0.05 else "calm",
                None if spread is None else "off" if spread > 0.05 else "on",
            ),
            tile("SOFR volume ($bn)", sofr["volume_bn"], sofr["effective_date"]),
        ]
    for t in (
        _series_tile(
            conn,
            "Fed balance sheet, SOMA par ($T)",
            "SELECT as_of_date, par_value FROM v_soma_runoff ORDER BY as_of_date",
            limit=52,
            scale=1e12,
        ),
        _series_tile(
            conn,
            "reverse repo take-up ($B)",
            "SELECT operation_date, take_up FROM v_rrp_trend ORDER BY operation_date",
            limit=_DAYS,
            scale=1e9,
        ),
    ):
        if t:
            tiles.append(t)
    return {"tiles": tiles, **({"empty": "no NY Fed rows yet"} if not tiles else {})}


_DEALER_COLUMNS = [
    col("series_key", "Series", numeric=False),
    col("as_of_date", "As of", numeric=False),
    col("value", "Value"),
]


def dealer_positioning(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT series_key, as_of_date, value FROM v_dealer_positioning"
        " ORDER BY as_of_date DESC, series_key LIMIT ?",
        (_TOP,),
    )
    return {
        "columns": _DEALER_COLUMNS,
        "rows": rows,
        "empty": "the NY Fed primary-dealer feed returns no rows for this query"
        " — empty by design until the fetcher's series filter is revisited",
    }


# --- calendars ------------------------------------------------------------------

_WEEK_COLUMNS = [
    col("event_date", "Date", numeric=False),
    col("event_time", "Time", numeric=False),
    col("kind", "Kind", numeric=False),
    col("title", "Event", numeric=False),
    col("detail", "Detail", numeric=False),
]


def week_ahead(data_dir: str, now_iso: str) -> dict[str, Any]:
    """Econ releases and earnings this week as one list, with the FOMC,
    blackout, OPEX and early-close facts as tiles. Each DB is guarded on
    its own so one missing calendar drops only its rows."""
    rows: list[dict[str, Any]] = []
    tiles: list[dict[str, Any]] = []
    failed: list[str] = []

    def guarded(db: str, fn: Any) -> None:
        try:
            conn = ro(data_dir, db)
            try:
                fn(conn)
            finally:
                conn.close()
        except Exception:
            failed.append(db)

    def econ(conn: sqlite3.Connection) -> None:
        for r in fetch(
            conn,
            "SELECT event_date, event_time, label, title, impact, category FROM v_this_week"
            " ORDER BY event_date, event_time",
        ):
            rows.append(
                {
                    "event_date": r["event_date"],
                    "event_time": r["event_time"],
                    "kind": "econ release",
                    "title": r["label"] or r["title"],
                    "detail": f"{r['impact'] or ''} impact · {r['category'] or ''}".strip(" ·"),
                }
            )

    def earnings(conn: sqlite3.Connection) -> None:
        for r in fetch(
            conn,
            "SELECT event_date, event_time, ticker, title, status FROM v_this_week_earnings"
            " ORDER BY event_date, event_time",
        ):
            rows.append(
                {
                    "event_date": r["event_date"],
                    "event_time": r["event_time"],
                    "kind": "earnings",
                    "title": r["ticker"],
                    "detail": r["status"],
                }
            )

    def fomc(conn: sqlite3.Connection) -> None:
        nxt = conn.execute("SELECT event_date, days_until, has_sep FROM v_next_fomc").fetchone()
        if nxt is not None:
            d = nxt["days_until"]
            tiles.append(
                tile(
                    "days to next FOMC",
                    d,
                    f"{nxt['event_date']}{' · with projections' if nxt['has_sep'] else ''}",
                    "mid" if d is not None and d <= 7 else None,
                )
            )
        bo = conn.execute("SELECT in_blackout FROM v_in_blackout").fetchone()
        if bo is not None:
            inb = bool(bo["in_blackout"])
            tiles.append(tile("Fed blackout", "yes" if inb else "no", None, "mid" if inb else "on"))

    def market(conn: sqlite3.Connection) -> None:
        opex = conn.execute("SELECT event_date FROM v_next_opex").fetchone()
        if opex is not None:
            tiles.append(tile("next options expiry", opex["event_date"]))
        early = conn.execute(
            "SELECT event_date, title FROM v_early_closes ORDER BY event_date LIMIT 1"
        ).fetchone()
        if early is not None:
            tiles.append(tile("next early close", early["event_date"], early["title"]))

    calendars = ("econ_calendar.db", "earnings.db", "fomc.db", "market_calendar.db")
    for db, fn in zip(calendars, (econ, earnings, fomc, market), strict=True):
        guarded(db, fn)
    if len(failed) == len(calendars):
        # Nothing readable at all is an outage, not an empty week.
        raise FileNotFoundError("no calendar DB readable")
    rows.sort(key=lambda r: (r["event_date"] or "", r["event_time"] or "", r["kind"]))
    body: dict[str, Any] = {
        "tiles": tiles,
        "columns": _WEEK_COLUMNS,
        "rows": rows,
        "empty": "nothing scheduled this week",
    }
    if failed:
        body["caveat"] = f"{', '.join(failed)} could not be read; the list is partial."
    return body


_EARNINGS_COLUMNS = [
    col("event_date", "Date", numeric=False),
    col("event_time", "Time", numeric=False),
    col("ticker", "Ticker", numeric=False),
    col("title", "Company", numeric=False),
    col("mktcap", "Market cap"),
    col("eps_est", "EPS estimate"),
]


def earnings_confirmed(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT c.event_date, c.event_time, c.ticker, c.title, u.mktcap, u.eps_est"
        " FROM v_earnings_confirmed c LEFT JOIN v_upcoming_earnings u"
        " ON u.ticker = c.ticker AND u.event_date = c.event_date"
        " ORDER BY c.event_date, c.event_time, c.ticker",
    )
    return {
        "columns": _EARNINGS_COLUMNS,
        "rows": rows,
        "empty": "no confirmed earnings dates in the window",
    }


_CLOSURE_COLUMNS = [
    col("event_date", "Date", numeric=False),
    col("kind", "Kind", numeric=False),
    col("title", "Holiday", numeric=False),
    col("event_time", "Closes at", numeric=False),
]


def market_closures(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT event_date, 'closed' AS kind, title, NULL AS event_time FROM v_upcoming_closures"
        " UNION ALL"
        " SELECT event_date, 'early close', title, event_time FROM v_early_closes"
        " ORDER BY event_date",
    )
    return {
        "columns": _CLOSURE_COLUMNS,
        "rows": rows,
        "empty": "no closures in the window",
    }


# --- EIA ----------------------------------------------------------------------------

_EIA_COLUMNS = [
    col("label", "Series", numeric=False),
    col("category", "Category", numeric=False),
    col("latest_period", "Week", numeric=False),
    col("latest", "Latest"),
    col("prior", "Prior week"),
    col("change_abs", "Change"),
    col("change_pct", "Change %"),
    spark_col("history", "52 weeks"),
]


def energy_inventories(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT series_id, label, category, latest_period, latest, prior, change_abs, change_pct"
        " FROM v_weekly_change ORDER BY category, label",
    )
    hist = histories(
        conn, "SELECT series_id, value FROM v_series_history ORDER BY period", limit=52
    )
    attach_history(rows, hist, "series_id")
    for r in rows:
        del r["series_id"]
    return {
        "columns": _EIA_COLUMNS,
        "rows": rows,
        "empty": "no EIA weekly series yet",
    }


# --- USDA ---------------------------------------------------------------------------

_AG_COLUMNS = [
    col("commodity", "Commodity", numeric=False),
    col("period", "Marketing year", numeric=False),
    col("ending_stocks", "Ending stocks"),
    col("total_use", "Total use"),
    col("stocks_to_use", "Stocks-to-use", term="Stocks-to-use"),
    spark_col("history", "Stocks-to-use by year"),
]


def ag_balance(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT s.commodity, s.period, s.ending_stocks, s.total_use, s.stocks_to_use"
        " FROM v_stocks_to_use s WHERE s.period = (SELECT MAX(period) FROM v_stocks_to_use s2"
        " WHERE s2.commodity = s.commodity) ORDER BY s.commodity",
    )
    hist = histories(
        conn,
        "SELECT commodity, stocks_to_use FROM v_stocks_to_use ORDER BY period",
        limit=20,
    )
    attach_history(rows, hist, "commodity")
    series: dict[str, list[dict[str, Any]]] = {}
    for r in conn.execute(
        "SELECT commodity || ' ' || metric, period, value FROM v_series_history ORDER BY period"
    ):
        if r[2] is not None:
            series.setdefault(r[0], []).append({"date": r[1], "value": r[2]})
    tiles = [
        tile(
            f"{b['commodity']} {b['metric']}",
            b["value"],
            f"{b['period']} · {b['unit']}",
            None,
            series.get(f"{b['commodity']} {b['metric']}", [])[-20:],
        )
        for b in fetch(
            conn,
            "SELECT commodity, metric, period, value, unit FROM v_latest_balance"
            " ORDER BY commodity, metric",
        )
    ]
    return {
        "tiles": tiles,
        "columns": _AG_COLUMNS,
        "rows": rows,
        "empty": "no USDA balance-sheet rows yet",
    }


_WASDE_COLUMNS = [
    col("commodity", "Commodity", numeric=False),
    col("region", "Region", numeric=False),
    col("market_year", "Marketing year", numeric=False),
    col("ending_stocks", "Ending stocks"),
    col("total_use", "Total use"),
    col("stocks_to_use", "Stocks-to-use", term="Stocks-to-use"),
    col("unit", "Unit", numeric=False),
]


def wasde(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT commodity, region, market_year, ending_stocks, total_use, stocks_to_use, unit"
        " FROM v_wasde_stocks_to_use ORDER BY commodity, region, market_year",
    )
    return {
        "columns": _WASDE_COLUMNS,
        "rows": rows,
        "empty": "no WASDE report loaded yet",
    }


# --- reddit ---------------------------------------------------------------------------

_REDDIT_COLUMNS = [
    col("ticker", "Ticker", numeric=False),
    col("name", "Name", numeric=False),
    col("filter", "Community", numeric=False),
    col("rank", "Rank"),
    col("mentions", "Mentions, 24h"),
    col("mention_delta", "Δ mentions"),
    col("mention_pct_change", "Δ mentions %"),
    col("rank_delta", "Δ rank"),
    col("upvotes", "Upvotes"),
    spark_col("history", "Mentions, recent captures"),
]


def reddit_trending(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT ticker, name, filter, rank, mentions, mention_delta, mention_pct_change,"
        " rank_delta, upvotes FROM v_trending WHERE filter = 'all-stocks'"
        " ORDER BY mention_delta DESC LIMIT ?",
        (_TOP,),
    )
    syms = [r["ticker"] for r in rows]
    hist = histories(
        conn,
        "SELECT ticker, mentions FROM v_history WHERE filter = 'all-stocks'"
        f" AND ticker IN ({_marks(syms)}) ORDER BY captured_at",
        syms,
        limit=48,
    )
    attach_history(rows, hist, "ticker")
    return {
        "columns": _REDDIT_COLUMNS,
        "rows": rows,
        "caveat": "Crowd attention, not information. A mention spike tells you a"
        " name is crowded — which cuts both ways.",
        "empty": "no reddit capture yet",
    }


# --- EDGAR ----------------------------------------------------------------------------

_INSIDER_COLUMNS = [
    col("ticker", "Ticker", numeric=False),
    col("company", "Company", numeric=False),
    col("insider_filings", "Insider filings"),
    spark_col("history", "Filings per index day"),
]


def insider_activity(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT ticker, company, insider_filings FROM v_insider_activity"
        " ORDER BY insider_filings DESC, ticker LIMIT ?",
        (_TOP,),
    )
    syms = [r["ticker"] for r in rows]
    hist = histories(
        conn,
        f"SELECT ticker, filings_count FROM v_activity_history WHERE ticker IN ({_marks(syms)})"
        " ORDER BY index_date",
        syms,
        limit=30,
    )
    attach_history(rows, hist, "ticker")
    return {
        "columns": _INSIDER_COLUMNS,
        "rows": rows,
        "empty": "no insider filings in the retained window",
    }


_FILING_COLUMNS = [
    col("filed_date", "Filed", numeric=False),
    col("ticker", "Ticker", numeric=False),
    col("company", "Company", numeric=False),
    col("form", "Form", numeric=False),
]


def _filings(conn: sqlite3.Connection, view: str, empty: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        f"SELECT filed_date, ticker, company, form FROM {view}"
        " ORDER BY filed_date DESC, ticker LIMIT ?",
        (_TOP,),
    )
    return {"columns": _FILING_COLUMNS, "rows": rows, "empty": empty}


def recent_filings(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    return _filings(conn, "v_events", "no event filings in the retained window")


def offerings(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    return _filings(conn, "v_offerings", "no offering filings in the retained window")


def stakes(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    return _filings(conn, "v_stakes", "no 13D/13G stake filings in the retained window")


SECTIONS: list[Any] = [
    (
        "week-ahead",
        "This week",
        "econ_calendar + earnings + fomc + market_calendar DBs",
        week_ahead,
        "Macro",
        "Every scheduled release and earnings report this week, plus the Fed and expiry dates that shape it.",
        [
            (
                "What is in it",
                "Economic releases from the official calendar, confirmed"
                " earnings dates, the next FOMC meeting and whether the Fed"
                " is in its pre-meeting quiet period, the next monthly"
                " options expiry, and the next early market close.",
            ),
            (
                "Why it matters",
                "A high-impact release or an FOMC day is the most common"
                " reason a signal moves for reasons that have nothing to do"
                " with the stock.",
            ),
        ],
    ),
    (
        "yield-curve",
        "Treasury yield curve",
        "treasury.db",
        yield_curve,
        "Macro",
        "Short and long Treasury yields and whether the curve is inverted, straight from the Treasury's daily table.",
        [
            (
                "How to read it",
                "Normally the 10-year pays more than the 2-year. When it"
                " pays less the curve is 'inverted' — historically a"
                " recession warning, though the timing is loose.",
            ),
        ],
    ),
    (
        "federal-debt",
        "Federal debt and the Treasury's cash",
        "treasury.db",
        federal_debt,
        "Macro",
        "Total public debt and the government's checking-account balance over the last 90 days.",
        [
            (
                "Why it matters",
                "When the Treasury rebuilds its cash balance it drains"
                " reserves from the banking system; when it spends it down"
                " it adds them. Either way it is liquidity moving in the"
                " background of every price.",
            ),
        ],
    ),
    (
        "funding-markets",
        "Funding markets",
        "nyfed.db",
        funding_markets,
        "Macro",
        "Overnight rates and the Fed's balance sheet — the plumbing that shows stress before prices do.",
        [
            (
                "What the numbers are",
                "SOFR is the overnight rate banks actually borrow at; IORB"
                " is what the Fed pays on reserves. SOFR trading above IORB"
                " means cash is scarce. SOMA is the Fed's bond portfolio;"
                " reverse repo is cash parked at the Fed overnight.",
            ),
        ],
    ),
    (
        "fred-series",
        "FRED series",
        "fred.db",
        fred_series,
        "Macro",
        "Every tracked economic series with its year-over-year change and how unusual today's level is.",
        [
            (
                "How to read it",
                "Z-score is how many standard deviations the latest value"
                " sits from the series' own history — beyond ±2 is rare."
                " The tiles are the regime's raw inputs; the regime card"
                " above turns them into a verdict.",
            ),
        ],
    ),
    (
        "cot-positioning",
        "Futures positioning — legacy report",
        "cftc.db",
        cot_positioning,
        "Signals",
        "Where large speculators sit in each futures contract, and which contracts are at a positioning extreme.",
        [
            (
                "What the COT index is",
                "Speculators' net position, scaled 0–100 against its own"
                " three-year range: 100 means the most long they have been,"
                " 0 the most short. Extremes tend to precede reversals"
                " because there is nobody left to join the trade.",
            ),
            (
                "The three reports",
                "The CFTC publishes the same data three ways: this legacy"
                " split (commercial vs speculator), a disaggregated split"
                " for commodities, and a financial-futures split. The other"
                " two have their own cards.",
            ),
        ],
    ),
    (
        "cot-disaggregated",
        "Futures positioning — commodities",
        "cftc.db",
        cot_disaggregated,
        "Signals",
        "Managed money versus the producers and merchants who actually handle each commodity.",
        [
            (
                "How to read it",
                "Managed money is hedge funds; commercials are producers"
                " and processors hedging real supply. When the two indexes"
                " sit at opposite ends the commercials have usually been"
                " right.",
            ),
        ],
    ),
    (
        "cot-financial",
        "Futures positioning — financials",
        "cftc.db",
        cot_financial,
        "Signals",
        "Leveraged funds versus dealers in equity-index, rate and currency futures.",
        [
            (
                "How to read it",
                "Leveraged funds are the fast money; dealers are the banks"
                " on the other side of their trades. A leveraged-fund"
                " index near 0 or 100 marks a crowded position.",
            ),
        ],
    ),
    (
        "auction-demand",
        "Treasury auction demand",
        "treasury.db",
        auction_demand,
        "Macro",
        "How eagerly the last thirty Treasury auctions were bid, against each security's usual demand.",
        [
            (
                "How to read it",
                "Bid-to-cover is dollars bid per dollar sold; below its"
                " typical level means buyers wanted a higher yield to show"
                " up. A run of weak auctions pushes long rates up.",
            ),
        ],
    ),
    (
        "upcoming-auctions",
        "Upcoming Treasury auctions",
        "treasury.db",
        upcoming_auctions,
        "Macro",
        "Announced auctions in the coming weeks — supply days that can move rates.",
        [
            (
                "Why it matters",
                "A large coupon auction on the same day as a data release"
                " is the classic set-up for a rates surprise.",
            ),
        ],
    ),
    (
        "dark-pools",
        "Dark pools",
        "ats.db",
        dark_pools,
        "Signals",
        "How much trading happened off the public exchanges last week, and on which venues.",
        [
            (
                "What a dark pool is",
                "A private venue where large orders trade without showing"
                " on the public order book. FINRA publishes each venue's"
                " weekly volume with a two-week delay.",
            ),
        ],
    ),
    (
        "off-exchange-leaders",
        "Most-traded off exchange",
        "ats.db",
        off_exchange_leaders,
        "Signals",
        "The symbols with the most dark-pool volume last week, with their weekly trend.",
        [
            (
                "Why it matters",
                "Institutions work large orders in the dark. A symbol whose"
                " off-exchange share is climbing is being accumulated or"
                " distributed by someone big — the direction is not shown.",
            ),
        ],
    ),
    (
        "sec-revisions",
        "Restated financials",
        "sec_fundamentals.db",
        sec_revisions,
        "Signals",
        "The newest cases where a company's later filing changed a number it had already reported.",
        [
            (
                "Why it matters",
                "A restatement is a company correcting its own past. Small"
                " ones are routine; a large one on revenue or net income"
                " is a reason to read the filing.",
            ),
        ],
    ),
    (
        "sec-screener",
        "Largest filers",
        "sec_fundamentals.db",
        sec_screener,
        "Signals",
        "The biggest companies by reported revenue, straight from their XBRL filings.",
        [
            (
                "Where it comes from",
                "The SEC's company-facts feed — the audited numbers"
                " themselves, not a data vendor's copy. The candidates"
                " screen reads the same feed for its quality gates.",
            ),
        ],
    ),
    (
        "ftd-spikes",
        "Fails-to-deliver spikes",
        "ftd.db",
        ftd_spikes,
        "Signals",
        "Securities whose delivery failures jumped far above their own normal on the latest settlement date.",
        [
            (
                "What a fail is",
                "A trade where the seller did not deliver the shares on"
                " time. A spike often means shares are hard to borrow —"
                " a crowded short.",
            ),
        ],
    ),
    (
        "ftd-largest",
        "Largest fails by dollar value",
        "ftd.db",
        ftd_largest,
        "Signals",
        "The biggest delivery failures on the latest settlement date, in dollars.",
        [
            (
                "How to read it",
                "Dollar value is fails × price. Large-cap names appear here"
                " on routine settlement noise; a small-cap here is the"
                " interesting case.",
            ),
        ],
    ),
    (
        "ftd-streaks",
        "Persistent fails",
        "ftd.db",
        ftd_streaks,
        "Signals",
        "Securities that have failed to deliver for the most consecutive days and are still failing.",
        [
            (
                "Why it matters",
                "A fail that persists past the regulatory close-out window"
                " means someone is being forced to buy in — a mechanical"
                " source of demand.",
            ),
        ],
    ),
    (
        "short-volume-ratio",
        "Heaviest short selling today",
        "short_volume.db",
        short_volume_ratio,
        "Signals",
        "Symbols where an unusually large share of today's volume was short sales.",
        [
            (
                "How to read it",
                "FINRA reports each day's short volume per symbol. A high"
                " ratio can mean bearish conviction — or market makers"
                " hedging heavy call buying. The sparkline shows whether"
                " it is new.",
            ),
        ],
    ),
    (
        "short-volume-streaks",
        "Sustained short pressure",
        "short_volume.db",
        short_volume_streaks,
        "Signals",
        "Symbols that have stayed above the short-ratio threshold for the most consecutive days.",
        [
            (
                "Why it matters",
                "One heavy day is noise; a streak is a campaign. These are"
                " the names where the short side has been leaning for"
                " weeks.",
            ),
        ],
    ),
    (
        "short-interest-crowded",
        "Most crowded shorts",
        "short_interest.db",
        short_interest_crowded,
        "Signals",
        "Symbols where it would take the longest to buy back every short share at normal volume.",
        [
            (
                "What days-to-cover means",
                "Shares short divided by average daily volume. Ten days"
                " means shorts need two weeks of the entire market's"
                " volume to exit — the fuel for a squeeze.",
            ),
        ],
    ),
    (
        "unusual-options",
        "Unusual option activity",
        "options.db",
        unusual_options,
        "Signals",
        "Option contracts that traded far more today than exist in open interest.",
        [
            (
                "How to read it",
                "Volume ÷ open interest above 1 means more contracts"
                " changed hands today than were outstanding — new"
                " positioning, not old positions closing. Whether it is"
                " a bet or a hedge is not visible.",
            ),
        ],
    ),
    (
        "options-sentiment",
        "Options-market mood",
        "cboe_stats.db",
        options_sentiment,
        "Sources",
        "The fear gauge, the put/call ratios and the VIX term structure — the regime's raw Cboe inputs.",
        [
            (
                "What the numbers are",
                "The VIX is the market's expected 30-day swing; above 25"
                " is fear, below 20 calm. Put/call above 1 means more"
                " hedging than betting. VIX above VIX3M ('backwardation')"
                " means the next month scares people more than the quarter.",
            ),
            (
                "Why it matters",
                "These three are the regime card's voters, shown here raw so"
                " you can see how close the call was.",
            ),
        ],
    ),
    (
        "dealer-positioning",
        "Primary dealer positions",
        "nyfed.db",
        dealer_positioning,
        "Macro",
        "What the Fed's primary dealers hold, from the NY Fed's weekly survey.",
        [
            (
                "Status",
                "The current fetch returns no rows for this domain; the"
                " card stays so the gap is visible rather than silent.",
            ),
        ],
    ),
    (
        "earnings-confirmed",
        "Confirmed earnings dates",
        "earnings.db",
        earnings_confirmed,
        "Signals",
        "Upcoming earnings reports whose dates the company has confirmed, not estimated.",
        [
            (
                "Why confirmed matters",
                "Estimated dates slip. A confirmed date is when the"
                " options market's implied move becomes a real deadline"
                " for any thesis on the name.",
            ),
        ],
    ),
    (
        "market-closures",
        "Market holidays",
        "market_calendar.db",
        market_closures,
        "Ops",
        "Upcoming NYSE closures and early closes — days the executor must not expect an open.",
        [
            (
                "Why it is under Ops",
                "The order executor and every trading-day calculation key"
                " off this list. An early close ends the intraday window"
                " early.",
            ),
        ],
    ),
    (
        "energy-inventories",
        "Energy inventories",
        "eia.db",
        energy_inventories,
        "Signals",
        "Weekly US crude, product and gas stocks with the change from last week and a year's trend.",
        [
            (
                "How to read it",
                "A draw (negative change) tightens supply and supports"
                " prices; a build does the opposite. The sparkline shows"
                " the seasonal pattern the weekly number sits inside.",
            ),
        ],
    ),
    (
        "ag-balance",
        "Grain balance sheets",
        "usda.db",
        ag_balance,
        "Signals",
        "For each major crop, how much will be left over at the end of the marketing year relative to use.",
        [
            (
                "What stocks-to-use means",
                "Ending stocks divided by total use — the cushion. A low"
                " ratio means any weather scare hits price hard; a high"
                " one means supply can absorb surprises.",
            ),
        ],
    ),
    (
        "wasde",
        "WASDE world balance",
        "usda.db",
        wasde,
        "Signals",
        "The USDA's monthly world supply-and-demand estimates by commodity and region.",
        [
            (
                "How to read it",
                "The same stocks-to-use ratio as the card above, but from"
                " the monthly WASDE report and split by region — the"
                " number grain traders wait for each month.",
            ),
        ],
    ),
    (
        "reddit-trending",
        "Reddit attention",
        "reddit.db",
        reddit_trending,
        "Signals",
        "The tickers gaining the most mentions across stock subreddits in the last 24 hours.",
        [
            (
                "How to read it",
                "Rank and mentions come from ApeWisdom's tally. Attention"
                " is a crowding measure: a name everyone is talking about"
                " has no one left to discover it.",
            ),
        ],
    ),
    (
        "insider-activity",
        "Insider filings",
        "edgar.db",
        insider_activity,
        "Signals",
        "Companies with the most insider transaction filings in the retained window.",
        [
            (
                "What a Form 4 is",
                "Officers and directors must report their own trades"
                " within two days. Filing count alone does not say buy or"
                " sell — click through to EDGAR for the direction.",
            ),
        ],
    ),
    (
        "recent-filings",
        "Recent event filings",
        "edgar.db",
        recent_filings,
        "Sources",
        "The newest 8-K and other event filings from tracked companies — something happened and had to be disclosed.",
        [
            (
                "What an 8-K is",
                "A 'current report' a company must file within four days"
                " of a material event: an acquisition, a departure, a"
                " restatement, a covenant breach. The form code says which.",
            ),
        ],
    ),
    (
        "offerings",
        "Share offerings",
        "edgar.db",
        offerings,
        "Signals",
        "The newest registration statements and prospectuses — companies preparing to sell stock.",
        [
            (
                "Why it matters",
                "An offering adds supply and usually prices below market."
                " A name on the candidates list that files one is about"
                " to dilute you.",
            ),
        ],
    ),
    (
        "stakes",
        "Activist and large-holder stakes",
        "edgar.db",
        stakes,
        "Signals",
        "New 13D and 13G filings — someone crossed the 5% ownership line.",
        [
            (
                "13D vs 13G",
                "A 13D is an active holder who may push for change; a 13G"
                " is passive. Either is a large buyer revealing itself.",
            ),
        ],
    ),
]

# Raw-source cards live in their own "Sources" strand so the Signals tab
# stays composite's opinions and Macro stays the verdict plus the calendar.
# Two cards are the exception: the week's calendar is Macro, and the
# holiday list is Ops (the executor keys off it).
_STRAND_OVERRIDES = {"week-ahead": "Macro", "market-closures": "Ops"}
SECTIONS = [
    (sid, title, db, fn, _STRAND_OVERRIDES.get(sid, "Sources"), note, about)
    for sid, title, db, fn, _kicker, note, about in SECTIONS
]
