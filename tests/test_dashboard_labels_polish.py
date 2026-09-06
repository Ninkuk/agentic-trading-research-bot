"""The last label pass: single-phrase swaps on cards the audit scored 4, so
no tile or header on the page is left in shorthand."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import book, data, sources_views  # noqa: E402

NOW = "2026-07-08T04:13:00+00:00"


def _sections(populated_data_dir):
    return data.export_data(populated_data_dir, NOW)["sections"]


def _tiles(sec):
    return {t["label"]: t for t in sec.get("tiles") or []}


def _labels(sec):
    return {c["key"]: c["label"] for c in sec["columns"]}


def test_macro_and_fred_tiles_name_the_series_in_words(populated_data_dir):
    secs = _sections(populated_data_dir)
    assert set(_tiles(secs["macro-drivers"])) <= {
        "Long vs short Treasury yields",
        "Junk-bond premium",
        "Fear index (VIX)",
    }
    assert set(_tiles(secs["fred-series"])) <= {
        "Long vs short Treasury yields",
        "Junk-bond premium",
        "Fed funds rate",
        "Unemployment rate",
    }


def test_regime_tiles_read_as_a_mood_and_an_input_count(populated_data_dir):
    tiles = _tiles(_sections(populated_data_dir)["regime"])
    assert "Tonight's mood" in tiles
    inputs = tiles["Inputs with data"]
    assert " of " in str(inputs["value"])


def test_week_ahead_and_yield_curve_tiles_drop_the_shorthand(populated_data_dir):
    secs = _sections(populated_data_dir)
    week = _tiles(secs["week-ahead"])
    assert {"Days to the Fed meeting", "Fed quiet period"} <= set(week) or not week
    assert not any("FOMC" in k or "blackout" in k for k in week)
    curve = _tiles(secs["yield-curve"])
    for label in ("10-year minus 2-year", "10-year minus 3-month"):
        if label in curve:
            assert curve[label]["band"] in ("normal", "inverted")
    assert not any("spread" in k for k in curve)


def test_health_tiles_carry_captions(populated_data_dir):
    tiles = _tiles(_sections(populated_data_dir)["health"])
    assert tiles["Jobs that ran"]["band"] == "last 24 hours"
    assert tiles["Jobs on the schedule"]["band"] == "in launchd"
    assert "Need attention" in tiles


def test_order_columns_and_reasons_are_plain():
    queue = {c["key"]: c["label"] for c in book._QUEUE_COLUMNS}
    assert queue["ref_price"] == "Price you noted"
    assert queue["max_gap_pct"] == "Max above that price %"
    assert book.reason_words("manual resolve") == "resolved by hand"
    assert book.reason_words("planned") == "limit planned"
    assert book.reason_words("placed") == "placed with the broker"
    assert book.reason_words("gapped: ask 12 > ceiling 11.5") == "gapped: ask 12 > ceiling 11.5"
    assert book.reason_words(None) is None


def test_auction_earnings_disagreement_headers():
    auction = {c["key"]: c["label"] for c in sources_views._AUCTION_COLUMNS}
    assert auction["latest_btc"] == "Bids per dollar sold"
    assert auction["avg_btc"] == "Typical bids per dollar"
    earnings = {c["key"]: c["label"] for c in sources_views._EARNINGS_COLUMNS}
    assert earnings["eps_est"] == "Expected earnings per share"
    dis = {c["key"]: c["label"] for c in data._DISAGREEMENTS_COLUMNS}
    assert dis["score_sum"] == "Signal lean" and dis["strong"] == "Strong disagreement?"


def test_market_closures_note_is_one_sentence(populated_data_dir):
    note = _sections(populated_data_dir)["market-closures"]["note"]
    assert "—" not in note and note.count(". ") == 0
