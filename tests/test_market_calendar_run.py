import sqlite3

from sources.monitors.market_calendar import run as runmod

NOW = "2026-06-01T00:00:00+00:00"


def test_run_writes_holidays_early_closes_and_opex(tmp_path):
    db_path = str(tmp_path / "m.db")
    sid, count = runmod.run(db_path, years=1, now_iso=NOW)
    conn = sqlite3.connect(db_path)
    types = {r[0] for r in conn.execute(
        "SELECT DISTINCT event_type FROM events")}
    assert {"market_holiday", "early_close", "bond_holiday",
            "bond_early_close", "opex", "quad_witching"} <= types
    # 12 monthly expirations for the one computed year, all future from June 1.
    n_opex = conn.execute(
        "SELECT COUNT(*) FROM events WHERE event_type IN ('opex','quad_witching')"
    ).fetchone()[0]
    assert n_opex >= 7            # Jun..Dec forward at least
    assert count > 0


def test_run_is_idempotent_no_duplicates(tmp_path):
    db_path = str(tmp_path / "m.db")
    runmod.run(db_path, years=1, now_iso=NOW)
    runmod.run(db_path, years=1, now_iso=NOW)
    conn = sqlite3.connect(db_path)
    # replace_forward_window keeps the future set stable across identical runs.
    dupes = conn.execute(
        "SELECT event_type, event_date, COUNT(*) c FROM events "
        "GROUP BY event_type, event_date HAVING c > 1").fetchall()
    assert dupes == []


def test_run_keep_days_prunes_snapshots_not_future_events(tmp_path):
    db_path = str(tmp_path / "m.db")
    runmod.run(db_path, years=1, now_iso="2026-01-01T00:00:00+00:00")   # old snap
    runmod.run(db_path, years=1, now_iso=NOW, keep_days=30)             # prunes
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] > 0


def test_run_refresh_merges_parsed_pages_over_seed(tmp_path):
    db_path = str(tmp_path / "m.db")
    pages = {"nyse": "<tr><th>Holiday</th><th>2026</th></tr>"
                     "<tr><th>Test Holiday</th><td>Monday, June 15</td></tr>",
             "sifma": None}
    runmod.run(db_path, years=1, now_iso=NOW, pages=pages)
    conn = sqlite3.connect(db_path)
    hit = conn.execute(
        "SELECT title FROM events WHERE event_date='2026-06-15' "
        "AND event_type='market_holiday'").fetchone()
    assert hit == ("Test Holiday",)
