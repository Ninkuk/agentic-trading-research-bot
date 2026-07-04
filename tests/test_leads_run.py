import json

from pipeline.leads import run as leads_run
from pipeline.leads import db as leads_db
from sources.screeners.cftc_screener import catalog as cftc_catalog
from sources.screeners.cftc_screener import db as cftc_db
from sources.screeners.fred_screener import db as fred_db
from sources.screeners.sec_fundamentals import db as fund_db
from sources.screeners.stock_analysis_screener import db as stocks_db_mod

NOW = "2026-07-04T12:00:00+00:00"


def _make_cftc(path):
    conn = cftc_db.connect(path)
    cftc_db.ensure_schema(conn)
    cftc_db.upsert_markets(conn, [{"code": "088691", "name": "Gold",
                                   "asset_class": "metals"}], NOW)
    cftc_db.write_family(conn, cftc_catalog.DISAGG, "088691", [
        {"code": "088691", "report_date": "2026-06-16",
         "prod_merc_long": 0, "prod_merc_short": 0, "open_interest": 1000},
        {"code": "088691", "report_date": "2026-06-23",
         "prod_merc_long": 100, "prod_merc_short": 0, "open_interest": 1000},
    ])
    cftc_db.write_snapshot(conn, NOW, 1, 2)
    conn.close()


def _make_fred(path):
    conn = fred_db.connect(path)
    fred_db.ensure_schema(conn)
    for sid, obs in {
        "CPIAUCSL": [("2025-06-01", 100.0), ("2026-06-01", 104.0)],
        "UNRATE": [("2026-06-01", 4.0)],
        "T10Y2Y": [("2026-06-30", 0.5)],
        "BAMLH0A0HYM2": [("2026-06-30", 3.5)],
    }.items():
        fred_db.upsert_series(conn, [{"id": sid, "title": sid,
                                      "theme": "test"}], NOW)
        fred_db.write_observations(
            conn, sid, [{"date": d, "value": v} for d, v in obs])
    fred_db.write_snapshot(conn, NOW, 4, 5)
    conn.close()


def _make_fundamentals(path):
    conn = fund_db.connect(path)
    fund_db.ensure_schema(conn)
    fund_db.upsert_companies(
        conn, [{"cik": i, "ticker": f"T{i}"} for i in range(10)], NOW)
    for i in range(10):
        fund_db.write_facts(conn, i, [
            {"tag": "Revenues", "period_end": "2025-12-31",
             "value": 100.0 + 10 * i, "form": "10-K"},
            {"tag": "Revenues", "period_end": "2024-12-31",
             "value": 100.0, "form": "10-K"},
            {"tag": "NetIncomeLoss", "period_end": "2025-12-31",
             "value": 5.0 + 5 * i, "form": "10-K"},
            {"tag": "StockholdersEquity", "period_end": "2025-12-31",
             "value": 100.0, "form": "10-K"},
            {"tag": "Liabilities", "period_end": "2025-12-31",
             "value": 100.0 - 5 * i, "form": "10-K"},
        ])
    fund_db.write_snapshot(conn, NOW, 10, 50)
    conn.close()


def _make_stocks(path):
    conn = stocks_db_mod.connect(path)
    cols = {"sector": "TEXT", "isPrimaryListing": "INTEGER"}
    stocks_db_mod.ensure_schema(conn, cols)
    data = {f"T{i}": {"sector": "Technology", "isPrimaryListing": 1}
            for i in range(10)}
    stocks_db_mod.write_snapshot(conn, NOW, "test", data, list(cols))
    conn.close()


def _sources(tmp_path):
    paths = {name: str(tmp_path / f"{name}.db")
             for name in ("cftc", "fred", "fundamentals", "stocks")}
    _make_cftc(paths["cftc"])
    _make_fred(paths["fred"])
    _make_fundamentals(paths["fundamentals"])
    _make_stocks(paths["stocks"])
    return paths


def test_run_writes_all_three_legs(tmp_path):
    paths = _sources(tmp_path)
    db_path = str(tmp_path / "leads.db")
    sid, count = leads_run.run(db_path, cftc_db=paths["cftc"],
                               fred_db=paths["fred"],
                               fundamentals_db=paths["fundamentals"],
                               stocks_db=paths["stocks"], now_iso=NOW)
    conn = leads_db.connect(db_path)
    signals = {r[0] for r in conn.execute(
        "SELECT DISTINCT signal FROM leads WHERE snapshot_id=?", (sid,))}
    assert signals == {"cot_commercial_extreme", "quality_composite"}
    scalar = conn.execute("SELECT exposure_scalar FROM regime "
                          "WHERE snapshot_id=?", (sid,)).fetchone()[0]
    assert scalar == 0.5  # fixture is late-cycle (CPI 4%, UNRATE 4.0)
    header = conn.execute("SELECT lead_count FROM snapshots WHERE id=?",
                          (sid,)).fetchone()[0]
    assert header == count > 0
    states = {r[0] for r in conn.execute(
        "SELECT source FROM source_state WHERE snapshot_id=?", (sid,))}
    assert states == {"cftc", "fred", "fundamentals", "stocks"}
    conn.close()


def test_run_only_filters_legs(tmp_path):
    paths = _sources(tmp_path)
    db_path = str(tmp_path / "leads.db")
    sid, _ = leads_run.run(db_path, cftc_db=paths["cftc"],
                           fred_db=paths["fred"],
                           fundamentals_db=paths["fundamentals"],
                           stocks_db=paths["stocks"],
                           only=["cot"], now_iso=NOW)
    conn = leads_db.connect(db_path)
    signals = {r[0] for r in conn.execute(
        "SELECT DISTINCT signal FROM leads WHERE snapshot_id=?", (sid,))}
    assert signals == {"cot_commercial_extreme"}
    assert conn.execute("SELECT COUNT(*) FROM regime").fetchone()[0] == 0
    conn.close()


def test_run_skips_missing_source_and_continues(tmp_path, capsys):
    paths = _sources(tmp_path)
    db_path = str(tmp_path / "leads.db")
    sid, count = leads_run.run(db_path, cftc_db=str(tmp_path / "absent.db"),
                               fred_db=paths["fred"],
                               fundamentals_db=paths["fundamentals"],
                               stocks_db=paths["stocks"], now_iso=NOW)
    err = capsys.readouterr().err
    assert "skipping cot leg: OperationalError" in err
    assert "absent.db" not in err  # secret hygiene: class name only
    conn = leads_db.connect(db_path)
    signals = {r[0] for r in conn.execute(
        "SELECT DISTINCT signal FROM leads WHERE snapshot_id=?", (sid,))}
    assert signals == {"quality_composite"}  # other legs still ran
    assert conn.execute("SELECT COUNT(*) FROM regime WHERE snapshot_id=?",
                        (sid,)).fetchone()[0] == 1
    conn.close()


def test_run_source_dbs_stay_untouched(tmp_path):
    paths = _sources(tmp_path)
    import hashlib, pathlib
    before = {p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
              for p in paths.values()}
    leads_run.run(str(tmp_path / "leads.db"), cftc_db=paths["cftc"],
                  fred_db=paths["fred"], fundamentals_db=paths["fundamentals"],
                  stocks_db=paths["stocks"], now_iso=NOW)
    after = {p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
             for p in paths.values()}
    assert before == after


def test_run_prunes_old_snapshots(tmp_path):
    paths = _sources(tmp_path)
    db_path = str(tmp_path / "leads.db")
    leads_run.run(db_path, cftc_db=paths["cftc"], fred_db=paths["fred"],
                  fundamentals_db=paths["fundamentals"],
                  stocks_db=paths["stocks"],
                  now_iso="2026-01-01T00:00:00+00:00")
    leads_run.run(db_path, cftc_db=paths["cftc"], fred_db=paths["fred"],
                  fundamentals_db=paths["fundamentals"],
                  stocks_db=paths["stocks"], now_iso=NOW, keep_days=30)
    conn = leads_db.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    conn.close()


def test_main_cli_smoke(tmp_path, capsys):
    paths = _sources(tmp_path)
    db_path = str(tmp_path / "leads.db")
    leads_run.main(["--db", db_path, "--cftc-db", paths["cftc"],
                    "--fred-db", paths["fred"],
                    "--fundamentals-db", paths["fundamentals"],
                    "--stocks-db", paths["stocks"]])
    out = capsys.readouterr().out
    assert "leads into" in out
