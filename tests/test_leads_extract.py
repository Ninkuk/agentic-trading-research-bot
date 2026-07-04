import json

import pytest

from pipeline.leads import catalog, extract
from sources.screeners.cftc_screener import catalog as cftc_catalog
from sources.screeners.cftc_screener import db as cftc_db
from sources.screeners.fred_screener import db as fred_db
from sources.screeners.sec_fundamentals import db as fund_db
from sources.screeners.stock_analysis_screener import db as stocks_db_mod

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


# Quality composite tests

STOCK_COLUMNS = {"sector": "TEXT", "isPrimaryListing": "INTEGER"}


def _stocks_conn(rows, captured_at=NOW):
    """rows: list of (symbol, sector, is_primary)."""
    conn = stocks_db_mod.connect(":memory:")
    stocks_db_mod.ensure_schema(conn, STOCK_COLUMNS)
    data = {sym: {"sector": sector, "isPrimaryListing": prim}
            for sym, sector, prim in rows}
    stocks_db_mod.write_snapshot(conn, captured_at, "test",
                                 data, list(STOCK_COLUMNS))
    return conn


def _fund_conn(companies, facts):
    """companies: list of (cik, ticker). facts: (cik, tag, period_end, value)."""
    conn = fund_db.connect(":memory:")
    fund_db.ensure_schema(conn)
    fund_db.upsert_companies(
        conn, [{"cik": c, "ticker": t} for c, t in companies], NOW)
    by_cik = {}
    for cik, tag, pe, value in facts:
        by_cik.setdefault(cik, []).append(
            {"tag": tag, "period_end": pe, "value": value, "form": "10-K"})
    for cik, rows in by_cik.items():
        fund_db.write_facts(conn, cik, rows)
    return conn


def _quality_facts(cik, revenue_now, revenue_ago, net_income, equity,
                   liabilities):
    """Annual-aligned fact set giving a company all three dimensions."""
    return [
        (cik, "Revenues", "2025-12-31", revenue_now),
        (cik, "Revenues", "2024-12-31", revenue_ago),
        (cik, "NetIncomeLoss", "2025-12-31", net_income),
        (cik, "StockholdersEquity", "2025-12-31", equity),
        (cik, "Liabilities", "2025-12-31", liabilities),
    ]


def test_quality_ranks_within_sector_and_emits_decile_leads():
    # 10 tech names, one clear winner and one clear loser, so the top/bottom
    # decile of 10 valid names is exactly 1 lead each.
    companies = [(i, f"T{i}") for i in range(10)]
    facts = []
    for i in range(10):
        # margins/roe/growth/safety improve monotonically with i
        facts += _quality_facts(i, revenue_now=100 + 10 * i, revenue_ago=100,
                                net_income=5 + 5 * i, equity=100,
                                liabilities=100 - 5 * i)
    fund = _fund_conn(companies, facts)
    stocks = _stocks_conn([(f"T{i}", "Technology", 1) for i in range(10)])
    leads, dropped = extract.extract_quality(fund, stocks)
    assert dropped == 0
    by_dir = {l["direction"]: l for l in leads}
    assert by_dir["long"]["instrument"] == "T9"
    assert by_dir["short"]["instrument"] == "T0"
    assert by_dir["long"]["rank_pct"] == 1.0
    assert by_dir["short"]["rank_pct"] == 0.0
    assert by_dir["long"]["signal"] == "quality_composite"
    assert by_dir["long"]["signal_type"] == "quality"
    assert by_dir["long"]["horizon_band"] == "months"
    assert by_dir["long"]["instrument_kind"] == "stock"
    assert by_dir["long"]["as_of_date"] == NOW[:10]
    details = json.loads(by_dir["long"]["details"])
    assert details["sector"] == "Technology"
    assert "profitability_z" in details and "growth_z" in details


def test_quality_requires_min_two_dimensions():
    # cik 0/1 complete; cik 2 has ONLY revenue facts (growth alone = 1 dim)
    companies = [(0, "A"), (1, "B"), (2, "C")]
    facts = (_quality_facts(0, 110, 100, 10, 100, 50)
             + _quality_facts(1, 120, 100, 20, 100, 40)
             + [(2, "Revenues", "2025-12-31", 130.0),
                (2, "Revenues", "2024-12-31", 100.0)])
    fund = _fund_conn(companies, facts)
    stocks = _stocks_conn([("A", "Tech", 1), ("B", "Tech", 1), ("C", "Tech", 1)])
    leads, dropped = extract.extract_quality(fund, stocks)
    assert dropped == 1
    assert all(l["instrument"] != "C" for l in leads)


def test_quality_universe_requires_primary_listing_and_join():
    companies = [(0, "A"), (1, "B"), (2, "ZZZ")]  # ZZZ not in stocks universe
    facts = (_quality_facts(0, 110, 100, 10, 100, 50)
             + _quality_facts(1, 120, 100, 20, 100, 40)
             + _quality_facts(2, 130, 100, 30, 100, 30))
    fund = _fund_conn(companies, facts)
    stocks = _stocks_conn([("A", "Tech", 1), ("B", "Tech", 0)])  # B secondary
    leads, _dropped = extract.extract_quality(fund, stocks)
    instruments = {l["instrument"] for l in leads}
    assert "B" not in instruments and "ZZZ" not in instruments


def test_quality_normalizes_class_share_tickers():
    companies = [(0, "BRK-B"), (1, "A")]
    facts = (_quality_facts(0, 110, 100, 10, 100, 50)
             + _quality_facts(1, 120, 100, 20, 100, 40))
    fund = _fund_conn(companies, facts)
    stocks = _stocks_conn([("BRK.B", "Financials", 1), ("A", "Financials", 1)])
    leads, _ = extract.extract_quality(fund, stocks, top=0.5, bottom=0.4)
    assert {l["instrument"] for l in leads} <= {"BRK-B", "A"}
    assert len(leads) > 0


def test_revenue_yoy_pair_alignment_and_ratio_guard():
    # 2025-12-31 vs 2024-12-31 is within +/-35d of 12 months -> pair OK.
    # cik 1's year-ago is 40x smaller -> ratio 40 > 5 -> pair discarded.
    companies = [(0, "A"), (1, "B")]
    facts = [(0, "Revenues", "2025-12-31", 110.0),
             (0, "Revenues", "2024-12-31", 100.0),
             (1, "Revenues", "2025-12-31", 400.0),
             (1, "Revenues", "2024-12-31", 10.0)]
    fund = _fund_conn(companies, facts)
    yoy = extract._revenue_yoy(fund)
    assert abs(yoy[0] - 0.10) < 1e-9
    assert 1 not in yoy


def test_revenue_yoy_tag_precedence_per_company():
    # cik 0 has BOTH tags: Revenues wins even though the other tag would give
    # a bigger number. cik 1 has only the contract-revenue tag: it is used.
    companies = [(0, "A"), (1, "B")]
    rc = "RevenueFromContractWithCustomerExcludingAssessedTax"
    facts = [(0, "Revenues", "2025-12-31", 110.0),
             (0, "Revenues", "2024-12-31", 100.0),
             (0, rc, "2025-12-31", 500.0),
             (0, rc, "2024-12-31", 100.0),
             (1, rc, "2025-12-31", 120.0),
             (1, rc, "2024-12-31", 100.0)]
    fund = _fund_conn(companies, facts)
    yoy = extract._revenue_yoy(fund)
    assert abs(yoy[0] - 0.10) < 1e-9
    assert abs(yoy[1] - 0.20) < 1e-9


def test_revenue_yoy_dedupes_restated_facts_by_filing_recency():
    # Latest period 2025-12-31 was filed twice: the original 10-K (filed
    # 2026-02-01) reported 200.0, then a 10-K/A restatement (filed
    # 2026-03-01) reported 110.0. The later-filed row must win even though
    # it is numerically smaller -- sorted(series, reverse=True) would
    # otherwise let the larger restated value win the (period_end, value)
    # tuple tie-break regardless of filing recency.
    companies = [(0, "A")]
    fund = _fund_conn(companies, [])
    fund_db.write_facts(fund, 0, [
        {"tag": "Revenues", "period_end": "2025-12-31", "value": 200.0,
         "form": "10-K", "filed": "2026-02-01"},
        {"tag": "Revenues", "period_end": "2025-12-31", "value": 110.0,
         "form": "10-K/A", "filed": "2026-03-01"},
        {"tag": "Revenues", "period_end": "2024-12-31", "value": 100.0,
         "form": "10-K", "filed": "2025-02-01"},
    ])
    yoy = extract._revenue_yoy(fund)
    assert yoy[0] == pytest.approx(0.10)


def test_percent_rank_matches_sql_semantics():
    assert extract._percent_rank({"a": 1.0}) == {"a": 0.0}
    ranks = extract._percent_rank({"a": 1.0, "b": 2.0, "c": 2.0, "d": 3.0})
    assert ranks["a"] == 0.0
    assert ranks["b"] == ranks["c"] == 1 / 3
    assert ranks["d"] == 1.0


# Regime dial tests

def _fred_conn(series_obs):
    """series_obs: dict series_id -> list of (date, value)."""
    conn = fred_db.connect(":memory:")
    fred_db.ensure_schema(conn)
    for sid, obs in series_obs.items():
        fred_db.upsert_series(conn, [{"id": sid, "title": sid,
                                      "theme": "test"}], NOW)
        fred_db.write_observations(
            conn, sid, [{"date": d, "value": v} for d, v in obs])
    fred_db.write_snapshot(conn, NOW, len(series_obs), 1)
    return conn


def test_regime_late_cycle_halves_exposure():
    conn = _fred_conn({
        "CPIAUCSL": [("2025-06-01", 100.0), ("2026-06-01", 104.0)],  # 4.0% YoY
        "UNRATE": [("2026-06-01", 4.0)],
        "T10Y2Y": [("2026-06-30", 0.5)],           # not inverted
        "BAMLH0A0HYM2": [("2026-06-30", 3.5)],
    })
    r = extract.extract_regime(conn)
    assert abs(r["cpi_yoy"] - 4.0) < 1e-9
    assert r["unrate"] == 4.0
    assert r["yield_curve_inverted"] == 0
    assert r["late_cycle"] == 1
    assert r["exposure_scalar"] == 0.5
    assert r["regime_incomplete"] == 0
    assert r["as_of_date"] == "2026-06-30"


def test_regime_inversion_alone_triggers_risk_off():
    conn = _fred_conn({
        "CPIAUCSL": [("2025-06-01", 100.0), ("2026-06-01", 102.0)],  # 2.0%
        "UNRATE": [("2026-06-01", 4.0)],
        "T10Y2Y": [("2026-06-30", -0.2)],          # inverted
        "BAMLH0A0HYM2": [("2026-06-30", 3.5)],
    })
    r = extract.extract_regime(conn)
    assert r["late_cycle"] == 0
    assert r["yield_curve_inverted"] == 1
    assert r["exposure_scalar"] == 0.5


def test_regime_benign_full_exposure():
    conn = _fred_conn({
        "CPIAUCSL": [("2025-06-01", 100.0), ("2026-06-01", 102.0)],
        "UNRATE": [("2026-06-01", 5.0)],
        "T10Y2Y": [("2026-06-30", 0.5)],
        "BAMLH0A0HYM2": [("2026-06-30", 3.5)],
    })
    r = extract.extract_regime(conn)
    assert r["late_cycle"] == 0
    assert r["exposure_scalar"] == 1.0
    assert r["regime_incomplete"] == 0


def test_regime_missing_inputs_flags_incomplete_defaults_full():
    conn = _fred_conn({"UNRATE": [("2026-06-01", 4.0)]})  # CPI/curve missing
    r = extract.extract_regime(conn)
    assert r["cpi_yoy"] is None
    assert r["yield_curve_inverted"] is None
    assert r["regime_incomplete"] == 1
    assert r["exposure_scalar"] == 1.0


def test_regime_known_trigger_fires_even_when_incomplete():
    conn = _fred_conn({"T10Y2Y": [("2026-06-30", -0.2)]})  # only the curve
    r = extract.extract_regime(conn)
    assert r["regime_incomplete"] == 1
    assert r["exposure_scalar"] == 0.5  # inversion is known -> risk-off anyway
