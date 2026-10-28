"""`col(pin=True)` marks a table's row-identity first column (pinned when the
table scrolls sideways on a phone). The flag is only meaningful on the first
column of a list and only on a short text identity, never a number or a
date, so the exporter modules are scanned for both."""

import re
from pathlib import Path

from dashboard_lib import data
from dashboard_lib.common import col

MODULES = ["book.py", "data.py", "grades.py", "sources_views.py"]
LIB = Path(__file__).resolve().parents[1] / "deploy" / "launchd" / "dashboard_lib"
PIN = re.compile(r'pin=True|"pin": True')
KEY = re.compile(r'"([a-z_]+)"')
DATE_LIKE = ("date", "kind", "horizon", "verdict", "response", "version")


def test_col_emits_pin_only_when_asked():
    assert col("symbol", "Symbol", numeric=False, pin=True)["pin"] is True
    assert "pin" not in col("symbol", "Symbol", numeric=False)
    assert data._track_col("signal_id", "Signal", numeric=False, pin=True)["pin"] is True


def test_pin_sits_only_on_a_text_identity_first_column():
    seen = 0
    for name in MODULES:
        lines = (LIB / name).read_text().split("\n")
        for i, line in enumerate(lines):
            if not PIN.search(line):
                continue
            seen += 1
            where = f"{name}:{i + 1}"
            start = i
            while not re.search(r"col\(|\{", lines[start]):
                start -= 1
            decl = " ".join(lines[start : i + 1])
            assert lines[start - 1].rstrip().endswith("["), f"{where}: pin on a non-first column"
            assert "numeric=False" in decl or '"numeric": False' in decl, f"{where}: numeric pin"
            key = KEY.search(decl).group(1)
            assert not any(k in key for k in DATE_LIKE), f"{where}: {key} is a grouping key"
    assert seen >= 40
