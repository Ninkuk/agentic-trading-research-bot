"""Position-checkpoints digest block: held-name reopen dates, 7-day lookahead."""

import datetime as dt
import sqlite3
import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import daily_summary  # noqa: E402

# 9:15pm Phoenix on 2026-07-29 == 04:15 UTC on the 30th (rollover fixture).
NOW_UTC = dt.datetime.fromisoformat("2026-07-30T04:15:00+00:00")
TODAY = "2026-07-29"  # phx_date(NOW_UTC)


def test_format_upcoming_today_and_past():
    got = daily_summary.format_checkpoint_lines(
        [
            ("BR", "2026-08-02", "fy27-guide", "2026-07-30"),
            ("DECK", "2026-07-29", "print-checkpoint", "2026-07-27"),
            ("SAP", "2026-07-26", "q2-print", "2026-07-25"),
        ],
        TODAY,
    )
    assert got == [
        "SAP 2026-07-26 q2-print (3d ago, thesis 2026-07-25)",
        "DECK 2026-07-29 print-checkpoint (today, thesis 2026-07-27)",
        "BR 2026-08-02 fy27-guide (in 4d, thesis 2026-07-30)",
    ]


def test_format_sorts_ties_by_ticker():
    got = daily_summary.format_checkpoint_lines(
        [
            ("MORN", "2026-08-02", "b-slug", "2026-07-30"),
            ("INTU", "2026-08-02", "a-slug", "2026-07-30"),
        ],
        TODAY,
    )
    assert [ln.split()[0] for ln in got] == ["INTU", "MORN"]


HEADER = "# Format: ... [reopen=<YYYY-MM-DD|event>:<slug>]\n"


def _write_vlog(tmp_path, *lines):
    (tmp_path / "verdicts.log").write_text(HEADER + "".join(f"{ln}\n" for ln in lines))
    return tmp_path


def _write_pdb(tmp_path, *snapshots):
    """Fixture portfolio.db. Each snapshot is a list of held symbols; the
    LAST one is the latest (later captured_at). Returns the db path."""
    db = tmp_path / "portfolio.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        "CREATE TABLE snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " captured_at TEXT NOT NULL, position_count INTEGER NOT NULL,"
        " option_count INTEGER NOT NULL DEFAULT 0);"
        "CREATE TABLE positions (snapshot_id INTEGER NOT NULL, symbol TEXT NOT NULL,"
        " quantity REAL NOT NULL, avg_cost REAL, market_value REAL,"
        " PRIMARY KEY (snapshot_id, symbol));"
        "CREATE VIEW v_latest_positions AS SELECT p.* FROM positions p"
        " WHERE p.snapshot_id = (SELECT id FROM snapshots"
        " ORDER BY captured_at DESC, id DESC LIMIT 1);"
    )
    for i, symbols in enumerate(snapshots):
        cur = conn.execute(
            "INSERT INTO snapshots (captured_at, position_count) VALUES (?, ?)",
            (f"2026-07-{28 + i:02d}T04:00:00+00:00", len(symbols)),
        )
        for s in symbols:
            conn.execute(
                "INSERT INTO positions VALUES (?, ?, 1.0, NULL, NULL)",
                (cur.lastrowid, s),
            )
    conn.commit()
    conn.close()
    return db


def test_upcoming_checkpoint_surfaces_with_lookahead(tmp_path):
    _write_vlog(
        tmp_path,
        "2026-07-30 BR UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-08-04:fy27-guide",
    )
    db = _write_pdb(tmp_path, ["BR"])
    got = daily_summary.position_checkpoints(NOW_UTC, research_dir=tmp_path, portfolio_db=db)
    assert got == ["BR 2026-08-04 fy27-guide (in 6d, thesis 2026-07-30)"]


def test_beyond_lookahead_absent(tmp_path):
    _write_vlog(
        tmp_path,
        "2026-07-30 INTU SOUND conditions=6 refuted=0 unknown=0 reopen=2026-08-20:fy27-guide",
    )
    db = _write_pdb(tmp_path, ["INTU"])
    assert daily_summary.position_checkpoints(NOW_UTC, research_dir=tmp_path, portfolio_db=db) == []


def test_past_due_within_window_nags(tmp_path):
    _write_vlog(
        tmp_path,
        "2026-07-20 SAP UNPROVEN conditions=5 refuted=0 unknown=2 reopen=2026-07-26:q2-print",
    )
    db = _write_pdb(tmp_path, ["SAP"])
    got = daily_summary.position_checkpoints(NOW_UTC, research_dir=tmp_path, portfolio_db=db)
    assert got == ["SAP 2026-07-26 q2-print (3d ago, thesis 2026-07-20)"]


def test_past_due_beyond_window_quiet(tmp_path):
    _write_vlog(
        tmp_path,
        "2026-07-01 OLD UNPROVEN conditions=1 refuted=0 unknown=1 reopen=2026-07-15:q2-print",
    )
    db = _write_pdb(tmp_path, ["OLD"])
    assert daily_summary.position_checkpoints(NOW_UTC, research_dir=tmp_path, portfolio_db=db) == []


def test_not_held_absent(tmp_path):
    _write_vlog(
        tmp_path,
        "2026-07-30 BSY UNPROVEN conditions=5 refuted=0 unknown=1 reopen=2026-08-01:q2-print",
    )
    db = _write_pdb(tmp_path, ["BR"])
    assert daily_summary.position_checkpoints(NOW_UTC, research_dir=tmp_path, portfolio_db=db) == []


def test_held_but_undated_or_event_absent(tmp_path):
    _write_vlog(
        tmp_path,
        "2026-07-30 FIX SOUND conditions=5 refuted=0 unknown=1 reopen=event:price-le-1100",
        "2026-07-30 ERO SOUND conditions=4 refuted=0 unknown=0",
    )
    db = _write_pdb(tmp_path, ["FIX", "ERO"])
    assert daily_summary.position_checkpoints(NOW_UTC, research_dir=tmp_path, portfolio_db=db) == []


def test_newer_verdict_retires_older_checkpoint(tmp_path):
    _write_vlog(
        tmp_path,
        "2026-07-20 BR UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-08-01:fy27-guide",
        "2026-07-29 BR SOUND conditions=6 refuted=0 unknown=0",
    )
    db = _write_pdb(tmp_path, ["BR"])
    assert daily_summary.position_checkpoints(NOW_UTC, research_dir=tmp_path, portfolio_db=db) == []


def test_sold_position_absent(tmp_path):
    # Held in an older snapshot only -> not in v_latest_positions -> absent.
    _write_vlog(
        tmp_path,
        "2026-07-30 BR UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-08-04:fy27-guide",
    )
    db = _write_pdb(tmp_path, ["BR"], [])
    assert daily_summary.position_checkpoints(NOW_UTC, research_dir=tmp_path, portfolio_db=db) == []


def test_missing_vlog_returns_empty(tmp_path):
    db = _write_pdb(tmp_path, ["BR"])
    assert daily_summary.position_checkpoints(NOW_UTC, research_dir=tmp_path, portfolio_db=db) == []


def test_missing_db_returns_empty(tmp_path, capsys):
    _write_vlog(
        tmp_path,
        "2026-07-30 BR UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-08-04:fy27-guide",
    )
    got = daily_summary.position_checkpoints(
        NOW_UTC, research_dir=tmp_path, portfolio_db=tmp_path / "nope.db"
    )
    assert got == []
    err = capsys.readouterr().err
    assert "position checkpoints failed" in err
    assert "nope.db" not in err  # type name only, never the message/path


def test_corrupt_db_returns_empty(tmp_path):
    _write_vlog(
        tmp_path,
        "2026-07-30 BR UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-08-04:fy27-guide",
    )
    bad = tmp_path / "portfolio.db"
    bad.write_text("not a database")
    assert (
        daily_summary.position_checkpoints(NOW_UTC, research_dir=tmp_path, portfolio_db=bad) == []
    )


def test_build_summary_includes_section(tmp_path, monkeypatch):
    # Wiring only: stub the section fn; build_summary must render its lines
    # under the header without affecting health judgment.
    monkeypatch.chdir(tmp_path)  # no logs/, data/, research/ -> all sections degrade
    monkeypatch.setattr(daily_summary, "job_exit_codes", dict)
    monkeypatch.setattr(daily_summary, "running_jobs", dict)
    monkeypatch.setattr(
        daily_summary,
        "position_checkpoints",
        lambda now_utc: ["BR 2026-08-04 fy27-guide (in 6d, thesis 2026-07-30)"],
    )
    healthy, summary = daily_summary.build_summary(dt.datetime(2026, 7, 29, 21, 15), NOW_UTC)
    assert "— position checkpoints —" in summary
    assert "BR 2026-08-04 fy27-guide" in summary
    assert healthy  # informational only
