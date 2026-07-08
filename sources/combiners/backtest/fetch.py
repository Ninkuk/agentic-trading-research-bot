"""Pure extraction against fred.db ATTACHed read-only. No network anywhere
in this package — the replay's external feed is the local data/ dir (same
convention as the composite combiner)."""

import os


def attach_ro(conn, db_path: str, alias: str = "src") -> None:
    """Attach a source DB read-only. The connection must have been opened
    with uri=True or the mode=ro URI is rejected by SQLite."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    conn.execute(f"ATTACH DATABASE ? AS {alias}", (f"file:{db_path}?mode=ro",))


def detach(conn, alias: str = "src") -> None:
    conn.execute(f"DETACH DATABASE {alias}")


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
