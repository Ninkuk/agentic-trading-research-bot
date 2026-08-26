"""scan_log returns counts, never content: data.json is published to public
gh-pages, and a log line can carry whatever a subprocess printed (URLs with
keys, paths). The payload must be structurally incapable of leaking one."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import health  # noqa: E402

SINCE = health.dt.datetime(2026, 7, 22, 0, 0, 0)


def test_marker_lines_become_counts(tmp_path):
    log = tmp_path / "cboe_stats.log"
    log.write_text(
        "[2026-07-22 18:00:01] start: cboe stats\n"
        "[2026-07-22 18:00:05] FAILED: step one\n"
        "[2026-07-22 18:00:09] FAILED: step two\n"
        "[2026-07-22 18:00:12] Error: something\n"
    )
    runs, markers = health.scan_log(log, SINCE)
    assert runs == 1
    assert markers == {"FAILED": 2, "Error:": 1}


def test_headless_json_result_lines_are_not_markers(tmp_path):
    # The claude -p JSON envelope narrates freely; only real log lines count.
    log = tmp_path / "journal.log"
    log.write_text(
        "[2026-07-22 18:00:01] start: journal sync\n"
        '{"is_error":false,"result":"no STALE marker yet; Error: none; FAILED: 0"}\n'
        "[2026-07-22 18:00:09] STALE: no journal run in the last 2h\n"
    )
    runs, markers = health.scan_log(log, SINCE)
    assert runs == 1
    assert markers == {"STALE": 1}


def test_raw_log_content_never_appears_in_output(tmp_path):
    secret = "https://api.example.com/v1?api_key=SHOULD-NEVER-LEAK"
    log = tmp_path / "fred.log"
    log.write_text(f"[2026-07-22 18:00:05] FAILED: {secret}\n")
    runs, markers = health.scan_log(log, SINCE)
    assert secret not in repr((runs, markers))


def test_out_of_window_markers_are_not_counted(tmp_path):
    log = tmp_path / "fred.log"
    log.write_text("[2026-07-01 18:00:05] FAILED: old\n")
    assert health.scan_log(log, SINCE) == (0, {})


def test_untimestamped_lines_inherit_window_state(tmp_path):
    log = tmp_path / "fred.log"
    log.write_text("[2026-07-22 18:00:01] start: fred\nTraceback (most recent call last):\n")
    runs, markers = health.scan_log(log, SINCE)
    assert markers == {"Traceback": 1}


def test_step_lines_do_not_count_as_runs(tmp_path):
    log = tmp_path / "cftc-weekly.log"
    log.write_text(
        "[2026-07-22 18:00:01] start: cftc weekly\n"
        "[2026-07-22 18:00:30] step: family disaggregated\n"
    )
    assert health.scan_log(log, SINCE)[0] == 1
