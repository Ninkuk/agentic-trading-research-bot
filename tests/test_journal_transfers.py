import sqlite3

import pytest

from sources.combiners.scorer import journal


def _rows(db_path):
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute("SELECT obs_date, amount, note FROM transfers ORDER BY id").fetchall()
    finally:
        conn.close()


def test_transfer_records_signed_amount(tmp_path, capsys):
    db_path = tmp_path / "scorer.db"
    journal.main(
        [
            "--db",
            str(db_path),
            "--transfer",
            "100",
            "--date",
            "2026-08-01",
            "--note",
            "first deposit",
        ]
    )
    assert _rows(db_path) == [("2026-08-01", 100.0, "first deposit")]
    assert "deposit 100.00 on 2026-08-01" in capsys.readouterr().out


def test_withdrawal_is_negative(tmp_path, capsys):
    db_path = tmp_path / "scorer.db"
    journal.main(["--db", str(db_path), "--transfer", "-40", "--date", "2026-08-02"])
    assert _rows(db_path) == [("2026-08-02", -40.0, None)]
    assert "withdrawal 40.00" in capsys.readouterr().out


@pytest.mark.parametrize(
    "argv",
    [
        ["--transfer", "100"],  # no --date
        ["--transfer", "100", "--date", "2026-08-01T21:00:00"],  # timestamp, not bare date
        ["--transfer", "0", "--date", "2026-08-01"],  # zero amount
    ],
)
def test_transfer_rejects_bad_input(tmp_path, argv):
    with pytest.raises(SystemExit):
        journal.main(["--db", str(tmp_path / "scorer.db"), *argv])
