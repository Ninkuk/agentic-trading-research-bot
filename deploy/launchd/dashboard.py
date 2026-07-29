"""Generate the zero-dependency nightly HTML dashboard.

Thin entrypoint over dashboard_lib/ (style.py CSS + color tokens, svg.py pure
chart builders, sections.py assembly, js.py inline script). Kept at this path
because dashboard.sh and launchd invoke it, and tests import `dashboard`.

A single self-contained static HTML file summarizing the pipeline's accumulated
state — regime, ticker scorecard, signal efficacy/recommendations, bucket
performance, the human-filter tally, and the advisor book — for a human to
review before the weekly reweighting decision. Opens locally (double-click,
file://); no server, no auth, no JS framework, no CDN, no external asset of any
kind (CLAUDE.md's stdlib-only constraint, extended to the emitted HTML).

Mirrors deploy/launchd/daily_summary.py: reads each source DB with
`sqlite3.connect("file:data/<db>?mode=ro", uri=True)`, strictly read-only, and
wraps every section in its own try/except so a missing DB, a dropped view, or
zero rows degrades to a visible "unavailable"/"no rows yet" note rather than a
crash. A total failure still writes an explicit "generation failed" page — a
stale dashboard with no error banner would be worse than an honest one.

Wired as its own launchd slot at 9:13pm (after advisor 9:12, before the
daily-summary ntfy at 9:15) so it reflects tonight's rows; being a separate
process, a bug here can never delay or suppress that health alert.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # dashboard_lib
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root

# Re-exports below: tests and launchd import `dashboard`; keep this list in
# sync with dashboard_lib.sections.
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


def main() -> int:
    now_iso = datetime.now(UTC).isoformat()
    try:
        page = build_page(DATA_DIR, now_iso)
    except Exception as e:  # never leave a stale file with no error banner
        page = (
            "<!doctype html>\n<html><head><meta charset='utf-8'>"
            "<title>Agentic Trading Research Bot Dashboard</title></head><body>"
            f"<h1>Agentic Trading Research Bot Dashboard</h1><p>generation failed"
            f" ({_esc(type(e).__name__)})</p></body></html>\n"
        )
    write_dashboard(page, OUTPUT_PATH)
    print(f"wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
