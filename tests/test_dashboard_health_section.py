"""Tests for the `health` section exporter (data._health): the pipeline
health payload exported into data.json for the dashboard's Ops strand.
Because data.json is published to a public gh-pages site, the
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
    assert "empty" not in body


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
    """now_iso = 2026-07-23T04:13:00+00:00 (9:13pm Phoenix on 2026-07-22).
    Correctly derived (Phoenix) the 24h window is
    [2026-07-21 21:13, 2026-07-22 21:13]; derived UTC-side (no Phoenix
    offset applied) it would instead be [2026-07-22 04:13, 2026-07-23
    04:13]. A `start:` line stamped 2026-07-22 00:30:00 sits in the
    Phoenix-only window and NOT the buggy UTC one -- it's inside the
    former, before the latter's 04:13 floor -- so it is the discriminating
    fixture: it counts as a run only under a correct Phoenix derivation."""
    data_dir, logs_dir = _layout(tmp_path)
    (logs_dir / "fred.log").write_text("[2026-07-22 00:30:00] start: fred\n")
    monkeypatch.setattr(data.health, "job_exit_codes", lambda: {})
    monkeypatch.setattr(data.health, "running_jobs", lambda: set())

    body = data._health(str(data_dir), NOW)

    runs_tile = next(t for t in body["tiles"] if t["label"] == "Jobs that ran")
    assert runs_tile["value"] == 1


# --- last runs (the home page's terminal) -----------------------------------


def test_last_run_rebuilds_the_summary_from_matched_numbers_only(tmp_path):
    log = tmp_path / "fred.log"
    log.write_text(
        "[2026-10-27 16:40:05] start: fred --db data/fred.db\n"
        "stored 142300 observations across 31 series into data/fred.db\n"
        "[2026-10-27 16:40:30] end: fred --db data/fred.db (25s, exit 0)\n"
        "[2026-10-28 16:40:05] start: fred --db data/fred.db\n"
        "warning: skipping DGS10: https://api.stlouisfed.org/?api_key=LEAKME\n"
        "stored 142314 observations across 31 series into data/fred.db\n"
        "[2026-10-28 16:40:33] end: fred --db data/fred.db (28s, exit 0)\n"
    )
    run = data.health.last_run(log)
    assert run == {
        "command": "fred --db data/fred.db",
        "at": "16:40",
        "summary": "stored 142314 observations across 31 series into data/fred.db",
        "seconds": 28,
        "exit": 0,
    }
    assert "LEAKME" not in json.dumps(run)


def test_last_run_knows_each_job_shape_and_drops_the_unknown(tmp_path):
    cases = {
        "composite snapshot 120: 32 signals ok, 0 failed, into data/composite.db": (
            "composite snapshot 120: 32 signals ok, 0 failed, into data/composite.db"
        ),
        "scorer snapshot 130: 11393 prices, 6923 registered, 6574 matured, 456 skipped,"
        " into data/scorer.db": (
            "scorer snapshot 130: 11393 prices, 6923 registered, 6574 matured, 456 skipped,"
            " into data/scorer.db"
        ),
        "advisor snapshot 128: 26 positions, 7 caps, 26 exit rows, into data/advisor.db": (
            "advisor snapshot 128: 26 positions, 7 caps, 26 exit rows, into data/advisor.db"
        ),
        "stored 4341 filings into data/edgar.db": "stored 4341 filings into data/edgar.db",
        "stored 204 weekly rows across 17 markets (tff) into data/cftc.db": (
            "stored 204 weekly rows across 17 markets into data/cftc.db"
        ),
        "done: 3 ok, 0 failed of 3 selected": "done: 3 ok, 0 failed of 3 selected",
        "stored 4341 filings into data/edgar.db; see https://x/?api_key=LEAKME": None,
        "selected: TOPP, PRI, ZTO (max=3, stale_days=30, model=opus)": None,
    }
    for line, expected in cases.items():
        assert data.health._rebuild_summary(line) == expected, line


def test_last_run_refuses_a_command_outside_the_allowlist_and_needs_a_finished_run(tmp_path):
    log = tmp_path / "x.log"
    log.write_text(
        "[2026-10-28 16:40:05] start: fred --db data/fred.db?api_key=LEAKME\n"
        "stored 1 observations across 1 series into data/fred.db\n"
        "[2026-10-28 16:40:33] end: fred (28s, exit 0)\n"
    )
    assert data.health.last_run(log) is None
    log.write_text("[2026-10-28 16:40:05] start: fred --db data/fred.db\nstill running\n")
    assert data.health.last_run(log) is None
    # A finished run whose output matched nothing keeps the command, no summary.
    log.write_text(
        "[2026-10-28 16:40:05] start: nyfed --db data/nyfed.db\n"
        "warning: skipping soma: IncompleteRead\n"
        "[2026-10-28 16:40:11] end: nyfed --db data/nyfed.db (6s, exit 1)\n"
    )
    assert data.health.last_run(log) == {
        "command": "nyfed --db data/nyfed.db",
        "at": "16:40",
        "summary": None,
        "seconds": 6,
        "exit": 1,
    }


def test_health_section_carries_last_runs_in_job_order(tmp_path, monkeypatch):
    data_dir, logs_dir = _layout(tmp_path)
    (logs_dir / "scorer.log").write_text(
        "[2026-07-22 21:10:05] start: scorer --db data/scorer.db --keep-days 365\n"
        "scorer snapshot 9: 10 prices, 8 registered, 6 matured, 0 skipped, into data/scorer.db\n"
        "[2026-07-22 21:10:08] end: scorer --db data/scorer.db --keep-days 365 (3s, exit 0)\n"
    )
    (logs_dir / "treasury.log").write_text(
        "[2026-07-22 16:30:05] start: treasury --db data/treasury.db\n"
        "stored 11513 rows across 6 datasets into data/treasury.db\n"
        "[2026-07-22 16:30:47] end: treasury --db data/treasury.db (42s, exit 0)\n"
    )
    monkeypatch.setattr(data.health, "job_exit_codes", lambda: {})
    monkeypatch.setattr(data.health, "running_jobs", lambda: set())
    runs = data._health(str(data_dir), NOW)["last_runs"]
    assert [r["job"] for r in runs] == ["treasury", "scorer"]
    assert runs[0]["summary"] == "stored 11513 rows across 6 datasets into data/treasury.db"
