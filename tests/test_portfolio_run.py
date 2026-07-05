import io
import json

import pytest

from sources.screeners.portfolio_screener import db, run

NOW = "2026-07-05T20:00:00+00:00"

DOC = {"account": {"equity": 205.37, "cash": 12.4, "buying_power": 12.4},
       "positions": [{"symbol": "GLD", "quantity": 0.5,
                      "average_buy_price": 301.2, "market_value": 155.0}]}


def test_run_ingests_doc(tmp_path):
    path = str(tmp_path / "portfolio.db")
    sid, n_pos, skipped = run.run(path, DOC, now_iso=NOW)
    conn = db.connect(path)
    assert conn.execute("SELECT captured_at FROM snapshots WHERE id=?",
                        (sid,)).fetchone()[0] == NOW
    assert n_pos == 1 and skipped == 0
    assert conn.execute("SELECT equity FROM v_latest_account"
                        ).fetchone()[0] == 205.37
    conn.close()


def test_main_reads_input_file(tmp_path, capsys):
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(DOC))
    path = str(tmp_path / "portfolio.db")
    run.main(["--db", path, "--input", str(doc_path)])
    out = capsys.readouterr().out
    assert "1 positions" in out
    conn = db.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 1
    conn.close()


def test_main_reads_stdin(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(DOC)))
    path = str(tmp_path / "portfolio.db")
    run.main(["--db", path, "--input", "-"])
    assert "1 positions" in capsys.readouterr().out


def test_main_bad_json_prints_type_name_only(tmp_path, capsys):
    doc_path = tmp_path / "doc.json"
    doc_path.write_text("{not json")
    with pytest.raises(SystemExit):
        run.main(["--db", str(tmp_path / "p.db"), "--input", str(doc_path)])
    err = capsys.readouterr().err
    assert "JSONDecodeError" in err
    assert "{not json" not in err


def test_run_prunes_with_keep_days(tmp_path):
    path = str(tmp_path / "portfolio.db")
    run.run(path, DOC, now_iso="2026-06-01T20:00:00+00:00")
    run.run(path, DOC, now_iso=NOW, keep_days=7)
    conn = db.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    conn.close()
