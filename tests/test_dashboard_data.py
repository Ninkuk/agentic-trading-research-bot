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
