"""Batch-2 label pass on the grades.py and book.py cards: word labels,
detail columns folded (`hidden`), humanized values, and headline tiles
where a card grades something. Fake views in memory, in the style of
test_dashboard_readability_grades.py."""

import sqlite3

from dashboard_lib import book, grades

NOW = "2026-07-09T04:12:00+00:00"


def _mem(ddl: str) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ddl)
    return conn


def _view(name: str, cols: list[str], rows: list[tuple]) -> str:
    t = f"t_{name}"
    ddl = f"CREATE TABLE {t}({', '.join(cols)});\n"
    for r in rows:
        vals = ", ".join("NULL" if v is None else repr(v) for v in r)
        ddl += f"INSERT INTO {t} VALUES ({vals});\n"
    return ddl + f"CREATE VIEW {name} AS SELECT * FROM {t};\n"


def _labels(sec, hidden=False):
    return [c["label"] for c in sec["columns"] if bool(c.get("hidden")) == hidden]


def _keys(sec):
    return [c["key"] for c in sec["columns"]]


def _about(sections, sid):
    entry = next(s for s in sections if s[0] == sid)
    return " ".join(f"{h} {b}" for h, b in entry[6])


# --- candidate-outcomes ------------------------------------------------------

OUTCOME_COLS = [
    "symbol",
    "screen_date",
    "growth_door",
    "branch",
    "screen_version",
    "horizon",
    "entry_close",
    "fwd_return",
    "bench_fwd_return",
    "excess",
    "beat_benchmark",
]


def test_candidate_outcomes_folds_the_screen_mechanics():
    conn = _mem(
        _view(
            "v_candidate_outcomes",
            OUTCOME_COLS,
            [("AZN", "2026-08-03", "3y", "rsi", "2026-07-29", 21, 155.6, 0.04, -0.01, 0.05, 1)],
        )
    )
    sec = grades.candidate_outcomes(conn, NOW)
    assert _labels(sec) == [
        "Symbol",
        "Entered list",
        "Horizon",
        "Return",
        "SPY return",
        "Vs SPY",
        "Beat SPY?",
    ]
    assert _labels(sec, hidden=True) == [
        "Why it qualified",
        "What flagged it",
        "Screen version",
        "Price at entry",
    ]
    excess = next(c for c in sec["columns"] if c["key"] == "excess")
    assert excess["term"] == "Excess"


# --- candidate-quality-trend -------------------------------------------------

TREND_COLS = [
    "symbol",
    "days_on_list",
    "n_sightings",
    "fscore_entry",
    "fscore_now",
    "roic_entry",
    "roic_now",
    "fcf_yield_entry",
    "fcf_yield_now",
    "accruals_now",
]


def test_quality_trend_names_what_weakened_and_folds_the_pairs():
    conn = _mem(
        _view(
            "v_candidate_quality_trend",
            TREND_COLS,
            [
                ("GDDY", 37, 28, 7.0, 6.0, 40.0, 37.3, 12.0, 13.0, -10.2),
                ("FINE", 10, 8, 6.0, 7.0, 20.0, 21.0, 8.0, 7.0, 1.0),
                ("PART", 5, 4, None, None, 20.0, 18.0, 8.0, 9.0, 1.0),
            ],
        )
    )
    sec = grades.candidate_quality_trend(conn, NOW)
    assert _keys(sec)[:2] == ["symbol", "what_weakened"]
    by = {r["symbol"]: r for r in sec["rows"]}
    assert by["GDDY"]["what_weakened"] == "F-score, ROIC"
    assert by["FINE"]["what_weakened"] == "nothing"
    assert by["PART"]["what_weakened"] == "ROIC"
    hidden = {c["key"] for c in sec["columns"] if c.get("hidden")}
    assert hidden == {
        "fscore_entry",
        "fscore_now",
        "roic_entry",
        "roic_now",
        "fcf_yield_entry",
        "fcf_yield_now",
        "accruals_now",
    }
    about = _about(grades.SECTIONS, "candidate-quality-trend")
    for word in ("F-score", "ROIC", "FCF yield", "accruals"):
        assert word in about


# --- flag-response -----------------------------------------------------------


def test_flag_response_speaks_the_response_in_words():
    conn = _mem(
        _view(
            "v_flag_response",
            ["composite_date", "symbol", "score_sum", "total", "response", "horizon", "dir_excess"],
            [
                ("2026-08-26", "BHF", 3, 2, "passed_inferred", 5, -0.011),
                ("2026-08-26", "EDRY", -3, 2, "acted", 5, 0.02),
                ("2026-08-25", "WB", 3, 2, "passed", 5, 0.01),
                ("2026-08-25", "IEP", 3, 2, "acted_option", 5, 0.03),
            ],
        )
    )
    sec = grades.flag_response(conn, NOW)
    assert [r["response"] for r in sec["rows"]] == [
        "Skipped (no journal entry)",
        "Acted",
        "Acted (options)",
        "Passed",
    ]
    labels = {c["key"]: c for c in sec["columns"]}
    assert labels["composite_date"]["label"] == "Flag date"
    assert labels["dir_excess"]["label"] == "Gain had you followed it"
    assert labels["dir_excess"]["term"] == "Directional excess"


# --- option-pnl --------------------------------------------------------------


def test_option_pnl_labels_are_distinct_and_plain():
    conn = _mem(
        _view(
            "v_option_pnl",
            [
                "symbol",
                "direction",
                "expiration",
                "fill_date",
                "contracts_opened",
                "contracts_closed",
                "contracts_outstanding",
                "pnl_dollars",
                "premium_return",
            ],
            [],
        )
        + _view("v_option_actor", ["direction", "n_closed", "hit_rate", "total_pnl"], [])
    )
    sec = grades.option_pnl(conn, NOW)
    labels = _labels(sec)
    assert len(labels) == len(set(labels))
    by = {c["key"]: c["label"] for c in sec["columns"]}
    assert by["fill_date"] == "Opened on"
    assert by["contracts_opened"] == "Contracts opened"
    assert by["pnl_dollars"] == "Profit $"
    assert by["premium_return"] == "Return on premium"


# --- replay-flags ------------------------------------------------------------


def test_replay_flags_carry_a_lean_word_and_fold_the_score():
    conn = _mem(
        _view(
            "v_replay_flags",
            ["signal_id", "benchmark", "asof_date", "value", "score"],
            [
                ("cboe_equity_pcr", "SP500", "2026-09-04", 12.3, -1),
                ("eia_natgas_storage", "UNG", "2026-09-04", 3.1, 1),
                ("fred_t10y2y", "SP500", "2026-09-04", 0.4, 0),
                ("fred_none", "SP500", "2026-09-04", 0.4, None),
            ],
        )
    )
    sec = grades.replay_flags(conn, NOW)
    assert _keys(sec)[:2] == ["signal_id", "lean"]
    by = {r["signal_id"]: r["lean"] for r in sec["rows"]}
    assert by == {
        "cboe_equity_pcr": "bearish",
        "eia_natgas_storage": "bullish",
        "fred_t10y2y": "neutral",
        "fred_none": None,
    }
    score = next(c for c in sec["columns"] if c["key"] == "score")
    assert score["hidden"] is True


# --- research-verdict-outcomes -----------------------------------------------

VERDICT_COLS = [
    "symbol",
    "verdict",
    "verdict_date",
    "horizon",
    "fwd_return",
    "bench_fwd_return",
    "excess",
    "verdict_correct",
]


def test_verdict_outcomes_tiles_count_right_calls_at_the_longest_horizon():
    rows = []
    for i, ok in enumerate((1, 1, 0)):
        rows.append((f"B{i}", "buy", "2026-08-01", 5, 0.01, 0.0, 0.01, 1))
        rows.append((f"B{i}", "buy", "2026-08-01", 21, 0.01, 0.0, 0.01, ok))
    rows.append(("P0", "pass", "2026-08-01", 21, -0.1, 0.0, -0.1, 1))
    rows.append(("P1", "pass", "2026-08-02", 21, 0.1, 0.0, 0.1, None))  # unmatured leg
    conn = _mem(_view("v_research_verdict_outcomes", VERDICT_COLS, rows))
    sec = grades.research_verdict_outcomes(conn, NOW)
    tiles = {t["label"]: t for t in sec["tiles"]}
    assert tiles["Buy calls right"]["value"] == "2 of 3"
    assert tiles["Buy calls right"]["band"] == "at 21d"
    assert tiles["Pass calls right"]["value"] == "1 of 1"
    assert _labels(sec, hidden=True) == ["SPY return"]
    excess = next(c for c in sec["columns"] if c["key"] == "excess")
    assert excess["label"] == "Vs SPY" and excess["term"] == "Excess"


def test_verdict_outcomes_have_no_tiles_without_rows():
    conn = _mem(_view("v_research_verdict_outcomes", VERDICT_COLS, []))
    assert grades.research_verdict_outcomes(conn, NOW)["tiles"] == []


# --- signal-effective-n ------------------------------------------------------


def test_effective_n_labels_and_folds_the_row_counts():
    conn = _mem(
        _view(
            "v_signal_efficacy",
            [
                "signal_id",
                "via_crosswalk",
                "horizon",
                "n_matured",
                "n_dates",
                "n_blocks",
                "hit_rate",
            ],
            [("ftd_persistent", 0, 5, 2251, 15, 3, 0.38)],
        )
        + _view(
            "v_signal_efficacy_by_date",
            ["signal_id", "via_crosswalk", "horizon", "composite_date", "date_hit_rate"],
            [],
        )
        + _view(
            "v_signal_blocks",
            ["signal_id", "via_crosswalk", "horizon", "composite_date", "exit_date"],
            [],
        )
    )
    sec = grades.signal_effective_n(conn, NOW)
    by = {c["key"]: c for c in sec["columns"]}
    assert by["hit_rate"]["label"] == "Hit rate (all rows)"
    assert by["n_blocks"]["label"] == "Independent episodes"
    assert by["n_matured"]["label"] == "Rows graded" and by["n_matured"]["hidden"] is True
    assert by["n_dates"]["label"] == "Distinct dates" and by["n_dates"]["hidden"] is True
    assert by["via_crosswalk"]["hidden"] is True


# --- exit-advice (book) ------------------------------------------------------


def test_exit_advice_opens_on_the_decision_columns():
    conn = _mem(
        _view(
            "v_exit_advice",
            [
                "symbol",
                "quantity",
                "price",
                "avg_cost",
                "unrealized_pct",
                "stop_price",
                "stop_distance_pct",
                "score_sum",
                "strong",
                "trim_shares",
                "atr_stale",
            ],
            [("ORI", 0.24, 42.6, 42.1, 1.1, 41.1, 3.5, 0, 0, None, 0)],
        )
    )
    sec = book.exit_advice(conn, NOW)
    assert _labels(sec) == [
        "Symbol",
        "Price",
        "Suggested stop",
        "Room to stop %",
        "Signal lean",
        "Trim shares",
    ]
    assert _labels(sec, hidden=True) == [
        "Shares",
        "Avg cost",
        "Unrealized %",
        "Strong disagreement",
        "Volatility data old?",
    ]


# --- option-heat (book) ------------------------------------------------------


def test_option_heat_says_at_risk_and_explains_delta():
    conn = _mem(
        _view(
            "v_latest_option_heat",
            [
                "underlying",
                "type",
                "expiration",
                "quantity",
                "delta",
                "share_equiv",
                "market_value",
                "heat_dollars",
                "heat_pct",
                "short_leg",
                "uncovered",
            ],
            [],
        )
    )
    sec = book.option_heat(conn, NOW)
    by = {c["key"]: c["label"] for c in sec["columns"]}
    assert by["share_equiv"] == "Acts like N shares"
    assert by["heat_dollars"] == "At risk $"
    assert by["heat_pct"] == "At risk %"
    assert by["short_leg"] == "Short?"
    assert by["uncovered"] == "Uncovered?"
    assert "delta" in _about(book.SECTIONS, "option-heat").lower()
