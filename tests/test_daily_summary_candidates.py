"""Candidates digest block: pure formatter + a total reader.

The screen is the only artifact in the nightly push that surfaces investable
names, so it must (a) never crash the health alert, (b) never read as a flag,
and (c) always disclose how old its data is — stocks.db does not run at
weekends, so a Sunday digest is quoting Friday's RSI.
"""

import sqlite3
import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import daily_summary  # noqa: E402

# 9:15pm Phoenix on 2026-07-26 == 04:15 UTC on the 27th (rollover fixture).
NOW_UTC = "2026-07-27T04:15:00+00:00"

_ROW = dict(
    symbol="ADBE",
    sector="Technology",
    marketCap=84.3e9,
    dollarVolume=500e6,
    roic=60.7,
    roic5y=45.3,
    fcfYield=12.2,
    revenueGrowth3Y=11.0,
    netDebtEbitda=0.15,
    sharesYoY=-5.8,
    fScore=7.0,
    rsi=42.3,
    ch6m=-29.2,
    priceDate="2026-07-24",
)


def _stocks_db(tmp_path, rows, captured_at="2026-07-25T11:00:00+00:00"):
    """A stocks.db shaped like the real one: a snapshots header plus a
    v_latest the screen can read."""
    path = tmp_path / "stocks.db"
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE snapshots (id INTEGER PRIMARY KEY, captured_at TEXT,"
        " universe_count INTEGER, source TEXT)"
    )
    conn.execute("INSERT INTO snapshots VALUES (1, ?, 0, 'test')", (captured_at,))
    cols = ", ".join(f"{k} {'TEXT' if isinstance(v, str) else 'REAL'}" for k, v in _ROW.items())
    conn.execute(f"CREATE TABLE v_latest ({cols}, isin TEXT, isPrimaryListing TEXT)")
    for r in rows:
        m = {**_ROW, **r, "isin": r.get("isin", "US" + r.get("symbol", "X").ljust(10, "0"))}
        m.setdefault("isPrimaryListing", "1")
        names = ", ".join(m)
        marks = ", ".join("?" * len(m))
        conn.execute(f"INSERT INTO v_latest ({names}) VALUES ({marks})", tuple(m.values()))
    conn.commit()
    conn.close()
    return path


def test_format_lines_leads_with_the_count_and_names():
    lines = daily_summary.format_candidates_lines(
        [_ROW, {**_ROW, "symbol": "PEGA", "fcfYield": 11.5}], "2026-07-24", 2
    )
    body = "\n".join(lines)
    assert "2 name" in body
    assert "ADBE" in body and "PEGA" in body


def test_format_lines_carry_the_not_a_recommendation_label():
    """A screen appearing next to `N flagged` in the same push must not read
    as a flag. Nothing downstream grades it."""
    body = "\n".join(daily_summary.format_candidates_lines([_ROW], "2026-07-24", 5)).lower()
    assert "ungraded" in body
    assert "not a recommendation" in body


def test_format_lines_state_the_data_date():
    body = "\n".join(daily_summary.format_candidates_lines([_ROW], "2026-07-24", 5))
    assert "2026-07-24" in body


def test_format_lines_cap_the_listing():
    rows = [{**_ROW, "symbol": f"T{i}", "fcfYield": 20.0 - i} for i in range(12)]
    lines = daily_summary.format_candidates_lines(rows, "2026-07-24", 5)
    named = [ln for ln in lines if any(f"T{i}" in ln for i in range(12))]
    assert len(named) == 5, "the ntfy is a push notification, not a report"
    assert "12 name" in lines[0], "the full count is still disclosed"


def test_format_lines_on_empty_screen_say_so():
    lines = daily_summary.format_candidates_lines([], "2026-07-24", 5)
    assert lines and "0 name" in lines[0]


def test_digest_reads_a_real_db_end_to_end(tmp_path):
    db = _stocks_db(tmp_path, [{}, {"symbol": "PEGA", "isin": "US2000000002"}])
    body = "\n".join(daily_summary.candidates_digest(NOW_UTC, db_path=db))
    assert "ADBE" in body and "PEGA" in body
    assert "2 name" in body


def test_digest_reports_stale_data_age(tmp_path):
    """stocks.db does not run at weekends. A Sunday-night digest quoting
    Friday's RSI must say so rather than implying it is tonight's."""
    db = _stocks_db(tmp_path, [{}], captured_at="2026-07-24T11:00:00+00:00")
    body = "\n".join(daily_summary.candidates_digest(NOW_UTC, db_path=db))
    # 9:15pm Phoenix on the 26th; the snapshot is the 24th in Phoenix terms.
    assert "2026-07-24" in body
    assert "2d old" in body or "2 days old" in body


def test_digest_is_total_on_a_missing_db(tmp_path):
    """The health alert must survive anything this section does."""
    got = daily_summary.candidates_digest(NOW_UTC, db_path=tmp_path / "absent.db")
    assert got == [] or all(isinstance(ln, str) for ln in got)
    assert not any("Traceback" in ln for ln in got)


def test_digest_leaks_only_the_exception_type_on_failure(tmp_path):
    """Secret hygiene: a path or message could carry more than the type name."""
    bad = tmp_path / "stocks.db"
    bad.write_text("this is not a database")
    got = daily_summary.candidates_digest(NOW_UTC, db_path=bad)
    body = "\n".join(got)
    assert "not a database" not in body
    assert str(bad) not in body
    if body:
        assert "Error" in body or "unreadable" in body.lower()


def test_digest_actually_calls_the_shared_screen(tmp_path, monkeypatch):
    """The digest must not fork the screen's gates — one definition of a
    candidate, in candidates.py, or the push and the CLI drift apart.

    Asserted by observing the CALL, not by grepping the source for "SELECT":
    that proxy is trivially bypassed by reading `candidates._SCREEN_SQL`
    directly, which is the exact anti-pattern it claimed to forbid."""
    from sources.combiners.composite import candidates

    seen = {}

    def fake_screen(conn):
        seen["called"] = True
        return []

    monkeypatch.setattr(candidates, "screen", fake_screen)
    daily_summary.candidates_digest(NOW_UTC, db_path=_stocks_db(tmp_path, [{}]))
    assert seen.get("called"), "digest must go through candidates.screen()"


def test_digest_flags_data_dated_ahead_of_the_clock(tmp_path):
    """A snapshot dated in the FUTURE means clock skew or a restored backup.
    Showing the bare date lets it read as fresh; the reader must see something
    is wrong."""
    db = _stocks_db(tmp_path, [{}], captured_at="2026-07-30T11:00:00+00:00")
    body = "\n".join(daily_summary.candidates_digest(NOW_UTC, db_path=db))
    assert "2026-07-30" in body
    assert "ahead" in body.lower()


def test_build_summary_renders_the_section(tmp_path, monkeypatch):
    monkeypatch.setattr(daily_summary, "candidates_digest", lambda *a, **k: ["36 names"])
    monkeypatch.setattr(daily_summary, "signals_digest", lambda *a, **k: [])
    monkeypatch.setattr(daily_summary, "advisor_digest", lambda *a, **k: [])
    monkeypatch.setattr(daily_summary, "research_digest", lambda *a, **k: [])
    monkeypatch.setattr(daily_summary, "job_exit_codes", lambda: {})
    monkeypatch.setattr(daily_summary, "running_jobs", lambda: [])
    monkeypatch.setattr(daily_summary, "hung_jobs", lambda *a: [])
    monkeypatch.setattr(daily_summary, "stale_dbs", lambda *a: [])
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    import datetime as dt

    _, text = daily_summary.build_summary(
        dt.datetime(2026, 7, 26, 21, 15), dt.datetime.fromisoformat(NOW_UTC)
    )
    assert "— candidates —" in text
    assert "36 names" in text


def test_digest_survives_a_row_the_formatter_cannot_render(tmp_path, monkeypatch):
    """The formatter is only safe today because every column it prints is
    gated non-NULL by the screen's WHERE clause — a coupling across two files.
    Relax one gate in candidates.py and a `:.1f` on None raises TypeError; if
    that escapes, the whole nightly HEALTH ALERT dies with it. The alert must
    outlive anything this informational section does."""
    from sources.combiners.composite import candidates

    db = _stocks_db(tmp_path, [{}])
    monkeypatch.setattr(
        candidates,
        "screen",
        lambda conn: [{"symbol": "X", "fcfYield": None, "roic": 1.0, "fScore": 1.0, "rsi": 1.0}],
    )
    got = daily_summary.candidates_digest(NOW_UTC, db_path=db)
    assert isinstance(got, list)
    assert all(isinstance(ln, str) for ln in got)
    assert any("candidates" in ln for ln in got), "a failure must still be reported"
