import sqlite3

from sources.screeners.nyfed_screener import run as runmod

NOW = "2026-07-03T00:00:00+00:00"


def test_run_happy_path_counts(tmp_path):
    db_path = str(tmp_path / "n.db")

    def fetch_domain(endpoint, *, start=None, end=None):
        if "rates" in endpoint:
            return [{"effectiveDate": "2026-06-01", "type": "SOFR",
                     "percentRate": "5.3"}]
        if "results" in endpoint:                 # combined repo/reverserepo feed
            return [{"operationId": "R1", "operationDate": "2026-06-01",
                     "operationType": "Reverse Repo", "totalAmtAccepted": "400"}]
        return []

    sid, nd, nr = runmod.run(db_path, only=["reference_rates", "rrp"],
                             fetch_domain=fetch_domain, now_iso=NOW)
    assert nd == 2 and nr == 2
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM reference_rates").fetchone()[0] == 1


def test_run_skips_failing_domain_hides_secret(tmp_path, capsys):
    def fetch_domain(endpoint, *, start=None, end=None):
        if "rates" in endpoint:
            raise RuntimeError("https://markets?t=SECRET boom")
        return [{"asOfDate": "2026-06-03", "total": "7e12"}]   # wide SOMA row

    sid, nd, nr = runmod.run(str(tmp_path / "n.db"),
                             only=["reference_rates", "soma"],
                             fetch_domain=fetch_domain, now_iso=NOW)
    assert nd == 1 and nr == 1                    # rates failed, soma stored
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRET" not in err


def test_run_all_fail_zero_snapshot(tmp_path, capsys):
    def boom(endpoint, *, start=None, end=None):
        raise RuntimeError("x")

    sid, nd, nr = runmod.run(str(tmp_path / "n.db"), only=["reference_rates"],
                             fetch_domain=boom, now_iso=NOW)
    assert (nd, nr) == (0, 0)
    conn = sqlite3.connect(str(tmp_path / "n.db"))
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert "warning" in capsys.readouterr().err.lower()


def test_run_incremental_floors_start_at_max_date(tmp_path):
    db_path = str(tmp_path / "n.db")
    seen = {"start": []}

    def fetch_domain(endpoint, *, start=None, end=None):
        seen["start"].append(start)
        return [{"effectiveDate": "2026-06-02", "type": "SOFR",
                 "percentRate": "5.3"}]

    runmod.run(db_path, only=["reference_rates"], fetch_domain=fetch_domain,
               now_iso=NOW)
    runmod.run(db_path, only=["reference_rates"], fetch_domain=fetch_domain,
               now_iso=NOW)
    assert seen["start"][0] is None              # first run: full history
    # second run: floored 7 days BEFORE the max stored date (2026-06-02) so the
    # NY Fed's few-days-back restatements to stored rows are re-absorbed.
    assert seen["start"][1] == "2026-05-26"


def test_run_incremental_reabsorbs_restated_prior_day(tmp_path):
    db_path = str(tmp_path / "n.db")
    seen = {"start": []}
    responses = [
        [{"effectiveDate": "2026-05-30", "type": "SOFR", "percentRate": "5.3"},
         {"effectiveDate": "2026-06-02", "type": "SOFR", "percentRate": "5.3"}],
        [{"effectiveDate": "2026-05-30", "type": "SOFR", "percentRate": "9.9"}],
    ]

    def fetch_domain(endpoint, *, start=None, end=None):
        seen["start"].append(start)
        return responses[len(seen["start"]) - 1]

    runmod.run(db_path, only=["reference_rates"], fetch_domain=fetch_domain,
               now_iso=NOW)
    runmod.run(db_path, only=["reference_rates"], fetch_domain=fetch_domain,
               now_iso=NOW)
    assert seen["start"][1] == "2026-05-26"      # window covers restated 05-30
    conn = sqlite3.connect(db_path)
    val = conn.execute("SELECT percent_rate FROM reference_rates "
                       "WHERE effective_date='2026-05-30'").fetchone()[0]
    assert val == 9.9                            # restatement re-absorbed


def test_run_full_ignores_incremental_lookback(tmp_path):
    db_path = str(tmp_path / "n.db")
    seen = {"start": []}

    def fetch_domain(endpoint, *, start=None, end=None):
        seen["start"].append(start)
        return [{"effectiveDate": "2026-06-02", "type": "SOFR",
                 "percentRate": "5.3"}]

    runmod.run(db_path, only=["reference_rates"], fetch_domain=fetch_domain,
               now_iso=NOW)
    runmod.run(db_path, only=["reference_rates"], fetch_domain=fetch_domain,
               full=True, now_iso=NOW)
    assert seen["start"] == [None, None]         # --full re-pulls full history


def test_run_keep_days_prunes_snapshots_not_facts(tmp_path):
    db_path = str(tmp_path / "n.db")

    def fetch_domain(endpoint, *, start=None, end=None):
        return [{"effectiveDate": "2026-06-02", "type": "SOFR",
                 "percentRate": "5.3"}]

    runmod.run(db_path, only=["reference_rates"], fetch_domain=fetch_domain,
               now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, only=["reference_rates"], fetch_domain=fetch_domain,
               now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM reference_rates").fetchone()[0] == 1
