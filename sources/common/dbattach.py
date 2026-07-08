"""Read-only ATTACH helpers shared by the combiners. A combiner reads other
data/*.db files ATTACHed read-only and derives cross-source views; this is the
one place that contract lives."""

import os


def attach_ro(conn, db_path: str, alias: str = "src") -> None:
    """Attach a source DB read-only. The connection must have been opened with
    uri=True or the mode=ro URI is rejected by SQLite."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    conn.execute(f"ATTACH DATABASE ? AS {alias}", (f"file:{db_path}?mode=ro",))


def detach(conn, alias: str = "src") -> None:
    conn.execute(f"DETACH DATABASE {alias}")
