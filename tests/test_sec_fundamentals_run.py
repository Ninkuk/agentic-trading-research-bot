import sqlite3

from sec_fundamentals import run as runmod

NOW = "2026-05-01T00:00:00+00:00"      # most recent completed quarter: CY2026Q1
MAP = {1: {"ticker": "AAA", "title": "Alpha"},
       2: {"ticker": "BBB", "title": "Beta"}}


def _frame_rows(cik, value):
    return [{"cik": cik, "tag": None, "uom": None, "period_end": "2026-03-31",
             "fiscal_year": None, "fiscal_period": None, "value": value,
             "form": None, "filed": None, "accession": "acc"}]


def test_run_frames_path_writes_companies_and_facts(tmp_path):
    db_path = str(tmp_path / "f.db")

    def fetch_frame(tag, unit, period, taxonomy="us-gaap"):
        return _frame_rows(1, 100) + _frame_rows(2, 200)

    sid, ncomp, nfact = runmod.run(
        db_path, only=["Assets"], fetch_frame=fetch_frame,
        fetch_map=lambda: MAP, now_iso=NOW)
    assert ncomp == 2 and nfact == 2
    conn = sqlite3.connect(db_path)
    # frames facts carry the FRAME provenance marker
    forms = {r[0] for r in conn.execute("SELECT DISTINCT form FROM facts")}
    assert forms == {"FRAME"}
    assert conn.execute("SELECT ticker FROM companies WHERE cik=1").fetchone() \
        == ("AAA",)


def test_run_instant_concept_requests_I_suffixed_period():
    seen = {}

    def fetch_frame(tag, unit, period, taxonomy="us-gaap"):
        seen[tag] = period
        return []

    runmod.run(":memory:", only=["Assets"], fetch_frame=fetch_frame,
               fetch_map=lambda: {}, now_iso=NOW)
    assert seen["Assets"].endswith("I")        # instant -> trailing I


def test_run_skips_failing_item_without_leaking_secret(tmp_path, capsys):
    def fetch_frame(tag, unit, period, taxonomy="us-gaap"):
        if tag == "Assets":
            raise RuntimeError("http://data.sec.gov/secret boom")
        return _frame_rows(1, 5)

    sid, ncomp, nfact = runmod.run(
        str(tmp_path / "f.db"), only=["Assets", "Liabilities"],
        fetch_frame=fetch_frame, fetch_map=lambda: MAP, now_iso=NOW)
    assert nfact == 1                          # Assets skipped, Liabilities kept
    err = capsys.readouterr().err
    assert "RuntimeError" in err
    assert "boom" not in err                   # secret hygiene: type name only


def test_run_watchlist_depth_uses_companyfacts(tmp_path):
    db_path = str(tmp_path / "f.db")
    payload = {"facts": {"us-gaap": {"NetIncomeLoss": {"units": {"USD": [
        {"end": "2025-12-31", "val": 7, "fy": 2025, "fp": "FY",
         "form": "10-K", "filed": "2026-02-01", "accn": "a"}]}}}}}

    def fetch_facts(cik):
        return payload

    sid, ncomp, nfact = runmod.run(
        db_path, only=["NetIncomeLoss"], tickers=["AAA"],
        fetch_frame=lambda *a, **k: [], fetch_facts=fetch_facts,
        fetch_map=lambda: MAP, now_iso=NOW)
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT form, value FROM facts").fetchone()
    assert row == ("10-K", 7.0)                # real form from companyfacts


def test_run_all_fail_writes_zero_snapshot(tmp_path, capsys):
    def fetch_frame(tag, unit, period, taxonomy="us-gaap"):
        raise RuntimeError("boom")

    sid, ncomp, nfact = runmod.run(
        str(tmp_path / "f.db"), only=["Assets"], fetch_frame=fetch_frame,
        fetch_map=lambda: {}, now_iso=NOW)
    assert (ncomp, nfact) == (0, 0)
    assert "warning" in capsys.readouterr().err.lower()


def test_run_keep_days_prunes_snapshots_not_facts(tmp_path):
    db_path = str(tmp_path / "f.db")

    def fetch_frame(tag, unit, period, taxonomy="us-gaap"):
        return _frame_rows(1, 100)

    runmod.run(db_path, only=["Assets"], fetch_frame=fetch_frame,
               fetch_map=lambda: MAP, now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, only=["Assets"], fetch_frame=fetch_frame,
               fetch_map=lambda: MAP, now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] >= 1
