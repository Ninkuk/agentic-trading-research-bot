"""Publish reports/dashboard.html to the gh-pages branch backing GitHub Pages.

The page is *current state*, not history: each run force-pushes a single-commit
orphan branch, so the previous blob is orphaned and reclaimed by gc rather than
accumulating ~400KB a night in the repo.

Everything happens in a temp directory. The live worktree, index, and HEAD are
never touched -- a branch switch at 9:20pm could collide with the owner working
in the repo, or with another scheduled job reading data/.

Runs at 9:20pm Phoenix, AFTER the 9:15pm daily-summary ntfy, so a slow or hung
push can neither delay nor suppress that health alert.

Refuses to publish a stale file. If the 9:13pm dashboard job did not run,
reports/dashboard.html is yesterday's, and pushing it would put an old page up
wearing a fresh publication time -- worse than an honest failure, which is the
same judgment dashboard.py applies to its own generation-failed page.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sources.common.clock import phx_date  # noqa: E402

DASHBOARD_PATH = "reports/dashboard.html"
BRANCH = "gh-pages"
NOINDEX_META = '<meta name="robots" content="noindex,nofollow">'
# Public and *discoverable* are separate decisions; only the first was made.
ROBOTS_TXT = "User-agent: *\nDisallow: /\n"


def is_fresh(mtime_epoch: float, now_iso: str) -> bool:
    """True when the file was last written on the same Phoenix date as now_iso.

    Both sides go through phx_date. Slicing either one is a bug: this job runs
    at 04:20 UTC, which is the previous Phoenix day.
    """
    file_dt = datetime.fromtimestamp(mtime_epoch, tz=UTC)
    return phx_date(file_dt) == phx_date(now_iso)


def inject_noindex(html: str) -> str:
    """Add a robots noindex meta to the published copy. Idempotent."""
    if NOINDEX_META in html:
        return html
    if "<head>" in html:
        return html.replace("<head>", "<head>" + NOINDEX_META, 1)
    return NOINDEX_META + html


def stage(html: str, dest: Path) -> None:
    """Write the publishable tree into dest.

    .nojekyll disables Jekyll processing: the dashboard is already self-contained
    HTML with no external asset of any kind, so Jekyll could only add latency and
    a chance of mangling it.
    """
    (dest / "index.html").write_text(inject_noindex(html), encoding="utf-8")
    (dest / ".nojekyll").write_text("", encoding="utf-8")
    (dest / "robots.txt").write_text(ROBOTS_TXT, encoding="utf-8")
