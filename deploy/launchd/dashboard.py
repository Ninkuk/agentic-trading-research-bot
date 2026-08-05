"""Generate the nightly dashboard's data.json.

Thin entrypoint over dashboard_lib/data.py, which assembles the document from
each source DB. Kept at this path because dashboard.sh and launchd invoke it,
and tests import `dashboard`.

Writes reports/data.json: the same accumulated pipeline state as the old
HTML dashboard — regime, ticker scorecard, signal efficacy/recommendations,
bucket performance, the human-filter tally, and the advisor book — exported
as plain data for the dashboard/ React frontend to render instead of
server-rendered markup.

Reads each source DB read-only, the same pattern as every other launchd
reporter: dashboard_lib.data opens with
`sqlite3.connect("file:data/<db>?mode=ro", uri=True)`,
strictly read-only, and wraps every section in its own try/except so a
missing DB, a dropped view, or zero rows degrades to an `"error"` key on
that section rather than crashing. A total failure here still writes an
explicit minimal error document ({"schema_version", "generated_at",
"error"}) — an absent/stale data.json with no error signal would be worse
than an honest one.

Wired as its own launchd slot at 9:13pm (after advisor 9:12) so it reflects
tonight's rows. It is now the last nightly reporter, and after writing the
document it pings HEALTHCHECK_URL as the external dead-man's switch — so an
absent ping means a dead host or a dead scheduler, the one failure an
on-host reporter structurally cannot detect for itself. `main()` returns 0
on both a clean run and a GENERATION failure (any exception from
`data.export_json` — a missing DB, a dropped view, a bad row — is caught and
degrades to the minimal error document above); the ping still fires on that
path, since a document generated with errors still proves the host and
scheduler are alive. A failure in the WRITE itself (reports/ unwritable,
disk full) is not caught and propagates as a process crash with a non-zero
exit, and the ping correctly never fires.
"""

import json
import os
import sys
import urllib.error
import urllib.request
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
    heartbeat()
    return 0


def heartbeat(get=None):
    """Best-effort ping to an external dead-man's switch (e.g. healthchecks.io)
    so an absent ping — a dead host/scheduler — raises an alarm the on-host
    summary structurally cannot. No-op if HEALTHCHECK_URL is unset. Never raises
    and never affects the exit code; a failure prints only the exception type."""
    url = os.environ.get("HEALTHCHECK_URL")
    if not url:
        return
    get = get or _default_get
    try:
        get(url)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        # Never re-raise: the URL (its own auth secret) rides in the message.
        print(f"heartbeat failed ({type(e).__name__})", file=sys.stderr)


def _default_get(url: str) -> None:
    with urllib.request.urlopen(url, timeout=10):
        pass


if __name__ == "__main__":
    sys.exit(main())
