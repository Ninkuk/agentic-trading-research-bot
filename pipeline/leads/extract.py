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
