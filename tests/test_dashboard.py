"""Tests for the zero-dependency nightly HTML dashboard generator.

Offline, like the rest of the suite. Fixtures build real per-combiner schemas
via each combiner's own `db.ensure_schema` (never a hand-rolled replica of
production table/view DDL) — that is the whole point: a hand-rolled mimic of
a production schema is exactly the drift risk this file exists to catch, so
if a combiner view's shape changes, these fixtures either keep working (real
schema) or a renderer's SQL breaks loudly here instead of silently blanking a
section on the live dashboard.

Two kinds of coverage:
  * resilience — pointing the generator at an empty data dir (every section
    degrades to 'unavailable' rather than crashing) and self-containment
    asserted on the emitted HTML string.
  * positive path — a `populated_data_dir` fixture with real rows in all
    three DBs, so every one of the 16 section renderers is exercised against
    actual data, and `test_no_populated_section_degrades` (parametrized over
    every registered section) fails loudly if a renderer's SQL ever drifts
    from the schema it reads.
"""

import re
import sqlite3
import sys
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import dashboard  # noqa: E402

from sources.combiners.advisor import db as advisor_db  # noqa: E402
from sources.combiners.composite import catalog as composite_catalog  # noqa: E402
from sources.combiners.composite import db as composite_db  # noqa: E402
from sources.combiners.scorer import db as scorer_db  # noqa: E402

NOW = "2026-07-08T21:13:00+00:00"


def _make_scorer_pending_db(path, n_pending):
    conn = scorer_db.connect(str(path))
    scorer_db.ensure_schema(conn)
    for i in range(n_pending):
        conn.execute(
            "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date, symbol,"
            " score_sum, total, bullish, bearish, horizon, entry_date, entry_close,"
            " matured_at) VALUES (1, ?, ?, 0, 0, 0, 0, 5, ?, 100.0, NULL)",
            (NOW, f"T{i}", NOW),
        )
    conn.commit()
    conn.close()


def _make_composite_db(path, regime="risk_on", vix=16.1, symbol=None, score_sum=5, tickers=None):
    """`tickers` (extra to the single `symbol`/`score_sum` pair) is a list of
    dicts with keys symbol, score_sum, total, bullish, bearish, in_portfolio
    (last defaults to 0) — for fixtures that need many scorecard rows with
    independently-controlled total (the flagged-truncation bug needs total
    to diverge from |score_sum| ranking).

    Builds on composite/db.py's real `ensure_schema` (not a hand-rolled
    replica) — schema drift between this fixture and production is
    structurally impossible. ticker_scores/market_regime rows are still
    inserted directly (rather than derived via write_ticker_scores from
    signal_values) because several callers need combinations — e.g.
    score_sum=5 with total=2 — that no real per-signal scoring could ever
    produce; that is the whole point of some of those tests."""
    conn = composite_db.connect(str(path))
    composite_db.ensure_schema(conn)
    conn.execute(
        "INSERT INTO snapshots VALUES (1, ?, 10, 10, 0)",
        (NOW,),
    )
    conn.execute(
        "INSERT INTO market_regime VALUES"
        " (1, -0.1, 0, 3.05, ?, 0, 0.42, 0, 0, 8, -12.3, 4.1, ?, 10, 10)",
        (vix, regime),
    )
    if symbol:
        conn.execute(
            "INSERT INTO ticker_scores VALUES (1, ?, 5, 0, 5, ?, 0.417, 0.5, 1)",
            (symbol, score_sum),
        )
    for t in tickers or []:
        conn.execute(
            "INSERT INTO ticker_scores VALUES (1, ?, ?, ?, ?, ?, 0.417, 0.5, ?)",
            (
                t["symbol"],
                t["bullish"],
                t["bearish"],
                t["total"],
                t["score_sum"],
                t.get("in_portfolio", 0),
            ),
        )
    conn.commit()
    conn.close()


def _make_advisor_db(path, equity=200.0, positions=None, sources_failed=0):
    conn = advisor_db.connect(str(path))
    advisor_db.ensure_schema(conn)
    conn.execute(
        "INSERT INTO snapshots VALUES (1, ?, ?, 50.0, 100.0, ?, ?, 'risk_on', ?)",
        (NOW, equity, NOW, NOW, sources_failed),
    )
    for symbol, score_sum in positions or []:
        conn.execute(
            "INSERT INTO position_heat VALUES"
            " (1, ?, NULL, 10, 100.0, 2.0, 10.0, ?, 0.42, 0.0021, 0.5, ?, 0, 1, 1, 0)",
            (symbol, NOW, score_sum),
        )
    conn.commit()
    conn.close()


def test_sparkline_needs_two_points():
    assert "no data" in dashboard._sparkline_svg([])
    assert "no data" in dashboard._sparkline_svg([("risk_on", 16.0)])


def test_sparkline_emits_inline_polyline_no_external_refs():
    svg = dashboard._sparkline_svg([("risk_on", 16.0), ("mixed", 18.0), ("risk_off", 25.0)])
    assert "<polyline" in svg and "points=" in svg
    # inline only — no external asset references of any kind
    assert "http" not in svg and "xlink" not in svg


def test_sparkline_flat_series_does_not_divide_by_zero():
    # identical VIX across points -> zero range; must not raise
    svg = dashboard._sparkline_svg([("risk_on", 16.0), ("risk_on", 16.0)])
    assert "<polyline" in svg


def test_regime_badge_colors():
    assert "risk-on" in dashboard._regime_badge("risk_on")
    assert "risk-off" in dashboard._regime_badge("risk_off")
    assert "mixed" in dashboard._regime_badge("mixed")


def test_recommendation_badge_all_states():
    for state in ("keep", "watch", "anti-signal", "insufficient evidence"):
        assert dashboard._rec_badge(state)  # non-empty span, never raises


def test_build_page_degrades_when_all_dbs_missing(tmp_path):
    # empty data dir: every section's mode=ro connect fails -> unavailable,
    # never a crash; the whole page still assembles.
    html = dashboard.build_page(str(tmp_path), NOW)
    assert html.startswith("<!doctype html>") or "<html" in html
    assert html.count('class="unavailable"') >= 8  # most sections degrade
    # all 12 catalogued sections are present by id even when empty
    for sid in dashboard.SECTION_IDS:
        assert f'id="{sid}"' in html


# An external asset can only be pulled in through one of these carriers. The
# check is a property of the markup, not a blacklist of host-ish words: "cdn"
# as a bare substring both false-positives on page *data* (CDNA is a real
# ticker in composite.db) and misses a protocol-relative <img src="//cdn.x/y">.
# Every carrier below needs punctuation a symbol or date can never contain.
_EXTERNAL_ASSET_CARRIERS = ("src=", "href=", "<link", "<script", "@font-face", "@import")


def _assert_no_external_asset(html: str) -> None:
    lower = html.lower()
    for carrier in _EXTERNAL_ASSET_CARRIERS:
        assert carrier not in lower, f"external-asset carrier {carrier!r} in page"
    assert "http://" not in lower and "https://" not in lower
    # url(...) is legal only as an internal SVG fragment ref, e.g. url(#dashfade)
    assert re.findall(r"url\((?!#)", lower) == [], "url() pointing outside the document"


def test_build_page_is_self_contained(tmp_path):
    html = dashboard.build_page(str(tmp_path), NOW)
    _assert_no_external_asset(html)
    assert "<style>" in html  # CSS is inlined in-head


def test_self_containment_holds_for_real_world_tickers(tmp_path):
    """Page *data* must never be able to trip the self-containment check.

    The old assertion forbade the substring "cdn" anywhere in the output. It
    passed only because it rendered an empty data dir: `composite.db` holds the
    real ticker CDNA, so the moment the page has rows the blacklist fires on a
    document that is perfectly self-contained. Carriers, not words.
    """
    _make_composite_db(tmp_path / "composite.db", symbol="CDNA", score_sum=5)
    html = dashboard.build_page(str(tmp_path), NOW)
    assert "CDNA" in html  # the row really rendered; we are not asserting on an empty page
    assert "cdn" in html.lower()  # ...and it really does contain the old forbidden substring
    _assert_no_external_asset(html)


def test_score_cell_clamps_and_signs():
    saturated = dashboard._score_cell(9, 9, 0, True)
    assert "width:50%" in saturated and "+9" in saturated and '<i class="p"' in saturated
    down = dashboard._score_cell(-2, 0, 1, False)
    assert "-2" in down and '<i class="n"' in down
    unsaturated = dashboard._score_cell(3, 2, 0, False)
    assert "width:30%" in unsaturated


def test_pill_class_for_every_recommendation():
    for state in ("keep", "watch", "anti-signal", "insufficient evidence"):
        badge = dashboard._rec_badge(state)
        # extract the class actually applied and confirm _STYLE defines it
        cls = badge.split('class="pill ')[1].split('"')[0]
        assert f".pill.{cls}" in dashboard._STYLE or f",.pill.{cls}" in dashboard._STYLE


def test_reliability_meter_reads_n_bench_not_n_matured():
    low = dashboard._reliability_meter(9, 30)
    assert 'class="fil low"' in low and "9 / 30" in low
    assert "matured" not in low
    full = dashboard._reliability_meter(31, 30)
    assert 'class="fil low"' not in full and "31 / 30" in full
    assert "width:100%" in full


def test_ci_bar_clamps_and_shows_numbers():
    bar = dashboard._ci_bar(0.57, 0.44, 0.71)
    assert "57%" in bar and "44" in bar and "71" in bar
    left = int(bar.split('class="rng" style="left:')[1].split("%")[0])
    width = int(bar.split("width:")[1].split("%")[0])
    assert left + width <= 100
    null_bar = dashboard._ci_bar(None, None, None)
    assert "—" in null_bar and 'class="est"' not in null_bar


def test_yn_helper():
    assert dashboard._yn(1) == "yes"
    assert dashboard._yn(0) == "no"
    assert dashboard._yn(None) == "—"


def test_regime_expander_shows_raw_curve_spread(tmp_path):
    _make_composite_db(tmp_path / "composite.db")
    conn = dashboard._ro(str(tmp_path), "composite.db")
    try:
        html = dashboard._regime(conn, NOW)
    finally:
        conn.close()
    assert "10y–2y spread" in html
    assert "-0.10" in html or "-0.1" in html
    assert "<summary>All regime inputs</summary>" in html
    assert "All 10 regime inputs" not in html


def test_flagged_ticker_never_truncated(tmp_path):
    # 15 unflagged rows with a HIGHER |score_sum| (5) but total=2 (below the
    # v_flagged total>=3 gate) outrank a flagged ticker (|score_sum|=4,
    # total=3) under ORDER BY ABS(score_sum) DESC LIMIT 15 -> without the
    # union fix, the flagged ticker falls to rank 16 and is dropped.
    unflagged = [
        {"symbol": f"U{i}", "score_sum": 5, "total": 2, "bullish": 2, "bearish": 0}
        for i in range(15)
    ]
    flagged_ticker = {"symbol": "FLAGD", "score_sum": 4, "total": 3, "bullish": 3, "bearish": 0}
    _make_composite_db(tmp_path / "composite.db", symbol=None, tickers=[*unflagged, flagged_ticker])
    conn = dashboard._ro(str(tmp_path), "composite.db")
    try:
        html = dashboard._scorecard(conn, NOW)
    finally:
        conn.close()
    # Isolate the headline table from the full-universe expander below it —
    # the expander always has every row, so checking the whole `html` string
    # would pass even without the union fix.
    headline_html = html.split("<details>")[0]
    assert "FLAGD" in headline_html


def test_scorecard_expander_counts_real_rows(tmp_path):
    tickers = [
        {"symbol": f"T{i}", "score_sum": i % 5, "total": 3, "bullish": 2, "bearish": 1}
        for i in range(20)
    ]
    _make_composite_db(tmp_path / "composite.db", symbol=None, tickers=tickers)
    conn = dashboard._ro(str(tmp_path), "composite.db")
    try:
        html = dashboard._scorecard(conn, NOW)
    finally:
        conn.close()
    assert "Show all 20 scored tickers" in html
    assert "214" not in html


def test_signal_efficacy_has_show_all_expander(tmp_path):
    # A real signal_outcomes row through scorer/db.py's own ensure_schema and
    # v_signal_efficacy — not a hand-rolled view mimicking its column set.
    conn = scorer_db.connect(str(tmp_path / "scorer.db"))
    scorer_db.ensure_schema(conn)
    conn.execute(
        "INSERT INTO signal_outcomes (composite_snapshot_id, composite_date,"
        " signal_id, entity, score, via_crosswalk, horizon, entry_date,"
        " entry_close, benchmark, bench_entry_close, exit_date, exit_close,"
        " fwd_return, bench_fwd_return, matured_at)"
        " VALUES (1, '2026-07-01', 'fred:t10y2y', 'GME', 1, 0, 5, '2026-07-02',"
        " 100.0, 'SPY', 500.0, '2026-07-09', 106.2, 0.031, 0.0, ?)",
        (NOW,),
    )
    conn.commit()
    conn.close()
    ro = dashboard._ro(str(tmp_path), "scorer.db")
    try:
        html = dashboard._signal_efficacy(ro, NOW)
    finally:
        ro.close()
    assert "Show all 1 signals" in html


def test_view_table_renders_headers_from_description():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE toy (name TEXT, note TEXT)")
    conn.execute("INSERT INTO toy VALUES (?, ?)", ("plain", "<script>alert(1)</script>"))
    conn.commit()

    html = dashboard._view_table(conn, "SELECT name, note FROM toy", empty="none yet")
    assert "<th" in html and ">name<" in html and ">note<" in html
    assert "&lt;script&gt;" in html
    assert "<script>alert" not in html

    empty_html = dashboard._view_table(conn, "SELECT name, note FROM toy WHERE 0", empty="none yet")
    assert "none yet" in empty_html


def test_view_table_aligns_only_numeric_columns():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE toy (name TEXT, n INT, x REAL, code TEXT)")
    conn.execute("INSERT INTO toy VALUES (?, ?, ?, ?)", ("risk_on", 5, 0.5, "007"))
    conn.commit()

    html = dashboard._view_table(conn, "SELECT name, n, x, code FROM toy", empty="none")
    # text columns: header and cell carry no num class
    assert "<th>name</th>" in html
    assert "<td>risk_on</td>" in html
    # digits-as-text in a TEXT column is still non-numeric
    assert "<th>code</th>" in html
    assert "<td>007</td>" in html
    # numeric columns: header and cell are right-aligned
    assert '<th class="num">n</th>' in html
    assert '<th class="num">x</th>' in html
    assert '<td class="num">5</td>' in html
    assert '<td class="num">0.5</td>' in html


def test_view_table_all_null_column_is_not_numeric():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE toy (label TEXT, maybe REAL)")
    conn.execute("INSERT INTO toy VALUES (?, NULL)", ("a",))
    conn.commit()
    html = dashboard._view_table(conn, "SELECT label, maybe FROM toy", empty="none")
    # an all-None column is non-numeric (no num class) and renders empty, no crash
    assert "<th>maybe</th>" in html
    assert "<td></td>" in html


def test_view_table_applies_formatter_map():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE toy (x REAL)")
    conn.execute("INSERT INTO toy VALUES (0.5)")
    conn.commit()
    html = dashboard._view_table(conn, "SELECT x FROM toy", empty="none", fmt={"x": dashboard._pct})
    assert "50.0%" in html
    assert ">0.5<" not in html  # raw fraction not shown
    assert '<td class="num">50.0%</td>' in html  # formatted column stays right-aligned


def test_regime_performance_shows_percent_returns(tmp_path):
    # A real regime_outcomes row + scorer/db.py's own v_regime_performance —
    # not a hand-rolled table/view pair reproducing its shape.
    conn = scorer_db.connect(str(tmp_path / "scorer.db"))
    scorer_db.ensure_schema(conn)
    conn.execute(
        "INSERT INTO regime_outcomes (composite_snapshot_id, composite_date, regime,"
        " horizon, entry_date, bench_entry_close, exit_date, bench_exit_close,"
        " bench_fwd_return, matured_at)"
        " VALUES (1, '2026-07-01', 'risk_on', 5, '2026-07-02', 500.0,"
        " '2026-07-09', 506.15, 0.0123, ?)",
        (NOW,),
    )
    conn.commit()
    conn.close()
    ro = dashboard._ro(str(tmp_path), "scorer.db")
    try:
        html = dashboard._regime_performance(ro, NOW)
    finally:
        ro.close()
    assert "%" in html
    assert "0.0123" not in html  # raw fraction never shown


def test_new_sections_registered():
    for sid in ("regime-performance", "pending", "basis-breaks", "position-heat"):
        assert sid in dashboard.SECTION_IDS
    for entry in dashboard.SECTIONS:
        assert len(entry) == 6
        _sid, _title, _db_name, _fn, kicker, note = entry
        assert kicker
        assert note


def test_pending_cap_is_disclosed(tmp_path):
    _make_scorer_pending_db(tmp_path / "scorer.db", n_pending=150)
    conn = dashboard._ro(str(tmp_path), "scorer.db")
    try:
        html = dashboard._pending(conn, NOW)
    finally:
        conn.close()
    assert "150" in html
    assert 'class="cap"' in html


def test_pending_no_cap_note_under_limit(tmp_path):
    _make_scorer_pending_db(tmp_path / "scorer.db", n_pending=10)
    conn = dashboard._ro(str(tmp_path), "scorer.db")
    try:
        html = dashboard._pending(conn, NOW)
    finally:
        conn.close()
    assert 'class="cap"' not in html


def test_position_heat_hides_snapshot_id(tmp_path):
    _make_advisor_db(tmp_path / "advisor.db", equity=200.0, positions=[("AAPL", 3), ("MSFT", -2)])
    conn = dashboard._ro(str(tmp_path), "advisor.db")
    try:
        html = dashboard._position_heat(conn, NOW)
    finally:
        conn.close()
    assert "snapshot_id" not in html
    assert "AAPL" in html and "MSFT" in html


def test_section_wrapper_keeps_plain_id():
    html = dashboard._render_section(
        "regime", "Regime", "composite.db", lambda c, n: "body", "Macro", "note text", "", NOW
    )
    assert 'id="regime"' in html
    assert 'aria-labelledby="s-regime"' in html


def test_sparkline_maps_value_to_height():
    # Callers pass newest-first; here the newest snapshot (series[0]) has
    # the max VIX, so after the internal reverse it lands last in render
    # order. Its y must be smaller (higher on screen) than the oldest/min
    # point's y — asserts the value->height scale isn't inverted.
    svg = dashboard._sparkline_svg([("risk_on", 30.0), ("risk_on", 10.0)])
    ys = [float(m.group(1)) for m in re.finditer(r'cy="([\d.]+)"', svg)]
    assert len(ys) == 2
    assert ys[-1] < ys[0]


def test_hero_degrades_on_empty_dir(tmp_path):
    html = dashboard._hero_read(str(tmp_path), NOW)
    assert 'class="read"' in html
    assert "$None" not in html
    assert "1 positions" not in html


def test_hero_clause_logs_failure_type_only(capsys):
    def boom(_data_dir):
        raise ValueError("secret=abc123")

    assert dashboard._hero_clause(boom, "unused") is None
    err = capsys.readouterr().err
    assert "ValueError" in err  # the exception type is logged
    assert "secret" not in err and "abc123" not in err  # message never leaks


def test_hero_all_dbs_missing_falls_back(tmp_path):
    # every clause fails -> exactly the single honest fallback line
    assert dashboard._hero_read(str(tmp_path), NOW) == dashboard._HERO_FALLBACK


def test_hero_survives_missing_advisor_db(tmp_path):
    # composite only: the advisor-backed clauses fail, but the read still
    # renders the regime + flagged-ticker lines instead of vanishing.
    _make_composite_db(
        tmp_path / "composite.db", regime="risk_off", vix=25.5, symbol="NVDA", score_sum=5
    )
    html = dashboard._hero_read(str(tmp_path), NOW)
    assert html != dashboard._HERO_FALLBACK
    assert '<b class="off">' in html  # regime sentence present
    assert "NVDA" in html  # flagged-ticker sentence present
    assert "Your book" not in html  # advisor clause dropped, not faked


def test_hero_survives_missing_composite_db(tmp_path):
    # advisor only: the composite-backed clauses fail, but the book line renders.
    _make_advisor_db(tmp_path / "advisor.db", equity=200.0, positions=[])
    html = dashboard._hero_read(str(tmp_path), NOW)
    assert html != dashboard._HERO_FALLBACK
    assert "Your book holds" in html
    assert "The market is" not in html  # regime clause dropped, not faked


def test_hero_no_book_makes_no_disagreement_claim(tmp_path):
    claim = "nothing you own is being second-guessed"
    # advisor snapshot with zero positions -> the reassuring sentence appears
    _make_advisor_db(tmp_path / "advisor.db", equity=200.0, positions=[])
    with_book = dashboard._hero_read(str(tmp_path), NOW)
    assert claim in with_book
    # advisor.db absent -> the claim must NOT appear (we have no positions data)
    (tmp_path / "advisor.db").unlink()
    no_book = dashboard._hero_read(str(tmp_path), NOW)
    assert claim not in no_book


def test_hero_pluralizes(tmp_path):
    _make_composite_db(tmp_path / "composite.db")
    _make_advisor_db(tmp_path / "advisor.db", equity=200.0, positions=[("AAPL", 2)])
    html = dashboard._hero_read(str(tmp_path), NOW)
    assert ">1</span> position" in html
    assert ">1</span> positions" not in html
    assert "$None" not in html


def test_hero_riskoff_color(tmp_path):
    _make_composite_db(tmp_path / "composite.db", regime="risk_off", vix=25.5)
    _make_advisor_db(tmp_path / "advisor.db", positions=[])
    html = dashboard._hero_read(str(tmp_path), NOW)
    assert '<b class="off">' in html
    assert "risk-off" in html


def test_write_dashboard_is_atomic_replace(tmp_path):
    out = tmp_path / "sub" / "dashboard.html"
    dashboard.write_dashboard("<!doctype html><p>hi</p>", str(out))
    assert out.read_text(encoding="utf-8") == "<!doctype html><p>hi</p>"
    # no leftover temp file beside the target
    leftovers = [p.name for p in out.parent.iterdir() if p.name != "dashboard.html"]
    assert leftovers == []


def test_main_writes_page_and_returns_zero(tmp_path, monkeypatch):
    out = tmp_path / "dashboard.html"
    monkeypatch.setattr(dashboard, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(dashboard, "OUTPUT_PATH", str(out))
    rc = dashboard.main()
    assert rc == 0
    assert out.exists() and "Trading Bot Dashboard" in out.read_text(encoding="utf-8")


# --- populated-DB fixture: real rows via each combiner's own db.py, for
# every one of the 16 section renderers (plan 003) ---------------------------
#
# THE RULE (enforced by test_no_handrolled_combiner_schema below): every
# fixture in this file builds its schema ONLY via composite_db / scorer_db /
# advisor_db's real `ensure_schema`. Never hand-roll a CREATE TABLE / CREATE
# VIEW that replicates a combiner's own table or view — a hand-rolled replica
# silently diverges from production, the suite stays green, and the dashboard
# blanks the section. Rows may be inserted directly, but the SCHEMA must be the
# real one. (The generic `toy` tables for the pure _view_table helper are fine:
# `toy` is nobody's production table.)

_REGIME_SIGNAL_VALUES = {
    "fred_curve": -0.42,
    "fred_hy_spread": 3.05,
    "cboe_vix_backwardation": 0,
    "cboe_equity_pcr": 0.42,
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


def _build_composite_db(path):
    """composite.db with 2 snapshots (>=2 points for the regime timeline
    sparkline) and, on the latest, one flagged ticker (FLAG1, held) and one
    non-flagged ticker (PLAIN1) — via real write_signal_values +
    write_ticker_scores/write_market_regime, not direct table pokes."""
    conn = composite_db.connect(str(path))
    composite_db.ensure_schema(conn)

    older = composite_db.write_snapshot(conn, "2026-07-07T21:13:00+00:00", 10)
    _write_market_signals(conn, older, vix=18.4)
    composite_db.write_market_regime(conn, older, composite_catalog.REGIME_FIELDS)

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
    v_regime_performance, v_pending, and v_basis_breaks — modeled on
    tests/test_scorer_db_views.py and tests/test_journal_db_views.py."""
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


@pytest.fixture
def populated_data_dir(tmp_path):
    """A tmp_path with composite.db, scorer.db, and advisor.db populated via
    each combiner's own db.py — real schemas/views throughout, no hand-rolled
    DDL — so every one of dashboard.SECTIONS' 16 renderers has at least one
    real row to show."""
    _build_composite_db(tmp_path / "composite.db")
    _build_scorer_db(tmp_path / "scorer.db")
    _build_advisor_db(tmp_path / "advisor.db")
    return str(tmp_path)


def test_populated_fixture_has_no_unavailable_sections(populated_data_dir):
    html = dashboard.build_page(populated_data_dir, NOW)
    assert 'class="unavailable"' not in html


# --- Step 2: one positive-path test per section renderer --------------------


def test_regime_renders_values(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "composite.db")
    try:
        html = dashboard._regime(conn, NOW)
    finally:
        conn.close()
    assert "16.1" in html  # VIX, the latest snapshot
    assert '<span class="tag-on">risk-on</span>' in html  # _regime_badge's real markup
    assert "<summary>All regime inputs</summary>" in html
    assert "10y–2y spread" in html
    assert "-0.42" in html  # signed t10y2y we inserted


def test_regime_timeline_renders_positive(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "composite.db")
    try:
        html = dashboard._regime_timeline(conn, NOW)
    finally:
        conn.close()
    assert "<polyline" in html
    assert "no data" not in html


def test_scorecard_shows_flagged_and_split(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "composite.db")
    try:
        html = dashboard._scorecard(conn, NOW)
    finally:
        conn.close()
    headline_html = html.split("<details>")[0]
    assert '<tr class="flag"><td>FLAG1</td>' in headline_html
    assert "4 / 0" in headline_html  # FLAG1's bullish/bearish split
    assert "<tr><td>PLAIN1</td>" in headline_html  # non-flagged: plain <tr>


def test_signal_efficacy_renders_rows(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "scorer.db")
    try:
        html = dashboard._signal_efficacy(conn, NOW)
    finally:
        conn.close()
    assert "sig_test_a" in html
    assert '<span class="tag-dim">thin</span>' in html  # n_bench=1 < RELIABLE_MIN_N


def test_bucket_performance_renders_rows(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "scorer.db")
    try:
        html = dashboard._bucket_performance(conn, NOW)
    finally:
        conn.close()
    assert "strong_bull" in html
    assert "thin" in html


def test_human_filter_renders_rows(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "scorer.db")
    try:
        html = dashboard._human_filter(conn, NOW)
    finally:
        conn.close()
    assert "acted" in html


def test_regime_performance_section_renders(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "scorer.db")
    try:
        html = dashboard._regime_performance(conn, NOW)
    finally:
        conn.close()
    assert "risk_on" in html


def test_pending_section_renders(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "scorer.db")
    try:
        html = dashboard._pending(conn, NOW)
    finally:
        conn.close()
    assert "PEND1" in html


def test_basis_breaks_section_renders(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "scorer.db")
    try:
        html = dashboard._basis_breaks(conn, NOW)
    finally:
        conn.close()
    assert "ACME" in html


def test_signal_recommendation_renders_rows(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "scorer.db")
    try:
        html = dashboard._signal_recommendation(conn, NOW)
    finally:
        conn.close()
    assert "sig_test_a" in html
    assert "1 / 30" in html  # reliability meter reads n_bench, not n_matured
    assert "n_matured" not in html
    rng = html.split('class="rng" style="left:')[1]
    left = int(rng.split("%")[0])
    width = int(rng.split("width:")[1].split("%")[0])
    assert left + width <= 100  # CI bar's range stays within the track


def test_trader_scorecard_renders(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "scorer.db")
    try:
        html = dashboard._trader_scorecard(conn, NOW)
    finally:
        conn.close()
    assert html.startswith("<pre>")
    assert "Trader Decision-Quality Scorecard" in html
    assert "acted" in html


def test_book_heat_and_group_heat_render(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "advisor.db")
    try:
        book_html = dashboard._book_heat(conn, NOW)
        group_html = dashboard._group_heat(conn, NOW)
    finally:
        conn.close()
    assert '<div class="v">3</div>' in book_html  # 3 positions tile
    assert "energy" in group_html  # XOM + XLE collapsed into one bet
    assert "AAPL" in group_html  # ungrouped symbol is its own bet


def test_position_heat_never_shows_snapshot_id(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "advisor.db")
    try:
        html = dashboard._position_heat(conn, NOW)
    finally:
        conn.close()
    assert "snapshot_id" not in html
    assert "AAPL" in html and "XOM" in html and "XLE" in html


def test_disagreements_render(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "advisor.db")
    try:
        html = dashboard._disagreements(conn, NOW)
    finally:
        conn.close()
    assert "XOM" in html
    assert '<span class="pill anti">STRONG</span>' in html


def test_size_caps_render(populated_data_dir):
    conn = dashboard._ro(populated_data_dir, "advisor.db")
    try:
        html = dashboard._size_caps(conn, NOW)
    finally:
        conn.close()
    assert "NVDA" in html
    assert "⚠" in html  # exceeds_buying_power marker


def test_hero_read_positive_path(populated_data_dir):
    html = dashboard._hero_read(populated_data_dir, NOW)
    assert html != dashboard._HERO_FALLBACK
    assert "risk-on" in html
    assert ">3</span> position" in html  # 3 positions, correct pluralization
    assert "FLAG1" in html  # strongest-agreement flagged ticker
    assert "$None" not in html
    assert "1 positions" not in html


# --- Step 3: parametrized guard against silent degradation of a populated
# section, plus the coverage contract that every section has a positive-path
# test above -----------------------------------------------------------------

_SECTIONS_WITH_POSITIVE_TEST = {
    "regime",
    "regime-timeline",
    "scorecard",
    "signal-efficacy",
    "bucket-performance",
    "human-filter",
    "regime-performance",
    "pending",
    "basis-breaks",
    "book-heat",
    "group-heat",
    "position-heat",
    "disagreements",
    "size-caps",
    "plan-001-report",
    "plan-004-scorecard",
}


def test_every_section_has_a_positive_path_test():
    assert set(dashboard.SECTION_IDS) == _SECTIONS_WITH_POSITIVE_TEST


@pytest.mark.parametrize("section", dashboard.SECTIONS, ids=lambda s: s[0])
def test_no_populated_section_degrades(section, populated_data_dir):
    sid, title, db_name, fn, kicker, note = section
    html = dashboard._render_section(sid, title, db_name, fn, kicker, note, populated_data_dir, NOW)
    assert 'class="unavailable"' not in html, f"{sid} degraded against a populated DB"
    assert 'class="empty"' not in html, f"{sid} rendered zero rows"


def _combiner_schema_names() -> set[str]:
    """Every table/view name owned by a combiner, read out of the real
    schema (not a hardcoded list) by running each ensure_schema against an
    in-memory DB — so the forbidden set grows automatically when a combiner
    gains a view tomorrow."""
    names: set[str] = set()
    for mod in (composite_db, scorer_db, advisor_db):
        conn = sqlite3.connect(":memory:")
        mod.ensure_schema(conn)
        names |= {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")
        }
        conn.close()
    return names


def test_no_handrolled_combiner_schema():
    """The fixtures must build combiner schema ONLY via composite_db /
    scorer_db / advisor_db's real ensure_schema — never a hand-rolled CREATE
    TABLE / CREATE VIEW that replicates a combiner's own table or view.

    Why this is the invariant Plan 003 exists to protect: a hand-rolled replica
    of a production schema silently diverges the day a combiner renames a
    column or reshapes a view. The fixture keeps building the OLD shape, every
    test here stays green, and the live dashboard blanks the affected section
    with no alert. Only the real ensure_schema guarantees the fixture and
    production can never drift apart.

    Self-maintaining: the forbidden set is derived from the combiners
    themselves, so a view added upstream tomorrow is protected automatically
    without editing this test. The generic `toy` tables for the pure
    _view_table helper are unaffected — `toy` is nobody's production name."""
    source = Path(__file__).read_text(encoding="utf-8")
    forbidden = _combiner_schema_names()
    # Find the identifier named by each CREATE TABLE / CREATE VIEW in this
    # file's own source (case-insensitive, tolerating IF NOT EXISTS).
    declared = {
        m.group(1)
        for m in re.finditer(
            r"create\s+(?:table|view)\s+(?:if\s+not\s+exists\s+)?([A-Za-z_][A-Za-z0-9_]*)",
            source,
            re.IGNORECASE,
        )
    }
    offenders = sorted(declared & forbidden)
    assert not offenders, (
        f"hand-rolled combiner schema in this test file: {offenders} — build fixtures"
        " via composite_db / scorer_db / advisor_db.ensure_schema instead (see the"
        " module docstring and the fixtures' THE RULE comment)"
    )


def test_edition_date_is_the_phoenix_date_not_utc():
    """The masthead prints the Phoenix date.

    Regression: _edition_date formatted datetime.now(UTC) directly. The 9:13pm
    Phoenix render slot is already the next UTC day, so the masthead announced
    tomorrow's edition every single night.
    """
    # 2026-07-08 21:13 Phoenix == 2026-07-09 04:13 UTC
    assert _strip(dashboard._edition_date("2026-07-09T04:13:00+00:00")) == "2026·07·08"
    # ...and a pre-rollover instant on the same Phoenix day agrees.
    assert _strip(dashboard._edition_date("2026-07-08T23:40:00+00:00")) == "2026·07·08"


def test_edition_date_degrades_on_unparseable_input():
    assert dashboard._edition_date("not-a-timestamp") == "not-a-time"


def _strip(s):
    return s.replace("&#8202;", "")
