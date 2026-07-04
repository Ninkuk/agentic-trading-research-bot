"""Read-only inputs for the promotion gates: the latest lead cohort (with the
run's regime scalar) and per-symbol liquidity/sizing fields from the
stockanalysis stocks/etfs DBs."""
from pipeline.common import pipeline_common

_LEAD_KEYS = ("instrument", "instrument_kind", "signal", "direction",
              "signal_type", "implementation", "horizon_band", "score",
              "rank_pct", "as_of_date", "details")


def load_latest_leads(conn) -> dict:
    """Latest snapshot's leads + the regime exposure scalar (1.0 when the
    regime leg was skipped — NULL scalar must not zero the book)."""
    sid_row = conn.execute(
        "SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1"
    ).fetchone()
    leads = []
    scalar = None
    for row in conn.execute(
            "SELECT instrument, instrument_kind, signal, direction, "
            "signal_type, implementation, horizon_band, score, rank_pct, "
            "as_of_date, details, exposure_scalar FROM v_latest_leads"):
        leads.append(dict(zip(_LEAD_KEYS, row[:-1])))
        scalar = row[-1]
    return {"leads": leads,
            "regime_scalar": scalar if scalar is not None else 1.0,
            "leads_snapshot_id": sid_row[0] if sid_row else None}


def check_required_columns(conn, required, db_label: str) -> None:
    """Fail up front with the full missing-id list (dynamic metrics columns —
    a clear error beats `no such column` mid-gate)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(metrics)")}
    missing = [c for c in required if c not in cols]
    if missing:
        raise ValueError(
            f"{db_label} metrics table missing required data points: "
            f"{', '.join(missing)} (was it built with --only?)")


def load_liquidity(conn, required) -> dict:
    """SYMBOL -> {data point: value} for the latest snapshot's rows."""
    quoted = ", ".join(f'"{c}"' for c in required)
    out = {}
    for row in conn.execute(f"SELECT symbol, {quoted} FROM v_latest"):
        sym = row[0]
        if sym:
            out[pipeline_common.normalize_ticker(sym)] = dict(
                zip(required, row[1:]))
    return out
