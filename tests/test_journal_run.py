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
