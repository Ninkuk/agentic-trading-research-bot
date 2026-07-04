import io
import sqlite3
import zipfile

from sources.screeners.sec_fundamentals import run as runmod

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


def _bulk_zip(cik, name, sic, value):
    """A minimal quarterly financial-statement-data-set ZIP (sub.tsv ⋈ num.tsv)."""
    sub = ("adsh\tcik\tname\tsic\tform\tperiod\tfy\tfp\tfiled\n"
           f"acc1\t{cik}\t{name}\t{sic}\t10-K\t20240928\t2024\tFY\t20241101\n")
    num = ("adsh\ttag\tversion\tddate\tqtrs\tuom\tvalue\n"
           f"acc1\tNetIncomeLoss\tus-gaap/2024\t20240928\t4\tUSD\t{value}\n")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("sub.tsv", sub)
        z.writestr("num.tsv", num)
    return buf.getvalue()


def test_run_bulk_enumerates_quarters_skips_unpublished_labels_from_sub(tmp_path):
    db_path = str(tmp_path / "f.db")
    calls = []
    # NOW = CY2026Q1 label but the month (May) puts the current quarter at Q2,
    # so start=2025q4 enumerates 2025q4, 2026q1, 2026q2. Only 2025q4 is published.
    zips = {(2025, 4): _bulk_zip(320193, "APPLE INC", "3571", 100)}

    def fetch_bulk(year, quarter, get=None):
        calls.append((year, quarter))
        return zips.get((year, quarter))          # None -> unpublished, skipped

    def fetch_frame(*a, **k):
        raise AssertionError("frames path must not run in --bulk mode")

    sid, ncomp, nfact = runmod.run(
        db_path, only=["NetIncomeLoss"], bulk=True, bulk_start="2025q4",
        fetch_bulk=fetch_bulk, fetch_frame=fetch_frame, fetch_map=lambda: {},
        now_iso=NOW)

    assert calls == [(2025, 4), (2026, 1), (2026, 2)]   # inclusive to current qtr
    assert (ncomp, nfact) == (1, 1)
    conn = sqlite3.connect(db_path)
    # company labeled from sub.tsv even with an empty ticker map
    assert conn.execute("SELECT name, sic FROM companies WHERE cik=320193"
                        ).fetchone() == ("APPLE INC", "3571")
    assert conn.execute("SELECT form, value FROM facts WHERE cik=320193"
                        ).fetchone() == ("10-K", 100.0)


def test_run_bulk_default_start_is_latest_completed_quarter(tmp_path):
    # No bulk_start: default to the most recent completed quarter (CY2026Q1 for
    # NOW), enumerating just that quarter through the current one.
    calls = []

    def fetch_bulk(year, quarter, get=None):
        calls.append((year, quarter))
        return None

    runmod.run(str(tmp_path / "f.db"), only=["NetIncomeLoss"], bulk=True,
               fetch_bulk=fetch_bulk, fetch_map=lambda: {}, now_iso=NOW)
    assert calls[0] == (2026, 1)          # previous completed quarter
    assert calls[-1] == (2026, 2)         # current quarter (unpublished -> None)


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
