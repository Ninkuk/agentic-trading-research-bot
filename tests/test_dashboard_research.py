"""The dashboard's research section (`dashboard_lib.data._research`): every
researched name rows, the BUY/PASS call joins from scorer.db, and the
default order is due, upcoming, event, then closed names newest first."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import data  # noqa: E402

# 9:13pm Phoenix on 2026-07-22 == 04:13 UTC on the 23rd (straddles the UTC
# rollover so a UTC-side "today" would misread as 2026-07-23).
NOW = "2026-07-23T04:13:00+00:00"

HEADER = "# Format: ... [reopen=<YYYY-MM-DD|event>:<slug>]\n"


def _write_vlog(research_dir: Path, *lines: str) -> None:
    research_dir.mkdir(exist_ok=True)
    (research_dir / "verdicts.log").write_text(
        HEADER + "".join(f"{ln}\n" for ln in lines), encoding="utf-8"
    )


def _write_scorer(data_dir: Path, *verdicts: tuple[str, str, str]) -> None:
    """Fake scorer.db `research_verdicts` rows as (symbol, verdict,
    verdict_date). The live table stores lowercase 'buy'/'pass'; the
    exporter uppercases."""
    data_dir.mkdir(exist_ok=True)
    conn = sqlite3.connect(data_dir / "scorer.db")
    conn.execute(
        "CREATE TABLE research_verdicts (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " symbol TEXT, verdict TEXT, verdict_date TEXT)"
    )
    for sym, v, d in verdicts:
        conn.execute(
            "INSERT INTO research_verdicts (symbol, verdict, verdict_date) VALUES (?, ?, ?)",
            (sym, v, d),
        )
    conn.commit()
    conn.close()


def test_every_researched_name_rows_with_or_without_a_trigger(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 AAA UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-08-01:q2-print",
        "2026-07-02 BBB FLAWED conditions=4 refuted=1 unknown=0",
    )
    (tmp_path / "data").mkdir()
    rows = {r["ticker"]: r for r in data._research(str(tmp_path / "data"), NOW)["rows"]}
    assert set(rows) == {"AAA", "BBB"}
    assert rows["BBB"]["due"] is None
    assert rows["BBB"]["trigger"] is None
    assert rows["BBB"]["verdict"] == "FLAWED"
    assert rows["BBB"]["thesis_path"] == "research/BBB-2026-07-02.md"


def test_call_joins_newest_scorer_verdict_uppercased(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-10 AAA SOUND conditions=5 refuted=0 unknown=0",
        "2026-07-10 BBB FLAWED conditions=5 refuted=1 unknown=0",
    )
    _write_scorer(
        tmp_path / "data",
        ("AAA", "pass", "2026-06-01"),
        ("AAA", "buy", "2026-07-10"),  # newest wins
        ("BBB", "pass", "2026-07-10"),
    )
    rows = {r["ticker"]: r for r in data._research(str(tmp_path / "data"), NOW)["rows"]}
    assert rows["AAA"]["call"] == "BUY"
    assert rows["BBB"]["call"] == "PASS"


def test_call_is_none_without_scorer_db_or_row(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-10 AAA SOUND conditions=5 refuted=0 unknown=0",
        "2026-07-10 BBB SOUND conditions=5 refuted=0 unknown=0",
    )
    (tmp_path / "data").mkdir()
    rows = data._research(str(tmp_path / "data"), NOW)["rows"]
    assert all(r["call"] is None for r in rows)
    _write_scorer(tmp_path / "data", ("AAA", "buy", "2026-07-10"))
    rows = {r["ticker"]: r for r in data._research(str(tmp_path / "data"), NOW)["rows"]}
    assert rows["AAA"]["call"] == "BUY"
    assert rows["BBB"]["call"] is None


def test_default_order_due_upcoming_event_then_closed_newest_first(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 NEW SOUND conditions=5 refuted=0 unknown=0",  # closed, newer thesis
        "2026-06-01 OLD SOUND conditions=5 refuted=0 unknown=0",  # closed, older thesis
        "2026-07-01 EVT UNPROVEN conditions=5 refuted=0 unknown=1 reopen=event:deal-close",
        "2026-07-01 UPC UNPROVEN conditions=5 refuted=0 unknown=1 reopen=2026-08-15:q3-print",
        "2026-07-01 DU2 UNPROVEN conditions=5 refuted=0 unknown=1 reopen=2026-07-21:q2-print",
        "2026-07-01 DU1 UNPROVEN conditions=5 refuted=0 unknown=1 reopen=2026-07-15:q2-print",
    )
    (tmp_path / "data").mkdir()
    sec = data._research(str(tmp_path / "data"), NOW)
    assert [r["ticker"] for r in sec["rows"]] == ["DU1", "DU2", "UPC", "EVT", "NEW", "OLD"]
    assert sec["dated"] == 3
    assert sec["events"] == 1
