"""Read-only SQLite access shared by the combiners and the reporters. A
combiner reads other data/*.db files ATTACHed read-only and derives
cross-source views; a reporter opens a source read-only outright. This is the
one place both contracts live."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager


def connect_ro(path: str) -> sqlite3.Connection:
    """Open a DB read-only. The guarantee lives in the connection, not in
    discipline, so a reporter can never write to a source DB."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return sqlite3.connect(f"file:{os.path.abspath(path)}?mode=ro", uri=True)


def attach_ro(conn, db_path: str, alias: str = "src") -> None:
    """Attach a source DB read-only. The connection must have been opened with
    uri=True or the mode=ro URI is rejected by SQLite."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    conn.execute(f"ATTACH DATABASE ? AS {alias}", (f"file:{db_path}?mode=ro",))


def detach(conn, alias: str = "src") -> None:
    conn.execute(f"DETACH DATABASE {alias}")


@contextmanager
def attached(conn, db_path: str, alias: str = "src") -> Iterator[None]:
    """attach_ro for the block, detached on every exit. A failing attach raises
    before anything is attached, so the detach only runs after a success. An
    exception inside the block rolls back first: SQLite refuses to DETACH
    inside an open transaction, and the error would mask the real one."""
    attach_ro(conn, db_path, alias)
    try:
        yield
    except BaseException:
        conn.rollback()
        raise
    finally:
        detach(conn, alias)
