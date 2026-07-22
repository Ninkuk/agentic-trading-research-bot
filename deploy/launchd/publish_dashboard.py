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

import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
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


class GitError(RuntimeError):
    """A git invocation returned non-zero."""


# A remote may embed credentials (https://user:token@host). Never log one.
_CREDS = re.compile(r"(https://)[^/@\s]*@")


def _redact(text: str) -> str:
    return _CREDS.sub(r"\1<redacted>@", text)


def _git(
    run: Callable[..., subprocess.CompletedProcess], cwd: Path, *args: str
) -> subprocess.CompletedProcess:
    result = run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if result.returncode != 0:
        raise GitError(
            _redact(f"git {args[0]} failed ({result.returncode}): {result.stderr.strip()}")
        )
    return result


def publish(
    *,
    now_iso: str,
    repo_root: Path,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    log: Callable[[str], None] = print,
) -> int:
    """Force-push the current dashboard to BRANCH. Returns 0 on success, 1 on failure."""
    html_path = repo_root / DASHBOARD_PATH
    if not html_path.exists():
        log(f"FAILED: {DASHBOARD_PATH} missing — did the 9:13pm dashboard job run?")
        return 1
    today = phx_date(now_iso)
    if not is_fresh(html_path.stat().st_mtime, now_iso):
        log(f"STALE: {DASHBOARD_PATH} is not from {today} (Phoenix) — refusing to publish")
        return 1

    try:
        remote = _git(run, repo_root, "remote", "get-url", "origin").stdout.strip()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            stage(html_path.read_text(encoding="utf-8"), dest)
            _git(run, dest, "init", "-q", "-b", BRANCH)
            _git(run, dest, "add", "-A")
            # --no-gpg-sign is mandatory: see the module docstring in the plan and
            # test_publish_commit_disables_gpg_signing. Without it this hangs forever.
            _git(run, dest, "commit", "-q", "--no-gpg-sign", "-m", f"dashboard {today}")
            _git(run, dest, "push", "--force", "--quiet", remote, f"HEAD:{BRANCH}")
    except GitError as e:
        log(f"FAILED: {e}")
        return 1

    log(f"published {today} dashboard to {BRANCH}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Thin wrapper. Time enters here and only here; publish() takes it injected."""
    try:
        return publish(
            now_iso=datetime.now(UTC).isoformat(),
            repo_root=Path.cwd(),
        )
    except Exception as e:  # noqa: BLE001
        # publish() handles GitError and the stale/missing cases itself; this
        # catches the unexpected (disk full, tempfile failure) so the nightly
        # job logs a line and exits non-zero instead of dumping a traceback.
        print(f"FAILED: unexpected {type(e).__name__}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
