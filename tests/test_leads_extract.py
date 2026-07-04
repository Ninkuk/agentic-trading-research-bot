import json

from pipeline.leads import catalog, extract
from sources.screeners.cftc_screener import catalog as cftc_catalog
from sources.screeners.cftc_screener import db as cftc_db

NOW = "2026-07-04T12:00:00+00:00"


def _cftc_conn():
    conn = cftc_db.connect(":memory:")
    cftc_db.ensure_schema(conn)
    return conn


def _seed_disagg(conn, code, series, asset_class="metals"):
    """series: (report_date, prod_merc_long, prod_merc_short, mm_long, mm_short)."""
    cftc_db.upsert_markets(conn, [{"code": code, "name": "M",
                                   "asset_class": asset_class}], NOW)
    rows = [{"code": code, "report_date": d, "prod_merc_long": pl,
             "prod_merc_short": ps, "mm_long": ml, "mm_short": ms,
             "open_interest": 1000}
            for (d, pl, ps, ml, ms) in series]
    cftc_db.write_family(conn, cftc_catalog.DISAGG, code, rows)


def _seed_tff(conn, code, series, asset_class="equity_index"):
    """series: (report_date, dealer_long, dealer_short, lev_long, lev_short)."""
    cftc_db.upsert_markets(conn, [{"code": code, "name": "M",
                                   "asset_class": asset_class}], NOW)
    rows = [{"code": code, "report_date": d, "dealer_long": dl,
             "dealer_short": ds, "lev_long": ll, "lev_short": ls,
             "open_interest": 1000}
            for (d, dl, ds, ll, ls) in series]
    cftc_db.write_family(conn, cftc_catalog.TFF, code, rows)


GOLD = catalog.Mapping("088691", "GLD", "metals", "Gold")
SPX = catalog.Mapping("13874A", "SPY", "equity_index", "E-Mini S&P 500")


def test_cot_long_lead_on_commercial_extreme_high():
    conn = _cftc_conn()
    # commercial net walks 0 -> 100 (latest): index 100 -> long GLD.
    # managed money walks 100 -> 0 (latest): confirm index 0.
    _seed_disagg(conn, "088691", [("2026-06-16", 0, 0, 100, 0),
                                  ("2026-06-23", 100, 0, 0, 0)])
    leads = extract.extract_cot_extremes(conn, mappings=[GOLD])
    assert len(leads) == 1
    lead = leads[0]
    assert lead["instrument"] == "GLD"
    assert lead["instrument_kind"] == "etf"
    assert lead["direction"] == "long"
    assert lead["signal"] == "cot_commercial_extreme"
    assert lead["signal_type"] == "mean_reversion"
    assert lead["horizon_band"] == "weeks"
    assert lead["score"] == 100.0
    assert lead["as_of_date"] == "2026-06-23"
    details = json.loads(lead["details"])
    assert details["code"] == "088691"
    assert details["asset_class"] == "metals"
    assert details["family"] == "disaggregated"
    assert details["speculator_index"] == 0.0


def test_cot_short_lead_on_commercial_extreme_low():
    conn = _cftc_conn()
    _seed_disagg(conn, "088691", [("2026-06-16", 100, 0, 0, 0),
                                  ("2026-06-23", 0, 0, 100, 0)])
    leads = extract.extract_cot_extremes(conn, mappings=[GOLD])
    assert [l["direction"] for l in leads] == ["short"]
    assert leads[0]["score"] == 0.0


def test_cot_financials_use_tff_dealer_net():
    conn = _cftc_conn()
    _seed_tff(conn, "13874A", [("2026-06-16", 0, 0, 50, 0),
                               ("2026-06-23", 100, 0, 60, 0)])
    leads = extract.extract_cot_extremes(conn, mappings=[SPX])
    assert len(leads) == 1
    assert leads[0]["instrument"] == "SPY"
    assert json.loads(leads[0]["details"])["family"] == "tff"


def test_cot_mid_range_and_missing_markets_produce_no_lead():
    conn = _cftc_conn()
    # index 50 (mid-range) -> no lead; SPY absent from db -> no lead
    _seed_disagg(conn, "088691", [("2026-06-09", 0, 0, 0, 0),
                                  ("2026-06-16", 100, 0, 0, 0),
                                  ("2026-06-23", 50, 0, 0, 0)])
    assert extract.extract_cot_extremes(conn, mappings=[GOLD, SPX]) == []


def test_cot_degenerate_range_produces_no_lead():
    conn = _cftc_conn()
    _seed_disagg(conn, "088691", [("2026-06-23", 10, 0, 0, 0)])
    assert extract.extract_cot_extremes(conn, mappings=[GOLD]) == []


def test_read_source_state_cftc():
    conn = _cftc_conn()
    _seed_disagg(conn, "088691", [("2026-06-23", 100, 0, 0, 0)])
    cftc_db.write_snapshot(conn, NOW, 1, 1)
    state = extract.read_source_state(conn, "cftc", "cftc.db")
    assert state == {"source": "cftc", "db_path": "cftc.db",
                     "source_captured_at": NOW,
                     "max_data_date": "2026-06-23"}
