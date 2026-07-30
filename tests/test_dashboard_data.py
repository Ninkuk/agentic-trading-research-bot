"""Tests for the data.json exporter scaffold: schema shape, per-section
degradation on an empty/missing data dir, and the Phoenix-date edition
formatter. Positive-path coverage (real rows behind a real section) lands
with each section's own task (4-8); this file only exercises the scaffold
itself — the resilience contract and the document envelope."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import data  # noqa: E402

sys.path.insert(
    0, str(Path(__file__).resolve().parent)
)  # tests/ itself, for a bare `conftest` import
from conftest import NOW, ROLLOVER_NOW, _build_composite_db  # noqa: E402


def test_empty_data_dir_degrades_not_crashes(tmp_path):
    doc = data.export_data(str(tmp_path), NOW)
    assert doc["schema_version"] == 1
    assert doc["generated_at"] == NOW
    for sid, body in doc["sections"].items():
        assert "error" in body, f"{sid} should degrade on empty dir"
        assert body["title"] and body["kicker"] and body["note"]


def test_edition_date_is_phoenix():
    doc = data.export_data(str(Path("/nonexistent")), ROLLOVER_NOW)
    assert doc["edition_date"] == "July 7, 2026"  # UTC July 8 04:13 = Phoenix July 7


def test_glossary_embedded(tmp_path):
    doc = data.export_data(str(tmp_path), NOW)
    assert len(doc["glossary"]) >= 10


def test_document_is_json_serializable(tmp_path):
    json.dumps(data.export_data(str(tmp_path), NOW))


def test_schema_top_level_keys_locked(tmp_path):
    assert set(data.export_data(str(tmp_path), NOW)) == {
        "schema_version",
        "generated_at",
        "edition_date",
        "snapshot_number",
        "hero",
        "sections",
        "tickers",
        "glossary",
    }


def test_regime_section_exports_verdict_and_tiles(populated_data_dir):
    doc = data.export_data(populated_data_dir, NOW)
    sec = doc["sections"]["regime"]
    assert "error" not in sec
    assert sec["verdict"]["tone"] in ("on", "off", "mid")
    assert any(t.get("band") for t in sec["tiles"])


def test_regime_timeline_rows_oldest_first(populated_data_dir):
    rows = data.export_data(populated_data_dir, NOW)["sections"]["regime-timeline"]["rows"]
    assert rows == sorted(rows, key=lambda r: r["date"])
    assert {"date", "regime", "vix"} <= set(rows[0])


def test_macro_drivers_history_bounded(populated_data_dir):
    tiles = data.export_data(populated_data_dir, NOW)["sections"]["macro-drivers"]["tiles"]
    assert len(tiles) == 3
    for t in tiles:
        assert len(t["history"]) <= 90
        assert t["band"] is not None


def test_streak_nights_counts_leading_run_of_matching_regime(tmp_path):
    """Seed [risk_off, risk_on, risk_on] chronologically (oldest first) —
    the latest snapshot's regime (risk_on) matches the one before it but not
    the oldest, so the streak is 2, not 3."""
    from sources.combiners.composite import db as composite_db

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    conn = composite_db.connect(str(data_dir / "composite.db"))
    composite_db.ensure_schema(conn)
    for captured_at, regime, vix in (
        ("2026-07-06T21:13:00+00:00", "risk_off", 28.0),
        ("2026-07-07T21:13:00+00:00", "risk_on", 16.0),
        (NOW, "risk_on", 15.0),
    ):
        sid = composite_db.write_snapshot(conn, captured_at, 1)
        conn.execute(
            "INSERT INTO market_regime (snapshot_id, vix, regime, inputs_expected,"
            " inputs_present) VALUES (?, ?, ?, 1, 1)",
            (sid, vix, regime),
        )
    conn.commit()
    conn.close()

    doc = data.export_data(str(data_dir), NOW)
    assert doc["sections"]["regime"]["verdict"]["text"] == "Risk-on, 2nd night"


def test_scorecard_rows_carry_history_and_flag(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["scorecard"]
    row = sec["rows"][0]  # rows ordered by |score_sum| desc: row 0 is headline
    assert {"symbol", "score_sum", "flagged", "history"} <= set(row)
    assert row["symbol"] == "FLAG1"
    assert row["flagged"] is True
    assert isinstance(row["history"], list)
    assert sec["total"] == len(sec["rows"]) == 2


def test_scorecard_unflagged_row_not_in_headline_has_no_history(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["scorecard"]
    plain = next(r for r in sec["rows"] if r["symbol"] == "PLAIN1")
    assert plain["flagged"] is False
    assert isinstance(plain["history"], list)  # still headline: only 2 scored tickers total


def test_scorecard_history_only_for_headline_rows(tmp_path):
    """_build_composite_db seeds only FLAG1 (flagged) + PLAIN1 by default —
    extended here with 20 extra unflagged tickers (one signal each, so
    total=1 never crosses v_flagged's total>=2 gate) to get >15 unflagged
    rows and exercise the headline-only history size cap."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    extras = [{"symbol": f"EXTRA{i:02d}", "score": 2} for i in range(20)]
    _build_composite_db(data_dir / "composite.db", extra_tickers=extras)

    sec = data.export_data(str(data_dir), NOW)["sections"]["scorecard"]
    tail = [r for r in sec["rows"] if not r["flagged"]][15:]
    assert tail and all(r["history"] is None for r in tail)
    head = [r for r in sec["rows"] if not r["flagged"]][:1]
    assert head and head[0]["history"] is not None


def test_scorecard_columns_have_direction_metadata(populated_data_dir):
    cols = data.export_data(populated_data_dir, NOW)["sections"]["scorecard"]["columns"]
    assert any(c["direction"] is None for c in cols)  # diverging score: no direction arrow
    coverage = next(c for c in cols if c["key"] == "coverage")
    assert coverage["term"] == "Coverage"


def test_headline_symbols_includes_flagged(populated_data_dir):
    conn = data._ro(populated_data_dir, "composite.db")
    try:
        assert "FLAG1" in data.headline_symbols(conn)
    finally:
        conn.close()


def test_flagged_tickers_helper(populated_data_dir):
    assert data.flagged_tickers(populated_data_dir) == ["FLAG1"]


def test_flagged_tickers_helper_degrades_on_missing_db(tmp_path):
    assert data.flagged_tickers(str(tmp_path)) == []


def test_candidates_section_exports_screened_rows(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["candidates"]
    assert "error" not in sec
    assert sec["rows"], "fixture's ADBE/PEGA should pass the screen"
    row = sec["rows"][0]
    assert {"symbol", "sector", "marketCap", "roic", "fcfYield", "fScore", "rsi", "ch6m"} <= set(
        row
    )
    assert row["marketCap"] == 8.4e10  # raw dollars, not pre-divided into $B


def test_research_reopens_dated_upcoming_event_and_superseded(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["research-reopens"]
    by_ticker = {r["ticker"]: r for r in sec["rows"]}
    assert by_ticker["STNE"]["due"] == "2026-07-07"  # NOW's Phoenix date is 2026-07-08: due
    assert by_ticker["GNTX"]["due"] == "2026-08-20"  # ahead of today: upcoming
    assert by_ticker["GFI"]["due"] is None  # event-shaped trigger, no date
    assert by_ticker["GFI"]["trigger"] == "tarkwa-renewal"
    assert "OLD" not in by_ticker  # re-researched after its trigger: superseded, no reopen=
    assert by_ticker["STNE"]["verdict"] == "UNPROVEN"
    assert by_ticker["STNE"]["thesis_path"] == "research/STNE-2026-07-01.md"


def test_efficacy_rows_have_ci_for_dotplot(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["signal-efficacy"]
    r = sec["rows"][0]
    assert {
        "hit_rate",
        "hit_ci_lo",
        "hit_ci_hi",
        "null_rate",
        "via_crosswalk",
        "recommendation",
    } <= set(r)
    assert sec["caveat"]  # every track-record section explains its own trust level


def test_signal_efficacy_carries_signal_id(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["signal-efficacy"]
    assert any(r["signal_id"] == "sig_test_a" for r in sec["rows"])


def test_bucket_performance_exports_matured_buckets(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["bucket-performance"]
    buckets = {r["bucket"] for r in sec["rows"]}
    assert "strong_bull" in buckets
    assert "thin" in buckets
    assert sec["caveat"]


def test_human_filter_exports_response_rows(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["human-filter"]
    assert any(r["response"] == "acted" for r in sec["rows"])
    assert sec["caveat"]


def test_regime_performance_exports_raw_fraction(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["regime-performance"]
    row = next(r for r in sec["rows"] if r["regime"] == "risk_on")
    assert row["avg_bench_return"] == 0.04  # raw fraction, no _pct formatting
    assert sec["caveat"]


def test_pending_rows_and_total(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["pending"]
    assert sec["total"] >= len(sec["rows"])  # LIMIT 100 port keeps the full count
    assert {"symbol", "horizon"} <= set(sec["rows"][0])
    assert any(r["symbol"] == "PEND1" for r in sec["rows"])
    assert sec["caveat"]


def test_pending_cap_preserves_total_count(tmp_path):
    """150 unmatured ticker_outcomes: rows are capped at 100 (the LIMIT 100
    port) but `total` still reports the real count — "never remove a
    number" (mirrors the legacy test_pending_cap_is_disclosed)."""
    from sources.combiners.scorer import db as scorer_db

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    conn = scorer_db.connect(str(data_dir / "scorer.db"))
    scorer_db.ensure_schema(conn)
    for i in range(150):
        conn.execute(
            "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date,"
            " symbol, score_sum, total, bullish, bearish, horizon, entry_date,"
            " entry_close, matured_at) VALUES (1, ?, ?, 0, 0, 0, 0, 5, ?, 100.0, NULL)",
            (NOW, f"T{i}", NOW),
        )
    conn.commit()
    conn.close()

    sec = data.export_data(str(data_dir), NOW)["sections"]["pending"]
    assert sec["total"] == 150
    assert len(sec["rows"]) == 100


def test_basis_breaks_exports_rows_and_no_caveat(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["basis-breaks"]
    assert any(r["symbol"] == "ACME" for r in sec["rows"])
    assert sec["caveat"] is None  # integrity check, not a grade — deliberate


def test_recommendation_section_verdict_counts(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["plan-001-report"]
    assert sec["verdict"] is None or sec["verdict"]["tone"] in ("on", "off", "mid")
    assert any(r["signal_id"] == "sig_test_a" for r in sec["rows"])
    assert sec["caveat"]


def test_trader_scorecard_is_text(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["plan-004-scorecard"]
    assert "text_lines" in sec and isinstance(sec["text_lines"], list)
    assert any("Trader Decision-Quality Scorecard" in line for line in sec["text_lines"])
    assert any("acted" in line for line in sec["text_lines"])
    assert sec["caveat"]


def test_candidate_efficacy_exports_branch_rows(populated_data_dir):
    sec = data.export_data(populated_data_dir, NOW)["sections"]["candidate-efficacy"]
    assert sec["rows"], "fixture's matured candidate episode should grade"
    for r in sec["rows"]:
        assert r["branch"] in {"rsi", "drawdown", "both"}
    assert sec["caveat"]


def test_research_reopens_exports_relative_thesis_paths(tmp_path):
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "verdicts.log").write_text(
        "2026-07-27 STNE UNPROVEN conditions=6 refuted=0 unknown=3"
        " reopen=2026-08-13:q2-print-cost-of-risk\n",
        encoding="utf-8",
    )  # real line shape (verified): <date> <TICKER> <SOUND|FLAWED|UNPROVEN>
    # conditions=n refuted=n unknown=n [reopen=<date|event>:<slug>]
    sec = data.export_data(str(tmp_path / "data"), NOW, repo_root=str(tmp_path))["sections"][
        "research-reopens"
    ]
    assert all(
        not r["thesis_path"].startswith("http") for r in sec.get("rows", []) if r["thesis_path"]
    )
