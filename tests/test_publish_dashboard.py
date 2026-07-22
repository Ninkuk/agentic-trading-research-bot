from datetime import UTC, datetime

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
    """The job runs 9:20pm Phoenix = 04:20 UTC the NEXT day.

    The dashboard was written at 9:13pm Phoenix (04:13 UTC on the 22nd). Both are
    Phoenix 2026-07-21, so this must be fresh. A `now_iso[:10]` implementation
    compares "2026-07-22" against the file's Phoenix date "2026-07-21", calls it
    stale, and refuses to publish every single night. That is what this test catches.
    """
    assert is_fresh(_epoch(2026, 7, 22, 4, 13), "2026-07-22T04:20:00+00:00")


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
    """Stands in for subprocess.run. Records argv; never touches a real repo."""

    def __init__(self, fail_on=None, remote="https://github.com/Ninkuk/x.git", stderr=""):
        self.calls: list[list[str]] = []
        self.fail_on = fail_on
        self.remote = remote
        self.stderr = stderr

    def __call__(self, argv, cwd=None, capture_output=False, text=False):
        self.calls.append(argv)
        args = argv[1:]
        if self.fail_on is not None and args[0] == self.fail_on:
            return subprocess.CompletedProcess(argv, 1, "", self.stderr or "fatal: boom")
        stdout = f"{self.remote}\n" if args[:2] == ["remote", "get-url"] else ""
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    def argv_for(self, subcommand):
        return next((a for a in self.calls if a[1] == subcommand), None)


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
