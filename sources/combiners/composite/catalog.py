"""Curated signal catalog: which source signals feed the composite, how
each normalizes to a -2..+2 score, and how asset classes map to tickers.

Every SQL runs against ONE source DB attached read-only as `src`, with
:today (YYYY-MM-DD) bound by the run. Required row shape:
    (entity, raw_value, score, obs_date)
entity is '*' (market), an asset class, or a ticker. score is an integer
-2..+2, positive = bullish for the entity — contrarian readings (crowded
shorts, panicky put buying) are applied HERE, not by consumers.

One-clock rule: never reference a source's calendar_now-dependent views
(monitor v_upcoming/v_imminent, treasury.v_upcoming_auctions, fred.v_asof);
query base tables with :today instead.
"""

SIGNALS = [
    # ------------------------------------------------ market grain ----
    {
        "signal_id": "fred_curve", "db": "fred.db", "grain": "market",
        "staleness_budget_days": 7,
        "sql": """
            SELECT '*', value,
                   CASE WHEN value < 0 THEN -1 ELSE 0 END,
                   date
            FROM src.observations
            WHERE series_id = 'T10Y2Y' AND value IS NOT NULL
            ORDER BY date DESC LIMIT 1
        """,
    },
    {
        "signal_id": "fred_hy_spread", "db": "fred.db", "grain": "market",
        "staleness_budget_days": 7,
        "sql": """
            SELECT '*', value,
                   CASE WHEN value >= 5.0 THEN -2
                        WHEN value >= 4.0 THEN -1
                        WHEN value < 3.5 THEN 1 ELSE 0 END,
                   date
            FROM src.observations
            WHERE series_id = 'BAMLH0A0HYM2' AND value IS NOT NULL
            ORDER BY date DESC LIMIT 1
        """,
    },
    {
        "signal_id": "cboe_vix", "db": "cboe_stats.db", "grain": "market",
        "staleness_budget_days": 5,
        "sql": """
            SELECT '*', close,
                   CASE WHEN close >= 30 THEN -2
                        WHEN close >= 25 THEN -1
                        WHEN close < 15 THEN 1 ELSE 0 END,
                   date
            FROM src.vix_daily WHERE close IS NOT NULL
            ORDER BY date DESC LIMIT 1
        """,
    },
    {
        "signal_id": "cboe_vix_backwardation", "db": "cboe_stats.db",
        "grain": "market", "staleness_budget_days": 5,
        "sql": """
            SELECT '*', close - vix3m,
                   CASE WHEN close > vix3m THEN -2 ELSE 0 END,
                   date
            FROM src.vix_daily
            WHERE close IS NOT NULL AND vix3m IS NOT NULL
            ORDER BY date DESC LIMIT 1
        """,
    },
    {
        # Contrarian: panicky put buying (high PCR percentile) is bullish.
        "signal_id": "cboe_equity_pcr", "db": "cboe_stats.db",
        "grain": "market", "staleness_budget_days": 5,
        "sql": """
            WITH latest AS (
                SELECT date, equity_pcr FROM src.pcr_daily
                WHERE equity_pcr IS NOT NULL ORDER BY date DESC LIMIT 1),
            hist AS (
                SELECT equity_pcr FROM src.pcr_daily
                WHERE equity_pcr IS NOT NULL ORDER BY date DESC LIMIT 252),
            p AS (
                SELECT l.date AS date,
                       100.0 * (SELECT COUNT(*) FROM hist h
                                WHERE h.equity_pcr <= l.equity_pcr)
                             / (SELECT COUNT(*) FROM hist) AS pctile
                FROM latest l)
            SELECT '*', pctile,
                   CASE WHEN pctile >= 90 THEN 2 WHEN pctile >= 75 THEN 1
                        WHEN pctile <= 10 THEN -2 WHEN pctile <= 25 THEN -1
                        ELSE 0 END,
                   date
            FROM p
        """,
    },
    {
        # Gate, not direction: score 0; regime tier reads the raw flag.
        "signal_id": "fomc_blackout", "db": "fomc.db", "grain": "market",
        "staleness_budget_days": 0,
        "sql": """
            SELECT '*',
                   EXISTS(SELECT 1 FROM src.events e
                          WHERE e.event_type = 'fomc_blackout_start'
                            AND e.event_date <= :today
                            AND json_extract(e.payload, '$.window_end')
                                >= :today),
                   0, :today
        """,
    },
    {
        "signal_id": "econ_imminent", "db": "econ_calendar.db",
        "grain": "market", "staleness_budget_days": 0,
        "sql": """
            SELECT '*', COUNT(*), 0, :today
            FROM src.events
            WHERE event_date >= :today
              AND event_date <= date(:today, '+3 days')
        """,
    },
    {
        "signal_id": "mcal_days_to_opex", "db": "market_calendar.db",
        "grain": "market", "staleness_budget_days": 0,
        "sql": """
            SELECT '*',
                   CAST(julianday(MIN(event_date)) - julianday(:today)
                        AS INTEGER),
                   0, :today
            FROM src.events
            WHERE event_type IN ('opex', 'quad_witching')
              AND event_date >= :today
        """,
    },
    {
        # Falling RRP take-up releases liquidity into markets: bullish.
        "signal_id": "nyfed_rrp", "db": "nyfed.db", "grain": "market",
        "staleness_budget_days": 5,
        "sql": """
            SELECT '*', change_vs_prior,
                   CASE WHEN change_vs_prior < 0 THEN 1
                        WHEN change_vs_prior > 0 THEN -1 ELSE 0 END,
                   operation_date
            FROM src.v_rrp_trend
            WHERE change_vs_prior IS NOT NULL
            ORDER BY operation_date DESC LIMIT 1
        """,
    },
    {
        # Rising TGA drains liquidity from markets: bearish.
        "signal_id": "tsy_tga", "db": "treasury.db", "grain": "market",
        "staleness_budget_days": 7,
        "sql": """
            SELECT '*', wow_change,
                   CASE WHEN wow_change < 0 THEN 1
                        WHEN wow_change > 0 THEN -1 ELSE 0 END,
                   record_date
            FROM src.v_tga_trend
            WHERE wow_change IS NOT NULL
            ORDER BY record_date DESC LIMIT 1
        """,
    },
    # ------------------------------------------- asset-class grain ----
    {
        # Contrarian at extremes: washed-out managed money = bullish.
        "signal_id": "cftc_mm_extreme", "db": "cftc.db",
        "grain": "asset_class", "staleness_budget_days": 12,
        "sql": """
            SELECT m.asset_class, AVG(c.cot_index),
                   CASE WHEN AVG(c.cot_index) <= 10 THEN 2
                        WHEN AVG(c.cot_index) <= 20 THEN 1
                        WHEN AVG(c.cot_index) >= 90 THEN -2
                        WHEN AVG(c.cot_index) >= 80 THEN -1 ELSE 0 END,
                   MAX(c.report_date)
            FROM src.v_disagg_cot_index_latest c
            JOIN src.markets m ON m.code = c.code
            WHERE c.cot_index IS NOT NULL
            GROUP BY m.asset_class
        """,
    },
    {
        "signal_id": "cftc_lev_extreme", "db": "cftc.db",
        "grain": "asset_class", "staleness_budget_days": 12,
        "sql": """
            SELECT m.asset_class, AVG(c.cot_index),
                   CASE WHEN AVG(c.cot_index) <= 10 THEN 2
                        WHEN AVG(c.cot_index) <= 20 THEN 1
                        WHEN AVG(c.cot_index) >= 90 THEN -2
                        WHEN AVG(c.cot_index) >= 80 THEN -1 ELSE 0 END,
                   MAX(c.report_date)
            FROM src.v_tff_cot_index_latest c
            JOIN src.markets m ON m.code = c.code
            WHERE c.cot_index IS NOT NULL
            GROUP BY m.asset_class
        """,
    },
    {
        # Crude build = bearish energy; draw = bullish.
        "signal_id": "eia_crude_stocks", "db": "eia.db",
        "grain": "asset_class", "staleness_budget_days": 10,
        "sql": """
            SELECT 'energy', change_pct,
                   CASE WHEN change_pct <= -2.0 THEN 1
                        WHEN change_pct >= 2.0 THEN -1 ELSE 0 END,
                   latest_period
            FROM src.v_weekly_change WHERE series_id = 'WCESTUS1'
        """,
    },
    {
        "signal_id": "eia_natgas_storage", "db": "eia.db",
        "grain": "asset_class", "staleness_budget_days": 10,
        "sql": """
            SELECT 'energy', change_pct,
                   CASE WHEN change_pct <= -2.0 THEN 1
                        WHEN change_pct >= 2.0 THEN -1 ELSE 0 END,
                   latest_period
            FROM src.v_weekly_change
            WHERE series_id = 'NW2_EPG0_SWO_R48_BCF'
        """,
    },
    {
        # Tight US grain stocks-to-use = bullish ags. WASDE is monthly and
        # market-year keyed; obs_date is :today by construction (budget 35).
        "signal_id": "usda_stocks_to_use", "db": "usda.db",
        "grain": "asset_class", "staleness_budget_days": 35,
        "sql": """
            SELECT 'ags', AVG(stocks_to_use),
                   CASE WHEN AVG(stocks_to_use) < 0.10 THEN 1 ELSE 0 END,
                   :today
            FROM src.v_wasde_stocks_to_use
            WHERE region = 'United States'
              AND commodity IN ('Corn', 'Soybeans', 'Wheat')
              AND stocks_to_use IS NOT NULL
              AND market_year = (SELECT MAX(market_year)
                                 FROM src.v_wasde_stocks_to_use
                                 WHERE region = 'United States')
        """,
    },
    # ------------------------------------------------ ticker grain ----
    {
        # Crowded shorts = squeeze fuel (contrarian bullish). The source
        # view pre-filters days_to_cover >= 5 / ADV >= 100k, but at >= 5
        # this blankets ~1,600 tickers and skews the whole composite
        # bullish (measured 2026-07-06); score only genuine extremes.
        # FAMILY OVERLAP: this and ftd_persistent both read squeeze fuel —
        # a flag driven by only these two is one phenomenon double-counted.
        "signal_id": "si_days_to_cover", "db": "short_interest.db",
        "grain": "ticker", "staleness_budget_days": 25,
        "sql": """
            SELECT symbol, days_to_cover,
                   CASE WHEN days_to_cover >= 20 THEN 2 ELSE 1 END,
                   settlement_date
            FROM src.v_high_days_to_cover
            WHERE days_to_cover >= 10
        """,
    },
    {
        # NEW shorting pressure (vs own 6-period base) reads as informed
        # bears arriving: bearish. Distinct from the level read above.
        # At the old >= 1.5 floor this emitted 1,135 rows (52% of all signal
        # rows) and skewed the composite bearish (measured 2026-07-06);
        # >= 2.5 = 443 rows, >= 8.0 = 82 -- matching si_days_to_cover's scale.
        "signal_id": "si_spike", "db": "short_interest.db",
        "grain": "ticker", "staleness_budget_days": 25,
        "sql": """
            SELECT symbol, base_ratio,
                   CASE WHEN base_ratio >= 8.0 THEN -2 ELSE -1 END,
                   settlement_date
            FROM src.v_short_interest_spikes
            WHERE base_ratio >= 2.5
        """,
    },
    {
        "signal_id": "sv_ratio_spike", "db": "short_volume.db",
        "grain": "ticker", "staleness_budget_days": 4,
        "sql": """
            SELECT symbol, spike_ratio,
                   CASE WHEN spike_ratio >= 1.6 THEN -2 ELSE -1 END,
                   date
            FROM src.v_ratio_spikes WHERE spike_ratio >= 1.3
        """,
    },
    {
        # Persistent fails-to-deliver = delivery stress / squeeze fuel.
        # FAMILY OVERLAP with si_days_to_cover — see the note there.
        "signal_id": "ftd_persistent", "db": "ftd.db",
        "grain": "ticker", "staleness_budget_days": 25,
        "sql": """
            SELECT symbol, streak_days,
                   CASE WHEN streak_days >= 10 THEN 2 ELSE 1 END,
                   streak_end
            FROM src.v_persistent
            WHERE active = 1 AND symbol IS NOT NULL
        """,
    },
    {
        # Attention momentum: mention spikes with real volume behind them.
        "signal_id": "reddit_trending", "db": "reddit.db",
        "grain": "ticker", "staleness_budget_days": 2,
        "sql": """
            SELECT ticker, mention_pct_change,
                   CASE WHEN mention_pct_change >= 3.0 THEN 2 ELSE 1 END,
                   substr(captured_at, 1, 10)
            FROM src.v_signals
            WHERE filter = 'all-stocks' AND mentions >= 50
              AND mention_pct_change >= 1.0
        """,
    },
    {
        # Mean-reversion read on RSI extremes, liquid names only.
        "signal_id": "stocks_rsi", "db": "stocks.db",
        "grain": "ticker", "staleness_budget_days": 4,
        "sql": """
            SELECT symbol, rsi,
                   CASE WHEN rsi <= 20 THEN 2 WHEN rsi <= 30 THEN 1
                        WHEN rsi >= 80 THEN -2 ELSE -1 END,
                   priceDate
            FROM src.v_latest
            WHERE rsi IS NOT NULL AND rsi > 0
              AND (rsi <= 30 OR rsi >= 70)
              AND dollarVolume >= 10000000
        """,
    },
    {
        # Form 4 cluster = attention flag; direction unknown at index
        # level (buys and sells both file Form 4), hence score 0.
        "signal_id": "edgar_insider", "db": "edgar.db",
        "grain": "ticker", "staleness_budget_days": 5,
        "sql": """
            SELECT ticker, COUNT(*), 0, MAX(filed_date)
            FROM src.v_tickered
            WHERE bucket = 'insider' AND ticker IS NOT NULL
            GROUP BY ticker HAVING COUNT(*) >= 3
        """,
    },
    {
        # Live holdings: informational only (never votes; sets in_portfolio).
        "signal_id": "portfolio_holding", "db": "portfolio.db",
        "grain": "ticker", "staleness_budget_days": 3,
        "sql": """
            SELECT p.symbol, p.quantity, 0, substr(s.captured_at, 1, 10)
            FROM src.positions p
            JOIN src.snapshots s ON s.id = p.snapshot_id
            WHERE p.snapshot_id = (SELECT id FROM src.snapshots
                                   ORDER BY captured_at DESC, id DESC
                                   LIMIT 1)
        """,
    },
]

# market-grain signal -> market_regime column (raw_value is copied over;
# derived flags like curve_inverted are computed in db.write_market_regime).
REGIME_FIELDS = {
    "fred_curve": "t10y2y",
    "fred_hy_spread": "hy_spread",
    "cboe_vix": "vix",
    "cboe_vix_backwardation": "vix_backwardation",
    "cboe_equity_pcr": "equity_pcr_pctile",
    "fomc_blackout": "in_fomc_blackout",
    "econ_imminent": "imminent_high_impact",
    "mcal_days_to_opex": "days_to_opex",
    "nyfed_rrp": "rrp_change",
    "tsy_tga": "tga_change",
}

# Asset class -> liquid proxy tickers. Curated judgment; 'fx' is scored
# but deliberately NOT mapped (net-long EUR != net-long UUP).
CROSSWALK = {
    "energy": ["XLE", "XOM", "CVX", "USO"],
    "metals": ["GDX", "GLD", "SLV", "FCX", "COPX"],
    "ags": ["DBA", "CORN", "SOYB", "WEAT"],
    "softs": ["DBA"],
    "rates": ["TLT", "IEF"],
    "equity_index": ["SPY", "QQQ", "IWM"],
}


def select_ids(only=None, exclude=None, add=None):
    """Standard catalog selection: --only narrows, --add extends an --only
    list, --exclude removes. Returns catalog entries in catalog order."""
    ids = [s["signal_id"] for s in SIGNALS]
    sel = list(only) if only else list(ids)
    if add:
        sel += [a for a in add if a not in sel]
    if exclude:
        sel = [s for s in sel if s not in exclude]
    unknown = sorted(set(sel) - set(ids))
    if unknown:
        raise ValueError(f"unknown signal ids: {', '.join(unknown)}")
    chosen = set(sel)
    return [s for s in SIGNALS if s["signal_id"] in chosen]
