import json

import pytest

from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import db, journal

NOW = "2026-07-08T21:40:00+00:00"


def _mini_composite(path, date="2026-07-06", symbol="XLE"):
    conn = composite_db.connect(str(path))
    composite_db.ensure_schema(conn)
    conn.execute(
        "INSERT INTO snapshots (captured_at, signals_expected) VALUES (?, 1)",
        (f"{date}T21:05:00+00:00",),
    )
    conn.execute(
        "INSERT INTO ticker_scores (snapshot_id, symbol, total, score_sum) VALUES (1, ?, 4, 5)",
        (symbol,),
    )
    conn.commit()
    conn.close()


DOC = {
    "as_of": NOW,
    "fills": [
        {
            "symbol": "XLE",
            "side": "buy",
            "price": 94.30,
            "quantity": 2,
            "filled_at": "2026-07-07T14:31:00+00:00",
            "order_ref": "ref-1",
        }
    ],
}


def test_run_ingests(tmp_path):
    _mini_composite(tmp_path / "composite.db")
    counts = journal.run(
        str(tmp_path / "scorer.db"),
        DOC,
        composite_db=str(tmp_path / "composite.db"),
        now_iso=NOW,
    )
    assert counts["matched"] == 1


def test_run_empty_doc_needs_no_composite(tmp_path):
    counts = journal.run(str(tmp_path / "scorer.db"), {}, now_iso=NOW)
    assert counts["fills_seen"] == 0 and counts["run_id"] == 1


def test_run_no_composite_path_is_loud(tmp_path):
    # public API misuse: fills need matching but no path given — must be the
    # promised FileNotFoundError, not a TypeError from os.path.exists(None)
    with pytest.raises(FileNotFoundError):
        journal.run(str(tmp_path / "scorer.db"), DOC, now_iso=NOW)


def test_run_missing_composite_is_loud(tmp_path):
    with pytest.raises(FileNotFoundError):
        journal.run(
            str(tmp_path / "scorer.db"),
            DOC,
            composite_db=str(tmp_path / "composite.db"),
            now_iso=NOW,
        )
    conn = db.connect(str(tmp_path / "scorer.db"))
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM journal_runs").fetchone()[0] == 0


def test_main_file_input_and_default_composite_path(tmp_path, capsys):
    _mini_composite(tmp_path / "composite.db")
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(DOC))
    journal.main(["--db", str(tmp_path / "scorer.db"), "--input", str(doc_path)])
    out = capsys.readouterr().out
    assert "1 matched" in out


def test_main_stdin_input(tmp_path, capsys, monkeypatch):
    import io

    _mini_composite(tmp_path / "composite.db")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(DOC)))
    journal.main(["--db", str(tmp_path / "scorer.db"), "--input", "-"])
    assert "1 matched" in capsys.readouterr().out


def test_main_last_run(tmp_path, capsys):
    journal.main(["--db", str(tmp_path / "scorer.db"), "--last-run"])
    assert capsys.readouterr().out.strip() == "never"
    journal.run(str(tmp_path / "scorer.db"), {}, now_iso=NOW)
    journal.main(["--db", str(tmp_path / "scorer.db"), "--last-run"])
    assert capsys.readouterr().out.strip() == NOW


def test_main_bad_input_exits_nonzero(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(SystemExit):
        journal.main(["--db", str(tmp_path / "scorer.db"), "--input", str(bad)])
    err = capsys.readouterr().err
    assert "JSONDecodeError" in err


def test_main_missing_composite_exits_nonzero(tmp_path, capsys):
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(DOC))
    with pytest.raises(SystemExit):
        journal.main(["--db", str(tmp_path / "scorer.db"), "--input", str(doc_path)])
    assert "composite" in capsys.readouterr().err


def _manual_doc(**fill_overrides):
    fill = dict(
        symbol="XLE",
        side="buy",
        price=94.30,
        quantity=2,
        filled_at="2026-07-07T14:31:00+00:00",
    )
    fill.update(fill_overrides)
    return {"as_of": NOW, "fills": [fill]}


def test_manual_fill_reingest_is_idempotent(tmp_path):
    _mini_composite(tmp_path / "composite.db")
    doc = _manual_doc()
    counts = journal.run(
        str(tmp_path / "scorer.db"),
        doc,
        composite_db=str(tmp_path / "composite.db"),
        now_iso=NOW,
    )
    assert counts["duplicates_skipped"] == 0
    conn = db.connect(str(tmp_path / "scorer.db"))
    rows = conn.execute("SELECT source FROM decisions").fetchall()
    assert rows == [("manual",)]

    # re-ingest the exact same document
    counts2 = journal.run(
        str(tmp_path / "scorer.db"),
        doc,
        composite_db=str(tmp_path / "composite.db"),
        now_iso=NOW,
    )
    assert counts2["duplicates_skipped"] == 1
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1


def test_two_distinct_manual_fills_both_insert(tmp_path):
    _mini_composite(tmp_path / "composite.db")
    doc = {
        "as_of": NOW,
        "fills": [
            dict(
                symbol="XLE",
                side="buy",
                price=94.30,
                quantity=2,
                filled_at="2026-07-07T14:31:00+00:00",
            ),
            dict(
                symbol="XLE",
                side="buy",
                price=95.10,
                quantity=1,
                filled_at="2026-07-07T15:45:00+00:00",
            ),
        ],
    }
    counts = journal.run(
        str(tmp_path / "scorer.db"),
        doc,
        composite_db=str(tmp_path / "composite.db"),
        now_iso=NOW,
    )
    assert counts["duplicates_skipped"] == 0
    conn = db.connect(str(tmp_path / "scorer.db"))
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 2


def test_manual_sell_exit_reingest_is_idempotent(tmp_path):
    _mini_composite(tmp_path / "composite.db")
    doc = {
        "as_of": NOW,
        "fills": [
            dict(
                symbol="XLE",
                side="buy",
                price=94.30,
                quantity=2,
                filled_at="2026-07-07T14:31:00+00:00",
            ),
            dict(
                symbol="XLE",
                side="sell",
                price=99.10,
                quantity=2,
                filled_at="2026-07-09T15:00:00+00:00",
            ),
        ],
    }
    scorer_path = str(tmp_path / "scorer.db")
    composite_path = str(tmp_path / "composite.db")
    journal.run(scorer_path, doc, composite_db=composite_path, now_iso=NOW)
    conn = db.connect(scorer_path)
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1
    assert conn.execute("SELECT exit_fill_date FROM decisions").fetchone()[0] == "2026-07-09"

    # re-ingest the whole doc: the sell must not re-insert as a freelance sell
    counts2 = journal.run(scorer_path, doc, composite_db=composite_path, now_iso=NOW)
    assert counts2["duplicates_skipped"] == 2
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1
    exit_dates = conn.execute(
        "SELECT exit_fill_date FROM decisions WHERE exit_fill_date IS NOT NULL"
    ).fetchall()
    assert exit_dates == [("2026-07-09",)]


def test_real_order_ref_path_unchanged(tmp_path):
    _mini_composite(tmp_path / "composite.db")
    scorer_path = str(tmp_path / "scorer.db")
    composite_path = str(tmp_path / "composite.db")
    counts = journal.run(scorer_path, DOC, composite_db=composite_path, now_iso=NOW)
    assert counts["duplicates_skipped"] == 0
    conn = db.connect(scorer_path)
    row = conn.execute("SELECT order_ref, source FROM decisions").fetchone()
    assert row == ("ref-1", "mcp")

    # re-ingesting the same real-ref doc dedupes as before
    counts2 = journal.run(scorer_path, DOC, composite_db=composite_path, now_iso=NOW)
    assert counts2["duplicates_skipped"] == 1
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1


def test_dedup_ref_is_deterministic_and_field_sensitive():
    fill = dict(
        symbol="XLE",
        side="buy",
        price=94.30,
        quantity=2,
        filled_at="2026-07-07T14:31:00+00:00",
        order_ref=None,
    )
    key1 = journal._dedup_ref(dict(fill))
    key2 = journal._dedup_ref(dict(fill))
    assert key1 == key2
    assert key1.startswith("manual:")

    other_price = dict(fill, price=95.10)
    assert journal._dedup_ref(other_price) != key1

    # a real order_ref always wins, regardless of other fields
    with_ref = dict(fill, order_ref="ref-9")
    assert journal._dedup_ref(with_ref) == "ref-9"


def test_verdicts_only_doc_ingests_without_composite(tmp_path):
    dbp = str(tmp_path / "scorer.db")
    doc = {
        "as_of": "2026-07-22T20:00:00+00:00",
        "verdicts": [
            {
                "symbol": "bbai",
                "verdict": "pass",
                "verdict_date": "2026-07-22",
                "doc": "BBAI-2026-07-21.md",
                "note": "unproven",
            }
        ],
    }
    # Evening-Phoenix now_iso (next-day UTC) — must not shift verdict_date.
    c = journal.run(dbp, doc, composite_db=None, now_iso="2026-07-23T04:12:00+00:00")
    assert c["verdicts_recorded"] == 1 and c["skipped"] == 0
    conn = db.connect(dbp)
    row = conn.execute(
        "SELECT symbol, verdict, verdict_date, doc, note FROM research_verdicts"
    ).fetchone()
    assert row == ("BBAI", "pass", "2026-07-22", "BBAI-2026-07-21.md", "unproven")
    # Header row records the count.
    assert (
        conn.execute(
            "SELECT verdicts_recorded FROM journal_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()[0]
        == 1
    )
    conn.close()


def test_verdict_reingest_is_counted_duplicate(tmp_path):
    dbp = str(tmp_path / "scorer.db")
    doc = {"verdicts": [{"symbol": "EOSE", "verdict": "pass", "verdict_date": "2026-07-22"}]}
    journal.run(dbp, doc, composite_db=None, now_iso="2026-07-23T04:12:00+00:00")
    c = journal.run(dbp, doc, composite_db=None, now_iso="2026-07-23T04:13:00+00:00")
    assert c["verdicts_recorded"] == 0
    assert c["duplicates_skipped"] == 1
