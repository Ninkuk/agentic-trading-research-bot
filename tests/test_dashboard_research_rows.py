"""Research section rows from `dashboard_lib.data._research`: the held
flag from portfolio.db, the dated-vs-event reopen split, the newest-line
rule, and the +/- 7 Phoenix-day "due this week" badge."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import data  # noqa: E402

# 9:13pm Phoenix on 2026-07-22 == 04:13 UTC on the 23rd -- deliberately
# straddles the UTC rollover so a UTC-side date derivation would misread
# today as 2026-07-23.
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


def test_phoenix_date_not_utc_date(tmp_path):
    """NOW's UTC calendar date is 2026-07-23 but its Phoenix date is
    2026-07-22 (9:13pm the prior evening), so the due-this-week window
    floors at 2026-07-15. A reopen on that floor is due this week on the
    Phoenix clock; a UTC-side `today` would floor at the 16th and miss it."""
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 III UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-07-15:rollover",
    )
    _write_pdb(tmp_path / "data", "III")
    sec = data._research(str(tmp_path / "data"), NOW)
    assert sec["verdict"]["text"] == "1 due this week"


def test_unheld_ticker_rows_held_false(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 DDD UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-07-22:q2-print",
    )
    _write_pdb(tmp_path / "data")  # nothing held
    sec = data._research(str(tmp_path / "data"), NOW)
    row = next(r for r in sec["rows"] if r["ticker"] == "DDD")
    assert row["held"] is False
    assert row["due"] == "2026-07-22"


def test_held_ticker_outside_window_not_due_this_week(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 EEE UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-08-15:q3-print",
    )
    _write_pdb(tmp_path / "data", "EEE")
    sec = data._research(str(tmp_path / "data"), NOW)
    assert sec["verdict"]["text"] == "nothing due this week"
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
    rows = data._research(str(tmp_path / "data"), NOW)["rows"]
    assert len(rows) == 1
    assert rows[0]["trigger"] == "new-trigger"
    assert rows[0]["thesis_date"] == "2026-07-15"


def test_missing_portfolio_db_degrades_to_nothing_held(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 GGG UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-07-22:q2-print",
    )
    (tmp_path / "data").mkdir()  # no portfolio.db written at all
    sec = data._research(str(tmp_path / "data"), NOW)
    assert all(r["held"] is False for r in sec["rows"])


def test_event_reopen_is_undated(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 HHH UNPROVEN conditions=6 refuted=0 unknown=2 reopen=event:some-trigger",
    )
    _write_pdb(tmp_path / "data", "HHH")
    sec = data._research(str(tmp_path / "data"), NOW)
    assert sec["verdict"]["text"] == "nothing due this week"
    row = next(r for r in sec["rows"] if r["ticker"] == "HHH")
    assert row["held"] is True
    assert row["due"] is None


def test_due_this_week_window_inclusive_both_ends(tmp_path):
    """The floor/ceiling comparison is inclusive on ISO strings -- a reopen
    dated exactly on `floor` (2026-07-15) and one exactly on `ceiling`
    (2026-07-29, per NOW's +/- 7 day window) both count as due this week."""
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 LLL UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-07-15:on-floor",
        "2026-07-01 MMM UNPROVEN conditions=6 refuted=0 unknown=2 reopen=2026-07-29:on-ceiling",
    )
    _write_pdb(tmp_path / "data", "LLL", "MMM")
    sec = data._research(str(tmp_path / "data"), NOW)
    assert sec["verdict"]["text"] == "2 due this week"


def _write_edgar(data_dir: Path, *filings: tuple[str, str, str, str]) -> None:
    """Fake edgar.db `filings` rows as (ticker, bucket, filed_date, accession)."""
    data_dir.mkdir(exist_ok=True)
    conn = sqlite3.connect(data_dir / "edgar.db")
    conn.execute(
        "CREATE TABLE filings (snapshot_id INTEGER, ticker TEXT, bucket TEXT,"
        " filed_date TEXT, accession TEXT)"
    )
    for i, (ticker, bucket, filed, acc) in enumerate(filings):
        conn.execute("INSERT INTO filings VALUES (?, ?, ?, ?, ?)", (i, ticker, bucket, filed, acc))
    conn.commit()
    conn.close()


def test_filings_since_counts_distinct_8ks_after_thesis_date(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 CAH UNPROVEN conditions=5 refuted=0 unknown=1 reopen=event:cvs-renewal",
        "2026-07-01 DDD SOUND conditions=5 refuted=0 unknown=0 reopen=2026-09-01:q3-print",
    )
    _write_edgar(
        tmp_path / "data",
        ("CAH", "event", "2026-07-02", "acc-1"),
        ("CAH", "event", "2026-07-02", "acc-1"),  # same accession, later snapshot
        ("CAH", "event", "2026-07-10", "acc-2"),
        ("CAH", "event", "2026-06-30", "acc-0"),  # before the thesis
        ("CAH", "insider", "2026-07-11", "acc-3"),  # Form 4, not an 8-K
        ("DDD", "event", "2026-07-05", "acc-4"),
    )
    rows = {r["ticker"]: r for r in data._research(str(tmp_path / "data"), NOW)["rows"]}
    assert rows["CAH"]["filings_since"] == 2
    assert rows["DDD"]["filings_since"] == 1  # dated rows carry it too


def test_filings_since_is_none_without_edgar_db(tmp_path):
    _write_vlog(
        tmp_path / "research",
        "2026-07-01 CAH UNPROVEN conditions=5 refuted=0 unknown=1 reopen=event:cvs-renewal",
    )
    (tmp_path / "data").mkdir()
    rows = data._research(str(tmp_path / "data"), NOW)["rows"]
    assert rows[0]["filings_since"] is None
