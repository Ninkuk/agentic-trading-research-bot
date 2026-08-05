"""Tests for the `health` section exporter (data._health): the pipeline
health payload the retired nightly ntfy carried, now exported into
data.json. Because data.json is published to a public gh-pages site, the
load-bearing property under test is that a raw log line — which can contain
whatever a subprocess printed, including a URL with an API key — never
reaches the exported payload; health.build_health already enforces that
(counts and code-formatted strings only), and one test here pins it from
this module's side too.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import data  # noqa: E402

NOW = "2026-07-23T04:13:00+00:00"  # 9:13pm Phoenix on 2026-07-22 — the real digest slot


def _layout(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    return data_dir, logs_dir


def test_healthy_body_shape(tmp_path, monkeypatch):
    data_dir, _logs_dir = _layout(tmp_path)
    monkeypatch.setattr(data.health, "job_exit_codes", lambda: {"fred": 0})
    monkeypatch.setattr(data.health, "running_jobs", lambda: set())

    body = data._health(str(data_dir), NOW)

    assert body["healthy"] is True
    assert len(body["tiles"]) == 3
    assert body["rows"] == []
    assert "empty" in body


def test_problem_rows_are_structured(tmp_path, monkeypatch):
    data_dir, logs_dir = _layout(tmp_path)
    (logs_dir / "edgar.log").write_text("[2026-07-22 18:00:05] FAILED: something broke\n")
    monkeypatch.setattr(data.health, "job_exit_codes", lambda: {})
    monkeypatch.setattr(data.health, "running_jobs", lambda: set())

    body = data._health(str(data_dir), NOW)

    assert len(body["rows"]) == 1
    assert set(body["rows"][0]) == {"kind", "target", "detail"}


def test_secret_in_log_never_reaches_payload(tmp_path, monkeypatch):
    data_dir, logs_dir = _layout(tmp_path)
    (logs_dir / "edgar.log").write_text("[2026-07-22 18:00:05] FAILED: https://x/?api_key=LEAKME\n")
    monkeypatch.setattr(data.health, "job_exit_codes", lambda: {})
    monkeypatch.setattr(data.health, "running_jobs", lambda: set())

    assert "LEAKME" not in json.dumps(data._health(str(data_dir), NOW))


def test_export_data_degrades_health_not_crashes(tmp_path, monkeypatch):
    data_dir, _logs_dir = _layout(tmp_path)

    def _boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(data.health, "build_health", _boom)

    doc = data.export_data(str(data_dir), NOW, repo_root=str(tmp_path))

    assert doc["sections"]["health"]["error"].startswith("unavailable")
    assert doc["schema_version"] == 1
    assert "sections" in doc and "tickers" in doc and "glossary" in doc


def test_export_data_dispatches_health_to_the_success_body(tmp_path, monkeypatch):
    """Mirrors tests/test_dashboard_data.py's per-section positive-path
    pattern (e.g. test_regime_section_exports_verdict_and_tiles,
    data.py:56-61). Exercises the real dispatch path in export_data --
    catching a regression like the one this test was added to guard: a
    SECTION_EXPORTERS db_name literal that (by accident) ends in `.db` would
    route health into the sqlite branch instead of the file-backed branch,
    so `_health` would never run and the section would degrade to `error`
    even when nothing is actually broken."""
    data_dir, _logs_dir = _layout(tmp_path)
    monkeypatch.setattr(data.health, "job_exit_codes", lambda: {"fred": 0})
    monkeypatch.setattr(data.health, "running_jobs", lambda: set())

    doc = data.export_data(str(data_dir), NOW, repo_root=str(tmp_path))
    sec = doc["sections"]["health"]

    assert "error" not in sec
    assert sec["healthy"] is True
    assert len(sec["tiles"]) == 3
    assert sec["columns"] == data._HEALTH_COLUMNS
    assert sec["rows"] == []


def test_rollover_now_local(tmp_path, monkeypatch):
    """A `start:` line stamped 2026-07-22 21:00:00 (13 minutes before the
    9:13pm Phoenix slot) must count as a run in the 24h window. now_iso's
    UTC date is 2026-07-23 — if now_local were derived UTC-side (no
    Phoenix offset applied), `since` would land on the wrong calendar day
    and this in-window run would be missed."""
    data_dir, logs_dir = _layout(tmp_path)
    (logs_dir / "fred.log").write_text("[2026-07-22 21:00:00] start: fred\n")
    monkeypatch.setattr(data.health, "job_exit_codes", lambda: {})
    monkeypatch.setattr(data.health, "running_jobs", lambda: set())

    body = data._health(str(data_dir), NOW)

    runs_tile = next(t for t in body["tiles"] if t["label"] == "runs (24h)")
    assert runs_tile["value"] == 1
