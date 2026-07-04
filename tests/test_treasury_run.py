import sqlite3

from treasury_screener import run as runmod

NOW = "2026-07-03T00:00:00+00:00"


def _raw_debt(dates):
    return [{"record_date": d, "tot_pub_debt_out_amt": "100",
             "debt_held_public_amt": "70", "intragov_hold_amt": "30"} for d in dates]


def test_run_happy_path_counts_rows(tmp_path):
    db_path = str(tmp_path / "t.db")

    def fetch_dataset(endpoint, *, fields=None, since=None):
        return _raw_debt(["2026-07-01", "2026-07-02"])

    def fetch_yc(year):
        return [{"record_date": f"{year}-07-01", **{c: None for c in
                 ["mo1", "mo2", "mo3", "mo4", "mo6", "yr1", "yr2", "yr3", "yr5",
                  "yr7", "yr10", "yr20", "yr30"]}}]

    sid, nds, nrows = runmod.run(db_path, only=["debt_penny", "yield_curve"],
                                 fetch_dataset=fetch_dataset,
                                 fetch_yield_curve=fetch_yc, now_iso=NOW)
    assert nds == 2 and nrows == 3
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM debt_penny").fetchone()[0] == 2


def test_run_skips_failing_dataset_without_leaking_secret(tmp_path, capsys):
    def fetch_dataset(endpoint, *, fields=None, since=None):
        if "debt_to_penny" in endpoint:
            raise RuntimeError("https://api?token=SECRET boom")
        return _raw_debt(["2026-07-01"])       # avg_rates path (reuses shape ok)

    sid, nds, nrows = runmod.run(str(tmp_path / "t.db"),
                                 only=["debt_penny"], fetch_dataset=fetch_dataset,
                                 now_iso=NOW)
    assert (nds, nrows) == (0, 0)              # the only dataset failed
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRET" not in err


def test_run_all_fail_writes_zero_snapshot(tmp_path, capsys):
    def boom(endpoint, *, fields=None, since=None):
        raise RuntimeError("x")

    sid, nds, nrows = runmod.run(str(tmp_path / "t.db"), only=["debt_penny"],
                                 fetch_dataset=boom, now_iso=NOW)
    assert (nds, nrows) == (0, 0)
    conn = sqlite3.connect(str(tmp_path / "t.db"))
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert "warning" in capsys.readouterr().err.lower()


def test_run_incremental_second_run_upserts(tmp_path):
    db_path = str(tmp_path / "t.db")
    seen = {"since": []}

    def fetch_dataset(endpoint, *, fields=None, since=None):
        seen["since"].append(since)
        return _raw_debt(["2026-07-02"])

    runmod.run(db_path, only=["debt_penny"], fetch_dataset=fetch_dataset, now_iso=NOW)
    runmod.run(db_path, only=["debt_penny"], fetch_dataset=fetch_dataset, now_iso=NOW)
    assert seen["since"][0] is None             # first run: full history
    # second run: floored 7 days BEFORE the max stored date (2026-07-02) so the
    # re-fetch window re-absorbs restatements to recent already-stored days.
    assert seen["since"][1] == "2026-06-25"
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM debt_penny").fetchone()[0] == 1


def test_run_incremental_reabsorbs_restated_prior_day(tmp_path):
    db_path = str(tmp_path / "t.db")
    seen = {"since": []}
    responses = [
        _raw_debt(["2026-06-28", "2026-07-02"]),   # first run: two stored days
        [{"record_date": "2026-06-28", "tot_pub_debt_out_amt": "999",
          "debt_held_public_amt": "70", "intragov_hold_amt": "30"}],  # restated
    ]

    def fetch_dataset(endpoint, *, fields=None, since=None):
        seen["since"].append(since)
        return responses[len(seen["since"]) - 1]

    runmod.run(db_path, only=["debt_penny"], fetch_dataset=fetch_dataset, now_iso=NOW)
    runmod.run(db_path, only=["debt_penny"], fetch_dataset=fetch_dataset, now_iso=NOW)
    # the widened window (from 2026-06-25) covers the restated 06-28 day
    assert seen["since"][1] == "2026-06-25"
    conn = sqlite3.connect(db_path)
    val = conn.execute("SELECT tot_pub_debt_out FROM debt_penny "
                       "WHERE record_date='2026-06-28'").fetchone()[0]
    assert val == 999.0                          # restatement re-absorbed


def test_run_full_ignores_incremental_lookback(tmp_path):
    db_path = str(tmp_path / "t.db")
    seen = {"since": []}

    def fetch_dataset(endpoint, *, fields=None, since=None):
        seen["since"].append(since)
        return _raw_debt(["2026-07-02"])

    runmod.run(db_path, only=["debt_penny"], fetch_dataset=fetch_dataset, now_iso=NOW)
    runmod.run(db_path, only=["debt_penny"], fetch_dataset=fetch_dataset,
               full=True, now_iso=NOW)
    assert seen["since"] == [None, None]         # --full re-pulls full history


def test_run_keep_days_prunes_snapshots_not_facts(tmp_path):
    db_path = str(tmp_path / "t.db")

    def fetch_dataset(endpoint, *, fields=None, since=None):
        return _raw_debt(["2026-07-02"])

    runmod.run(db_path, only=["debt_penny"], fetch_dataset=fetch_dataset,
               now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, only=["debt_penny"], fetch_dataset=fetch_dataset,
               now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM debt_penny").fetchone()[0] == 1
