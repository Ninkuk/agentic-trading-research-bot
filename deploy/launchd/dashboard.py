"""Generate the nightly dashboard's data.json.

Thin entrypoint over dashboard_lib/data.py, which assembles the document from
each source DB. Kept at this path because dashboard.sh and launchd invoke it,
and tests import `dashboard`.

Writes reports/data.json: the same accumulated pipeline state as the old
HTML dashboard — regime, ticker scorecard, signal efficacy/recommendations,
bucket performance, the human-filter tally, and the advisor book — exported
as plain data for the dashboard/ React frontend to render instead of
server-rendered markup.

Mirrors deploy/launchd/daily_summary.py: dashboard_lib.data reads each
source DB with `sqlite3.connect("file:data/<db>?mode=ro", uri=True)`,
strictly read-only, and wraps every section in its own try/except so a
missing DB, a dropped view, or zero rows degrades to an `"error"` key on
that section rather than crashing. A total failure here still writes an
explicit minimal error document ({"schema_version", "generated_at",
"error"}) — an absent/stale data.json with no error signal would be worse
than an honest one.

Wired as its own launchd slot at 9:13pm (after advisor 9:12, before the
daily-summary ntfy at 9:15) so it reflects tonight's rows; being a separate
process, a bug here can never delay or suppress that health alert. `main()`
returns 0 on both a clean run and a GENERATION failure (any exception from
`data.export_json` — a missing DB, a dropped view, a bad row — is caught and
degrades to the minimal error document above). A failure in the WRITE itself
(reports/ unwritable, disk full) is not caught and propagates as a process
crash with a non-zero exit — same as any other process crash, it still
cannot delay the 9:15 alert, since that is a separate process either way.
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # dashboard_lib
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root

from dashboard_lib import data  # noqa: E402

DATA_DIR = "data"
OUTPUT_PATH = "reports/data.json"

_SIZE_WARNING_BYTES = 1_500_000


def write_dashboard(text: str, output_path: str) -> None:
    """Write atomically: temp file in the same dir, then os.replace, so a
    reader who opens the file mid-write never sees a truncated document."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, out)


def main() -> int:
    now_iso = datetime.now(UTC).isoformat()
    try:
        text = data.export_json(DATA_DIR, now_iso)
    except Exception as e:  # never leave a stale file with no error signal
        text = json.dumps(
            {
                "schema_version": 1,
                "generated_at": now_iso,
                # type name only — never str(e)/repr(e), which can embed a
                # DB path or (for an upstream urllib error) a URL.
                "error": f"generation failed ({type(e).__name__})",
            },
            separators=(",", ":"),
        )
    write_dashboard(text, OUTPUT_PATH)
    size = len(text.encode("utf-8"))
    print(f"wrote {OUTPUT_PATH} ({size} bytes)")
    if size > _SIZE_WARNING_BYTES:
        print("WARNING: data.json exceeds 1.5MB target")
    return 0


if __name__ == "__main__":
    sys.exit(main())
