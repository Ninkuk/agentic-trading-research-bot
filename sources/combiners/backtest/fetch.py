"""Pure extraction against fred.db ATTACHed read-only. No network anywhere
in this package — the replay's external feed is the local data/ dir (same
convention as the composite combiner)."""

from sources.common.dbattach import attach_ro, detach  # noqa: F401  (re-exported)


def harvest_vintages(conn, series_ids) -> list:
    """Full vintage history for the replay series, verbatim."""
    ids = list(series_ids)
    qmarks = ",".join("?" * len(ids))
    return conn.execute(
        "SELECT series_id, date, realtime_start, value"
        f" FROM src.observation_vintages WHERE series_id IN ({qmarks})"
        " ORDER BY series_id, date, realtime_start",
        ids,
    ).fetchall()


def harvest_benchmark(conn, series_id: str) -> list:
    """Benchmark daily closes; index closes are unrevised so plain
    observations suffice (no vintages needed)."""
    return conn.execute(
        "SELECT date, value FROM src.observations"
        " WHERE series_id = ? AND value IS NOT NULL ORDER BY date",
        (series_id,),
    ).fetchall()
