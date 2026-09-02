"""Logic tests for the track-record, book/ops and source-card exporters.

Each exporter reads one or two `v_*` views by name, so a fake view with the
same columns over a tiny table exercises the Python (history grouping,
falling-knife rule, latest-date scan, partial-calendar caveat) without
rebuilding a source's whole schema. Schema fidelity is the coverage gate's
job (`test_dashboard_coverage.py` runs every exporter on the real DDL).
"""

import json
import sqlite3
from pathlib import Path

import pytest
from dashboard_lib import book, data, grades, sources_views

NOW = "2026-07-09T04:12:00+00:00"
REPO = Path(__file__).resolve().parents[1]


def _mem(ddl: str) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ddl)
    return conn


def _view(name: str, cols: list[str], rows: list[tuple]) -> str:
    """A base table + a view over it, so the exporter's `FROM v_x` resolves."""
    t = f"t_{name}"
    ddl = f"CREATE TABLE {t}({', '.join(cols)});\n"
    for r in rows:
        vals = ", ".join("NULL" if v is None else repr(v) for v in r)
        ddl += f"INSERT INTO {t} VALUES ({vals});\n"
    return ddl + f"CREATE VIEW {name} AS SELECT * FROM {t};\n"


# --- fixture completeness (the frontend half of the coverage gate) ---------


def test_fixture_carries_every_section():
    """registeredSections.test.tsx smoke-renders every fixture section; a
    section missing from the fixture never gets that render. Run
    `uv run python dashboard/make_fixture.py` to add it."""
    fixture = json.loads((REPO / "dashboard" / "src" / "fixtures" / "data.json").read_text())
    missing = [s[0] for s in data.SECTION_EXPORTERS if s[0] not in fixture["sections"]]
    assert not missing, f"run dashboard/make_fixture.py; fixture lacks {missing}"


# --- grades ------------------------------------------------------------------


def test_replay_flags_keeps_newest_per_signal_with_score_history():
    conn = _mem(
        _view(
            "v_replay_flags",
            ["asof_date", "benchmark", "signal_id", "value", "source_date", "score"],
            [
                ("2026-06-01", "SP500", "hy", 4.0, "2026-06-01", -1),
                ("2026-06-02", "SP500", "hy", 4.1, "2026-06-02", -1),
                ("2026-06-03", "SP500", "hy", 4.2, "2026-06-03", 0),
                ("2026-06-03", "XLE", "hy", 4.2, "2026-06-03", 1),
                ("2026-06-04", "SP500", "hy", 4.3, "2026-06-04", 1),
            ],
        )
    )
    sec = grades.replay_flags(conn, NOW)
    rows = {(r["signal_id"], r["benchmark"]): r for r in sec["rows"]}
    assert rows[("hy", "SP500")]["asof_date"] == "2026-06-04"
    assert rows[("hy", "SP500")]["history"] == [-1.0, -1.0, 0.0, 1.0]
    # One point is a dot, not a trend — dropped.
    assert rows[("hy", "XLE")]["history"] is None


def test_falling_knife_needs_rising_yield_and_a_falling_quality_gate():
    knife = {
        "fcf_yield_entry": 5.0,
        "fcf_yield_now": 7.0,
        "fscore_entry": 7,
        "fscore_now": 5,
        "roic_entry": 20.0,
        "roic_now": 21.0,
    }
    assert grades._falling_knife(knife) is True
    cheaper_and_better = {**knife, "fscore_now": 8}
    assert grades._falling_knife(cheaper_and_better) is False
    assert grades._falling_knife({**knife, "fcf_yield_now": None}) is None
    assert grades._falling_knife({**knife, "fscore_now": None, "roic_now": None}) is None


def test_candidate_quality_trend_sorts_knives_first_and_counts_them():
    cols = [
        "symbol",
        "entry_date",
        "latest_date",
        "days_on_list",
        "n_sightings",
        "fscore_entry",
        "roic_entry",
        "fcf_yield_entry",
        "accruals_entry",
        "fscore_now",
        "roic_now",
        "fcf_yield_now",
        "accruals_now",
    ]
    conn = _mem(
        _view(
            "v_candidate_quality_trend",
            cols,
            [
                ("AAA", "2026-06-01", "2026-07-01", 30, 5, 7, 20.0, 5.0, -1.0, 7, 21.0, 5.1, -1.0),
                ("KNF", "2026-06-10", "2026-07-01", 21, 4, 7, 20.0, 5.0, -1.0, 5, 18.0, 8.0, 2.0),
            ],
        )
    )
    sec = grades.candidate_quality_trend(conn, NOW)
    assert [r["symbol"] for r in sec["rows"]] == ["KNF", "AAA"]
    assert sec["verdict"] == {"text": "1 falling knife on the list", "tone": "off"}


def test_signal_effective_n_attaches_date_history_and_latest_episode():
    ddl = _view(
        "v_signal_efficacy",
        ["signal_id", "via_crosswalk", "horizon", "n_matured", "n_dates", "n_blocks", "hit_rate"],
        [("hy", 0, 5, 12, 4, 2, 0.6)],
    )
    ddl += _view(
        "v_signal_efficacy_by_date",
        ["signal_id", "via_crosswalk", "horizon", "composite_date", "date_hit_rate"],
        [
            ("hy", 0, 5, "2026-06-01", 0.5),
            ("hy", 0, 5, "2026-06-02", 0.75),
            ("hy", 0, 5, "2026-06-09", 0.6),
        ],
    )
    ddl += _view(
        "v_signal_blocks",
        ["signal_id", "via_crosswalk", "horizon", "composite_date", "exit_date"],
        [("hy", 0, 5, "2026-06-01", "2026-06-09"), ("hy", 0, 5, "2026-06-09", "2026-06-16")],
    )
    sec = grades.signal_effective_n(_mem(ddl), NOW)
    (row,) = sec["rows"]
    assert row["history"] == [50.0, 75.0, 60.0]
    assert row["latest_block"] == "2026-06-09 → 2026-06-16"
    assert "_k" not in row
    assert sec["verdict"]["text"] == "1 of 1 signals rest on fewer than 3 independent episodes"


def test_research_filter_tiles_take_longest_horizon_per_verdict():
    conn = _mem(
        _view(
            "v_research_filter",
            ["verdict", "horizon", "n", "hit_rate", "avg_excess", "avg_fwd_return"],
            [("buy", 5, 16, 0.5, 0.0, 0.01), ("buy", 10, 13, 0.69, 0.01, 0.02)],
        )
    )
    sec = grades.research_filter(conn, NOW)
    (t,) = sec["tiles"]
    assert t == {"label": "buy calls right", "value": "69%", "band": "n=13 · 10d", "tone": "on"}


def test_drill_downs_cap_rows_but_report_total():
    cols = [
        "verdict_id",
        "symbol",
        "verdict",
        "verdict_date",
        "doc",
        "note",
        "horizon",
        "entry_date",
        "entry_close",
        "fwd_return",
        "bench_fwd_return",
        "matured_at",
        "excess",
        "verdict_correct",
    ]
    rows = [
        (
            i,
            f"S{i}",
            "buy",
            f"2026-06-{i % 28 + 1:02d}",
            "d",
            "private",
            5,
            "e",
            1.0,
            0.1,
            0.05,
            "m",
            0.05,
            1,
        )
        for i in range(grades._DRILL_LIMIT + 20)
    ]
    sec = grades.research_verdict_outcomes(
        _mem(_view("v_research_verdict_outcomes", cols, rows)), NOW
    )
    assert len(sec["rows"]) == grades._DRILL_LIMIT
    assert sec["total"] == grades._DRILL_LIMIT + 20
    assert sec["rows"][0]["verdict_correct"] is True
    assert "note" not in sec["rows"][0] and "doc" not in sec["rows"][0]


# --- book / ops ---------------------------------------------------------------


def test_exit_advice_verdict_counts_trims_and_tight_stops():
    cols = [
        "snapshot_id",
        "symbol",
        "quantity",
        "price",
        "avg_cost",
        "atr",
        "atr_stale",
        "score_sum",
        "total",
        "strong",
        "stop_price",
        "stop_distance_pct",
        "unrealized_pct",
        "trim_shares",
    ]
    conn = _mem(
        _view(
            "v_exit_advice",
            cols,
            [
                (1, "AAA", 10, 100.0, 90.0, 2.0, 0, 2, 4, 0, 98.0, 1.5, 11.1, None),
                (1, "BBB", 10, 50.0, 60.0, 1.0, 1, -4, 4, 1, 49.0, 4.0, -16.6, 3),
            ],
        )
    )
    sec = book.exit_advice(conn, NOW)
    assert [r["symbol"] for r in sec["rows"]] == ["BBB", "AAA"]  # trims first
    assert sec["rows"][0]["strong"] is True and sec["rows"][0]["atr_stale"] is True
    assert sec["verdict"] == {"text": "1 trim suggestion · 1 within 2% of stop", "tone": "off"}


def test_unreconciled_verdict_and_no_broker_ids():
    conn = _mem(
        _view(
            "v_unreconciled",
            ["id", "symbol", "status", "resolution_reason"],
            [(7, "AAA", "placed", None)],
        )
    )
    sec = book.unreconciled(conn, NOW)
    assert sec["verdict"]["tone"] == "off"
    assert set(sec["rows"][0]) == {"symbol", "status", "resolution_reason"}


# --- sources -------------------------------------------------------------------


def test_latest_date_rows_stops_at_first_older_row():
    conn = _mem(
        _view(
            "v_x",
            ["d", "rank"],
            [("2026-07-02", 3), ("2026-07-02", 2), ("2026-07-01", 9), ("2026-07-01", 8)],
        )
    )
    rows = sources_views._latest_date_rows(
        conn, "SELECT d, rank FROM v_x ORDER BY d DESC, rank DESC", "d", 10
    )
    assert [r["rank"] for r in rows] == [3, 2]
    assert sources_views._latest_date_rows(
        conn, "SELECT d, rank FROM v_x ORDER BY d DESC", "d", 1
    ) == [{"d": "2026-07-02", "rank": 3}]


def test_week_ahead_partial_calendar_sets_caveat_and_all_missing_raises(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    with pytest.raises(FileNotFoundError):
        sources_views.week_ahead(str(d), NOW)
    conn = sqlite3.connect(d / "fomc.db")
    conn.executescript(
        _view(
            "v_next_fomc",
            ["event_date", "event_time", "status", "days_until", "has_sep"],
            [("2026-07-15", None, "confirmed", 6, 1)],
        )
        + _view("v_in_blackout", ["in_blackout"], [(1,)])
    )
    conn.commit()
    conn.close()
    sec = sources_views.week_ahead(str(d), NOW)
    labels = {t["label"]: t for t in sec["tiles"]}
    assert labels["days to next FOMC"]["value"] == 6
    assert labels["days to next FOMC"]["tone"] == "mid"
    assert labels["Fed blackout"]["value"] == "yes"
    assert sec["rows"] == []
    assert "econ_calendar.db" in sec["caveat"] and "fomc.db" not in sec["caveat"]


def test_cot_section_flags_extremes_first_with_index_sparkline():
    ddl = _view(
        "v_positioning",
        [
            "code",
            "name",
            "asset_class",
            "report_date",
            "open_interest",
            "net_noncomm",
            "net_comm",
            "net_nonrept",
            "cot_index",
            "pct_oi_noncomm_long",
            "pct_oi_noncomm_short",
            "chg_oi",
            "chg_noncomm_long",
            "chg_noncomm_short",
        ],
        [
            ("001", "CORN", "ag", "2026-07-07", 1, 10, -10, 0, 50.0, 30.0, 20.0, 1, 1, 1),
            ("002", "GOLD", "metal", "2026-07-07", 1, 90, -90, 0, 97.0, 60.0, 5.0, 1, 1, 1),
        ],
    )
    ddl += _view("v_extremes", ["code"], [("002",)])
    ddl += _view(
        "v_cot_index",
        ["code", "report_date", "net_noncomm", "lo", "hi", "cot_index"],
        [
            ("002", "2026-06-23", 1, 0, 1, 80.0),
            ("002", "2026-06-30", 1, 0, 1, 90.0),
            ("002", "2026-07-07", 1, 0, 1, 97.0),
        ],
    )
    sec = sources_views.cot_positioning(_mem(ddl), NOW)
    assert [r["name"] for r in sec["rows"]] == ["GOLD", "CORN"]
    assert sec["rows"][0]["extreme"] is True and sec["rows"][0]["history"] == [80.0, 90.0, 97.0]
    assert "code" not in sec["rows"][0]
    assert sec["verdict"] == {"text": "1 contract at a positioning extreme", "tone": "mid"}


def test_history_query_runs_with_no_symbols():
    """An empty leaderboard still issues the history query (`IN ()`), so the
    coverage gate sees the history view as read."""
    ddl = _view(
        "v_high_days_to_cover",
        [
            "symbol",
            "settlement_date",
            "current_short_qty",
            "avg_daily_volume",
            "days_to_cover",
            "change_pct",
            "market_class",
        ],
        [],
    )
    ddl += _view(
        "v_symbol_history",
        [
            "symbol",
            "settlement_date",
            "current_short_qty",
            "avg_daily_volume",
            "days_to_cover",
            "change_pct",
        ],
        [],
    )
    sec = sources_views.short_interest_crowded(_mem(ddl), NOW)
    assert sec["rows"] == []


def test_series_tile_applies_scale_to_value_and_history():
    """A tile captioned ($T) must not print raw dollars: scale divides both
    the headline value and every history point."""
    conn = _mem(
        "CREATE TABLE t(d, v);\nINSERT INTO t VALUES ('2026-08-27', 39e12), ('2026-08-28', 40e12);"
    )
    t = sources_views._series_tile(
        conn, "total public debt ($T)", "SELECT d, v FROM t ORDER BY d", limit=5, scale=1e12
    )
    assert t is not None
    assert t["value"] == 40.0
    assert [pt["value"] for pt in t["history"]] == [39.0, 40.0]


def test_filings_collapse_same_day_same_form_into_one_counted_row():
    """A serial filer's N same-day filings are one row with a count, not N
    identical rows."""
    conn = _mem(
        _view(
            "v_offerings",
            ["ticker", "company", "form", "accession", "filed_date", "path"],
            [
                ("AMUB", "UBS AG", "424B2", "a1", "2026-08-31", "p1"),
                ("AMUB", "UBS AG", "424B2", "a2", "2026-08-31", "p2"),
                ("AMUB", "UBS AG", "424B2", "a3", "2026-08-31", "p3"),
                ("AIIO", "ROBO.AI INC.", "424B3", "a4", "2026-08-31", "p4"),
            ],
        )
    )
    sec = sources_views.offerings(conn, NOW)
    rows = {r["ticker"]: r["filings"] for r in sec["rows"]}
    assert rows == {"AMUB": 3, "AIIO": 1}


def test_ag_balance_trends_ending_stocks_and_ships_no_dead_columns():
    """NASS has no total-use metric, so the card carries ending stocks only;
    the stocks-to-use gauge lives in the WASDE card."""
    conn = _mem(
        _view(
            "v_stocks_to_use",
            ["commodity", "period", "ending_stocks", "total_use", "stocks_to_use"],
            [
                ("CORN", "2024", 12075407000.0, None, None),
                ("CORN", "2025", 13305825000.0, None, None),
                ("CORN", "2026", 5294828000.0, None, None),
            ],
        )
        + _view("v_series_history", ["commodity", "metric", "period", "value"], [])
        + _view("v_latest_balance", ["commodity", "metric", "period", "value", "unit"], [])
    )
    sec = sources_views.ag_balance(conn, NOW)
    keys = [c["key"] for c in sec["columns"]]
    assert "total_use" not in keys and "stocks_to_use" not in keys
    (row,) = [r for r in sec["rows"] if r["period"] == "2026"]
    assert row["history"] == [12075407000.0, 13305825000.0, 5294828000.0]


def test_outcome_drilldowns_list_graded_rows_before_pending():
    """Newest-first alone buried every graded row below the row cap; graded
    rows sort first so the visible slice shows real outcomes."""
    conn = _mem(
        _view(
            "v_research_verdict_outcomes",
            [
                "symbol",
                "verdict",
                "verdict_date",
                "horizon",
                "fwd_return",
                "bench_fwd_return",
                "excess",
                "verdict_correct",
            ],
            [
                ("NEWA", "pass", "2026-08-31", 5, None, None, None, None),
                ("OLDG", "buy", "2026-07-01", 5, 0.02, 0.01, 0.01, 1),
            ],
        )
    )
    sec = grades.research_verdict_outcomes(conn, NOW)
    assert [r["symbol"] for r in sec["rows"]] == ["OLDG", "NEWA"]
    assert sec["rows"][0]["verdict_correct"] is True


def test_market_closures_one_row_per_date_per_market():
    """Shared holidays exist twice in events (NYSE + bond); the card keeps
    both but the kind names the market, and early closes carry their time."""
    conn = _mem(
        "CREATE TABLE events(event_type, event_date, event_time, title);\n"
        "CREATE TABLE calendar_now(today);\n"
        "INSERT INTO calendar_now VALUES ('2026-09-01');\n"
        "INSERT INTO events VALUES"
        " ('market_holiday', '2026-09-07', NULL, 'Labor Day'),"
        " ('bond_holiday', '2026-09-07', NULL, 'Labor Day'),"
        " ('bond_holiday', '2026-10-12', NULL, 'Columbus Day'),"
        " ('early_close', '2026-11-27', '13:00', NULL),"
        " ('bond_early_close', '2026-11-27', '14:00', NULL),"
        " ('opex', '2026-09-18', NULL, 'September Quad Witching'),"
        " ('market_holiday', '2026-01-01', NULL, 'New Year (past)');"
    )
    sec = sources_views.market_closures(conn, NOW)
    rows = [(r["event_date"], r["kind"], r["event_time"]) for r in sec["rows"]]
    assert rows == [
        ("2026-09-07", "bond closed", None),
        ("2026-09-07", "closed", None),
        ("2026-10-12", "bond closed", None),
        ("2026-11-27", "bond early close", "14:00"),
        ("2026-11-27", "early close", "13:00"),
    ]


def test_source_cards_live_in_the_sources_strand_except_calendar_and_holidays():
    kickers = {s[0]: s[4] for s in sources_views.SECTIONS}
    assert kickers["week-ahead"] == "Macro"
    assert kickers["market-closures"] == "Ops"
    assert {k for sid, k in kickers.items() if sid not in ("week-ahead", "market-closures")} == {
        "Sources"
    }
