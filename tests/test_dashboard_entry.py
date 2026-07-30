"""Tests for deploy/launchd/dashboard.py's main() entrypoint: writes
reports/data.json (via dashboard_lib.data.export_json), keeps the exit-0
contract on total failure (the 9:15pm health-alert ordering invariant), and
warns on oversize output. Every test monkeypatches dashboard.DATA_OUTPUT_PATH
to a tmp_path location so none of them ever write into the real reports/.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
import dashboard  # noqa: E402


def test_main_writes_json(tmp_path, monkeypatch, populated_data_dir):
    out = tmp_path / "data.json"
    monkeypatch.setattr(dashboard, "DATA_DIR", populated_data_dir)
    monkeypatch.setattr(dashboard, "DATA_OUTPUT_PATH", str(out))

    rc = dashboard.main()

    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema_version"] == 1


def test_main_total_failure_writes_error_doc_and_exits_zero(tmp_path, monkeypatch):
    out = tmp_path / "data.json"
    monkeypatch.setattr(dashboard, "DATA_OUTPUT_PATH", str(out))

    def _boom(data_dir, now_iso, repo_root=None):
        raise TypeError("boom with secret")

    monkeypatch.setattr(dashboard.data, "export_json", _boom)

    rc = dashboard.main()

    assert rc == 0
    text = out.read_text(encoding="utf-8")
    doc = json.loads(text)
    assert doc["error"] == "generation failed (TypeError)"
    assert "secret" not in text


def test_size_warning_over_target(capsys, tmp_path, monkeypatch):
    out = tmp_path / "data.json"
    monkeypatch.setattr(dashboard, "DATA_OUTPUT_PATH", str(out))
    monkeypatch.setattr(
        dashboard.data, "export_json", lambda data_dir, now_iso, repo_root=None: "x" * 1_600_000
    )

    rc = dashboard.main()

    assert rc == 0
    captured = capsys.readouterr()
    assert "WARNING" in captured.out
