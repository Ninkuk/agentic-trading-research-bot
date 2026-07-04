import json
from bisect import bisect_left
from collections import defaultdict
from datetime import date, timedelta

from pipeline.common import pipeline_common
from pipeline.leads import catalog

# How far each source's data reaches, for run provenance (source_state).
SOURCE_STATE_SQL = {
    "cftc": ("SELECT MAX(d) FROM ("
             "SELECT MAX(report_date) AS d FROM cot_disagg "
             "UNION ALL SELECT MAX(report_date) AS d FROM cot_tff)"),
    "fred": "SELECT MAX(date) FROM observations",
    "fundamentals": "SELECT MAX(period_end) FROM facts",
    "stocks": "SELECT MAX(captured_at) FROM snapshots",
}


def read_source_state(conn, source: str, db_path: str) -> dict:
    """One provenance row for source_state: the source's own latest run header
    plus how far its data reaches."""
    captured = conn.execute(
        "SELECT MAX(captured_at) FROM snapshots").fetchone()[0]
    max_data = conn.execute(SOURCE_STATE_SQL[source]).fetchone()[0]
    return {"source": source, "db_path": db_path,
            "source_captured_at": captured, "max_data_date": max_data}


# family -> (premise index view, speculator confirm view) — spec D1: physicals
# take producer/merchant, financials take dealer; speculator side is recorded
# in details, never required (whether divergence gates is Stage 2's call).
_FAMILY_VIEWS = {
    "disaggregated": ("v_disagg_cot_index_commercial_latest",
                      "v_disagg_cot_index_latest"),
    "tff": ("v_tff_cot_index_dealer_latest", "v_tff_cot_index_latest"),
}


def extract_cot_extremes(conn, mappings=catalog.ETF_MAP,
                         long_threshold=catalog.COT_LONG_THRESHOLD,
                         short_threshold=catalog.COT_SHORT_THRESHOLD) -> list[dict]:
    """COT commercial extremes -> ETF lead dicts (spec D2). Emits a lead when
    the commercial index is at a 3y extreme; mid-range, missing, or
    degenerate-range markets produce no lead."""
    leads = []
    for m in mappings:
        family = ("disaggregated" if m.asset_class in catalog.PHYSICAL_CLASSES
                  else "tff")
        premise_view, spec_view = _FAMILY_VIEWS[family]
        row = conn.execute(
            f"SELECT p.report_date, p.cot_index, s.cot_index "
            f"FROM {premise_view} p "
            f"LEFT JOIN {spec_view} s ON s.code = p.code "
            f"WHERE p.code = ?", (m.code,)).fetchone()
        if row is None:
            continue
        report_date, commercial_index, speculator_index = row
        if commercial_index is None:
            continue
        if commercial_index >= long_threshold:
            direction = "long"
        elif commercial_index <= short_threshold:
            direction = "short"
        else:
            continue
        leads.append({
            "instrument": m.etf,
            "instrument_kind": "etf",
            "signal": "cot_commercial_extreme",
            "direction": direction,
            "signal_type": "mean_reversion",
            "implementation": "cross_sectional",
            "horizon_band": "weeks",
            "score": commercial_index,
            "rank_pct": None,
            "as_of_date": report_date,
            "details": json.dumps(
                {"code": m.code, "asset_class": m.asset_class,
                 "family": family, "commercial_index": commercial_index,
                 "speculator_index": speculator_index},
                separators=(",", ":")),
        })
    return leads


def _universe(stocks_conn):
    """Latest stocks snapshot's primary listings: normalized ticker -> sector,
    plus the snapshot vintage (captured_at) — the quality leads' as_of basis
    (spec D5). Missing sector/isPrimaryListing columns raise OperationalError,
    which run() turns into a skipped leg."""
    vintage = stocks_conn.execute(
        "SELECT captured_at FROM snapshots "
        "ORDER BY captured_at DESC, id DESC LIMIT 1").fetchone()
    if vintage is None:
        return {}, None
    rows = stocks_conn.execute(
        'SELECT symbol, "sector" FROM v_latest '
        'WHERE "isPrimaryListing" = 1').fetchall()
    return ({pipeline_common.normalize_ticker(sym): sector
             for sym, sector in rows if sym}, vintage[0])


def _screener_ratios(fund_conn):
    """cik -> normalized ticker + the v_screener ratio columns."""
    out = {}
    for cik, ticker, nm, roe, dte in fund_conn.execute(
            "SELECT cik, ticker, net_margin, roe, debt_to_equity "
            "FROM v_screener"):
        if ticker:
            out[cik] = {"ticker": pipeline_common.normalize_ticker(ticker),
                        "net_margin": nm, "roe": roe, "debt_to_equity": dte}
    return out


def _pair_yoy(series_desc, window_days, ratio_bounds):
    """series_desc: [(period_end, value)] newest first. Latest fact vs the
    companion nearest 12 months earlier within +/-window_days (spec D4 —
    period_end-aligned, NOT keyed on fiscal_period). Returns a fraction or
    None. A pair whose latest/year-ago ratio falls outside ratio_bounds is
    discarded (quarterly/annual mismatch guard)."""
    latest_pe, latest_v = series_desc[0]
    target = date.fromisoformat(latest_pe) - timedelta(days=365)
    best = None
    for pe, v in series_desc[1:]:
        gap = abs((date.fromisoformat(pe) - target).days)
        if gap <= window_days and (best is None or gap < best[0]):
            best = (gap, v)
    if best is None:
        return None
    year_ago = best[1]
    if not year_ago:
        return None
    lo, hi = ratio_bounds
    if not (lo <= latest_v / year_ago <= hi):
        return None
    return (latest_v - year_ago) / abs(year_ago)


def _revenue_yoy(fund_conn, window_days=catalog.GROWTH_WINDOW_DAYS,
                 ratio_bounds=catalog.GROWTH_RATIO_BOUNDS):
    """cik -> revenue YoY fraction. Tag precedence is per company: the first
    REVENUE_TAGS tag the company reports at all is its revenue series (spec
    D4 — precedence, not v_screener's MAX-across-both quirk).

    facts' PK is (cik, tag, period_end, form): a restated filing (e.g. a
    10-K/A superseding the original 10-K for the same period_end) produces a
    second row. Dedupe to the most-recently-FILED row per (cik, tag,
    period_end) before pairing — same convention as
    sec_fundamentals.db.v_latest_fundamentals' ORDER BY period_end DESC,
    filed DESC. NULL filed sorts as older than any non-NULL filed date."""
    latest = {}  # (cik, tag, period_end) -> (filed_sort_key, value)
    qmarks = ",".join("?" * len(catalog.REVENUE_TAGS))
    for cik, tag, pe, value, filed in fund_conn.execute(
            f"SELECT cik, tag, period_end, value, filed FROM facts "
            f"WHERE tag IN ({qmarks}) AND value IS NOT NULL",
            catalog.REVENUE_TAGS):
        key = (cik, tag, pe)
        sort_key = filed or ""
        prior = latest.get(key)
        if prior is None or sort_key >= prior[0]:
            latest[key] = (sort_key, value)
    facts = defaultdict(list)
    for (cik, tag, pe), (_filed, value) in latest.items():
        facts[(cik, tag)].append((pe, value))
    out = {}
    for cik in {cik for cik, _tag in facts}:
        for tag in catalog.REVENUE_TAGS:
            series = facts.get((cik, tag))
            if not series:
                continue
            yoy = _pair_yoy(sorted(series, reverse=True),
                            window_days, ratio_bounds)
            if yoy is not None:
                out[cik] = yoy
            break  # precedence: first present tag decides, even if it yields None
    return out


def _zscores(values: dict) -> dict:
    """key -> z over the non-None values; population stddev via the moment
    form (AVG(x*x) - AVG(x)^2), matching fred_screener.v_zscore. Fewer than 2
    values or zero spread -> {} (no z is computable)."""
    keyed = {k: v for k, v in values.items() if v is not None}
    n = len(keyed)
    if n < 2:
        return {}
    mean = sum(keyed.values()) / n
    var = sum(v * v for v in keyed.values()) / n - mean * mean
    sd = var ** 0.5 if var > 0 else 0.0
    if sd == 0:
        return {}
    return {k: (v - mean) / sd for k, v in keyed.items()}


def _sector_zscores(metric_by_ticker: dict, sector_by_ticker: dict) -> dict:
    """Member z within stockanalysis sector — dummies-only OLS neutralization
    == group demeaning (spec D4 step 1)."""
    by_sector = defaultdict(dict)
    for t, v in metric_by_ticker.items():
        by_sector[sector_by_ticker[t]][t] = v
    out = {}
    for sector_values in by_sector.values():
        out.update(_zscores(sector_values))
    return out


def _percent_rank(scores: dict) -> dict:
    """PERCENT_RANK() semantics: (rank-1)/(N-1), ties share the lowest rank,
    a single row ranks 0.0. Denominator = valid names only (the research's
    drifting-universe rule)."""
    items = list(scores.items())
    n = len(items)
    if n == 1:
        return {items[0][0]: 0.0}
    ordered = sorted(v for _k, v in items)
    return {k: bisect_left(ordered, v) / (n - 1) for k, v in items}


def extract_quality(fund_conn, stocks_conn,
                    min_dimensions=catalog.QUALITY_MIN_DIMENSIONS,
                    top=catalog.QUALITY_TOP_DECILE,
                    bottom=catalog.QUALITY_BOTTOM_DECILE):
    """QMJ-style quality composite -> stock lead dicts (spec D4/D5).
    Returns (leads, dropped) — dropped counts joined names discarded for
    having fewer than min_dimensions dimension scores."""
    universe, vintage = _universe(stocks_conn)
    if not universe:
        return [], 0
    ratios = _screener_ratios(fund_conn)
    yoy = _revenue_yoy(fund_conn)

    # inner join on normalized ticker (spec D5): names failing the join drop out
    members = {}
    for cik, r in ratios.items():
        t = r["ticker"]
        if t in universe and universe[t] is not None:
            members[t] = {"cik": cik, "sector": universe[t],
                          "net_margin": r["net_margin"], "roe": r["roe"],
                          "debt_to_equity": r["debt_to_equity"],
                          "revenue_yoy": yoy.get(cik)}
    if not members:
        return [], 0

    sectors = {t: m["sector"] for t, m in members.items()}
    z_margin = _sector_zscores(
        {t: m["net_margin"] for t, m in members.items()}, sectors)
    z_roe = _sector_zscores(
        {t: m["roe"] for t, m in members.items()}, sectors)
    z_growth = _sector_zscores(
        {t: m["revenue_yoy"] for t, m in members.items()}, sectors)
    z_safety = _sector_zscores(
        {t: (-m["debt_to_equity"] if m["debt_to_equity"] is not None else None)
         for t, m in members.items()}, sectors)

    composites, dims_by_ticker, dropped = {}, {}, 0
    for t in members:
        prof_parts = [z for z in (z_margin.get(t), z_roe.get(t))
                      if z is not None]
        dims = {
            "profitability_z": (sum(prof_parts) / len(prof_parts)
                                if prof_parts else None),
            "growth_z": z_growth.get(t),
            "safety_z": z_safety.get(t),
        }
        present = [v for v in dims.values() if v is not None]
        if len(present) < min_dimensions:
            dropped += 1
            continue
        # mean of present dimensions (spec D4 step 2: a plain SQL `+` would
        # NULL the composite on one missing member — this must not)
        composites[t] = sum(present) / len(present)
        dims_by_ticker[t] = dims

    # outer z + PERCENT_RANK are global across the whole universe (spec D4
    # step 3 — sector effects were already removed at the member level)
    outer_z = _zscores(composites)
    if not outer_z:
        return [], dropped
    ranks = _percent_rank(outer_z)

    as_of = (vintage or "")[:10]
    leads = []
    for t, pct in ranks.items():
        if pct >= top:
            direction = "long"
        elif pct <= bottom:
            direction = "short"
        else:
            continue
        leads.append({
            "instrument": t,
            "instrument_kind": "stock",
            "signal": "quality_composite",
            "direction": direction,
            "signal_type": "quality",
            "implementation": "cross_sectional",
            "horizon_band": "months",
            "score": outer_z[t],
            "rank_pct": pct,
            "as_of_date": as_of,
            "details": json.dumps(
                {**dims_by_ticker[t], "sector": members[t]["sector"],
                 "cik": members[t]["cik"]}, separators=(",", ":")),
        })
    return leads, dropped
