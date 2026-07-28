import sqlite3
from pathlib import Path

import pytest

from sources.combiners.composite import catalog, fetch

KNOWN_DBS = {
    "fred.db",
    "cboe_stats.db",
    "fomc.db",
    "econ_calendar.db",
    "market_calendar.db",
    "nyfed.db",
    "treasury.db",
    "cftc.db",
    "eia.db",
    "usda.db",
    "short_interest.db",
    "short_volume.db",
    "ftd.db",
    "reddit.db",
    "stocks.db",
    "edgar.db",
    "earnings.db",
    "portfolio.db",
    "options.db",
}
ASSET_CLASSES = {"ags", "rates", "energy", "softs", "metals", "fx", "equity_index"}


def test_signal_ids_unique_and_wellformed():
    ids = [s["signal_id"] for s in catalog.SIGNALS]
    assert len(ids) == len(set(ids))
    for s in catalog.SIGNALS:
        assert s["grain"] in ("market", "asset_class", "ticker")
        assert s["db"] in KNOWN_DBS
        assert s["staleness_budget_days"] >= 0
        assert "src." in s["sql"]  # reads the attached alias
        assert "calendar_now" not in s["sql"]  # one-clock rule


def test_regime_fields_reference_market_signals():
    market_ids = {s["signal_id"] for s in catalog.SIGNALS if s["grain"] == "market"}
    assert set(catalog.REGIME_FIELDS) <= market_ids


def test_crosswalk_classes_are_known():
    assert set(catalog.CROSSWALK) <= ASSET_CLASSES
    assert "fx" not in catalog.CROSSWALK  # direction incoherent; excluded


def test_select_ids():
    ids = [s["signal_id"] for s in catalog.SIGNALS]
    assert [s["signal_id"] for s in catalog.select_ids(None, None, None)] == ids
    only = catalog.select_ids([ids[0]], None, None)
    assert [s["signal_id"] for s in only] == [ids[0]]
    excl = catalog.select_ids(None, [ids[0]], None)
    assert ids[0] not in [s["signal_id"] for s in excl]
    with pytest.raises(ValueError):
        catalog.select_ids(["nope"], None, None)


# db filename -> the source's own db module, so ensure_schema builds the
# real (empty) schema each catalog SQL runs against. Any rename of a view,
# table, or column referenced by a catalog SQL fails this test loudly.
DB_MODULES = {
    "fred.db": "sources.screeners.fred_screener.db",
    "cboe_stats.db": "sources.screeners.cboe_stats.db",
    "fomc.db": "sources.monitors.fomc_calendar.db",
    "econ_calendar.db": "sources.monitors.econ_calendar.db",
    "market_calendar.db": "sources.monitors.market_calendar.db",
    "nyfed.db": "sources.screeners.nyfed_screener.db",
    "treasury.db": "sources.screeners.treasury_screener.db",
    "cftc.db": "sources.screeners.cftc_screener.db",
    "eia.db": "sources.screeners.eia_screener.db",
    "usda.db": "sources.screeners.usda_screener.db",
    "short_interest.db": "sources.screeners.finra_short_interest.db",
    "short_volume.db": "sources.screeners.finra_short_volume.db",
    "ftd.db": "sources.screeners.ftd_screener.db",
    "reddit.db": "sources.screeners.reddit_screener.db",
    "stocks.db": "sources.screeners.stock_analysis_screener.db",
    "edgar.db": "sources.screeners.edgar_screener.db",
    "earnings.db": "sources.monitors.earnings_calendar.db",
    "portfolio.db": "sources.screeners.portfolio_screener.db",
    "options.db": "sources.screeners.cboe_options.db",
}

# stocks.db's metrics table only gets its data-point columns via
# ensure_schema(conn, columns) — supply the ones stocks_rsi's SQL references.
_STOCKS_COLUMNS = {
    "rsi": "REAL",
    "dollarVolume": "REAL",
    "priceDate": "TEXT",
    # stocks_rsi collapses share classes of one company to a single opinion.
    "isin": "TEXT",
    "isPrimaryListing": "TEXT",
    # sa_fscore / sa_fcf_yield annotations.
    "fScore": "REAL",
    "fcfYield": "REAL",
    "marketCap": "REAL",
}


def _build_source_db(db_file: str, path: str) -> None:
    import importlib

    mod = importlib.import_module(DB_MODULES[db_file])
    conn = mod.connect(path)
    if db_file == "stocks.db":
        mod.ensure_schema(conn, _STOCKS_COLUMNS)
    else:
        mod.ensure_schema(conn)
    conn.close()


@pytest.mark.parametrize("signal", catalog.SIGNALS, ids=lambda s: s["signal_id"])
def test_extraction_sql_executes_against_source_schema(signal, tmp_path):
    """Every catalog SQL must run against its source's real (empty) schema —
    fails loudly here if a source view/column is renamed."""
    assert signal["db"] in DB_MODULES, f"no DB_MODULES entry for {signal['db']}"
    path = str(tmp_path / signal["db"])
    _build_source_db(signal["db"], path)

    conn = sqlite3.connect(":memory:", uri=True)
    try:
        fetch.attach_ro(conn, path)
        rows = fetch.extract(conn, signal, today="2026-07-06")
    finally:
        conn.close()

    assert isinstance(rows, list)


def test_fred_score_cases_are_hoisted_constants():
    from sources.combiners.composite.catalog import (
        FRED_CURVE_SCORE,
        FRED_HY_SPREAD_SCORE,
        SIGNALS,
    )

    by_id = {s["signal_id"]: s for s in SIGNALS}
    assert FRED_CURVE_SCORE in by_id["fred_curve"]["sql"]
    assert FRED_HY_SPREAD_SCORE in by_id["fred_hy_spread"]["sql"]


def test_dff_score_cases_are_hoisted_constants():
    from sources.combiners.composite.catalog import (
        FRED_DFF_20D_CHANGE_SCORE,
        FRED_DFF_REGIME_SCORE,
        SIGNALS,
    )

    by_id = {s["signal_id"]: s for s in SIGNALS}
    assert FRED_DFF_20D_CHANGE_SCORE in by_id["fred_dff_chg20"]["sql"]
    assert FRED_DFF_REGIME_SCORE in by_id["fred_dff_regime"]["sql"]
    # separate constants: different windows, independently retunable
    assert FRED_DFF_20D_CHANGE_SCORE != FRED_DFF_REGIME_SCORE


def test_dff_signals_are_market_grain_and_not_regime_inputs():
    """Informational by construction: market grain never votes on tickers,
    and the DFF ids stay out of REGIME_FIELDS until a measured calibration
    pass promotes them."""
    by_id = {s["signal_id"]: s for s in catalog.SIGNALS}
    for sid in ("fred_dff_chg20", "fred_dff_regime"):
        assert by_id[sid]["grain"] == "market"
        assert sid not in catalog.REGIME_FIELDS
        assert by_id[sid]["db"] == "fred.db"


def test_dff_dead_zones_are_policy_quantum_fractions():
    """The cutoffs are structural (policy moves are quantized at 25bp):
    half an increment for the 20d view — any real move clears it, the
    measured 1-3bp month-end jitter never does — and one full increment
    for the year view. NOT return-calibrated thresholds."""
    from sources.combiners.composite.catalog import (
        FRED_DFF_20D_CHANGE_SCORE,
        FRED_DFF_REGIME_SCORE,
    )

    assert "0.125" in FRED_DFF_20D_CHANGE_SCORE and "chg20" in FRED_DFF_20D_CHANGE_SCORE
    assert "0.25" in FRED_DFF_REGIME_SCORE and "chg1y" in FRED_DFF_REGIME_SCORE


def _dff_extract(tmp_path, rows):
    path = str(tmp_path / "fred.db")
    _build_source_db("fred.db", path)
    src = sqlite3.connect(path)
    src.executemany(
        "INSERT INTO observations (series_id, date, value) VALUES ('DFF', ?, ?)",
        rows,
    )
    src.commit()
    src.close()
    conn = sqlite3.connect(":memory:", uri=True)
    try:
        fetch.attach_ro(conn, path)
        by_id = {s["signal_id"]: s for s in catalog.SIGNALS}
        out = {}
        for sid in ("fred_dff_chg20", "fred_dff_regime"):
            out[sid] = fetch.extract(conn, by_id[sid], today="2026-07-06")
    finally:
        conn.close()
    return out


def test_dff_scores_a_cut_as_bullish_both_windows(tmp_path):
    # 25bp cut visible in both the 20d and the 1y window
    out = _dff_extract(
        tmp_path,
        [("2025-07-06", 5.00), ("2026-06-16", 5.00), ("2026-07-06", 4.75)],
    )
    (row,) = out["fred_dff_chg20"]
    assert (row["entity"], row["score"], row["obs_date"]) == ("*", 1, "2026-07-06")
    assert abs(row["raw_value"] - (-0.25)) < 1e-9
    (row_y,) = out["fred_dff_regime"]
    assert row_y["score"] == 1 and abs(row_y["raw_value"] - (-0.25)) < 1e-9


def test_dff_scores_a_hold_as_neutral_and_a_hike_as_bearish(tmp_path):
    # flat rate -> both 0; sub-quantum jitter (+3bp over 20d) -> still 0
    out = _dff_extract(
        tmp_path,
        [("2025-07-06", 4.50), ("2026-06-16", 4.47), ("2026-07-06", 4.50)],
    )
    assert out["fred_dff_chg20"][0]["score"] == 0
    assert out["fred_dff_regime"][0]["score"] == 0
    # hiking: +50bp over the year, +25bp in the window -> -1 / -1
    out = _dff_extract(
        tmp_path,
        [("2025-07-07", 4.00), ("2026-06-17", 4.25), ("2026-07-07", 4.50)],
    )
    assert out["fred_dff_chg20"][0]["score"] == -1
    assert out["fred_dff_regime"][0]["score"] == -1


def test_cboe_score_cases_are_hoisted_constants():
    # Hoisted so the backtest combiner replays the IDENTICAL flag expression;
    # rendered composite SQL must be unchanged (constant interpolated back in).
    from sources.combiners.composite.catalog import (
        CBOE_VIX_BACKWARDATION_SCORE,
        CBOE_VIX_SCORE,
        SIGNALS,
    )

    by_id = {s["signal_id"]: s for s in SIGNALS}
    assert CBOE_VIX_SCORE in by_id["cboe_vix"]["sql"]
    assert CBOE_VIX_BACKWARDATION_SCORE in by_id["cboe_vix_backwardation"]["sql"]
    # the CASEs still reference their source columns verbatim
    assert "close >= 30" in CBOE_VIX_SCORE
    assert "close > vix3m" in CBOE_VIX_BACKWARDATION_SCORE


def test_liquidity_score_cases_are_hoisted_constants():
    from sources.combiners.composite.catalog import (
        NYFED_RRP_SCORE,
        SIGNALS,
        TSY_TGA_SCORE,
    )

    by_id = {s["signal_id"]: s for s in SIGNALS}
    assert NYFED_RRP_SCORE in by_id["nyfed_rrp"]["sql"]
    assert TSY_TGA_SCORE in by_id["tsy_tga"]["sql"]
    assert "change_vs_prior" in NYFED_RRP_SCORE
    assert "wow_change" in TSY_TGA_SCORE


def test_cboe_equity_pcr_score_case_is_hoisted_constant():
    from sources.combiners.composite.catalog import CBOE_EQUITY_PCR_SCORE, SIGNALS

    by_id = {s["signal_id"]: s for s in SIGNALS}
    assert CBOE_EQUITY_PCR_SCORE in by_id["cboe_equity_pcr"]["sql"]
    assert "pctile >= 90" in CBOE_EQUITY_PCR_SCORE


def test_eia_score_cases_are_separate_hoisted_constants():
    """Crude and natgas must be DIFFERENT constants, even while the two
    expressions are identical today. They shared one until 2026-07-09, which
    made either impossible to retune without silently retuning the other.

    Asserted on the source, not on object identity: Python interns equal string
    literals, so `EIA_CRUDE is not EIA_NATGAS` is False even when they are two
    genuinely independent assignments. The invariant is syntactic — each name
    binds its own literal, neither aliases the other."""
    import ast

    from sources.combiners.composite.catalog import (
        EIA_CRUDE_CHANGE_SCORE,
        EIA_NATGAS_CHANGE_SCORE,
        SIGNALS,
    )

    by_id = {s["signal_id"]: s for s in SIGNALS}
    assert EIA_CRUDE_CHANGE_SCORE in by_id["eia_crude_stocks"]["sql"]
    assert EIA_NATGAS_CHANGE_SCORE in by_id["eia_natgas_storage"]["sql"]
    assert "change_pct <= -2.0" in EIA_CRUDE_CHANGE_SCORE

    src = Path(catalog.__file__).read_text()
    assigned = {}
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Name) and t.id.startswith("EIA_"):
                assigned[t.id] = node.value

    assert set(assigned) == {"EIA_CRUDE_CHANGE_SCORE", "EIA_NATGAS_CHANGE_SCORE"}
    for name, value in assigned.items():
        assert isinstance(value, ast.Constant), f"{name} must bind its own literal"
    # ...and neither is an alias of the other (that would re-couple them).
    assert not any(isinstance(v, ast.Name) for v in assigned.values())


def test_backtest_replays_each_eia_signal_with_its_own_constant():
    """The replay must stay matched to composite per signal — that is what makes
    "flags cannot drift" true after the split. Asserted syntactically for the
    same interning reason."""
    import ast

    from sources.combiners.backtest import catalog as bt

    src = Path(bt.__file__).read_text()
    want = {
        "eia_crude_stocks": "EIA_CRUDE_CHANGE_SCORE",
        "eia_natgas_storage": "EIA_NATGAS_CHANGE_SCORE",
    }
    seen = {}
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Dict):
            continue
        keys = {k.value for k in node.keys if isinstance(k, ast.Constant)}
        if "signal_id" not in keys or "score_case" not in keys:
            continue
        d = {
            k.value: v
            for k, v in zip(node.keys, node.values, strict=True)
            if isinstance(k, ast.Constant)
        }
        sig = d["signal_id"]
        if isinstance(sig, ast.Constant) and sig.value in want:
            assert isinstance(d["score_case"], ast.Name)
            seen[sig.value] = d["score_case"].id
    assert seen == want


# --- earnings_imminent: per-ticker event gate (plan 002) --------------------


def _earnings_signal():
    return next(s for s in catalog.SIGNALS if s["signal_id"] == "earnings_imminent")


def test_earnings_imminent_is_a_ticker_grain_zero_score_gate():
    s = _earnings_signal()
    assert s["grain"] == "ticker"
    assert s["db"] == "earnings.db"
    # Forward-looking: obs_date is :today by construction, so nothing to age.
    assert s["staleness_budget_days"] == 0
    # score literal is 0 -> the row annotates, never votes.
    assert "0, :today" in s["sql"]


def test_earnings_imminent_not_in_regime_fields():
    """REGIME_FIELDS is market-grain only; a ticker signal there would try to
    write a per-symbol value into the single market_regime row."""
    assert "earnings_imminent" not in catalog.REGIME_FIELDS


def test_earnings_imminent_sql_obeys_the_one_clock_rule():
    """earnings.db's v_imminent_earnings filters on its own calendar_now
    singleton — a different clock from composite's bound :today."""
    sql = _earnings_signal()["sql"]
    for forbidden in ("v_imminent", "v_upcoming", "calendar_now", "v_asof"):
        assert forbidden not in sql, forbidden


def test_no_signal_reads_a_calendar_dependent_view():
    """The one-clock rule, enforced across the whole catalog, not just the new
    signal — this is the invariant stated in catalog.py's module docstring."""
    for s in catalog.SIGNALS:
        for forbidden in ("v_imminent", "v_upcoming", "calendar_now", "v_asof"):
            assert forbidden not in s["sql"], f"{s['signal_id']} reads {forbidden}"


def test_earnings_imminent_selectable_by_select_ids():
    only = catalog.select_ids(["earnings_imminent"], None, None)
    assert [s["signal_id"] for s in only] == ["earnings_imminent"]
    excl = catalog.select_ids(None, ["earnings_imminent"], None)
    assert "earnings_imminent" not in [s["signal_id"] for s in excl]


def test_earnings_imminent_emits_exactly_one_row_per_ticker(tmp_path):
    """Composite's signal_values PK is (snapshot_id, signal_id, entity) and the
    writer is INSERT OR IGNORE, so a duplicate entity is silently swallowed and
    whichever row the scan yields FIRST wins. That makes a run-level assertion
    unable to see a missing GROUP BY. Assert on the extraction itself, where a
    duplicate is still visible: one forward row per ticker, at the NEAREST date.

    The fixture stores the far date first so a missing MIN/GROUP BY cannot pass
    by accident."""
    import importlib

    mod = importlib.import_module("sources.monitors.earnings_calendar.db")
    path = str(tmp_path / "earnings.db")
    conn = mod.connect(path)
    mod.ensure_schema(conn)
    conn.executemany(
        "INSERT INTO events (event_type, event_date, subtype, source, fetched_at)"
        " VALUES ('earnings', ?, ?, 'test', '2026-07-06T00:00:00+00:00')",
        [("2026-07-12", "AAPL"), ("2026-07-09", "AAPL"), ("2026-07-10", "MSFT")],
    )
    conn.commit()
    conn.close()

    c = sqlite3.connect(":memory:", uri=True)
    try:
        fetch.attach_ro(c, path)
        rows = fetch.extract(c, _earnings_signal(), today="2026-07-07")
    finally:
        c.close()

    entities = [r["entity"] for r in rows]
    assert entities == sorted(set(entities)), f"duplicate entity emitted: {entities}"
    by = {r["entity"]: r["raw_value"] for r in rows}
    assert by == {"AAPL": 2, "MSFT": 3}, "must report days to the NEAREST print"
    assert all(r["score"] == 0 for r in rows), "gate must never vote"


# --- options annotations: per-ticker options context (plan 001) -------------

OPTIONS_SIGNAL_IDS = ("options_iv30", "options_pcr")


def _options_signals():
    by_id = {s["signal_id"]: s for s in catalog.SIGNALS}
    return [by_id[sid] for sid in OPTIONS_SIGNAL_IDS]


def test_options_signals_are_ticker_grain_annotations():
    for s in _options_signals():
        assert s["grain"] == "ticker"
        assert s["db"] == "options.db"
        # underlying_daily gains one row per trading day; 4 covers a long weekend.
        assert s["staleness_budget_days"] == 4


def test_options_signals_not_in_regime_fields():
    """Ticker-grain context, not market regime — the market-wide options read
    already exists as cboe_equity_pcr."""
    for sid in OPTIONS_SIGNAL_IDS:
        assert sid not in catalog.REGIME_FIELDS


def test_options_signals_selectable_by_select_ids():
    only = catalog.select_ids(list(OPTIONS_SIGNAL_IDS), None, None)
    assert [s["signal_id"] for s in only] == list(OPTIONS_SIGNAL_IDS)
    excl = catalog.select_ids(None, list(OPTIONS_SIGNAL_IDS), None)
    assert not set(OPTIONS_SIGNAL_IDS) & {s["signal_id"] for s in excl}


def _options_fixture(tmp_path):
    """options.db with: AAPL on two dates (the latest must win), SPX and VIX
    (index products — must be excluded), and BAC with a NULL iv30 (must appear
    in the PCR annotation but not the IV one)."""
    import importlib

    mod = importlib.import_module("sources.screeners.cboe_options.db")
    path = str(tmp_path / "options.db")
    conn = mod.connect(path)
    mod.ensure_schema(conn)
    conn.executemany(
        "INSERT INTO underlyings (symbol, is_index) VALUES (?, ?)",
        [("AAPL", 0), ("SPX", 1), ("VIX", 1), ("BAC", 0)],
    )
    conn.executemany(
        "INSERT INTO underlying_daily (snapshot_date, underlying,"
        " underlying_price, iv30, total_call_volume, total_put_volume,"
        " put_call_volume_ratio) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            # stale AAPL row first so a missing latest-per-underlying pick shows
            ("2026-07-17", "AAPL", 210.0, 35.0, 1000, 900, 0.9),
            ("2026-07-20", "AAPL", 212.0, 29.6, 1200, 780, 0.65),
            ("2026-07-20", "SPX", 6300.0, 13.5, 500, 615, 1.23),
            ("2026-07-20", "VIX", 16.5, 83.1, 300, 153, 0.51),
            ("2026-07-20", "BAC", 48.0, None, 400, 392, 0.98),
        ],
    )
    conn.commit()
    conn.close()
    return path


def test_options_annotations_emit_one_zero_score_row_per_tradeable_name(tmp_path):
    path = _options_fixture(tmp_path)
    c = sqlite3.connect(":memory:", uri=True)
    try:
        fetch.attach_ro(c, path)
        iv, pcr = (fetch.extract(c, s, today="2026-07-21") for s in _options_signals())
    finally:
        c.close()

    assert {r["entity"]: r["raw_value"] for r in iv} == {"AAPL": 29.6}
    assert {r["entity"]: r["raw_value"] for r in pcr} == {"AAPL": 0.65, "BAC": 0.98}
    for r in iv + pcr:
        assert r["score"] == 0, "annotation must never vote"
        assert r["obs_date"] == "2026-07-20"
        assert r["staleness_days"] == 1


def _stocks_fixture(tmp_path, rows):
    """A stocks.db holding one snapshot of `rows`, each a dict of column ->
    value. Built through the screener's own db module so a schema rename
    breaks this test rather than silently changing what composite reads."""
    import importlib

    mod = importlib.import_module(DB_MODULES["stocks.db"])
    path = str(tmp_path / "stocks.db")
    conn = mod.connect(path)
    mod.ensure_schema(conn, _STOCKS_COLUMNS)
    conn.execute(
        "INSERT INTO snapshots (id, captured_at, universe_count, source)"
        " VALUES (1, '2026-07-20T11:00:00+00:00', ?, 'test')",
        (len(rows),),
    )
    for r in rows:
        cols = ", ".join(f'"{k}"' for k in r)
        marks = ", ".join("?" * len(r))
        conn.execute(
            f"INSERT INTO metrics (snapshot_id, {cols}) VALUES (1, {marks})",
            tuple(r.values()),
        )
    conn.commit()
    conn.close()
    return path


def _extract_stocks_rsi(path):
    by_id = {s["signal_id"]: s for s in catalog.SIGNALS}
    c = sqlite3.connect(":memory:", uri=True)
    try:
        fetch.attach_ro(c, path)
        return fetch.extract(c, by_id["stocks_rsi"], today="2026-07-20")
    finally:
        c.close()


def test_stocks_rsi_emits_one_row_per_company_not_per_share_class(tmp_path):
    """UHAL/UHAL.B are one company with two listed classes, and BOTH cleared
    the liquidity floor on 2026-07-26 — so composite formed two independent
    opinions about one business. The CUSIP issuer number collapses them."""
    path = _stocks_fixture(
        tmp_path,
        [
            dict(
                symbol="UHAL",
                isin="US0235861004",
                isPrimaryListing="1",
                rsi=28.0,
                dollarVolume=40e6,
                priceDate="2026-07-20",
            ),
            dict(
                symbol="UHAL.B",
                isin="US0235862003",
                isPrimaryListing="0",
                rsi=27.5,
                dollarVolume=20e6,
                priceDate="2026-07-20",
            ),
        ],
    )
    assert [r["entity"] for r in _extract_stocks_rsi(path)] == ["UHAL"]


def test_stocks_rsi_keeps_a_liquid_adr_with_no_us_sibling(tmp_path):
    """isPrimaryListing='1' would have dropped 11 rows on 2026-07-26, ten of
    which were single-listing names with no duplicate to collapse."""
    path = _stocks_fixture(
        tmp_path,
        [
            dict(
                symbol="SAP",
                isin="US8030542042",
                isPrimaryListing="0",
                rsi=29.0,
                dollarVolume=645e6,
                priceDate="2026-07-20",
            ),
        ],
    )
    assert [r["entity"] for r in _extract_stocks_rsi(path)] == ["SAP"]


def test_stocks_rsi_does_not_merge_foreign_isin_neighbours(tmp_path):
    """Non-US agencies assign ISIN blocks sequentially across issuers: IL|001082
    covers 11 unrelated Israeli firms. Keying on a foreign prefix would delete
    real names, so foreign rows key on their own symbol."""
    path = _stocks_fixture(
        tmp_path,
        [
            dict(
                symbol="CHKP",
                isin="IL0010824113",
                isPrimaryListing="0",
                rsi=29.0,
                dollarVolume=50e6,
                priceDate="2026-07-20",
            ),
            dict(
                symbol="TSEM",
                isin="IL0010823724",
                isPrimaryListing="0",
                rsi=28.0,
                dollarVolume=40e6,
                priceDate="2026-07-20",
            ),
        ],
    )
    assert sorted(r["entity"] for r in _extract_stocks_rsi(path)) == ["CHKP", "TSEM"]


def _fundamental_signals():
    by_id = {s["signal_id"]: s for s in catalog.SIGNALS}
    return by_id["sa_fscore"], by_id["sa_fcf_yield"]


def test_fundamental_annotations_are_informational_and_never_vote(tmp_path):
    """composite has no business-quality read at all: every ticker signal is
    microstructure, so its universe is a microcap dislocation scanner. These two
    add the missing dimension as ANNOTATIONS ONLY — deferred from voting exactly
    like options_iv30/options_pcr, pending a measured calibration pass. Five
    correlated quality votes would be one fact counted five times (measured
    2026-07-26: roic x fcfYield rho=0.585, roic x sharesYoY rho=-0.513)."""
    from sources.combiners.composite import db as cdb

    path = _stocks_fixture(
        tmp_path,
        [
            dict(
                symbol="ADBE",
                isin="US00724F1012",
                isPrimaryListing="1",
                fScore=7.0,
                fcfYield=12.2,
                marketCap=84e9,
                dollarVolume=500e6,
                priceDate="2026-07-20",
            ),
        ],
    )
    c = sqlite3.connect(":memory:", uri=True)
    try:
        fetch.attach_ro(c, path)
        rows = [r for s in _fundamental_signals() for r in fetch.extract(c, s, today="2026-07-20")]
    finally:
        c.close()

    assert {r["entity"] for r in rows} == {"ADBE"}
    assert {r["raw_value"] for r in rows} == {7.0, 12.2}
    for r in rows:
        assert r["score"] == 0, "annotation must never vote"
        assert r["signal_id"] in cdb.INFORMATIONAL_SIGNALS


def test_fundamental_annotations_skip_illiquid_and_duplicate_classes(tmp_path):
    """Same universe discipline as stocks_rsi: one row per company, liquid only.
    Otherwise the calibration history accumulates junk it can never learn from."""
    path = _stocks_fixture(
        tmp_path,
        [
            dict(
                symbol="UHAL",
                isin="US0235861004",
                isPrimaryListing="1",
                fScore=6.0,
                fcfYield=5.0,
                marketCap=20e9,
                dollarVolume=40e6,
                priceDate="2026-07-20",
            ),
            dict(
                symbol="UHAL.B",
                isin="US0235862003",
                isPrimaryListing="0",
                fScore=6.0,
                fcfYield=5.0,
                marketCap=20e9,
                dollarVolume=20e6,
                priceDate="2026-07-20",
            ),
            dict(
                symbol="THIN",
                isin="US9999999999",
                isPrimaryListing="1",
                fScore=8.0,
                fcfYield=9.0,
                marketCap=20e9,
                dollarVolume=20e3,
                priceDate="2026-07-20",
            ),
        ],
    )
    c = sqlite3.connect(":memory:", uri=True)
    try:
        fetch.attach_ro(c, path)
        fscore, _ = _fundamental_signals()
        rows = fetch.extract(c, fscore, today="2026-07-20")
    finally:
        c.close()

    assert [r["entity"] for r in rows] == ["UHAL"]


def test_stocks_rsi_dedup_keeps_the_liquid_line_not_the_extreme_one(tmp_path):
    """Pins the tie-break the previous dedup test could not see: its two rows
    shared a score bucket, so it proved only that ONE row survived, not WHICH.

    When both classes clear the extreme bar, the better-price-discovery line
    wins even though the other reads more extreme — a thin class's extreme is
    more likely noise. Bounded by the data: on 2026-07-26 exactly one company
    had both classes extreme (same sign, same bucket) and the largest spread
    between any company's classes was 2.0 RSI points, so this can cost one
    score notch and can never flip the sign."""
    path = _stocks_fixture(
        tmp_path,
        [
            dict(
                symbol="AAA",
                isin="US0235861004",
                isPrimaryListing="0",
                rsi=15.0,
                dollarVolume=15e6,
                priceDate="2026-07-20",
            ),
            dict(
                symbol="AAB",
                isin="US0235862003",
                isPrimaryListing="0",
                rsi=29.0,
                dollarVolume=100e6,
                priceDate="2026-07-20",
            ),
        ],
    )
    rows = _extract_stocks_rsi(path)
    assert [r["entity"] for r in rows] == ["AAB"]
    assert rows[0]["score"] == 1, "the surviving line's own reading is scored, not the dropped one"


def test_ftd_persistent_is_demoted_to_annotation(tmp_path):
    """Measured 2026-07-27 against the universe base rate: -7.9pp at 5 days
    (n_bench 1149) and -9.7pp at 10 (n=415) — the worst signal in the catalog,
    and the one supplying 2 of the 3 points on every flag composite produced.
    Its contrarian thesis ("persistent fails-to-deliver = squeeze fuel =
    bullish") is not weak but BACKWARDS: names bleeding fails kept bleeding.

    Demoted, not deleted. The rows keep accruing as annotations so the claim
    can be re-tested once horizon=10 spans a non-risk_on regime — every
    composite snapshot since 2026-07-06 has classified risk_on, so ~1.6
    independent windows of one market state is all the evidence there is."""
    from sources.combiners.composite import db as cdb

    path = _stocks_fixture(tmp_path, [])  # unused; ftd reads its own DB
    del path
    by_id = {s["signal_id"]: s for s in catalog.SIGNALS}
    sql = by_id["ftd_persistent"]["sql"]
    assert "ftd_persistent" in cdb.INFORMATIONAL_SIGNALS
    assert "THEN 2" not in sql and "ELSE 1" not in sql, "must no longer vote"


def test_ftd_persistent_still_emits_its_raw_value(tmp_path):
    """The streak length is still recorded — demotion must not throw away the
    evidence needed to re-grade it later."""
    import importlib

    mod = importlib.import_module("sources.screeners.ftd_screener.db")
    p = str(tmp_path / "ftd.db")
    conn = mod.connect(p)
    mod.ensure_schema(conn)
    conn.close()
    by_id = {s["signal_id"]: s for s in catalog.SIGNALS}
    c = sqlite3.connect(":memory:", uri=True)
    try:
        fetch.attach_ro(c, p)
        rows = fetch.extract(c, by_id["ftd_persistent"], today="2026-07-27")
    finally:
        c.close()
    assert isinstance(rows, list)
    assert "streak_days" in by_id["ftd_persistent"]["sql"]
