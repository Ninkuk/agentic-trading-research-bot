"""Batch 1 of the card readability audit, data.py cards: pending, human-filter,
bucket-performance, signal-efficacy, candidate-efficacy, candidates. Each card
keeps every row it showed before; what changes is the headline (chip/tiles),
the column labels, and which columns fold behind "more columns"."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import data  # noqa: E402

from sources.combiners.scorer import db as scorer_db  # noqa: E402
from tests.conftest import _build_scorer_db, _build_stocks_db  # noqa: E402

NOW = "2026-08-07T04:13:00+00:00"


def _connect(tmp_path):
    conn = scorer_db.connect(str(tmp_path / "scorer.db"))
    scorer_db.ensure_schema(conn)
    conn.execute(
        "INSERT OR IGNORE INTO registered_snapshots (composite_snapshot_id, composite_date,"
        " entry_date, registered_at, ticker_rows, signal_rows, skipped)"
        " VALUES (1, '2026-07-01', '2026-07-02', ?, 9, 1, 0)",
        (NOW,),
    )
    return conn


def _outcome(conn, symbol, score_sum, fwd, bench, horizon=5, total=4, matured=True):
    """One matured (or pending) ticker outcome under snapshot 1."""
    conn.execute(
        "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date, symbol,"
        " score_sum, total, bullish, bearish, horizon, entry_date, entry_close,"
        " bench_entry_close, exit_date, exit_close, fwd_return, bench_fwd_return,"
        " matured_at) VALUES (1, '2026-07-01', ?, ?, ?, 2, 2, ?, '2026-07-02', 100.0,"
        " 500.0, ?, ?, ?, ?, ?)",
        (
            symbol,
            score_sum,
            total,
            horizon,
            "2026-07-09" if matured else None,
            104.0 if matured else None,
            fwd if matured else None,
            bench if matured else None,
            NOW if matured else None,
        ),
    )


def _acted(conn, symbol, side="buy"):
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, composite_snapshot_id, composite_date,"
        " opinion_score_sum, opinion_total, fill_date, fill_price, quantity, recorded_at)"
        " VALUES (?, 'acted', ?, 1, '2026-07-01', 3, 4, '2026-07-03', 100.0, 1.0, ?)",
        (symbol, side, NOW),
    )


def _sections(tmp_path):
    return data.export_data(str(tmp_path), NOW)["sections"]


def _labels(sec):
    return {c["key"]: c["label"] for c in sec["columns"]}


def _hidden(sec):
    return {c["key"] for c in sec["columns"] if c.get("hidden")}


# --- pending -----------------------------------------------------------------


def test_pending_chip_counts_the_queue_and_names_the_oldest_entry(tmp_path):
    conn = _connect(tmp_path)
    _outcome(conn, "OLD", 3, None, None, matured=False)
    conn.execute(
        "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date, symbol,"
        " score_sum, total, bullish, bearish, horizon, entry_date, entry_close, matured_at)"
        " VALUES (1, '2026-07-08', 'NEW', 0, 0, 0, 0, 21, '2026-07-08', 100.0, NULL)"
    )
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["pending"]
    assert sec["verdict"] == {
        "text": "2 opinions from 2 nights waiting to be graded, the oldest from 2026-07-02",
        "tone": "mid",
    }
    labels = _labels(sec)
    assert labels["composite_date"] == "Flag date"
    assert labels["symbol"] == "Symbol"
    assert labels["horizon"] == "Graded after (trading days)"
    assert labels["entry_date"] == "Entry date"


def test_pending_chip_counts_an_opinion_once_across_its_horizons(tmp_path):
    conn = _connect(tmp_path)
    for h in (5, 10, 21):
        conn.execute(
            "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date, symbol,"
            " score_sum, total, bullish, bearish, horizon, entry_date, entry_close, matured_at)"
            " VALUES (1, '2026-07-08', 'NEW', 0, 0, 0, 0, ?, '2026-07-08', 100.0, NULL)",
            (h,),
        )
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["pending"]
    assert sec["verdict"]["text"].startswith("1 opinion from 1 night waiting")
    assert sec["total"] == 3  # the table still discloses every horizon row


def test_pending_chip_is_absent_when_nothing_waits(tmp_path):
    conn = _connect(tmp_path)
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["pending"]
    assert sec["rows"] == [] and sec["verdict"] is None


# --- human-filter ------------------------------------------------------------


def test_human_filter_tile_withholds_an_average_under_five_flags(tmp_path):
    conn = _connect(tmp_path)
    for i in range(3):
        _outcome(conn, f"P{i}", 3, 0.10, 0.01)
        conn.execute(
            "INSERT INTO decisions (symbol, action, composite_snapshot_id, composite_date,"
            " recorded_at) VALUES (?, 'passed', 1, '2026-07-01', ?)",
            (f"P{i}", NOW),
        )
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["human-filter"]
    passed = next(t for t in sec["tiles"] if t["label"] == "Passed on")
    assert passed["value"] == "too few"
    assert passed["band"] == "3 flags · 5 days · 5 needed"


def test_human_filter_reads_the_skipped_flags_when_nothing_was_journaled(tmp_path):
    conn = _connect(tmp_path)
    for i in range(6):
        _outcome(conn, f"S{i}", 3, 0.03, 0.01)  # bull flag, +2% in the flag's direction
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["human-filter"]
    assert "error" not in sec
    assert sec["verdict"] == {
        "text": "Flags you skipped went on to gain +2.0% at 5 days",
        "tone": "on",
    }
    tiles = {t["label"]: t for t in sec["tiles"]}
    assert tiles["Skipped (no journal entry)"]["value"] == "+2.0%"
    assert tiles["Skipped (no journal entry)"]["band"] == "6 flags · 5 days"
    row = sec["rows"][0]
    assert row["response"] == "Skipped (no journal entry)"
    assert abs(row["avg_dir_excess"] - 0.02) < 1e-9
    labels = _labels(sec)
    assert labels["response"] == "You did"
    assert labels["n"] == "Flags"
    assert labels["avg_dir_excess"] == "Gain had you followed it"
    assert labels["avg_fwd_return"] == "Return"
    assert [a["heading"] for a in sec["about"]] == [
        "What a flag is",
        "Acted, passed, skipped",
        "Gain had you followed it",
    ]


def test_human_filter_compares_acted_to_skipped_when_both_are_thick(tmp_path):
    conn = _connect(tmp_path)
    for i in range(5):
        _outcome(conn, f"A{i}", 3, 0.05, 0.01)  # acted: +4%
        _acted(conn, f"A{i}")
    for i in range(5):
        _outcome(conn, f"K{i}", 3, 0.02, 0.01)  # skipped: +1%
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["human-filter"]
    assert sec["verdict"] == {
        "text": "Flags you acted on beat the ones you skipped by 3.0 points at 5 days",
        "tone": "on",
    }
    tiles = {t["label"]: t for t in sec["tiles"]}
    assert tiles["Acted on"]["value"] == "+4.0%"
    assert tiles["Skipped (no journal entry)"]["value"] == "+1.0%"
    assert {r["response"] for r in sec["rows"]} == {"Acted", "Skipped (no journal entry)"}


def test_human_filter_chip_refuses_a_thin_comparison(tmp_path):
    conn = _connect(tmp_path)
    _outcome(conn, "A0", 3, 0.05, 0.01)
    _acted(conn, "A0")
    for i in range(5):
        _outcome(conn, f"K{i}", 3, 0.02, 0.01)
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["human-filter"]
    # one acted flag is not a comparison; the skipped side still reads on its own
    assert sec["verdict"]["text"] == "Flags you skipped went on to gain +1.0% at 5 days"
    assert {t["label"] for t in sec["tiles"]} == {"Acted on", "Skipped (no journal entry)"}


# --- bucket-performance ------------------------------------------------------


def test_bucket_performance_chip_compares_strong_to_moderate_buckets(tmp_path):
    conn = _connect(tmp_path)
    for i in range(5):
        _outcome(conn, f"SB{i}", 4, 0.03, 0.01)  # strong_bull, every one a hit
    for i in range(5):
        _outcome(conn, f"B{i}", 2, 0.03 if i < 2 else -0.01, 0.01)  # bull, 2 of 5 hit
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["bucket-performance"]
    assert "error" not in sec
    assert sec["verdict"] == {
        "text": "Stronger flags did better: 100% right vs 40% at 5 days",
        "tone": "on",
    }
    labels = _labels(sec)
    assert labels["edge"] == "Better than chance by"
    assert labels["null_rate"] == "Chance alone"
    assert next(c for c in sec["columns"] if c["key"] == "null_rate")["term"] == "Base rate"
    assert all(isinstance(r["reliable"], bool) for r in sec["rows"])


def test_bucket_performance_chip_waits_for_five_per_bucket(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["bucket-performance"]
    assert sec["rows"]
    assert sec["verdict"] == {"text": "Too few graded flags to compare buckets", "tone": "mid"}


# --- signal-efficacy ---------------------------------------------------------


def test_signal_efficacy_folds_statistics_and_counts_verdicts(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["signal-efficacy"]
    assert _hidden(sec) == {"hit_ci_lo", "hit_ci_hi", "null_rate", "n_dates", "via_crosswalk"}
    labels = _labels(sec)
    assert labels["signal_id"] == "Signal"
    assert labels["n_bench"] == "Graded"
    assert labels["avg_directional_excess"] == "Better than SPY by"
    assert labels["recommendation"] == "Verdict"
    assert {r["recommendation"] for r in sec["rows"]} == {"insufficient evidence"}
    assert sec["verdict"] == {"text": "1 signal still unproven", "tone": "mid"}


# --- candidate-efficacy ------------------------------------------------------


def test_candidate_efficacy_tiles_count_beats_at_the_longest_horizon(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["candidate-efficacy"]
    assert sec["rows"]
    longest = max(r["horizon"] for r in sec["rows"])
    n = sum(r["n"] for r in sec["rows"] if r["horizon"] == longest)
    beats = sum(round(r["hit_rate"] * r["n"]) for r in sec["rows"] if r["horizon"] == longest)
    tiles = {t["label"]: t for t in sec["tiles"]}
    assert tiles["Beat SPY"]["value"] == f"{beats} of {n}"
    assert tiles["Beat SPY"]["band"] == f"{longest} trading days after joining the list"
    labels = _labels(sec)
    assert labels["growth_door"] == "Why it qualified"
    assert labels["branch"] == "What flagged it"
    assert labels["n"] == "Entries"
    assert labels["avg_excess"] == "Vs SPY"
    assert labels["avg_fwd_return"] == "Return"
    assert _hidden(sec) == {"screen_version"}
    assert any(a["heading"] == "The two doors" for a in sec["about"])


# --- candidates --------------------------------------------------------------


def test_candidates_hides_the_ratio_columns_and_counts_research(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    _build_stocks_db(d / "stocks.db")
    _build_scorer_db(d / "scorer.db")
    sc = scorer_db.connect(str(d / "scorer.db"))
    sc.execute(
        "INSERT INTO research_verdicts (symbol, verdict, verdict_date, recorded_at)"
        " VALUES ('ADBE', 'pass', '2026-07-01', ?)",
        (NOW,),
    )
    sc.commit()
    sc.close()
    (tmp_path / "research").mkdir()
    sec = data.export_data(str(d), NOW)["sections"]["candidates"]
    assert "error" not in sec
    assert sec["verdict"] == {"text": "2 names · 1 already researched", "tone": "mid"}
    assert _hidden(sec) == {
        "roic",
        "fcfYield",
        "fScore",
        "rsi",
        "accrualsPctAssets",
        "analystCount",
        "verdictDate",
        "fScoreEntry",
    }
    labels = _labels(sec)
    assert labels["growthDoor"] == "Why it qualified"
    assert labels["ch6m"] == "6-month change %"
    assert any(a["heading"] == "The hidden columns" for a in sec["about"])
