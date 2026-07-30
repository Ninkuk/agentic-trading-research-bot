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
from conftest import NOW, ROLLOVER_NOW  # noqa: E402


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
