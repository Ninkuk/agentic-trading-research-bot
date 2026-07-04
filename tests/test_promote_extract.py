import pytest

from pipeline.promote import catalog, extract
from pipeline.leads import db as leads_db
from sources.screeners.stock_analysis_screener import db as stocks_db_mod

NOW = "2026-07-04T21:00:00+00:00"

STOCK_COLS = {"price": "REAL", "averageVolume": "REAL", "dollarVolume": "REAL",
              "atr": "REAL", "sector": "TEXT", "nextEarningsDate": "TEXT"}


def _leads_conn(rows, regime=None):
    conn = leads_db.connect(":memory:")
    leads_db.ensure_schema(conn)
    sid = leads_db.write_snapshot(conn, NOW)
    leads_db.write_leads(conn, sid, rows)
    if regime is not None:
        leads_db.write_regime(conn, sid, regime)
    return conn, sid


def _lead(**over):
    lead = {"instrument": "GLD", "instrument_kind": "etf",
            "signal": "cot_commercial_extreme", "direction": "long",
            "signal_type": "mean_reversion", "implementation": "cross_sectional",
            "horizon_band": "weeks", "score": 95.0, "rank_pct": None,
            "as_of_date": "2026-06-30",
            "details": '{"asset_class":"metals","commercial_index":95.0}'}
    lead.update(over)
    return lead


def _regime(scalar):
    return {"as_of_date": "2026-06-01", "cpi_yoy": 4.0, "unrate": 4.0,
            "yield_curve_inverted": 0, "hy_spread": 3.0, "late_cycle": 1,
            "exposure_scalar": scalar, "regime_incomplete": 0}


def test_load_latest_leads_with_regime():
    conn, sid = _leads_conn([_lead()], regime=_regime(0.5))
    out = extract.load_latest_leads(conn)
    assert out["regime_scalar"] == 0.5
    assert out["leads_snapshot_id"] == sid
    assert out["leads"][0]["instrument"] == "GLD"
    assert out["leads"][0]["score"] == 95.0


def test_load_latest_leads_defaults_scalar_when_regime_absent():
    conn, _sid = _leads_conn([_lead()])
    assert extract.load_latest_leads(conn)["regime_scalar"] == 1.0


def test_check_required_columns_lists_all_missing():
    conn = stocks_db_mod.connect(":memory:")
    stocks_db_mod.ensure_schema(conn, {"price": "REAL"})
    with pytest.raises(ValueError) as e:
        extract.check_required_columns(conn, catalog.REQUIRED_STOCK_POINTS,
                                       "stocks.db")
    msg = str(e.value)
    assert "atr" in msg and "sector" in msg and "nextEarningsDate" in msg


def test_load_liquidity_normalizes_symbols():
    conn = stocks_db_mod.connect(":memory:")
    stocks_db_mod.ensure_schema(conn, STOCK_COLS)
    stocks_db_mod.write_snapshot(conn, NOW, "test", {
        "BRK.B": {"price": 400.0, "averageVolume": 3e6, "dollarVolume": 1.2e9,
                  "atr": 5.0, "sector": "Financials",
                  "nextEarningsDate": "2026-08-01"}}, list(STOCK_COLS))
    liq = extract.load_liquidity(conn, catalog.REQUIRED_STOCK_POINTS)
    assert liq["BRK-B"]["price"] == 400.0
    assert liq["BRK-B"]["sector"] == "Financials"
    assert liq["BRK-B"]["nextEarningsDate"] == "2026-08-01"
