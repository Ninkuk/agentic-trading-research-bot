"""Position-checkpoints digest block: held-name reopen dates, 7-day lookahead."""

import datetime as dt
import sqlite3  # noqa: F401
import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import daily_summary  # noqa: E402

# 9:15pm Phoenix on 2026-07-29 == 04:15 UTC on the 30th (rollover fixture).
NOW_UTC = dt.datetime.fromisoformat("2026-07-30T04:15:00+00:00")
TODAY = "2026-07-29"  # phx_date(NOW_UTC)


def test_format_upcoming_today_and_past():
    got = daily_summary.format_checkpoint_lines(
        [
            ("BR", "2026-08-02", "fy27-guide", "2026-07-30"),
            ("DECK", "2026-07-29", "print-checkpoint", "2026-07-27"),
            ("SAP", "2026-07-26", "q2-print", "2026-07-25"),
        ],
        TODAY,
    )
    assert got == [
        "SAP 2026-07-26 q2-print (3d ago, thesis 2026-07-25)",
        "DECK 2026-07-29 print-checkpoint (today, thesis 2026-07-27)",
        "BR 2026-08-02 fy27-guide (in 4d, thesis 2026-07-30)",
    ]


def test_format_sorts_ties_by_ticker():
    got = daily_summary.format_checkpoint_lines(
        [
            ("MORN", "2026-08-02", "b-slug", "2026-07-30"),
            ("INTU", "2026-08-02", "a-slug", "2026-07-30"),
        ],
        TODAY,
    )
    assert [ln.split()[0] for ln in got] == ["INTU", "MORN"]
