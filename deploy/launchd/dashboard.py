"""Generate the nightly dashboard's data.json.

Thin entrypoint over dashboard_lib/ (data.py assembles the document from
each source DB; sections.py/svg.py/style.py/js.py back the legacy HTML
generator, re-exported below for tests until Task 17 retires them). Kept at
this path because dashboard.sh and launchd invoke it, and tests import
`dashboard`.

Writes reports/data.json: the same accumulated pipeline state as the old
HTML dashboard — regime, ticker scorecard, signal efficacy/recommendations,
bucket performance, the human-filter tally, and the advisor book — exported
as plain data for a React frontend to render instead of server-rendered
markup.

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
process, a bug here can never delay or suppress that health alert — hence
`main()` always returns 0, success or failure alike.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # dashboard_lib
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root

# Re-exports below: tests and launchd import `dashboard`; keep this list in
# sync with dashboard_lib.sections.
from dashboard_lib import data  # noqa: E402
from dashboard_lib.sections import (  # noqa: E402,F401
    _EFFICACY_COLS,
    _HERO_FALLBACK,
    _REPO_URL,
    _STYLE,
    DATA_DIR,
    OUTPUT_PATH,
    SECTION_IDS,
    SECTIONS,
    _badge,
    _basis_breaks,
    _book_heat,
    _bucket_performance,
    _candidates,
    _ci_bar,
    _disagreements,
    _edition_date,
    _group_heat,
    _hero_clause,
    _hero_read,
    _human_filter,
    _pending,
    _position_heat,
    _rec_badge,
    _regime,
    _regime_badge,
    _regime_performance,
    _regime_timeline,
    _reliability_meter,
    _render_section,
    _research_reopens,
    _ro,
    _score_cell,
    _scorecard,
    _signal_efficacy,
    _signal_recommendation,
    _size_caps,
    _trader_scorecard,
    _view_table,
    build_page,
    write_dashboard,
)
from dashboard_lib.svg import _esc, _num, _pct, _signed_num, _sparkline_svg, _yn  # noqa: E402,F401

# Local definitions (not re-exported from sections.py, which stays HTML-only
# until Task 17): the new JSON output path, and DATA_DIR redefined here so
# both survive sections.py's eventual deletion. DATA_DIR's value is
# identical to the re-import above ("data") — this line shadows it, it does
# not change behavior.
DATA_OUTPUT_PATH = "reports/data.json"
DATA_DIR = "data"  # noqa: F811 — intentional shadow of the sections.py re-export

_SIZE_WARNING_BYTES = 1_500_000


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
    write_dashboard(text, DATA_OUTPUT_PATH)
    size = len(text.encode("utf-8"))
    print(f"wrote {DATA_OUTPUT_PATH} ({size} bytes)")
    if size > _SIZE_WARNING_BYTES:
        print("WARNING: data.json exceeds 1.5MB target")
    return 0


if __name__ == "__main__":
    sys.exit(main())
