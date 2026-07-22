from datetime import UTC, datetime
from pathlib import Path

from deploy.launchd.publish_dashboard import (
    NOINDEX_META,
    ROBOTS_TXT,
    inject_noindex,
    is_fresh,
    stage,
)


def _epoch(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=UTC).timestamp()


def test_is_fresh_same_phoenix_day():
    # 2026-07-21 14:00 UTC == 07:00 Phoenix, same Phoenix day as the now below
    assert is_fresh(_epoch(2026, 7, 21, 14, 0), "2026-07-21T14:30:00+00:00")


def test_is_fresh_rejects_yesterday():
    assert not is_fresh(_epoch(2026, 7, 20, 14, 0), "2026-07-21T14:30:00+00:00")


def test_is_fresh_survives_utc_rollover():
    """Fixture is chosen so the UTC dates DIFFER but the Phoenix dates MATCH.

    File mtime 2026-07-21T23:00:00Z = 2026-07-21 16:00 Phoenix.
    now_iso    2026-07-22T04:20:00+00:00 = 2026-07-21 21:20 Phoenix.
    Both are Phoenix 2026-07-21, so this must be fresh -- but their UTC dates are
    07-21 vs 07-22. Any UTC-based (or naive `now_iso[:10]`) comparison sees those
    two different UTC dates and wrongly calls the file stale. Because this fixture
    pair's UTC dates disagree while their Phoenix dates agree, a naive
    implementation is forced to return False here, so this test actually catches
    it (verified: fails against a naive UTC-date implementation, passes against
    the real phx_date-based one).
    """
    assert is_fresh(_epoch(2026, 7, 21, 23, 0), "2026-07-22T04:20:00+00:00")


def test_inject_noindex_after_head():
    out = inject_noindex("<html><head><title>x</title></head><body>b</body></html>")
    assert NOINDEX_META in out
    assert out.index(NOINDEX_META) < out.index("<title>")


def test_inject_noindex_without_head_tag():
    out = inject_noindex("<p>no head here</p>")
    assert NOINDEX_META in out
    assert "<p>no head here</p>" in out


def test_inject_noindex_is_idempotent():
    once = inject_noindex("<html><head></head></html>")
    assert inject_noindex(once) == once


def test_stage_writes_three_files(tmp_path):
    stage("<html><head></head><body>hi</body></html>", tmp_path)
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / ".nojekyll").exists()
    assert (tmp_path / "robots.txt").exists()


def test_stage_index_has_noindex_and_content(tmp_path):
    stage("<html><head></head><body>hi</body></html>", tmp_path)
    out = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert NOINDEX_META in out
    assert "hi" in out


def test_stage_robots_disallows_all(tmp_path):
    stage("<html></html>", tmp_path)
    assert (tmp_path / "robots.txt").read_text(encoding="utf-8") == ROBOTS_TXT
    assert "Disallow: /" in ROBOTS_TXT


def test_stage_nojekyll_is_empty(tmp_path):
    stage("<html></html>", tmp_path)
    assert (tmp_path / ".nojekyll").read_text(encoding="utf-8") == ""


import subprocess

from deploy.launchd.publish_dashboard import publish

FRESH_NOW = "2026-07-22T04:20:00+00:00"  # 9:20pm Phoenix on 2026-07-21


class FakeGit:
    """Stands in for subprocess.run. Records (cwd, argv) pairs; never touches a real repo."""

    def __init__(
        self,
        fail_on=None,
        remote="https://github.com/Ninkuk/x.git",
        stderr="",
        timeout_on=None,
    ):
        # (cwd, argv, "did cwd/index.html exist at call time") -- the third field
        # is captured live because dest is a tempfile.TemporaryDirectory that is
        # gone by the time a test can inspect it after publish() returns.
        self.calls: list[tuple[str | None, list[str], bool]] = []
        self.fail_on = fail_on
        self.remote = remote
        self.stderr = stderr
        self.timeout_on = timeout_on

    def __call__(self, argv, cwd=None, capture_output=False, text=False, timeout=None):
        index_present = cwd is not None and (Path(cwd) / "index.html").exists()
        self.calls.append((cwd, argv, index_present))
        args = argv[1:]
        if self.timeout_on is not None and args[0] == self.timeout_on:
            raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)
        if self.fail_on is not None and args[0] == self.fail_on:
            return subprocess.CompletedProcess(argv, 1, "", self.stderr or "fatal: boom")
        stdout = f"{self.remote}\n" if args[:2] == ["remote", "get-url"] else ""
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    def argv_for(self, subcommand):
        return next((argv for _cwd, argv, _idx in self.calls if argv[1] == subcommand), None)

    def cwd_for(self, subcommand):
        return next((cwd for cwd, argv, _idx in self.calls if argv[1] == subcommand), None)

    def index_present_for(self, subcommand):
        """Whether cwd/index.html existed at the moment this subcommand ran."""
        return next((idx for _cwd, argv, idx in self.calls if argv[1] == subcommand), None)


def _repo_with_dashboard(tmp_path, mtime_epoch):
    (tmp_path / "reports").mkdir()
    html = tmp_path / "reports" / "dashboard.html"
    html.write_text("<html><head></head><body>book</body></html>", encoding="utf-8")
    import os

    os.utime(html, (mtime_epoch, mtime_epoch))
    return tmp_path


def test_publish_returns_zero_on_fresh_file(tmp_path):
    repo = _repo_with_dashboard(tmp_path, _epoch(2026, 7, 22, 4, 13))
    git = FakeGit()
    assert publish(now_iso=FRESH_NOW, repo_root=repo, run=git, log=lambda m: None) == 0


def test_publish_force_pushes_to_gh_pages(tmp_path):
    repo = _repo_with_dashboard(tmp_path, _epoch(2026, 7, 22, 4, 13))
    git = FakeGit()
    publish(now_iso=FRESH_NOW, repo_root=repo, run=git, log=lambda m: None)
    push = git.argv_for("push")
    assert "--force" in push
    assert "HEAD:gh-pages" in push


def test_publish_commit_disables_gpg_signing(tmp_path):
    """commit.gpgsign=true + gpg.format=ssh + 1Password is set globally.

    A non-interactive commit without --no-gpg-sign blocks on the 1Password
    approval prompt forever, hanging the launchd job every night with no error.
    """
    repo = _repo_with_dashboard(tmp_path, _epoch(2026, 7, 22, 4, 13))
    git = FakeGit()
    publish(now_iso=FRESH_NOW, repo_root=repo, run=git, log=lambda m: None)
    assert "--no-gpg-sign" in git.argv_for("commit")


def test_publish_refuses_stale_file_and_runs_no_git(tmp_path):
    repo = _repo_with_dashboard(tmp_path, _epoch(2026, 7, 20, 4, 13))  # two days back
    git = FakeGit()
    msgs: list[str] = []
    assert publish(now_iso=FRESH_NOW, repo_root=repo, run=git, log=msgs.append) == 1
    assert git.calls == []
    assert any("STALE" in m for m in msgs)


def test_publish_refuses_missing_file(tmp_path):
    git = FakeGit()
    msgs: list[str] = []
    assert publish(now_iso=FRESH_NOW, repo_root=tmp_path, run=git, log=msgs.append) == 1
    assert git.calls == []


def test_publish_reports_push_failure_loudly(tmp_path):
    repo = _repo_with_dashboard(tmp_path, _epoch(2026, 7, 22, 4, 13))
    git = FakeGit(fail_on="push")
    msgs: list[str] = []
    assert publish(now_iso=FRESH_NOW, repo_root=repo, run=git, log=msgs.append) == 1
    assert any("FAILED" in m for m in msgs)


def test_publish_redacts_credentials_in_git_errors(tmp_path):
    repo = _repo_with_dashboard(tmp_path, _epoch(2026, 7, 22, 4, 13))
    git = FakeGit(fail_on="push", stderr="fatal: https://user:ghp_SECRET@github.com/x.git")
    msgs: list[str] = []
    publish(now_iso=FRESH_NOW, repo_root=repo, run=git, log=msgs.append)
    assert "ghp_SECRET" not in " ".join(msgs)


def test_publish_reports_git_timeout_loudly_and_without_secrets(tmp_path):
    """A stalled push (dropped VPN, keychain modal) must not hang the job forever.

    subprocess.TimeoutExpired.cmd carries the full argv INCLUDING the remote URL
    -- the FAILED line must name only the subcommand and the timeout, never the
    exception itself.
    """
    repo = _repo_with_dashboard(tmp_path, _epoch(2026, 7, 22, 4, 13))
    secret_remote = "https://user:ghp_TIMEOUTSECRET@github.com/x.git"
    git = FakeGit(remote=secret_remote, timeout_on="push")
    msgs: list[str] = []
    assert publish(now_iso=FRESH_NOW, repo_root=repo, run=git, log=msgs.append) == 1
    assert any("FAILED" in m and "timed out" in m for m in msgs)
    assert "ghp_TIMEOUTSECRET" not in " ".join(msgs)


def test_publish_stages_and_operates_outside_the_live_worktree(tmp_path):
    """Guards the worktree-isolation invariant the module docstring promises.

    The read-only `remote get-url` may run against the live repo, but every
    mutating git command (init/add/commit/push) MUST run in a throwaway temp
    directory, never in repo_root -- committing and force-pushing repo_root
    itself would mutate the live worktree/branch while publishing whatever
    happened to be sitting in it.
    """
    repo = _repo_with_dashboard(tmp_path, _epoch(2026, 7, 22, 4, 13))
    git = FakeGit()
    assert publish(now_iso=FRESH_NOW, repo_root=repo, run=git, log=lambda m: None) == 0

    assert git.cwd_for("remote") == str(repo)
    for subcommand in ("init", "add", "commit", "push"):
        cwd = git.cwd_for(subcommand)
        assert cwd is not None
        assert cwd != str(repo)
        # Proves stage() actually wrote into the directory git operates on --
        # checked live, at call time, since the tempdir is cleaned up by the
        # time publish() returns.
        assert git.index_present_for(subcommand) is True


def test_publish_does_not_modify_source_html(tmp_path):
    repo = _repo_with_dashboard(tmp_path, _epoch(2026, 7, 22, 4, 13))
    before = (repo / "reports" / "dashboard.html").read_text(encoding="utf-8")
    publish(now_iso=FRESH_NOW, repo_root=repo, run=FakeGit(), log=lambda m: None)
    assert (repo / "reports" / "dashboard.html").read_text(encoding="utf-8") == before


from deploy.launchd.publish_dashboard import main


def test_main_returns_one_when_dashboard_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main([]) == 1


def test_main_catches_unexpected_exception_and_returns_one(monkeypatch):
    """publish() only handles GitError; main() must still not raise on anything else.

    A disk-full OSError from stage() or a tempfile failure would otherwise escape
    as a bare traceback, violating this repo's "loud failure, never silent" rule.
    """

    def _boom(**kwargs):
        raise OSError("no space left on device")

    monkeypatch.setattr("deploy.launchd.publish_dashboard.publish", _boom)
    assert main([]) == 1


def test_main_logs_exception_type_not_message_on_unexpected_error(monkeypatch, capsys):
    """Pins the secret-hygiene contract on main()'s catch-all.

    Once Fix 1 lands, an unhandled subprocess.TimeoutExpired carries the full
    argv (including the remote URL) in its message. main() must log only
    `type(e).__name__`, never `str(e)`/`repr(e)`, or a stray exception in some
    other call path would leak a credential into the launchd job log.
    """
    secret = "https://user:ghp_UNEXPECTEDSECRET@github.com/x.git"

    def _boom(**kwargs):
        raise OSError(f"no space left on device, remote was {secret}")

    monkeypatch.setattr("deploy.launchd.publish_dashboard.publish", _boom)
    assert main([]) == 1
    out = capsys.readouterr().out
    assert "OSError" in out
    assert secret not in out
