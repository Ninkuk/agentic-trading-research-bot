import pytest

from sources.combiners.backtest import db


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.ensure_schema(c)
    yield c
    c.close()


def test_insert_vintages_upserts_last_wins(conn):
    db.insert_vintages(conn, [("T10Y2Y", "2025-01-09", "2025-01-09", 0.5)])
    db.insert_vintages(conn, [("T10Y2Y", "2025-01-09", "2025-01-09", 0.6)])
    rows = conn.execute("SELECT value FROM signal_vintages").fetchall()
    assert rows == [(0.6,)]


def test_insert_benchmark_upserts(conn):
    db.insert_benchmark(conn, "SP500", [("2025-01-09", 6000.0)])
    db.insert_benchmark(conn, "SP500", [("2025-01-09", 6001.0)])
    rows = conn.execute("SELECT close FROM benchmark_closes").fetchall()
    assert rows == [(6001.0,)]


def test_snapshot_header_roundtrip(conn):
    sid = db.write_snapshot(conn, "2025-01-15T00:00:00+00:00")
    db.finish_snapshot(conn, sid, 10, 20, 1)
    row = conn.execute(
        "SELECT vintage_rows, benchmark_rows, sources_failed FROM snapshots WHERE id = ?",
        (sid,),
    ).fetchone()
    assert row == (10, 20, 1)


def test_prune_deletes_only_old_headers_never_data(conn):
    old = db.write_snapshot(conn, "2024-01-01T00:00:00+00:00")
    new = db.write_snapshot(conn, "2025-01-14T00:00:00+00:00")
    db.insert_vintages(conn, [("T10Y2Y", "2020-01-09", "2020-01-09", 0.5)])
    db.insert_benchmark(conn, "SP500", [("2020-01-09", 3000.0)])
    n = db.prune(conn, keep_days=30, now_iso="2025-01-15T00:00:00+00:00")
    assert n == 1
    ids = [r[0] for r in conn.execute("SELECT id FROM snapshots")]
    assert ids == [new] and old not in ids
    assert conn.execute("SELECT COUNT(*) FROM signal_vintages").fetchone() == (1,)
    assert conn.execute("SELECT COUNT(*) FROM benchmark_closes").fetchone() == (1,)


# --- publication lag: obs_date is when the value became PUBLIC ---------------


def test_insert_market_obs_shifts_obs_date_by_publication_lag(tmp_path):
    """EIA's crude report covers the week ending Friday but is not released
    until the following Wednesday. Stamped at the Friday, the replay would trade
    on a number nobody had for another 5 days."""
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    db.insert_market_obs(conn, "eia_crude_stocks", [("2026-07-03", 1.5, None)], 6)
    got = conn.execute("SELECT obs_date, val1 FROM market_obs").fetchall()
    assert got == [("2026-07-09", 1.5)], "period Friday must be stamped at its release"


def test_insert_market_obs_zero_lag_keeps_the_date_verbatim(tmp_path):
    """Same-session feeds (exchange closes) must not be reformatted at all."""
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    db.insert_market_obs(conn, "cboe_vix", [("2026-07-03", 18.0, None)], 0)
    assert conn.execute("SELECT obs_date FROM market_obs").fetchone() == ("2026-07-03",)


def test_market_obs_value_is_invisible_before_its_release_date(tmp_path):
    """The property that actually matters: a point-in-time read on the period
    date must NOT see the value. This is the look-ahead the lag closes."""
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    db.insert_market_obs(conn, "eia_crude_stocks", [("2026-07-03", 1.5, None)], 6)

    def visible_on(asof):
        return conn.execute(
            "SELECT val1 FROM market_obs WHERE signal_id='eia_crude_stocks'"
            " AND obs_date <= ? ORDER BY obs_date DESC LIMIT 1",
            (asof,),
        ).fetchone()

    assert visible_on("2026-07-03") is None, "visible on its own period date = look-ahead"
    assert visible_on("2026-07-08") is None, "still unpublished"
    assert visible_on("2026-07-09") == (1.5,), "visible from the release date on"


def test_insert_market_obs_clears_stale_rows_for_that_signal(tmp_path):
    """market_obs PK is (signal_id, obs_date). Shifting a date mints a NEW key,
    so an un-shifted row written by an earlier build would survive INSERT OR
    REPLACE and keep serving the look-ahead value."""
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    db.insert_market_obs(conn, "eia_crude_stocks", [("2026-07-03", 1.5, None)], 0)  # old build
    db.insert_market_obs(conn, "eia_crude_stocks", [("2026-07-03", 1.5, None)], 6)  # new build
    dates = [r[0] for r in conn.execute("SELECT obs_date FROM market_obs ORDER BY obs_date")]
    assert dates == ["2026-07-09"], f"stale un-shifted row survived: {dates}"


def test_insert_market_obs_delete_is_scoped_to_one_signal(tmp_path):
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    db.insert_market_obs(conn, "cboe_vix", [("2026-07-03", 18.0, None)], 0)
    db.insert_market_obs(conn, "eia_crude_stocks", [("2026-07-03", 1.5, None)], 6)
    sigs = {r[0] for r in conn.execute("SELECT DISTINCT signal_id FROM market_obs")}
    assert sigs == {"cboe_vix", "eia_crude_stocks"}


def test_every_market_obs_signal_declares_a_publication_lag():
    """A new signal that forgets the key silently defaults to 0 — i.e. claims
    same-session publication. Force the decision to be explicit."""
    from sources.combiners.backtest import catalog as bt

    for s in bt.MARKET_OBS_SIGNALS:
        assert "publication_lag_days" in s, s["signal_id"]
        assert isinstance(s["publication_lag_days"], int)
        assert s["publication_lag_days"] >= 0
