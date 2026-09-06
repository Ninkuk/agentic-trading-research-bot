"""Batch 2 of the card readability audit, data.py cards: the label pass on
the cards scored 3. Every card keeps every row; what changes is a chip, a
plain-English label, or which columns fold behind "more columns"."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import data  # noqa: E402

from sources.combiners.scorer import db as scorer_db  # noqa: E402

NOW = "2026-07-08T21:12:00+00:00"  # Phoenix date 2026-07-08, like populated_data_dir


def _sections(data_dir):
    return data.export_data(str(data_dir), NOW)["sections"]


def _labels(sec):
    return {c["key"]: c["label"] for c in sec["columns"]}


def _hidden(sec):
    return {c["key"] for c in sec["columns"] if c.get("hidden")}


def _scorer(tmp_path):
    conn = scorer_db.connect(str(tmp_path / "scorer.db"))
    scorer_db.ensure_schema(conn)
    return conn


# --- basis-breaks ------------------------------------------------------------


def test_basis_breaks_chip_counts_suspect_moves_and_caps_rows(tmp_path):
    conn = _scorer(tmp_path)
    for i in range(120):
        conn.executemany(
            "INSERT INTO prices (symbol, price_date, close) VALUES (?, ?, ?)",
            [(f"S{i}", "2026-06-30", 100.0), (f"S{i}", "2026-07-01", 40.0)],
        )
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["basis-breaks"]
    assert sec["verdict"] == {"text": "120 suspect price moves tonight", "tone": "off"}
    assert len(sec["rows"]) == 100 and sec["total"] == 120
    assert _labels(sec)["ratio"] == "Move (×)"


def test_basis_breaks_chip_reads_clean_when_nothing_broke(tmp_path):
    conn = _scorer(tmp_path)
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["basis-breaks"]
    assert sec["verdict"] == {"text": "no suspect moves", "tone": "on"}
    assert sec["rows"] == [] and sec["total"] == 0


# --- book / group / position heat --------------------------------------------


def test_book_heat_tiles_speak_plainly(populated_data_dir):
    sec = _sections(populated_data_dir)["book-heat"]
    tiles = {t["label"]: t for t in sec["tiles"]}
    assert set(tiles) == {
        "Positions",
        "Money at risk on a bad day",
        "Positions counted",
        "Book value",
        "Feeds missing",
    }
    assert tiles["Money at risk on a bad day"]["value"] == "0.45%"
    assert tiles["Money at risk on a bad day"]["band"] == "of the book · comfortable"
    assert tiles["Positions counted"]["value"] == "100%"
    assert tiles["Book value"]["value"] == "$10,000"
    assert tiles["Feeds missing"]["value"] == 0
    assert tiles["Feeds missing"]["band"] == "of the inputs the advisor needs"
    assert any("one-ATR" in b["body"] or "bad day" in b["body"] for b in sec["about"])


def test_group_heat_is_bets_with_at_risk_columns(populated_data_dir):
    sec = _sections(populated_data_dir)["group-heat"]
    assert sec["title"] == "Bets, not positions"
    assert _labels(sec) == {
        "bet": "Bet",
        "members": "Positions in it",
        "symbols": "Symbols",
        "heat_dollars": "At risk $",
        "heat_pct": "At risk %",
    }


def test_position_heat_labels_and_folded_detail(populated_data_dir):
    sec = _sections(populated_data_dir)["position-heat"]
    labels = _labels(sec)
    assert labels["heat_dollars"] == "At risk $"
    assert labels["heat_pct"] == "At risk %"
    assert labels["weight_pct"] == "Share of book %"
    assert labels["score_sum"] == "Signal lean"
    assert labels["atr_stale"] == "Volatility data old?"
    assert _hidden(sec) == {"group_name", "price"}


# --- cot-tails ---------------------------------------------------------------


def test_cot_tails_title_and_stretch_column(populated_data_dir):
    sec = _sections(populated_data_dir)["cot-tails"]
    assert sec["title"] == "Crowded futures bets"
    stretch = next(c for c in sec["columns"] if c["key"] == "cot_index")
    assert stretch["label"] == "How stretched (0–100)"
    assert stretch["term"] == "COT / positioning"


# --- regime-performance ------------------------------------------------------


def test_regime_performance_humanizes_regimes_and_refuses_a_thin_chip(populated_data_dir):
    sec = _sections(populated_data_dir)["regime-performance"]
    assert [r["regime"] for r in sec["rows"]] == ["Risk on"]
    assert sec["verdict"] == {"text": "Too few risk-on nights to grade yet", "tone": "mid"}


def test_regime_performance_chip_reads_the_longest_horizon(tmp_path):
    conn = _scorer(tmp_path)
    for i in range(5):
        for horizon, ret in ((5, 0.01), (21, 0.04)):
            conn.execute(
                "INSERT INTO regime_outcomes (composite_snapshot_id, composite_date,"
                " regime, horizon, entry_date, bench_entry_close, exit_date,"
                " bench_exit_close, bench_fwd_return, matured_at)"
                " VALUES (?, '2026-06-01', 'risk_on', ?, '2026-06-02', 500.0,"
                " '2026-06-09', 520.0, ?, ?)",
                (i + 1, horizon, ret, NOW),
            )
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["regime-performance"]
    assert sec["verdict"] == {
        "text": "Risk-on nights averaged +4.0% over 21 days",
        "tone": "on",
    }
    assert {r["regime"] for r in sec["rows"]} == {"Risk on"}


# --- research-reopens --------------------------------------------------------


def test_research_reopens_chip_counts_the_week_and_sorts_due_first(populated_data_dir):
    sec = _sections(populated_data_dir)["research-reopens"]
    # STNE's 2026-07-07 trigger is a day past NOW's Phoenix date: due this week
    assert sec["verdict"] == {"text": "1 due this week", "tone": "mid"}
    assert [r["ticker"] for r in sec["rows"]] == ["STNE", "GNTX", "GFI"]
    assert _labels(sec)["trigger"] == "Waiting for"


def test_research_reopens_chip_when_nothing_is_due(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "verdicts.log").write_text(
        "2026-07-01 GNTX UNPROVEN conditions=5 refuted=0 unknown=2 reopen=2026-08-20:q3-print\n"
    )
    sec = _sections(tmp_path / "data")["research-reopens"]
    assert sec["verdict"] == {"text": "nothing due this week", "tone": "mid"}


# --- scorecard ---------------------------------------------------------------


def test_scorecard_chip_counts_flagged_and_held(populated_data_dir):
    sec = _sections(populated_data_dir)["scorecard"]
    assert sec["verdict"] == {"text": "1 flagged tonight · 1 held", "tone": "mid"}
    coverage = next(c for c in sec["columns"] if c["key"] == "coverage")
    assert coverage["label"] == "Signals with data" and coverage["term"] == "Coverage"


# --- signal-recommendations --------------------------------------------------


def test_signal_recommendations_chip_and_folded_columns(populated_data_dir):
    sec = _sections(populated_data_dir)["signal-recommendations"]
    # one signal, graded only as "insufficient evidence": counted once, in words
    assert sec["verdict"] == {"text": "1 signal still unproven", "tone": "mid"}
    labels = _labels(sec)
    assert labels["avg_directional_excess"] == "Better than SPY by"
    excess = next(c for c in sec["columns"] if c["key"] == "avg_directional_excess")
    assert excess["term"] == "Directional excess"
    assert _hidden(sec) == {"via_crosswalk", "hit_ci_lo", "hit_ci_hi"}


# --- human-filter follow-up --------------------------------------------------


def test_human_filter_rows_withhold_averages_under_five_flags(tmp_path):
    conn = _scorer(tmp_path)
    conn.execute(
        "INSERT INTO registered_snapshots (composite_snapshot_id, composite_date,"
        " entry_date, registered_at, ticker_rows, signal_rows, skipped)"
        " VALUES (1, '2026-07-01', '2026-07-02', ?, 9, 1, 0)",
        (NOW,),
    )
    for i in range(8):
        conn.execute(
            "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date, symbol,"
            " score_sum, total, bullish, bearish, horizon, entry_date, entry_close,"
            " bench_entry_close, exit_date, exit_close, fwd_return, bench_fwd_return,"
            " matured_at) VALUES (1, '2026-07-01', ?, 3, 4, 2, 2, 5, '2026-07-02', 100.0,"
            " 500.0, '2026-07-09', 104.0, 0.04, 0.01, ?)",
            (f"F{i}", NOW),
        )
    for i in range(3):  # three journaled passes: too thin for an average
        conn.execute(
            "INSERT INTO decisions (symbol, action, composite_snapshot_id, composite_date,"
            " recorded_at) VALUES (?, 'passed', 1, '2026-07-01', ?)",
            (f"F{i}", NOW),
        )
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["human-filter"]
    by = {r["response"]: r for r in sec["rows"]}
    assert by["Passed"]["n"] == 3
    assert by["Passed"]["avg_dir_excess"] is None and by["Passed"]["avg_fwd_return"] is None
    skipped = by["Skipped (no journal entry)"]
    assert skipped["n"] == 5 and skipped["avg_dir_excess"] is not None
    assert any("fewer than 5" in b["body"] or "five" in b["body"] for b in sec["about"])
