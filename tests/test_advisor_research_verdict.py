"""Size caps must disclose that research already rejected the name.

The nightly push ends with `cap: BBAI <= 9.99sh · CRML <= 2.98sh · EOSE <=
3.90sh` — all three composite flags, and all three carry research documents
concluding PASS. advisor reads scorer.db already (for signal reliability) but
never read research_verdicts, so the last line of the digest sized names the
research layer had explicitly killed. A cap reads much closer to an
instruction than a scorecard tally does.

The cap is NOT suppressed. A pass is the research skill's opinion, not a
prohibition, and the human may disagree — hiding the row would remove
information. The row is annotated so the conflict is visible.
"""

import sqlite3

from sources.combiners.advisor import db, fetch


def _scorer_db(tmp_path, rows):
    """A scorer.db carrying research_verdicts, attached as `src` the way
    advisor's readers see it."""
    path = tmp_path / "scorer.db"
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE research_verdicts (id INTEGER PRIMARY KEY, symbol TEXT,"
        " verdict TEXT, verdict_date TEXT, doc TEXT, note TEXT, recorded_at TEXT)"
    )
    for i, (sym, verdict, vdate) in enumerate(rows, 1):
        conn.execute(
            "INSERT INTO research_verdicts VALUES (?, ?, ?, ?, NULL, NULL, ?)",
            (i, sym, verdict, vdate, vdate),
        )
    conn.commit()
    conn.close()
    reader = sqlite3.connect(":memory:", uri=True)
    fetch.attach_ro(reader, str(path))
    return reader


def test_reads_the_verdict_per_symbol(tmp_path):
    conn = _scorer_db(tmp_path, [("BBAI", "pass", "2026-07-21"), ("PEGA", "buy", "2026-07-26")])
    assert fetch.read_research_verdicts(conn) == {"BBAI": "pass", "PEGA": "buy"}


def test_the_most_recent_verdict_wins(tmp_path):
    """A ticker can be researched more than once — BBAI was, on 07-21 and
    07-22. The current opinion is the latest one."""
    conn = _scorer_db(tmp_path, [("BBAI", "buy", "2026-07-21"), ("BBAI", "pass", "2026-07-22")])
    assert fetch.read_research_verdicts(conn) == {"BBAI": "pass"}


def test_missing_table_degrades_to_empty(tmp_path):
    """advisor must still size when scorer.db predates the verdicts table."""
    path = tmp_path / "scorer.db"
    sqlite3.connect(str(path)).close()
    conn = sqlite3.connect(":memory:", uri=True)
    fetch.attach_ro(conn, str(path))
    assert fetch.read_research_verdicts(conn) == {}


def _cap_row(symbol, **kw):
    row = dict(
        symbol=symbol,
        direction="bullish",
        score_sum=3,
        atr=0.5,
        price=3.0,
        cap_shares=9.99,
        cap_dollars=30.0,
        group_name=None,
        group_heat_pct=None,
        reliable_signals=2,
        total_signals=2,
        exceeds_buying_power=0,
        already_held=0,
        research_verdict=None,
    )
    row.update(kw)
    return row


def test_cap_row_stores_the_verdict(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    conn.execute(
        "INSERT INTO snapshots (id, captured_at, equity, cash, buying_power,"
        " portfolio_captured_at, composite_captured_at, regime, sources_failed)"
        " VALUES (1, '2026-07-27T04:12:00+00:00', 200.0, 200.0, 200.0,"
        " '2026-07-27T04:00:00+00:00', '2026-07-27T04:05:00+00:00', 'risk_on', 0)"
    )
    db.write_size_caps(
        conn,
        1,
        [_cap_row("BBAI", research_verdict="pass"), _cap_row("XYZ")],
    )
    got = dict(conn.execute("SELECT symbol, research_verdict FROM v_latest_caps"))
    assert got == {"BBAI": "pass", "XYZ": None}


def test_a_rejected_name_is_annotated_not_suppressed(tmp_path):
    """The cap survives — the human may disagree with the research call. What
    must not happen is the conflict being invisible."""
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    conn.execute(
        "INSERT INTO snapshots (id, captured_at, equity, cash, buying_power,"
        " portfolio_captured_at, composite_captured_at, regime, sources_failed)"
        " VALUES (1, '2026-07-27T04:12:00+00:00', 200.0, 200.0, 200.0,"
        " '2026-07-27T04:00:00+00:00', '2026-07-27T04:05:00+00:00', 'risk_on', 0)"
    )
    db.write_size_caps(conn, 1, [_cap_row("BBAI", research_verdict="pass")])
    row = conn.execute("SELECT symbol, cap_shares, research_verdict FROM v_latest_caps").fetchone()
    assert row == ("BBAI", 9.99, "pass"), "the cap is kept, and labelled"


def test_a_caller_that_omits_the_key_still_writes(tmp_path):
    """research_verdict is a late annotation. A caller predating it — or a
    scorer.db with no verdicts yet — must not be unable to write a cap."""
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    conn.execute(
        "INSERT INTO snapshots (id, captured_at, equity, cash, buying_power,"
        " portfolio_captured_at, composite_captured_at, regime, sources_failed)"
        " VALUES (1, '2026-07-27T04:12:00+00:00', 200.0, 200.0, 200.0,"
        " '2026-07-27T04:00:00+00:00', '2026-07-27T04:05:00+00:00', 'risk_on', 0)"
    )
    row = _cap_row("OLD")
    del row["research_verdict"]
    db.write_size_caps(conn, 1, [row])
    assert conn.execute("SELECT research_verdict FROM v_latest_caps").fetchone() == (None,)
