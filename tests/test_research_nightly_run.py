"""Orchestration tests: the claude invocation is behind an injected `invoke`
seam — these tests never spawn a process."""

import json
import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import research_nightly  # noqa: E402

# 10:12pm Phoenix on 2026-07-22 == 05:12 UTC on the 23rd — the rollover trap.
NOW = "2026-07-23T05:12:00+00:00"
TODAY = "2026-07-22"


def _write_thesis(research_dir, ticker, date=TODAY, size=4096):
    (research_dir / f"{ticker}-{date}.md").write_text("x" * size)


def test_allowlist_never_contains_order_tools():
    for forbidden in ("place_equity_order", "place_option_order", "cancel_", "review_"):
        assert forbidden not in research_nightly.ALLOWED_TOOLS


def test_allowlist_bash_entries_are_enumerated_not_catchall():
    entries = research_nightly.ALLOWED_TOOLS.split(",")
    assert "Bash(uv run python *)" not in entries
    allowed_bash = {
        "Bash(uv run python -m sources.screeners.stock_analysis_screener.probe *)",
        "Bash(uv run python -m tools.valuation.reverse_dcf *)",
        "Bash(uv run python -m tools.options.implied_move *)",
        "Bash(uv run python main.py journal *)",
    }
    bash_entries = [e for e in entries if e.startswith("Bash(")]
    assert bash_entries
    for entry in bash_entries:
        assert entry in allowed_bash


def test_build_command_shape():
    cmd = research_nightly.build_command("EOSE", "opus")
    assert cmd[0] == "claude"
    prompt = cmd[cmd.index("-p") + 1]
    assert prompt.startswith("/research-ticker EOSE")
    assert "--model" in cmd and "opus" in cmd
    assert "--allowedTools" in cmd and "--output-format" in cmd


def test_build_command_prompt_declares_unattended_run():
    # A headless session that hits a judgment point and ASKS (e.g. "re-run or
    # refresh?") exits rc=0 with no thesis — observed live. The prompt must
    # rule out questions and mandate the dated output file, fast kills included.
    prompt = research_nightly.build_command("EOSE", "opus")[2]
    assert "unattended" in prompt
    assert "research/EOSE-" in prompt
    assert "fast kill" in prompt


def test_parse_denials_extracts_tool_names():
    out = json.dumps({"permission_denials": [{"tool_name": "Edit"}, {"tool_name": "Bash"}]})
    assert research_nightly.parse_denials(out) == ["Edit", "Bash"]


def test_parse_denials_total_on_garbage():
    assert research_nightly.parse_denials("not json") == []
    assert research_nightly.parse_denials(json.dumps({"result": "ok"})) == []


def test_verify_thesis_requires_today_and_min_size(tmp_path):
    _write_thesis(tmp_path, "GOOD")
    _write_thesis(tmp_path, "TINY", size=100)
    _write_thesis(tmp_path, "STALE", date="2026-07-21")
    assert research_nightly.verify_thesis(tmp_path, "GOOD", TODAY)
    assert not research_nightly.verify_thesis(tmp_path, "TINY", TODAY)
    assert not research_nightly.verify_thesis(tmp_path, "STALE", TODAY)
    assert not research_nightly.verify_thesis(tmp_path, "ABSENT", TODAY)


def test_run_night_continue_on_failure(tmp_path):
    calls = []

    def invoke(cmd, timeout_s):
        prompt = next(a for a in cmd if a.startswith("/research-ticker "))
        ticker = prompt.splitlines()[0].split()[-1]
        calls.append(ticker)
        if ticker == "BAD":
            return 1, "{}"
        _write_thesis(tmp_path, ticker)
        return 0, "{}"

    ok, failed = research_nightly.run_night(
        ["BAD", "GOOD1", "GOOD2"], invoke, tmp_path, TODAY, "opus"
    )
    assert calls == ["BAD", "GOOD1", "GOOD2"]  # BAD did not stop the night
    assert ok == ["GOOD1", "GOOD2"] and failed == ["BAD"]


def test_run_night_exit0_but_no_thesis_is_a_failure(tmp_path):
    def invoke(cmd, timeout_s):
        return 0, "{}"  # claude "succeeded" but wrote nothing

    ok, failed = research_nightly.run_night(["X"], invoke, tmp_path, TODAY, "opus")
    assert ok == [] and failed == ["X"]


def test_main_disabled_is_clean_noop(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("RESEARCH_NIGHTLY_MAX", "0")
    rc = research_nightly.main(invoke=lambda c, t: (0, "{}"), now_iso=NOW)
    assert rc == 0
    assert "disabled" in capsys.readouterr().out


def test_main_all_failed_exits_nonzero(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_NIGHTLY_MAX", "3")
    monkeypatch.setenv("RESEARCH_COMPOSITE_DB", str(tmp_path / "absent.db"))
    monkeypatch.setenv("RESEARCH_PORTFOLIO_DB", str(tmp_path / "absent2.db"))
    monkeypatch.setenv("RESEARCH_DIR", str(tmp_path / "research"))
    # No DBs -> empty selection -> clean exit 0.
    assert research_nightly.main(invoke=lambda c, t: (1, ""), now_iso=NOW) == 0


def test_result_excerpt_tail_one_line_and_total():
    doc = json.dumps({"result": "line1\n" + "x" * 600 + " THE END"})
    exc = research_nightly._result_excerpt(doc)
    assert exc.endswith("THE END") and len(exc) <= 500 and "\n" not in exc
    assert research_nightly._result_excerpt("not json") == ""
    assert research_nightly._result_excerpt(json.dumps({})) == ""


def test_run_night_failure_prints_session_tail(tmp_path, capsys):
    def invoke(cmd, timeout_s):
        return 0, json.dumps({"result": "declined to write because reasons"})

    research_nightly.run_night(["X"], invoke, tmp_path, TODAY, "opus")
    assert "declined to write" in capsys.readouterr().out
