"""Shared fixtures for the dashboard test suite.

The populated-fixture web below exists so `tests/test_dashboard_data.py`
and the other dashboard test modules can `from conftest import ...` one
source of truth instead of re-diverging copies. Fixtures build real
per-combiner/screener schemas via each source's own `ensure_schema` (never
hand-rolled DDL) — a combiner view's shape change breaks loudly here instead
of silently blanking a section.

`NOW` stays `"2026-07-08T21:13:00+00:00"` (Phoenix July 8) — the fixture's
embedded dates (verdicts.log due/upcoming split, stocks `priceDate`, snapshot
`obs_date`s) are calibrated to that Phoenix date; silently shifting it flips
due/upcoming semantics. `ROLLOVER_NOW` is a second constant, Phoenix July 7
(UTC July 8 04:13), for tests exercising the UTC-midnight-is-still-yesterday-
in-Phoenix date derivation.
"""

import sys
from pathlib import Path

import pytest

from sources.combiners.advisor import db as advisor_db
from sources.combiners.composite import catalog as composite_catalog
from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import db as scorer_db

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import health  # noqa: E402

NOW = "2026-07-08T21:13:00+00:00"
ROLLOVER_NOW = "2026-07-08T04:13:00+00:00"


class _NoJobsRunning:
    stdout = ""


@pytest.fixture(autouse=True)
def _no_real_launchctl(monkeypatch):
    """Global safety net: dashboard_lib.data's `health` section shells out to
    `launchctl list` via health.job_exit_codes/running_jobs. Any test that
    exercises data.export_data generically (e.g.
    test_empty_data_dir_degrades_not_crashes, which iterates every section
    id) would otherwise reach real launchctl -- violating the repo-wide
    no-shelling-in-tests invariant and making results machine-dependent.
    Autouse so no test can hit it by accident.

    `health.subprocess` IS the real stdlib `subprocess` module (Python
    caches it in sys.modules -- there's only ever one), so patching
    `health.subprocess.run` unconditionally would silently stub out every
    OTHER test's subprocess.run too, including the real bash-wrapper
    invocations in test_launchd_wrappers.py / test_config_ui_envfile.py
    (verified: doing that turned their real script runs into no-ops and
    broke them). The guard below only intercepts the exact
    `["launchctl", "list"]` call and passes every other command through to
    the real subprocess.run unchanged.

    Deliberately does NOT patch job_exit_codes/running_jobs directly either:
    those two functions parse real `launchctl list` output, and
    test_running_jobs_detects_running_via_pid_column_not_status_column
    (test_dashboard_health_build.py) monkeypatches health.subprocess.run
    itself and calls the real running_jobs() to exercise that parsing --
    patching the functions here would shadow that test's own patch and make
    it pass for the wrong reason. Tests that want specific
    exit-code/running-job scenarios monkeypatch job_exit_codes/running_jobs
    directly, which overrides this default regardless."""
    real_run = health.subprocess.run

    def _guarded_run(cmd, *args, **kwargs):
        if isinstance(cmd, list | tuple) and list(cmd[:2]) == ["launchctl", "list"]:
            return _NoJobsRunning()
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(health.subprocess, "run", _guarded_run)


def _make_fred_db(path):
    """Built through the fred screener's own ensure_schema/write_observations
    (not hand-rolled DDL), same rule as the combiner fixtures above — three
    regime-driver series with 24 daily observations each, enough for the
    macro-drivers section's 90-day sparklines and one-day delta."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from sources.screeners.fred_screener import db as fred_db

    conn = fred_db.connect(str(path))
    fred_db.ensure_schema(conn)
    for sid in ("T10Y2Y", "BAMLH0A0HYM2", "VIXCLS"):
        conn.execute("INSERT OR IGNORE INTO series (series_id) VALUES (?)", (sid,))
        fred_db.write_observations(
            conn, sid, [{"date": f"2026-07-{d:02d}", "value": 1.0 + d / 10} for d in range(1, 25)]
        )
    conn.commit()
    conn.close()


_REGIME_SIGNAL_VALUES = {
    "fred_curve": -0.42,
    "fred_hy_spread": 3.05,
    "cboe_vix_backwardation": 0,
    "cboe_equity_pcr": 96.4,  # already a 0-100 percentile, like production's raw_value
    "cboe_implied_corr": 41.0,
    "fomc_blackout": 0,
    "econ_imminent": 0,
    "mcal_days_to_opex": 8,
    "nyfed_rrp": -12.3,
    "tsy_tga": 4.1,
}


def _write_market_signals(conn, sid, vix):
    """One market-grain signal_values row per composite/catalog.py's
    REGIME_FIELDS key, so write_market_regime (the real production function)
    derives market_regime exactly as a live run would."""
    vals = dict(_REGIME_SIGNAL_VALUES, cboe_vix=vix)
    composite_db.write_signal_values(
        conn,
        sid,
        [
            dict(
                signal_id=signal_id,
                grain="market",
                entity="*",
                raw_value=raw,
                score=0,
                obs_date="2026-07-07",
                staleness_days=1.0,
            )
            for signal_id, raw in vals.items()
        ],
    )


def _build_composite_db(path, extra_tickers: list[dict] | None = None):
    """composite.db with 2 snapshots (>=2 points for the regime timeline
    sparkline) and, on the latest, one flagged ticker (FLAG1, held) and one
    non-flagged ticker (PLAIN1) — via real write_signal_values +
    write_ticker_scores/write_market_regime, not direct table pokes.

    `extra_tickers` (additive-only, default None keeps prior behavior
    identical) seeds further unflagged latest-snapshot rows for
    `test_scorecard_history_only_for_headline_rows` (dashboard export needs
    >15 unflagged rows to exercise its headline-only history size cap) —
    each item is `{"symbol": str, "score": int}`, written as one ticker-grain
    bullish/bearish signal (`total=1`, so it never crosses `v_flagged`'s
    `total >= 2` gate) on the same latest snapshot as FLAG1/PLAIN1."""
    conn = composite_db.connect(str(path))
    composite_db.ensure_schema(conn)

    older = composite_db.write_snapshot(conn, "2026-07-07T21:13:00+00:00", 10)
    _write_market_signals(conn, older, vix=18.4)
    composite_db.write_market_regime(conn, older, composite_catalog.REGIME_FIELDS)
    # One ticker-grain signal per symbol on the older snapshot too, so both
    # FLAG1 and PLAIN1 have >=2 v_score_history points — the scorecard's new
    # trend sparkline needs at least 2 points per symbol to render
    # (score_spark degrades to "no data" below that).
    composite_db.write_signal_values(
        conn,
        older,
        [
            dict(
                signal_id="sig_a",
                grain="ticker",
                entity=symbol,
                raw_value=1.0,
                score=1,
                obs_date="2026-07-06",
                staleness_days=1.5,
            )
            for symbol in ("FLAG1", "PLAIN1")
        ],
    )
    composite_db.write_ticker_scores(conn, older)

    latest = composite_db.write_snapshot(conn, NOW, 10)
    _write_market_signals(conn, latest, vix=16.1)
    composite_db.write_market_regime(conn, latest, composite_catalog.REGIME_FIELDS)

    # FLAG1: 4 bullish ticker signals -> score_sum 4, total 4 -> flagged
    # (|score_sum| >= 4 AND total >= 3).
    composite_db.write_signal_values(
        conn,
        latest,
        [
            dict(
                signal_id=f"sig_{c}",
                grain="ticker",
                entity="FLAG1",
                raw_value=1.0,
                score=1,
                obs_date="2026-07-07",
                staleness_days=0.5,
            )
            for c in "abcd"
        ],
    )
    # Mark FLAG1 as held (informational signal; never votes).
    composite_db.write_signal_values(
        conn,
        latest,
        [
            dict(
                signal_id="portfolio_holding",
                grain="ticker",
                entity="FLAG1",
                raw_value=None,
                score=0,
                obs_date="2026-07-07",
                staleness_days=0.0,
            )
        ],
    )
    # Two COT positioning tails on the latest snapshot (the cot-tails
    # section reads these; market grain never reaches ticker scoring, so
    # every other section is unaffected).
    composite_db.write_signal_values(
        conn,
        latest,
        [
            dict(
                signal_id="cftc_mm_tail",
                grain="market",
                entity="SUGAR NO. 11 - ICE FUTURES U.S.",
                raw_value=11.6,
                score=0,
                obs_date="2026-06-23",
                staleness_days=14.0,
            ),
            dict(
                signal_id="cftc_mm_tail",
                grain="market",
                entity="COTTON NO. 2 - ICE FUTURES U.S.",
                raw_value=91.2,
                score=0,
                obs_date="2026-06-23",
                staleness_days=14.0,
            ),
        ],
    )
    # PLAIN1: one bullish signal -> score_sum 1, total 1 -> not flagged.
    composite_db.write_signal_values(
        conn,
        latest,
        [
            dict(
                signal_id="sig_a",
                grain="ticker",
                entity="PLAIN1",
                raw_value=1.0,
                score=1,
                obs_date="2026-07-07",
                staleness_days=0.5,
            )
        ],
    )
    if extra_tickers:
        composite_db.write_signal_values(
            conn,
            latest,
            [
                dict(
                    signal_id="sig_extra",
                    grain="ticker",
                    entity=t["symbol"],
                    raw_value=1.0,
                    score=t["score"],
                    obs_date="2026-07-07",
                    staleness_days=0.5,
                )
                for t in extra_tickers
            ],
        )
    composite_db.write_ticker_scores(conn, latest)
    conn.commit()
    conn.close()


def _matured_signal_row(
    conn, signal_id, entity, score, fwd_return, bench_fwd_return, horizon=5, benchmark="SPY"
):
    """Insert one matured signal_outcomes row directly — mirrors
    tests/test_scorer_db_views.py's own `_signal_row` helper (the model this
    plan's fixture is asked to follow)."""
    conn.execute(
        "INSERT INTO signal_outcomes (composite_snapshot_id, composite_date,"
        " signal_id, entity, score, via_crosswalk, horizon, entry_date,"
        " entry_close, benchmark, bench_entry_close, exit_date, exit_close,"
        " fwd_return, bench_fwd_return, matured_at)"
        " VALUES (1, '2026-07-01', ?, ?, ?, 0, ?, '2026-07-02', 100.0, ?, 500.0,"
        " '2026-07-09', 104.0, ?, ?, ?)",
        (signal_id, entity, score, horizon, benchmark, fwd_return, bench_fwd_return, NOW),
    )


def _matured_ticker_row(
    conn, symbol, score_sum, total, bullish, bearish, fwd_return, bench_fwd_return, in_portfolio=0
):
    """Mirrors tests/test_scorer_db_views.py's own `_ticker_row` helper."""
    conn.execute(
        "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date,"
        " symbol, score_sum, total, bullish, bearish, in_portfolio, horizon,"
        " entry_date, entry_close, bench_entry_close, exit_date, exit_close,"
        " fwd_return, bench_fwd_return, matured_at)"
        " VALUES (1, '2026-07-01', ?, ?, ?, ?, ?, ?, 5, '2026-07-02', 100.0, 500.0,"
        " '2026-07-09', 104.0, ?, ?, ?)",
        (
            symbol,
            score_sum,
            total,
            bullish,
            bearish,
            in_portfolio,
            fwd_return,
            bench_fwd_return,
            NOW,
        ),
    )


def _build_scorer_db(path):
    """scorer.db with real rows behind every one of v_signal_efficacy,
    v_bucket_performance, v_human_filter, v_signal_recommendation,
    v_regime_performance, v_pending, v_basis_breaks, and (additive)
    v_candidate_efficacy — modeled on tests/test_scorer_db_views.py,
    tests/test_journal_db_views.py, and tests/test_scorer_candidates.py."""
    conn = scorer_db.connect(str(path))
    scorer_db.ensure_schema(conn)

    conn.execute(
        "INSERT INTO registered_snapshots (composite_snapshot_id, composite_date,"
        " entry_date, registered_at, ticker_rows, signal_rows, skipped)"
        " VALUES (1, '2026-07-01', '2026-07-02', ?, 2, 1, 0)",
        (NOW,),
    )

    # v_bucket_performance: strong_bull (hit) + thin (total < 2).
    _matured_ticker_row(conn, "FLAG1", 4, 4, 4, 0, 0.04, 0.01, in_portfolio=1)
    _matured_ticker_row(conn, "PLAIN1", 1, 1, 1, 0, 0.02, 0.01)

    # v_pending: one still-unmatured ticker outcome.
    conn.execute(
        "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date,"
        " symbol, score_sum, total, bullish, bearish, horizon, entry_date,"
        " entry_close, matured_at) VALUES (1, '2026-07-08', 'PEND1', 0, 0, 0, 0,"
        " 21, '2026-07-08', 100.0, NULL)"
    )

    # v_signal_efficacy / v_signal_recommendation.
    _matured_signal_row(conn, "sig_test_a", "FLAG1", 1, 0.04, 0.01)

    # v_regime_performance.
    conn.execute(
        "INSERT INTO regime_outcomes (composite_snapshot_id, composite_date, regime,"
        " horizon, entry_date, bench_entry_close, exit_date, bench_exit_close,"
        " bench_fwd_return, matured_at)"
        " VALUES (1, '2026-07-01', 'risk_on', 5, '2026-07-02', 500.0,"
        " '2026-07-09', 520.0, 0.04, ?)",
        (NOW,),
    )

    # v_basis_breaks: ACME's close halves between consecutive ledger dates.
    conn.execute(
        "INSERT INTO prices (symbol, price_date, close) VALUES"
        " ('ACME', '2026-06-30', 100.0), ('ACME', '2026-07-01', 48.0)"
    )

    # v_human_filter / v_decision_outcomes / v_freelance (also feeds the
    # trader scorecard's build_report).
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, composite_snapshot_id,"
        " composite_date, opinion_score_sum, opinion_total, fill_date,"
        " fill_price, quantity, recorded_at)"
        " VALUES ('FLAG1', 'acted', 'buy', 1, '2026-07-01', 4, 4, '2026-07-02',"
        " 101.0, 10, ?)",
        (NOW,),
    )
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, fill_date, fill_price,"
        " exit_fill_date, exit_fill_price, quantity, recorded_at)"
        " VALUES ('NVDA', 'acted', 'buy', '2026-07-01', 100.0, '2026-07-09',"
        " 110.0, 5, ?)",
        (NOW,),
    )

    # Privacy-parity guard: a decision row with non-NULL note/
    # order_ref/exit_order_ref/placed_agent/contract_ref/strategy_ref — the
    # six fields test_ticker_subtree_never_leaks_journal_private_fields bans
    # from the exported doc["tickers"] subtree (contract_ref/strategy_ref are
    # option-identity columns, not exported today but banned so the guard
    # matches the full sensitive set). Additive-only (doesn't touch the
    # FLAG1/NVDA rows above).
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, fill_date, fill_price,"
        " quantity, order_ref, exit_order_ref, note, placed_agent,"
        " contract_ref, strategy_ref, recorded_at)"
        " VALUES ('PRIV1', 'acted', 'buy', '2026-07-03', 50.0, 3,"
        " 'ord-priv-1', 'ord-priv-1-exit', 'private note text', 'agentic',"
        " 'PRIV1260101C00050000', 'strategy-ref-1', ?)",
        (NOW,),
    )

    # Privacy-parity guard: a research_verdicts row (schema at
    # sources/combiners/scorer/db.py:253-276) with a non-NULL `note`, for
    # FLAG1 (already in the composite/decisions fixtures, so it reaches
    # doc["tickers"] via headline_symbols). `note` here — like decisions'
    # note above — must never leak into doc["tickers"]; only `doc` (a bare
    # "<TICKER>-<DATE>.md" filename per the research-ticker skill's journal
    # ingest) becomes `thesis_path`.
    conn.execute(
        "INSERT INTO research_verdicts (symbol, verdict, verdict_date, doc, note, recorded_at)"
        " VALUES ('FLAG1', 'buy', '2026-07-01', 'FLAG1-2026-07-01.md',"
        " 'private analyst note', ?)",
        (NOW,),
    )

    # v_candidate_efficacy: one matured candidates-screen list-entry episode
    # via the rsi dislocation door (direct-but-schema-true insert, mirroring
    # tests/test_scorer_candidates.py's own fixture shape).
    conn.execute(
        "INSERT INTO candidate_appearances (id, symbol, screen_date,"
        " screen_version, fcf_yield, rsi, high52ch, fscore, via_rsi,"
        " via_drawdown, recorded_at) VALUES (1, 'CAND1', '2026-07-01', 'v1',"
        " 10.0, 28.0, -30.0, 7.0, 1, 0, ?)",
        (NOW,),
    )
    conn.execute(
        "INSERT INTO candidate_outcomes (appearance_id, symbol, horizon,"
        " entry_date, entry_close, bench_entry_close, exit_date, exit_close,"
        " fwd_return, bench_fwd_return, matured_at) VALUES (1, 'CAND1', 21,"
        " '2026-07-02', 100.0, 500.0, '2026-07-09', 105.0, 0.05, 0.01, ?)",
        (NOW,),
    )

    conn.commit()
    conn.close()


def _build_advisor_db(path):
    """advisor.db with 3 held positions (one strong disagreement: XOM) and
    one size-cap row — via write_position_heat/write_size_caps, the same
    writers tests/test_advisor_db_views.py uses."""
    conn = advisor_db.connect(str(path))
    advisor_db.ensure_schema(conn)
    sid = advisor_db.write_snapshot(conn, NOW)
    heat_rows = [
        {
            "symbol": "AAPL",
            "group_name": None,
            "quantity": 10.0,
            "market_value": 1500.0,
            "avg_cost": None,
            "atr": 3.0,
            "price": 150.0,
            "price_date": "2026-07-08",
            "heat_dollars": 30.0,
            "heat_pct": 0.003,
            "weight_pct": 0.15,
            "score_sum": 2,
            "bullish": 2,
            "bearish": 0,
            "total": 2,
            "atr_stale": 0,
        },
        {
            "symbol": "XOM",
            "group_name": "energy",
            "quantity": 5.0,
            "market_value": 500.0,
            "avg_cost": None,
            "atr": 2.0,
            "price": 100.0,
            "price_date": "2026-07-08",
            "heat_dollars": 10.0,
            "heat_pct": 0.001,
            "weight_pct": 0.05,
            "score_sum": -4,
            "bullish": 0,
            "bearish": 4,
            "total": 4,
            "atr_stale": 0,
        },
        {
            "symbol": "XLE",
            "group_name": "energy",
            "quantity": 3.0,
            "market_value": 300.0,
            "avg_cost": None,
            "atr": 1.5,
            "price": 100.0,
            "price_date": "2026-07-01",
            "heat_dollars": 4.5,
            "heat_pct": 0.00045,
            "weight_pct": 0.03,
            "score_sum": 1,
            "bullish": 1,
            "bearish": 0,
            "total": 1,
            "atr_stale": 1,
        },
    ]
    advisor_db.write_position_heat(conn, sid, heat_rows)
    cap_rows = [
        {
            "symbol": "NVDA",
            "direction": "bullish",
            "score_sum": 4,
            "atr": 4.0,
            "price": 100.0,
            "cap_shares": 25.0,
            "cap_dollars": 2500.0,
            "group_name": None,
            "group_heat_pct": 0.0,
            "reliable_signals": 1,
            "total_signals": 3,
            "exceeds_buying_power": 1,
            "already_held": 0,
        },
    ]
    advisor_db.write_size_caps(conn, sid, cap_rows)
    advisor_db.finish_snapshot(
        conn,
        sid,
        {"equity": 10000.0, "cash": 500.0, "buying_power": 200.0, "captured_at": NOW},
        {"captured_at": NOW, "regime": "risk_on"},
        sources_failed=0,
    )
    conn.commit()
    conn.close()


_STOCKS_COLS = {
    "sector": "TEXT",
    "marketCap": "REAL",
    "dollarVolume": "REAL",
    "roic": "REAL",
    "roic5y": "REAL",
    "fcfYield": "REAL",
    "revenueGrowth3Y": "REAL",
    "netDebtEbitda": "REAL",
    "sharesYoY": "REAL",
    "fScore": "REAL",
    "rsi": "REAL",
    "ch6m": "REAL",
    "high52ch": "REAL",
    "zScore": "REAL",
    "interestCoverage": "REAL",
    "priceDate": "TEXT",
    "isin": "TEXT",
    "isPrimaryListing": "TEXT",
    "netIncome": "REAL",
    "operatingCF": "REAL",
    "assets": "REAL",
}


def _build_stocks_db(path):
    """Built through the stock_analysis_screener's own ensure_schema, same
    no-hand-rolled-DDL rule as the combiner fixtures above — the candidates
    section reads this source directly."""
    from sources.screeners.stock_analysis_screener import db as stocks_db

    conn = stocks_db.connect(str(path))
    stocks_db.ensure_schema(conn, _STOCKS_COLS)
    conn.execute(
        "INSERT INTO snapshots (id, captured_at, universe_count, source)"
        " VALUES (1, '2026-07-08T11:00:00+00:00', 2, 'test')"
    )
    for sym, isin, fcfy, roic in (
        ("ADBE", "US00724F1012", 12.2, 60.7),
        ("PEGA", "US69546K1097", 11.5, 68.4),
    ):
        conn.execute(
            'INSERT INTO metrics (snapshot_id, symbol, sector, "marketCap", "dollarVolume",'
            ' roic, roic5y, "fcfYield", "revenueGrowth3Y", "netDebtEbitda", "sharesYoY",'
            ' "fScore", rsi, ch6m, "priceDate", isin, "isPrimaryListing")'
            " VALUES (1, ?, 'Technology', 8.4e10, 5e8, ?, 20.0, ?, 11.0, 0.2, -5.0,"
            " 7.0, 42.3, -29.2, '2026-07-08', ?, '1')",
            (sym, roic, fcfy, isin),
        )
    conn.commit()
    conn.close()


@pytest.fixture
def populated_data_dir(tmp_path):
    """A data dir with composite.db, scorer.db, advisor.db and stocks.db
    populated via each source's own db.py — real schemas/views throughout, no
    hand-rolled DDL — so every section of dashboard_lib.data's export has at
    least one real row to show. Laid out as tmp_path/data + tmp_path/research
    because the research-reopens section resolves research/ as the data dir's
    sibling (mirroring repo-root data/ and research/)."""
    data = tmp_path / "data"
    data.mkdir()
    _build_composite_db(data / "composite.db")
    _build_scorer_db(data / "scorer.db")
    _build_advisor_db(data / "advisor.db")
    _build_stocks_db(data / "stocks.db")
    _make_fred_db(data / "fred.db")
    research = tmp_path / "research"
    research.mkdir()
    # NOW's Phoenix date is 2026-07-08: STNE's trigger has passed (due),
    # GNTX's is ahead (upcoming), GFI's is undated (event), and OLD was
    # re-researched after its trigger (superseded — must not render).
    (research / "verdicts.log").write_text(
        "# Format: <YYYY-MM-DD> <TICKER> <VERDICT> ... [reopen=<YYYY-MM-DD|event>:<slug>]\n"
        "2026-07-01 STNE UNPROVEN conditions=6 refuted=0 unknown=3 reopen=2026-07-07:q2-print\n"
        "2026-07-01 GNTX UNPROVEN conditions=5 refuted=0 unknown=2 reopen=2026-08-20:q3-print\n"
        "2026-07-01 GFI UNPROVEN conditions=4 refuted=0 unknown=2 reopen=event:tarkwa-renewal\n"
        "2026-06-20 OLD UNPROVEN conditions=1 refuted=0 unknown=1 reopen=2026-07-01:print\n"
        "2026-07-05 OLD SOUND conditions=3 refuted=0 unknown=0\n"
    )
    return str(data)
