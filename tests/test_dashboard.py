"""Tests for the zero-dependency nightly HTML dashboard generator.

Offline, like the rest of the suite: resilience is exercised by pointing the
generator at an empty data dir (every section degrades to 'unavailable' rather
than crashing), and self-containment is asserted on the emitted HTML string.
The per-section SQL is validated separately against live DB copies.
"""

import sqlite3
import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import dashboard  # noqa: E402

NOW = "2026-07-08T21:13:00+00:00"

_COMPOSITE_SCHEMA = """
CREATE TABLE snapshots (id INTEGER PRIMARY KEY, captured_at TEXT,
    signals_expected INTEGER, signals_ok INTEGER DEFAULT 0, signals_failed INTEGER DEFAULT 0);
CREATE TABLE market_regime (snapshot_id INTEGER PRIMARY KEY, t10y2y REAL, curve_inverted INTEGER,
    hy_spread REAL, vix REAL, vix_backwardation INTEGER, equity_pcr_pctile REAL,
    in_fomc_blackout INTEGER, imminent_high_impact INTEGER, days_to_opex INTEGER,
    rrp_change REAL, tga_change REAL, regime TEXT, inputs_expected INTEGER, inputs_present INTEGER);
CREATE TABLE ticker_scores (snapshot_id INTEGER, symbol TEXT, bullish INTEGER DEFAULT 0,
    bearish INTEGER DEFAULT 0, total INTEGER DEFAULT 0, score_sum INTEGER DEFAULT 0,
    coverage REAL, worst_staleness_days REAL, in_portfolio INTEGER DEFAULT 0,
    PRIMARY KEY (snapshot_id, symbol));
CREATE VIEW v_latest_snapshot AS SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1;
CREATE VIEW v_latest_regime AS SELECT m.* FROM market_regime m JOIN v_latest_snapshot l ON m.snapshot_id = l.id;
CREATE VIEW v_latest_scorecard AS SELECT t.* FROM ticker_scores t JOIN v_latest_snapshot l ON t.snapshot_id = l.id;
CREATE VIEW v_flagged AS SELECT * FROM v_latest_scorecard WHERE ABS(score_sum) >= 4 AND total >= 3;
"""

_ADVISOR_SCHEMA = """
CREATE TABLE snapshots (id INTEGER PRIMARY KEY, captured_at TEXT, equity REAL, cash REAL,
    buying_power REAL, portfolio_captured_at TEXT, composite_captured_at TEXT, regime TEXT,
    sources_failed INTEGER DEFAULT 0);
CREATE TABLE position_heat (snapshot_id INTEGER, symbol TEXT, group_name TEXT, quantity REAL,
    market_value REAL, atr REAL, price REAL, price_date TEXT, heat_dollars REAL, heat_pct REAL,
    weight_pct REAL, score_sum INTEGER, bullish INTEGER, bearish INTEGER, total INTEGER,
    atr_stale INTEGER, PRIMARY KEY (snapshot_id, symbol));
CREATE VIEW v_latest_snapshot AS SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1;
CREATE VIEW v_latest_heat AS SELECT p.* FROM position_heat p JOIN v_latest_snapshot l ON p.snapshot_id = l.id;
CREATE VIEW v_book_heat AS
SELECT s.id AS snapshot_id, s.captured_at, s.equity, s.sources_failed,
       COUNT(p.symbol) AS positions, SUM(p.heat_dollars) AS heat_dollars,
       SUM(p.heat_pct) AS heat_pct,
       CASE WHEN SUM(p.market_value) > 0 THEN
            SUM(CASE WHEN p.atr IS NOT NULL THEN p.market_value ELSE 0 END) * 1.0 / SUM(p.market_value)
       END AS heat_coverage
FROM snapshots s LEFT JOIN position_heat p ON p.snapshot_id = s.id
WHERE s.id IN (SELECT id FROM v_latest_snapshot)
GROUP BY s.id, s.captured_at, s.equity, s.sources_failed;
CREATE VIEW v_disagreements AS
SELECT *, (score_sum <= -4 AND total >= 3) AS strong FROM v_latest_heat WHERE score_sum < 0;
"""


def _make_composite_db(path, regime="risk_on", vix=16.1, symbol=None, score_sum=5):
    conn = sqlite3.connect(path)
    conn.executescript(_COMPOSITE_SCHEMA)
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
    conn.commit()
    conn.close()


def _make_advisor_db(path, equity=200.0, positions=None, sources_failed=0):
    conn = sqlite3.connect(path)
    conn.executescript(_ADVISOR_SCHEMA)
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


def test_build_page_is_self_contained(tmp_path):
    html = dashboard.build_page(str(tmp_path), NOW)
    # hard constraint: no external assets — no CDN, no link/script src, no font
    for forbidden in ("http://", "https://", "cdn", "<link", "<script", "@font-face", "googleapis"):
        assert forbidden not in html.lower()
    assert "<style>" in html  # CSS is inlined in-head


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
    import re

    ys = [float(m.group(1)) for m in re.finditer(r'cy="([\d.]+)"', svg)]
    assert len(ys) == 2
    assert ys[-1] < ys[0]


def test_hero_degrades_on_empty_dir(tmp_path):
    html = dashboard._hero_read(str(tmp_path), NOW)
    assert 'class="read"' in html
    assert "$None" not in html
    assert "1 positions" not in html


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
