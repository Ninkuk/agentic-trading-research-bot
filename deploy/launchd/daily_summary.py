"""Build and send the daily run summary over ntfy.

Reads three health layers (same as status.sh, but judged, not just listed):
  1. launchctl last-exit codes for every com.tradingbot.* job
  2. logs/*.log activity in the last 24h — runs started, FAILED/STALE lines
  3. data/*.db snapshot freshness vs. each DB's expected cadence

Run from the repo root (the launchd wrapper guarantees it). Exit 0 even on
an unhealthy summary — the notification IS the alert; only a failure to
notify exits non-zero so it surfaces in launchctl/status.sh.
"""

import datetime as dt
import os
import re
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sources.common import notify  # noqa: E402

LOGS = Path("logs")
DATA = Path("data")
PREFIX = "com.tradingbot."
# This script's own StandardOutPath, named for its job in install.py's JOBS.
SELF_LOG = "daily-summary.log"
_TS = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
_BAD = ("FAILED", "STALE", "Traceback", "Error:")

# How long a job may run before the digest calls it hung. INTERIM two-tier
# stopgap: replace with measured per-job values once env.sh's `end:` lines have
# accumulated (~2 weeks). A stopgap with no recorded end date becomes permanent.
#
# A threshold only matters for a job still plausibly running at 21:15 (the
# digest fires once, nightly) -- i.e. one that starts within roughly an hour
# of it. Measured gaps: dashboard 2min, advisor 3min, scorer 5min, composite
# 10min -- all safe under the default tier. `edgar` (20:30, 45min before the
# digest) is the only slow-tier entry that is actually load-bearing today;
# every other _SLOW_JOBS entry starts 2h-17h earlier; if still alive at
# digest time it would be flagged under either tier, so those are defensive
# against future schedule changes rather than currently load-bearing.
_HUNG_DEFAULT_MIN = 15
_HUNG_SLOW_MIN = 60
_SLOW_JOBS = {
    "fred-vintages",  # ~80 API calls, ~1.7M rows re-upserted
    "preopen",  # four screeners serially
    "portfolio",  # headless `claude -p`
    "journal",  # headless `claude -p`
    "backtest",  # point-in-time replay
    "ftd-full",  # re-ingests 24 months
    "short-interest-full",  # re-ingests ~12 months
    "fundamentals-bulk",  # downloads + ingests a DERA quarterly ZIP
    "edgar",  # starts 45min before the digest AND has a designed sleep 900 retry pause
}

# Max acceptable age (days) of the newest snapshot, by DB filename. Defaults
# to 4 (daily jobs surviving a weekend + a holiday). Slower cadences:
MAX_AGE_DAYS = {
    "ats.db": 9,
    "cftc.db": 9,
    "eia.db": 9,
    "econ_calendar.db": 9,
    "fomc.db": 9,
    "sec_fundamentals.db": 9,
    "ftd.db": 10,
    "usda.db": 35,
    "market_calendar.db": 35,
}
DEFAULT_MAX_AGE_DAYS = 4

# Snapshot column holding the count of domain rows written by the newest run,
# per DB filename. A fresh snapshot whose count is 0 means a silent-empty
# fetch (see plan 002) — flagged even though captured_at looks current. DBs
# absent from this map are not count-checked (freshness-only, as before).
ROW_COUNT_COL = {
    "ats.db": "row_count",
    "cboe_stats.db": "row_count",
    "cftc.db": "row_count",
    "composite.db": "signals_ok",
    "earnings.db": "event_count",
    "econ_calendar.db": "event_count",
    "edgar.db": "filing_count",
    "eia.db": "observation_count",
    "etfs.db": "universe_count",
    "fomc.db": "event_count",
    "fred.db": "observation_count",
    "ftd.db": "row_count",
    "market_calendar.db": "event_count",
    "nyfed.db": "row_count",
    "options.db": "row_count",
    "reddit.db": "ticker_count",
    "sec_fundamentals.db": "fact_count",
    "short_interest.db": "row_count",
    "short_volume.db": "row_count",
    "stocks.db": "universe_count",
    "treasury.db": "row_count",
    "usda.db": "observation_count",
}

# DBs that legitimately write zero-row snapshots on some runs — never flag
# these for an empty count (probe days / bimonthly / empty-by-design domains).
EMPTY_OK = {
    "ftd.db",  # SEC fails-to-deliver probe days write zero-row snapshots
    "short_interest.db",  # FINRA short interest is bimonthly; off-cycle runs are empty
    "nyfed.db",  # some NY Fed domains (iorb, primary_dealer) are empty by design
}


def job_exit_codes():
    """{job-name: launchctl's last-exit-status column}.

    NOT a running-vs-not indicator, despite appearances. `launchctl list`
    prints 0 in this column both for "exited cleanly" and for "has never
    exited" (see status.sh), and -- the part that matters here -- a job that
    is CURRENTLY RUNNING still shows its PREVIOUS exit status in this column,
    not a sentinel. Verified live: all 35 jobs read 0 here, including one
    caught mid-run. Use running_jobs() for a running/not signal instead.
    """
    out = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
    codes = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2].startswith(PREFIX):
            try:
                code = None if parts[1] == "-" else int(parts[1])
            except ValueError:
                continue
            codes[parts[2][len(PREFIX) :]] = code
    return codes


def running_jobs():
    """{job names} currently running, per launchctl's PID column.

    `launchctl list`'s three columns are PID, last-exit-status, label. As
    job_exit_codes documents, the exit-status column is ambiguous -- 0 means
    both "exited cleanly" and "never exited", and it holds a RUNNING job's
    PREVIOUS status, not a sentinel -- so it cannot answer "is this running
    right now". The PID column can: a running job shows a real PID there, an
    idle one shows "-". status.sh resolves the same ambiguity via
    `launchctl print` instead; this resolves it via the PID column so the
    digest can check all jobs with a single `launchctl list` call.
    """
    out = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
    running = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2].startswith(PREFIX) and parts[0] != "-":
            running.add(parts[2][len(PREFIX) :])
    return running


def scan_log(path, since):
    """(runs_started, [bad lines]) within the window. Untimestamped lines
    (e.g. tracebacks) inherit the in-window state of the last timestamped
    line, so a crash between two starts is attributed correctly.

    Counts only `start:` lines as a run -- env.sh's step_start emits `step:`
    for sub-steps of a multi-step wrapper (cftc_weekly.sh, preopen_batch.sh),
    which must NOT inflate the "N runs in 24h" headline the way they would if
    step_start reused the `start:` shape."""
    runs, bad, in_window = 0, [], False
    for line in path.read_text(errors="replace").splitlines():
        m = _TS.match(line)
        if m:
            ts = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            in_window = ts >= since
        if not in_window:
            continue
        if "start:" in line and m:
            runs += 1
        if any(marker in line for marker in _BAD):
            bad.append(f"{path.stem}: {line.strip()[:160]}")
    return runs, bad


def last_progress(path):
    """Timestamp of the most recent `start:` or `step:` line, or None.

    Returns a NAIVE datetime in LOCAL (Phoenix) time: wrapper logs are stamped
    by bash `date`, and build_summary compares against now_local. Do NOT route
    this through phx_date -- that converts UTC-stored instants and would be
    wrong here.

    A job progressing through env.sh's step_start markers must keep resetting
    its clock -- that is the correct hang semantic (a STUCK step should trip
    the tier; a job still moving through steps should not) -- so this counts
    `step:` lines as progress too, same as `start:`. The consequence: for a
    multi-step wrapper (cftc_weekly.sh, preopen_batch.sh) the age this
    returns is the CURRENT STEP's, not the whole run's, so the hung-job tier
    budgets a stuck step, not total runtime. This matters for the planned
    follow-up that derives measured per-job thresholds from these logs (see
    _HUNG_DEFAULT_MIN's docstring) -- those thresholds would be per-step
    budgets for multi-step jobs, not whole-run ones.
    """
    newest = None
    for line in path.read_text(errors="replace").splitlines():
        if "start:" not in line and "step:" not in line:
            continue
        m = _TS.match(line)
        if not m:
            continue
        try:
            ts = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if newest is None or ts > newest:
            newest = ts
    return newest


def hung_jobs(running, now_local):
    """[problem lines] for jobs in `running` that have been running past their limit.

    `running` is a set of job names currently running (see running_jobs()).
    Membership in that set IS the running signal -- launchctl's exit-status
    column cannot supply one (see job_exit_codes), so without a set built
    from the PID column a hung job is invisible, and launchd will not
    re-spawn it while the instance is alive.

    Detection only: never kills or restarts anything.
    """
    problems = []
    for job in sorted(running):
        if f"{job}.log" == SELF_LOG:  # the digest is running as it builds this
            continue
        try:
            path = LOGS / f"{job}.log"
            if not path.exists():
                continue
            started = last_progress(path)
            if started is None:
                continue
            minutes = (now_local - started).total_seconds() / 60
        except Exception as e:  # build_summary runs outside main's try
            problems.append(f"{job}: hang check failed ({type(e).__name__})")
            continue
        limit = _HUNG_SLOW_MIN if job in _SLOW_JOBS else _HUNG_DEFAULT_MIN
        if minutes > limit:
            problems.append(f"{job}: running {int(minutes)}min (limit {limit}min) — possible hang")
    return problems


def stale_dbs(now):
    stale = []
    for db in sorted(DATA.glob("*.db")):
        try:
            with sqlite3.connect(db) as conn:
                latest = conn.execute("SELECT MAX(captured_at) FROM snapshots").fetchone()[0]
        except sqlite3.Error:
            continue  # not a snapshots-bearing DB; not ours to judge
        if latest is None:
            stale.append(f"{db.name}: no snapshots")
            continue
        try:
            captured = dt.datetime.fromisoformat(latest)
            if captured.tzinfo is None:
                captured = captured.replace(tzinfo=dt.UTC)
            age = now - captured
        except (ValueError, TypeError):
            stale.append(f"{db.name}: unparseable captured_at")
            continue
        limit = MAX_AGE_DAYS.get(db.name, DEFAULT_MAX_AGE_DAYS)
        if age > dt.timedelta(days=limit):
            stale.append(f"{db.name}: {age.days}d old (limit {limit}d)")

        col = ROW_COUNT_COL.get(db.name)
        if col and db.name not in EMPTY_OK:
            try:
                with sqlite3.connect(db) as conn:
                    n = conn.execute(
                        f"SELECT {col} FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1"
                    ).fetchone()[0]
            except sqlite3.Error:
                n = None  # column vanished / schema drift — skip the count check
            if n == 0:
                stale.append(f"{db.name}: newest snapshot has 0 rows (empty fetch?)")
    return stale


def signals_digest():
    """Composite + scorer context appended below the health summary.
    Best-effort by design: these lines inform, the health layers above
    alert — any read failure becomes a one-line note, never a crash.
    Reads are mode=ro; the 9:15 slot runs after composite (9:05) and
    scorer (9:10) so tonight's rows are normally already there."""
    lines = []
    try:
        with sqlite3.connect("file:data/composite.db?mode=ro", uri=True) as conn:
            regime = conn.execute(
                "SELECT regime, vix, inputs_present, inputs_expected FROM v_latest_regime"
            ).fetchone()
            flagged = conn.execute("SELECT COUNT(*) FROM v_flagged").fetchone()[0]
        if regime:
            vix = f"{regime[1]:.1f}" if regime[1] is not None else "?"
            lines.append(
                f"regime: {regime[0]} (vix {vix},"
                f" {regime[2]}/{regime[3]} inputs) · {flagged} flagged"
            )
    except Exception as e:
        lines.append(f"composite: unreadable ({type(e).__name__})")
    try:
        with sqlite3.connect("file:data/scorer.db?mode=ro", uri=True) as conn:
            run = conn.execute(
                "SELECT registered, matured, skipped FROM snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
            pending = conn.execute("SELECT COUNT(*) FROM v_pending").fetchone()[0]
            bull5 = conn.execute(
                "SELECT n_matured, avg_excess, hit_rate FROM v_bucket_performance"
                " WHERE bucket='strong_bull' AND horizon=5"
            ).fetchone()
        if run:
            lines.append(
                f"scorer: {run[0]} registered, {run[1]} matured,"
                f" {run[2]} skipped · {pending} pending"
            )
        if bull5 and bull5[0]:
            exc = f"{bull5[1]:+.1%}" if bull5[1] is not None else "?"
            hit = f"{bull5[2]:.0%}" if bull5[2] is not None else "?"
            lines.append(f"strong_bull @5d: n={bull5[0]} exc {exc} hit {hit}")
    except Exception as e:
        lines.append(f"scorer: unreadable ({type(e).__name__})")
    return lines


def _book_line(book):
    hp = book["heat_pct"]
    heat = f"{hp:.2%}" if hp is not None else "n/a"
    n = book["positions"] or 0
    pos = f"{n} position" if n == 1 else f"{n} positions"
    hc = book["heat_coverage"]
    cov = f"cov {hc:.1f}" if hc is not None else "cov n/a"
    eq = book["equity"]
    equity = f"equity ${eq:.0f}" if eq is not None else "equity ?"
    return f"book: {heat} risk · {pos} · {cov} · {equity}"


def _sources_line(header):
    n = header["sources_failed"] or 0
    return f"advisor: {n} sources failed" if n > 0 else None


def _disagree_lines(rows):
    if not rows:
        return ["disagree: none"]
    ordered = sorted(rows, key=lambda r: (r["score_sum"], r["symbol"]))
    out = []
    for r in ordered:
        tag = "STRONG" if r["strong"] else "weak"
        grp = f" ({r['group_name']})" if r["group_name"] else ""
        out.append(f"disagree: {r['symbol']} {r['score_sum']:+d} {tag}{grp}")
    return out


def _caps_lines(rows):
    if not rows:
        return ["caps: none tonight"]
    out = []
    for r in sorted(rows, key=lambda r: r["symbol"]):
        cs = r["cap_shares"]
        sh = f"{cs:.2f}sh" if cs is not None else "n/a"
        out.append(f"cap: {r['symbol']} ≤ {sh}")
    return out


def _staleness_line(header):
    pc, rc = header["portfolio_captured_at"], header["captured_at"]
    if not pc or not rc:
        return None
    # Timestamps are stored UTC (+00:00). The slot runs ~9:12pm Phoenix = the
    # NEXT UTC day, so compare LOCAL dates (astimezone) or the age reads one
    # day high. Host TZ is Phoenix; tests pin it via the phoenix_tz fixture.
    pd = dt.datetime.fromisoformat(pc).astimezone().date()
    rd = dt.datetime.fromisoformat(rc).astimezone().date()
    if pd == rd:
        return None
    return f"(sized vs portfolio from {pd.strftime('%b %d')} — {(rd - pd).days}d old)"


def format_advisor_lines(book, disagreements, caps, header):
    """Render the advisor digest block from pre-fetched rows. Pure: no I/O.
    Rows are accessed by string key, so dict and sqlite3.Row both work."""
    if header is None:
        return ["advisor: no snapshot"]
    lines = []
    if book is not None:
        lines.append(_book_line(book))
    sources = _sources_line(header)
    if sources:
        lines.append(sources)
    lines += _disagree_lines(disagreements)
    lines += _caps_lines(caps)
    stale = _staleness_line(header)
    if stale:
        lines.append(stale)
    # Fallback for degenerate empty case; header is not None → real no-snapshot is caught above.
    return lines or ["advisor: no snapshot"]


def advisor_digest():
    """Advisor book view appended below the signals block. Best-effort:
    any read failure becomes a one-line note, never a crash. mode=ro; the
    9:15 slot runs after advisor (9:12) so tonight's rows are normally present."""
    try:
        with sqlite3.connect("file:data/advisor.db?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            header = conn.execute(
                "SELECT captured_at, portfolio_captured_at, sources_failed "
                "FROM snapshots WHERE id IN (SELECT id FROM v_latest_snapshot)"
            ).fetchone()
            book = conn.execute(
                "SELECT positions, heat_pct, heat_coverage, equity FROM v_book_heat"
            ).fetchone()
            disagreements = conn.execute(
                "SELECT symbol, score_sum, group_name, strong FROM v_disagreements"
            ).fetchall()
            caps = conn.execute(
                "SELECT symbol, cap_shares FROM v_latest_caps WHERE cap_shares IS NOT NULL"
            ).fetchall()
        return format_advisor_lines(book, disagreements, caps, header)
    except Exception as e:
        return [f"advisor: unreadable ({type(e).__name__})"]


def build_summary(now_local, now_utc):
    total_runs, problems = 0, []

    codes = job_exit_codes()
    for job, code in sorted(codes.items()):
        if code not in (None, 0):
            problems.append(f"{job}: last exit {code}")
    problems.extend(hung_jobs(running_jobs(), now_local))

    since = now_local - dt.timedelta(hours=24)
    for log in sorted(LOGS.glob("*.log")):
        # Skip our own launchd StandardOutPath: this function prints every
        # problem it finds, so re-reading that file would re-report yesterday's
        # problems (and write them again), keeping the alert red long after the
        # underlying job recovered.
        if log.name == SELF_LOG:
            continue
        runs, bad = scan_log(log, since)
        total_runs += runs
        problems.extend(bad)

    problems.extend(stale_dbs(now_utc))

    healthy = not problems
    lines = [f"{total_runs} runs in the last 24h, {len(codes)} jobs loaded."]
    lines += problems if problems else ["All healthy."]
    lines = lines[:30]
    digest = signals_digest()
    if digest:
        lines += ["", "— signals —", *digest]
    advisor = advisor_digest()
    if advisor:
        lines += ["", "— advisor —", *advisor]
    return healthy, "\n".join(lines)


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


def main():
    try:
        healthy, summary = build_summary(dt.datetime.now(), dt.datetime.now(dt.UTC))
    except Exception as e:  # never let summary assembly silence the alert
        healthy = False
        summary = f"summary build failed ({type(e).__name__})"
    try:
        notify.send(
            summary,
            title="trading-bot daily summary",
            priority="default" if healthy else "high",
            tags=["white_check_mark"] if healthy else ["warning"],
        )
    except RuntimeError as e:
        print(f"notify failed ({type(e).__name__})", file=sys.stderr)
        return 1
    heartbeat()
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
