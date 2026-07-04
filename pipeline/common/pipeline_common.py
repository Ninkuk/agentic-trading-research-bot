import sqlite3


def connect_ro(path: str) -> sqlite3.Connection:
    """Open an existing SQLite database read-only (URI mode) — the hard
    guarantee that pipeline stages cannot write to source DBs. Raises
    sqlite3.OperationalError if the file does not exist or on any write."""
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def normalize_ticker(t: str) -> str:
    """Normalize a ticker for cross-source joins: strip, uppercase, and map
    the class-share dot to a dash (stockanalysis 'BRK.B' == SEC 'BRK-B')."""
    return t.strip().upper().replace(".", "-")
