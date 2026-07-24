from sources.screeners.portfolio_screener import db

NOW = "2026-07-05T20:00:00+00:00"
OLD = "2026-06-01T20:00:00+00:00"

ACCOUNT = {"equity": 205.37, "cash": 12.4, "buying_power": 12.4}
POSITIONS = [
    {"symbol": "GLD", "quantity": 0.5, "avg_cost": 301.2, "market_value": 155.0},
    {"symbol": "SPY", "quantity": 0.1, "avg_cost": 500.0, "market_value": 51.0},
]


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_schema_idempotent_and_names():
    conn = _fresh()
    db.ensure_schema(conn)  # second call must not raise
    names = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")
    }
    assert {"snapshots", "account", "positions", "v_latest_account", "v_latest_positions"} <= names


def test_write_snapshot_roundtrip():
    conn = _fresh()
    sid = db.write_snapshot(conn, NOW, ACCOUNT, POSITIONS)
    assert (
        conn.execute("SELECT position_count FROM snapshots WHERE id=?", (sid,)).fetchone()[0] == 2
    )
    acct = conn.execute(
        "SELECT equity, cash, buying_power FROM account WHERE snapshot_id=?", (sid,)
    ).fetchone()
    assert acct == (205.37, 12.4, 12.4)
    rows = conn.execute(
        "SELECT symbol, quantity FROM positions WHERE snapshot_id=? ORDER BY symbol", (sid,)
    ).fetchall()
    assert rows == [("GLD", 0.5), ("SPY", 0.1)]


def test_latest_views_scope_to_newest_snapshot():
    conn = _fresh()
    db.write_snapshot(
        conn,
        OLD,
        {"equity": 100.0, "cash": 1.0, "buying_power": 1.0},
        [{"symbol": "OLD", "quantity": 1.0, "avg_cost": None, "market_value": None}],
    )
    db.write_snapshot(conn, NOW, ACCOUNT, POSITIONS)
    assert conn.execute("SELECT equity FROM v_latest_account").fetchone()[0] == 205.37
    syms = {r[0] for r in conn.execute("SELECT symbol FROM v_latest_positions")}
    assert syms == {"GLD", "SPY"}


def test_prune_cascades_both_children():
    conn = _fresh()
    db.write_snapshot(conn, OLD, ACCOUNT, POSITIONS)
    keep = db.write_snapshot(conn, NOW, ACCOUNT, POSITIONS)
    removed = db.prune(conn, keep_days=7, now_iso=NOW)
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert {r[0] for r in conn.execute("SELECT snapshot_id FROM account")} == {keep}
    assert {r[0] for r in conn.execute("SELECT snapshot_id FROM positions")} == {keep}


OPTIONS = [
    {
        "occ_symbol": "XLE260821C00095000",
        "underlying": "XLE",
        "type": "call",
        "strike": 95.0,
        "expiration": "2026-08-21",
        "quantity": 1.0,
        "avg_cost": 2.50,
        "market_value": 310.0,
        "multiplier": 100.0,
    },
    {  # second contract, SAME underlying — the (snapshot_id, symbol) PK on
        # positions could never hold this pair; the option table must
        "occ_symbol": "XLE260918P00090000",
        "underlying": "XLE",
        "type": "put",
        "strike": 90.0,
        "expiration": "2026-09-18",
        "quantity": -2.0,
        "avg_cost": None,
        "market_value": None,
        "multiplier": None,
    },
]


def test_option_positions_roundtrip_two_contracts_one_underlying():
    conn = _fresh()
    sid = db.write_snapshot(conn, NOW, ACCOUNT, POSITIONS, option_positions=OPTIONS)
    assert conn.execute("SELECT option_count FROM snapshots WHERE id=?", (sid,)).fetchone()[0] == 2
    rows = conn.execute(
        "SELECT occ_symbol, underlying, quantity FROM option_positions"
        " WHERE snapshot_id=? ORDER BY occ_symbol",
        (sid,),
    ).fetchall()
    assert rows == [
        ("XLE260821C00095000", "XLE", 1.0),
        ("XLE260918P00090000", "XLE", -2.0),
    ]


def test_latest_option_positions_scope_to_newest_snapshot():
    conn = _fresh()
    db.write_snapshot(conn, OLD, ACCOUNT, [], option_positions=OPTIONS)
    db.write_snapshot(conn, NOW, ACCOUNT, [], option_positions=OPTIONS[:1])
    rows = conn.execute("SELECT occ_symbol FROM v_latest_option_positions").fetchall()
    assert rows == [("XLE260821C00095000",)]


def test_prune_cascades_option_positions():
    conn = _fresh()
    db.write_snapshot(conn, OLD, ACCOUNT, POSITIONS, option_positions=OPTIONS)
    keep = db.write_snapshot(conn, NOW, ACCOUNT, POSITIONS, option_positions=OPTIONS)
    assert db.prune(conn, keep_days=7, now_iso=NOW) == 1
    assert {r[0] for r in conn.execute("SELECT snapshot_id FROM option_positions")} == {keep}


def test_option_count_migration():
    """A portfolio.db created before option capture (no option_count column,
    no option_positions table) gains both via ensure_schema."""
    conn = db.connect(":memory:")
    conn.execute(
        """CREATE TABLE snapshots (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            captured_at    TEXT NOT NULL,
            position_count INTEGER NOT NULL
        )"""
    )
    conn.execute("INSERT INTO snapshots (captured_at, position_count) VALUES (?, 1)", (OLD,))
    db.ensure_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(snapshots)")}
    assert "option_count" in cols
    assert conn.execute("SELECT option_count FROM snapshots").fetchone()[0] == 0
    db.ensure_schema(conn)  # idempotent
