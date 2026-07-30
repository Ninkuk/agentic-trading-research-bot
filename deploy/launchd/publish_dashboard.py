"""Publish the built dashboard React app + fresh reports/data.json to gh-pages.

The page is *current state*, not history: each run force-pushes a single-commit
orphan branch, so the previous blob is orphaned and reclaimed by gc rather than
accumulating a nightly delta in the repo.

Everything happens in a temp directory. The live worktree, index, and HEAD are
never touched -- a branch switch at 9:20pm could collide with the owner working
in the repo, or with another scheduled job reading data/.

Runs at 9:20pm Phoenix, AFTER the 9:15pm daily-summary ntfy, so a slow or hung
push can neither delay nor suppress that health alert.

Refuses to publish stale data. If the 9:13pm dashboard job did not run,
reports/data.json is yesterday's, and pushing it would put an old page up
wearing a fresh publication time -- worse than an honest failure, which is the
same judgment dashboard.py applies to its own generation-failed output.

Refuses to publish a dashboard/dist that was never built for production, or
was built without the noindex guard: the frontend build (`npm run build` in
dashboard/) is expected to bake `NOINDEX_META` into dist/index.html, and this
module only verifies that -- it never injects the tag itself. This also
catches the stale-fixture hazard: `predev` copies a fixture into
dashboard/public/data.json, and any `vite build` copies public/* into dist/,
so dist/data.json (if present) may be that fixture. stage() always writes the
real reports/data.json content last, clobbering whatever vite copied in.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sources.common.clock import phx_date  # noqa: E402

DATA_PATH = "reports/data.json"
DIST_DIR = "dashboard/dist"
BRANCH = "gh-pages"
NOINDEX_META = '<meta name="robots" content="noindex,nofollow">'
# The noindex meta tag above is the only crawler control that works here -- it is honored
# by crawlers that fetch this page. robots.txt is a per-ORIGIN file: this is a
# project page (ninkuk.github.io/agentic-trading-research-bot/), so robots.txt only ever
# lands at .../agentic-trading-research-bot/robots.txt, a path no crawler consults (they
# fetch https://ninkuk.github.io/robots.txt, served by a different repo). It is
# published anyway because it's harmless and becomes correct if this site ever
# moves to an apex/user-site origin -- but do not rely on it for anything.
ROBOTS_TXT = "User-agent: *\nDisallow: /\n"

# Local git operations are bounded generously; `push` gets extra headroom because
# it is the one subcommand that touches the network.
GIT_TIMEOUT_DEFAULT = 120
GIT_TIMEOUT_PUSH = 300


def is_fresh(mtime_epoch: float, now_iso: str) -> bool:
    """True when the file was last written on the same Phoenix date as now_iso.

    Both sides go through phx_date. Slicing either one is a bug: this job runs
    at 04:20 UTC, which is the previous Phoenix day.
    """
    file_dt = datetime.fromtimestamp(mtime_epoch, tz=UTC)
    return phx_date(file_dt) == phx_date(now_iso)


def stage(dist_dir: Path, data_json: str, dest: Path) -> None:
    """Write the publishable tree into dest.

    Order matters: the dist tree is copied first, then data.json is written
    LAST so it clobbers any fixture that leaked into dist via dashboard/public/
    (predev copies a fixture there, and vite build copies public/* into dist/).
    .nojekyll disables Jekyll processing -- the build output is already
    self-contained static assets, so Jekyll could only add latency and a
    chance of mangling something.
    """
    shutil.copytree(dist_dir, dest, dirs_exist_ok=True)
    (dest / "data.json").write_text(data_json, encoding="utf-8")
    (dest / ".nojekyll").write_text("", encoding="utf-8")
    (dest / "robots.txt").write_text(ROBOTS_TXT, encoding="utf-8")


class GitError(RuntimeError):
    """A git invocation returned non-zero."""


# A remote may embed credentials (https://user:token@host). Never log one.
_CREDS = re.compile(r"(https://)[^/@\s]*@")


def _redact(text: str) -> str:
    return _CREDS.sub(r"\1<redacted>@", text)


class GitTimeout(RuntimeError):
    """A git invocation exceeded its timeout. Never carries argv (may hold the remote URL)."""


def _git(
    run: Callable[..., subprocess.CompletedProcess],
    cwd: Path,
    *args: str,
    timeout: float = GIT_TIMEOUT_DEFAULT,
) -> subprocess.CompletedProcess:
    try:
        result = run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        # subprocess.TimeoutExpired.cmd carries the full argv INCLUDING the remote
        # URL -- never log the exception itself, only the subcommand name.
        raise GitTimeout(f"git {args[0]} timed out after {timeout}s") from None
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
    """Force-push the built dashboard to BRANCH. Returns 0 on success, 1 on failure."""
    data_path = repo_root / DATA_PATH
    if not data_path.exists():
        log(f"FAILED: {DATA_PATH} missing — did the 9:13pm dashboard job run?")
        return 1
    today = phx_date(now_iso)
    if not is_fresh(data_path.stat().st_mtime, now_iso):
        log(f"STALE: {DATA_PATH} is not from {today} (Phoenix) — refusing to publish")
        return 1

    dist_dir = repo_root / DIST_DIR
    index_path = dist_dir / "index.html"
    if not index_path.exists():
        log(
            f"FAILED: {DIST_DIR} missing — run 'npm run build' in dashboard/ after frontend changes"
        )
        return 1
    index_html = index_path.read_text(encoding="utf-8")
    if NOINDEX_META not in index_html:
        log("FAILED: built index.html lacks the noindex meta")
        return 1

    try:
        remote = _git(run, repo_root, "remote", "get-url", "origin").stdout.strip()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            stage(dist_dir, data_path.read_text(encoding="utf-8"), dest)
            _git(run, dest, "init", "-q", "-b", BRANCH)
            _git(run, dest, "add", "-A")
            # --no-gpg-sign is mandatory: see the module docstring in the plan and
            # test_publish_commit_disables_gpg_signing. Without it this hangs forever.
            _git(run, dest, "commit", "-q", "--no-gpg-sign", "-m", f"dashboard {today}")
            _git(
                run,
                dest,
                "push",
                "--force",
                "--quiet",
                remote,
                f"HEAD:{BRANCH}",
                timeout=GIT_TIMEOUT_PUSH,
            )
    except (GitError, GitTimeout) as e:
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
