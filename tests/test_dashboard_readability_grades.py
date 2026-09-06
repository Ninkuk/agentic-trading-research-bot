"""Readability rebuild of three grades.py cards: plain labels, detail
columns folded (`hidden`), and a one-line chip where the card makes a
judgement. Fake views in the style of test_dashboard_sections.py."""

import sqlite3

from dashboard_lib import grades

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


# --- replay-baseline ---------------------------------------------------------

BASE_COLS = ["benchmark", "horizon", "n_windows", "p_up", "p_down"]


def test_replay_baseline_speaks_in_words_and_leads_with_spy():
    conn = _mem(
        _view(
            "v_benchmark_baseline",
            BASE_COLS,
            [
                ("DBA", 5, 4940, 0.5123, 0.4773),
                ("SP500", 5, 4940, 0.58, 0.41),
                ("SP500", 21, 4900, 0.687, 0.31),
            ],
        )
    )
    sec = grades.replay_baseline(conn, NOW)
    assert _labels(sec) == ["Benchmark", "Horizon", "Days measured", "Went up", "Went down"]
    assert sec["verdict"] == {"text": "SP500 rose on 69% of 21-day windows", "tone": "mid"}


def test_replay_baseline_has_no_chip_without_rows():
    conn = _mem(_view("v_benchmark_baseline", BASE_COLS, []))
    assert grades.replay_baseline(conn, NOW)["verdict"] is None


# --- replay-efficacy ---------------------------------------------------------


def test_replay_efficacy_folds_the_statistics_columns():
    cols = [
        "signal_id",
        "direction",
        "horizon",
        "n_days",
        "hit_rate",
        "hit_ci_lo",
        "hit_ci_hi",
        "baseline",
        "excess",
        "perm_p",
        "beats_baseline",
        "anti_signal",
    ]
    conn = _mem(
        _view(
            "v_replay_efficacy",
            cols,
            [("eia_natgas_storage", "bearish", 21, 1607, 0.51, 0.45, 0.56, 0.44, 0.07, 0.04, 1, 0)],
        )
    )
    sec = grades.replay_efficacy(conn, NOW)
    assert _labels(sec) == [
        "Signal",
        "Flag",
        "Horizon",
        "Hit rate",
        "Better than drift by",
        "Beats drift?",
        "Anti-signal?",
    ]
    assert _labels(sec, hidden=True) == [
        "Days flagged",
        "CI low",
        "CI high",
        "Drift alone",
        "Chance of a fluke",
    ]
    # keys are unchanged so the cell formatter still recognises them
    assert {c["key"] for c in sec["columns"] if c.get("hidden")} == {
        "n_days",
        "hit_ci_lo",
        "hit_ci_hi",
        "baseline",
        "perm_p",
    }
    assert sec["verdict"]["text"] == "1 beat the drift · 0 anti-signal · 0 noise"


# --- research-calibration ----------------------------------------------------

CAL_COLS = [
    "horizon",
    "n",
    "n_dates",
    "n_stated",
    "avg_p",
    "beat_rate",
    "brier",
    "brier_base_rate",
    "brier_kill",
    "avg_disagreement",
]
BIN_COLS = ["horizon", "p_bin", "n", "n_dates", "avg_p", "beat_rate", "brier"]


def _calibration(summary, bins):
    conn = _mem(
        _view("v_research_calibration", CAL_COLS, summary)
        + _view("v_research_calibration_bins", BIN_COLS, bins)
    )
    return grades.research_calibration(conn, NOW)


def test_research_calibration_columns_and_bins_read_as_words():
    sec = _calibration(
        [(63, 8, 6, 8, 0.6, 0.5, 0.31, 0.25, None, None)],
        [(63, 0.6, 5, 4, 0.62, 0.4, 0.3), (63, 0.3, 3, 3, 0.3, 0.67, 0.32)],
    )
    assert _labels(sec) == [
        "Horizon",
        "Said it would win",
        "Calls",
        "Average confidence",
        "Actually won",
        "Forecast error",
    ]
    assert _labels(sec, hidden=True) == ["Distinct dates"]
    assert [r["p_bin"] for r in sec["rows"]] == ["30–40%", "60–70%"]
    labels = [t["label"] for t in sec["tiles"]]
    assert labels[:2] == ["Forecast error", "Said vs won"]
    assert sec["tiles"][0]["value"] == "0.31"
    assert sec["tiles"][0]["band"] == "63 days out · guessing the base rate scores 0.25 · 8 calls"
    assert sec["tiles"][0]["tone"] == "off"
    assert sec["tiles"][1]["value"] == "60% vs 50%"


def test_research_calibration_chip_names_the_bias_once_five_calls_matured():
    over = _calibration([(63, 8, 6, 8, 0.6, 0.5, 0.31, 0.25, None, None)], [])
    assert over["verdict"] == {"text": "Overconfident: said 60%, won 50%", "tone": "off"}
    under = _calibration([(63, 8, 6, 8, 0.5, 0.6, 0.2, 0.25, None, None)], [])
    assert under["verdict"] == {"text": "Underconfident: said 50%, won 60%", "tone": "on"}
    even = _calibration([(63, 8, 6, 8, 0.58, 0.6, 0.2, 0.25, None, None)], [])
    assert even["verdict"] == {
        "text": "Confidence matched results: said 58%, won 60%",
        "tone": "mid",
    }
    thin = _calibration([(63, 4, 4, 4, 0.9, 0.2, 0.5, 0.25, None, None)], [])
    assert thin["verdict"] is None
