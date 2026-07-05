"""Read-only inputs for the promotion gates: the latest lead cohort (with the
run's regime scalar), per-symbol liquidity/sizing fields from the
stockanalysis stocks/etfs DBs, and per-name retail-attention baselines from
reddit.db (crowding gate)."""
from datetime import datetime, timedelta

from pipeline.common import pipeline_common
from pipeline.promote import catalog

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


def load_crowding(conn, now_iso: str, baseline_days: int) -> dict:
    """TICKER -> latest all-stocks rank/mentions + the name's OWN trailing
    baseline (mean/std/n over prior snapshots inside the window, excluding
    the latest). Names absent from the latest snapshot are simply absent
    (= calm — top-N list semantics, no data_missing noise). Std is
    population std computed in Python (SQLite has no STDEV)."""
    latest = conn.execute(
        "SELECT id, captured_at FROM snapshots WHERE filter=? "
        "ORDER BY captured_at DESC, id DESC LIMIT 1",
        (catalog.CROWDING_FILTER,)).fetchone()
    if latest is None:
        return {}
    latest_id, latest_at = latest
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=baseline_days)).isoformat()
    out, hist = {}, {}
    for ticker, rank, mentions in conn.execute(
            "SELECT ticker, rank, mentions FROM observations "
            "WHERE snapshot_id=?", (latest_id,)):
        t = pipeline_common.normalize_ticker(ticker)
        out[t] = {"rank": rank, "mentions": mentions,
                  "baseline_mean": None, "baseline_std": None, "n": 0}
        hist[t] = []
    for ticker, mentions in conn.execute(
            "SELECT o.ticker, o.mentions FROM observations o "
            "JOIN snapshots s ON s.id = o.snapshot_id "
            "WHERE s.filter=? AND s.id != ? AND s.captured_at >= ? "
            "AND s.captured_at < ?",
            (catalog.CROWDING_FILTER, latest_id, cutoff, latest_at)):
        t = pipeline_common.normalize_ticker(ticker)
        if t in hist and mentions is not None:
            hist[t].append(mentions)
    for t, series in hist.items():
        out[t]["n"] = len(series)
        if series:
            mean = sum(series) / len(series)
            out[t]["baseline_mean"] = mean
            out[t]["baseline_std"] = (sum((x - mean) ** 2 for x in series)
                                      / len(series)) ** 0.5
    return out


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
