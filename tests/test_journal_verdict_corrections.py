"""Withdrawing a research verdict recorded on a defective analysis.

research_verdicts is INSERT OR IGNORE on (symbol, verdict_date), so a verdict
logged in error could never be withdrawn: re-ingesting the same day was a
counted duplicate and the wrong call graded forever in v_research_filter.

Found 2026-07-26 on PEGA — logged `buy`, then the analysis was found to have
missed a $2.04B trade-secret retrial (46% of market cap, dated 2027-01-11,
disclosed in a 10-Q filed five days before the run). The correction must be
possible AND auditable: suppressing the original would flatter the research
skill's measured hit rate, which is the one thing v_research_filter exists to
measure honestly.
"""

from sources.combiners.scorer import db, journal

NOW = "2026-07-27T02:00:00+00:00"
LATER = "2026-07-27T03:00:00+00:00"


def _fresh(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    return conn


def _verdict(symbol="PEGA", verdict="buy", corrects=None, note="original"):
    v = {
        "symbol": symbol,
        "verdict": verdict,
        "verdict_date": "2026-07-26",
        "doc": f"{symbol}-2026-07-26.md",
        "note": note,
    }
    if corrects:
        v["corrects"] = corrects
    return v


def _rows(conn, sql, args=()):
    return conn.execute(sql, args).fetchall()


def test_plain_reingest_is_still_a_counted_duplicate(tmp_path):
    """The idempotency guarantee must survive: only an explicit correction
    changes a recorded verdict."""
    conn = _fresh(tmp_path)
    journal.ingest(conn, [], [], [_verdict()], NOW)
    out = journal.ingest(conn, [], [], [_verdict(verdict="pass")], LATER)
    assert out["duplicates_skipped"] == 1
    assert out.get("corrected", 0) == 0
    assert _rows(conn, "SELECT verdict FROM research_verdicts")[0][0] == "buy"


def test_correction_updates_the_verdict(tmp_path):
    conn = _fresh(tmp_path)
    journal.ingest(conn, [], [], [_verdict()], NOW)
    out = journal.ingest(
        conn,
        [],
        [],
        [_verdict(verdict="pass", corrects="missed the Appian retrial", note="withdrawn")],
        LATER,
    )
    assert out["corrected"] == 1
    assert out["duplicates_skipped"] == 0, "a correction is not a duplicate"
    row = _rows(conn, "SELECT verdict, note FROM research_verdicts")[0]
    assert row == ("pass", "withdrawn")


def test_correction_preserves_the_original_for_audit(tmp_path):
    """Grading the corrected call is right; ERASING that a buy was once issued
    would make the skill look better than it was."""
    conn = _fresh(tmp_path)
    journal.ingest(conn, [], [], [_verdict()], NOW)
    journal.ingest(
        conn, [], [], [_verdict(verdict="pass", corrects="missed the Appian retrial")], LATER
    )
    audit = _rows(
        conn,
        "SELECT symbol, verdict_date, old_verdict, new_verdict, reason FROM verdict_corrections",
    )
    assert audit == [("PEGA", "2026-07-26", "buy", "pass", "missed the Appian retrial")]


def test_correction_of_an_unrecorded_verdict_is_a_plain_insert(tmp_path):
    """Correcting something never logged is not an error — it records the
    verdict and books no correction."""
    conn = _fresh(tmp_path)
    out = journal.ingest(conn, [], [], [_verdict(verdict="pass", corrects="n/a")], NOW)
    assert out["verdicts_recorded"] == 1
    assert out.get("corrected", 0) == 0
    assert _rows(conn, "SELECT COUNT(*) FROM verdict_corrections")[0][0] == 0


def test_correction_to_the_same_verdict_is_not_booked(tmp_path):
    """Re-asserting the same call is not a correction; only a real change is."""
    conn = _fresh(tmp_path)
    journal.ingest(conn, [], [], [_verdict()], NOW)
    out = journal.ingest(conn, [], [], [_verdict(verdict="buy", corrects="no change")], LATER)
    assert out.get("corrected", 0) == 0
    assert _rows(conn, "SELECT COUNT(*) FROM verdict_corrections")[0][0] == 0


def test_corrections_are_never_pruned(tmp_path):
    """Same rule as decisions and verdicts: the audit trail is the point."""
    conn = _fresh(tmp_path)
    journal.ingest(conn, [], [], [_verdict()], NOW)
    journal.ingest(conn, [], [], [_verdict(verdict="pass", corrects="why")], LATER)
    db.prune(conn, keep_days=0, now_iso="2027-01-01T00:00:00+00:00")
    assert _rows(conn, "SELECT COUNT(*) FROM verdict_corrections")[0][0] == 1
    assert _rows(conn, "SELECT COUNT(*) FROM research_verdicts")[0][0] == 1


def test_the_graded_view_sees_the_corrected_verdict(tmp_path):
    """v_research_filter groups by verdict; the correction must reach it, or
    the withdrawal is cosmetic."""
    conn = _fresh(tmp_path)
    journal.ingest(conn, [], [], [_verdict()], NOW)
    journal.ingest(conn, [], [], [_verdict(verdict="pass", corrects="why")], LATER)
    got = _rows(conn, "SELECT verdict FROM research_verdicts WHERE symbol='PEGA'")
    assert got == [("pass",)]


def test_a_correction_is_visible_in_the_run_summary_line(capsys, tmp_path):
    """A correction overwrites a graded call. In a scheduled run the log line
    is the only place an operator would ever see that happen, so it must not
    be silent."""
    import json

    p = tmp_path / "doc.json"
    db_path = str(tmp_path / "scorer.db")
    p.write_text(json.dumps({"verdicts": [_verdict()]}))
    journal.main(["--db", db_path, "--input", str(p)])
    p.write_text(json.dumps({"verdicts": [_verdict(verdict="pass", corrects="missed a filing")]}))
    journal.main(["--db", db_path, "--input", str(p)])
    assert "1 corrected" in capsys.readouterr().out
