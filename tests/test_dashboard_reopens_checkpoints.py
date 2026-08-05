"""Position checkpoints: held-ticker dated reopen triggers within +/- 7
Phoenix days, computed by `dashboard_lib.data._research_reopens`'s
`checkpoints` list and rendered on the dashboard's research-reopens
section."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import data  # noqa: E402

# 9:13pm Phoenix on 2026-07-22 == 04:13 UTC on the 23rd -- deliberately
# straddles the UTC rollover so a UTC-side date derivation (today would come
# out as 2026-07-23) is caught by test_phoenix_date_not_utc_date below.
NOW = "2026-07-23T04:13:00+00:00"
TODAY = "2026-07-22"  # phx_date(NOW)
# Window bounds for the fixture above: floor 2026-07-15, ceiling 2026-07-29.

HEADER = "# Format: ... [reopen=<YYYY-MM-DD|event>:<slug>]\n"


def _write_vlog(research_dir: Path, *lines: str) -> None:
    research_dir.mkdir(exist_ok=True)
    (research_dir / "verdicts.log").write_text(
        HEADER + "".join(f"{ln}\n" for ln in lines), encoding="utf-8"
    )


def _write_pdb(data_dir: Path, *symbols: str) -> None:
    """Fake portfolio.db: the real schema's `v_latest_positions` shape, with
    `quantity` kept TEXT (per the brief) to mirror the real column type that
    the query's CAST(quantity AS REAL) works around."""
    data_dir.mkdir(exist_ok=True)
    conn = sqlite3.connect(data_dir / "portfolio.db")
    conn.executescript(
        "CREATE TABLE positions (symbol TEXT, quantity TEXT);"
        "CREATE VIEW v_latest_positions AS SELECT symbol, quantity FROM positions;"
    )
    for s in symbols:
        conn.execute("INSERT INTO positions VALUES (?, '1')", (s,))
    conn.commit()
    conn.close()


def test_held_ticker_dated_reopen_today_is_checkpoint(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 AAA UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-07-22:q2-print",
    )
    _write_pdb(tmp_path / "data", "AAA")
    sec = data._research_reopens(str(tmp_path / "data"), NOW)
    assert sec["checkpoints"] == [
        {
            "ticker": "AAA",
            "reopen_date": "2026-07-22",
            "trigger": "q2-print",
            "thesis_date": "2026-07-01",
            "when_days": 0,
            "thesis_path": "research/AAA-2026-07-01.md",
        }
    ]


def test_held_ticker_past_and_future_checkpoints_have_signed_when_days(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 BBB UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-07-20:past-print",
        "2026-07-01 CCC UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-07-25:future-print",
    )
    _write_pdb(tmp_path / "data", "BBB", "CCC")
    checkpoints = data._research_reopens(str(tmp_path / "data"), NOW)["checkpoints"]
    by_ticker = {c["ticker"]: c for c in checkpoints}
    assert by_ticker["BBB"]["when_days"] == -2  # 2 days ago
    assert by_ticker["CCC"]["when_days"] == 3  # 3 days ahead


def test_phoenix_date_not_utc_date(tmp_path):
    """NOW's UTC calendar date is 2026-07-23 but its Phoenix date is
    2026-07-22 (9:13pm the prior evening). A reopen dated 2026-07-23 is
    *tomorrow* on the correct Phoenix clock (when_days == 1) -- a UTC-side
    `today` would instead compute 0. This is the regression the brief calls
    out explicitly."""
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 III UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-07-23:rollover",
    )
    _write_pdb(tmp_path / "data", "III")
    checkpoints = data._research_reopens(str(tmp_path / "data"), NOW)["checkpoints"]
    assert len(checkpoints) == 1
    assert checkpoints[0]["when_days"] == 1


def test_unheld_ticker_in_rows_not_checkpoints(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 DDD UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-07-22:q2-print",
    )
    _write_pdb(tmp_path / "data")  # nothing held
    sec = data._research_reopens(str(tmp_path / "data"), NOW)
    assert sec["checkpoints"] == []
    row = next(r for r in sec["rows"] if r["ticker"] == "DDD")
    assert row["held"] is False
    assert row["due"] == "2026-07-22"


def test_held_ticker_outside_window_not_checkpoint(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 EEE UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-08-15:q3-print",
    )
    _write_pdb(tmp_path / "data", "EEE")
    sec = data._research_reopens(str(tmp_path / "data"), NOW)
    assert sec["checkpoints"] == []
    row = next(r for r in sec["rows"] if r["ticker"] == "EEE")
    assert row["held"] is True
    assert row["due"] == "2026-08-15"


def test_only_newest_verdict_line_counts(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 FFF UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-07-25:old-trigger",
        "2026-07-15 FFF UNPROVEN conditions=5 refuted=0 unknown=1 reopen=2026-07-27:new-trigger",
    )
    _write_pdb(tmp_path / "data", "FFF")
    checkpoints = data._research_reopens(str(tmp_path / "data"), NOW)["checkpoints"]
    assert len(checkpoints) == 1
    assert checkpoints[0]["trigger"] == "new-trigger"
    assert checkpoints[0]["thesis_date"] == "2026-07-15"


def test_missing_portfolio_db_degrades_to_no_checkpoints(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 GGG UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-07-22:q2-print",
    )
    (tmp_path / "data").mkdir()  # no portfolio.db written at all
    sec = data._research_reopens(str(tmp_path / "data"), NOW)
    assert sec["checkpoints"] == []
    assert all(r["held"] is False for r in sec["rows"])


def test_event_reopen_never_becomes_checkpoint(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 HHH UNPROVEN conditions=6 refuted=0 unknown=2 reopen=event:some-trigger",
    )
    _write_pdb(tmp_path / "data", "HHH")
    sec = data._research_reopens(str(tmp_path / "data"), NOW)
    assert sec["checkpoints"] == []
    row = next(r for r in sec["rows"] if r["ticker"] == "HHH")
    assert row["held"] is True
    assert row["due"] is None


def test_malformed_date_on_held_ticker_drops_only_that_checkpoint(tmp_path):
    """`_REOPEN_FIELD_RE` validates digit shape only, never calendar
    validity -- verdicts.log is human-written, so a typo like 2026-02-30
    (2026 is not a leap year: Feb tops out at 28) is a live possibility.
    Before this branch `_research_reopens` only string-compared these
    values, so a bad date was inert; now it is `date.fromisoformat`-parsed
    for `when_days` and must not take the whole section down with it --
    only the one bad checkpoint drops, every row and every other checkpoint
    survives."""
    now = "2026-02-24T21:13:00+00:00"  # Phoenix 2026-02-24; window 02-17..03-03
    _write_vlog(
        tmp_path / "research",
        "2026-01-01 JJJ UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-02-30:bad-date",
        "2026-01-01 KKK UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-02-25:good-date",
    )
    _write_pdb(tmp_path / "data", "JJJ", "KKK")
    sec = data._research_reopens(str(tmp_path / "data"), now)
    assert {r["ticker"] for r in sec["rows"]} == {"JJJ", "KKK"}  # rows all survive
    assert {c["ticker"] for c in sec["checkpoints"]} == {"KKK"}  # JJJ's bad date dropped


def test_checkpoint_window_boundary_inclusive_both_ends(tmp_path):
    """The floor/ceiling comparison is inclusive on ISO strings -- a reopen
    dated exactly on `floor` (2026-07-15) and one exactly on `ceiling`
    (2026-07-29, per NOW's +/- 7 day window) must both become checkpoints.
    No existing test pinned this boundary."""
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 LLL UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-07-15:on-floor",
        "2026-07-01 MMM UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-07-29:on-ceiling",
    )
    _write_pdb(tmp_path / "data", "LLL", "MMM")
    checkpoints = data._research_reopens(str(tmp_path / "data"), NOW)["checkpoints"]
    by_ticker = {c["ticker"]: c for c in checkpoints}
    assert set(by_ticker) == {"LLL", "MMM"}
    assert by_ticker["LLL"]["when_days"] == -7
    assert by_ticker["MMM"]["when_days"] == 7
