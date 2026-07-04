from pipeline.scheduler import db as sdb
from pipeline.scheduler import run as srun
from sources.common import monitor_common

NOW_FRI_LATE = "2026-07-03T21:00:00+00:00"   # Fri 2026-07-03 17:00 ET (EDT)

REGISTRY_ALL = {name: (lambda argv: None) for name in
                ("earnings", "econ_calendar", "fomc", "market_calendar",
                 "treasury", "cftc", "fred", "fundamentals", "stocks", "leads")}


def _monitor(rows=()):
    conn = monitor_common.connect(":memory:")
    monitor_common.ensure_schema(conn)
    if rows:
        monitor_common.upsert_events(conn, list(rows), "2026-07-01T00:00:00+00:00")
    return conn


def _ctx(now_iso, econ_rows=(), earn_rows=(), mkt_rows=()):
    from pipeline.scheduler import extract
    today, hhmm, wd = extract.et_parts(now_iso)
    return {"today": today, "now_hhmm": hhmm, "weekday": wd,
            "econ": _monitor(econ_rows), "earnings": _monitor(earn_rows),
            "market": _monitor(mkt_rows)}


def _fresh_sched():
    conn = sdb.connect(":memory:")
    sdb.ensure_schema(conn)
    return conn


def _due_names(due):
    return [(d["job"], d["trigger_key"]) for d in due]


def test_friday_late_daily_cftc_and_gate_due():
    conn = _fresh_sched()
    due = srun.compute_due(conn, _ctx(NOW_FRI_LATE), REGISTRY_ALL, "data",
                           now_iso=NOW_FRI_LATE)
    names = _due_names(due)
    assert ("cftc", "2026-07-03") in names
    assert ("earnings", "daily:2026-07-03") in names
    # 17:00 ET on a trading Friday: pre-close gate window trigger holds, but
    # 'gate' is NOT in the registry -> skipped
    assert all(j != "gate_pre_close" for j, _k in names)


def test_ok_row_makes_job_not_due_idempotent():
    conn = _fresh_sched()
    a = sdb.start_attempt(conn, "cftc", "2026-07-03", NOW_FRI_LATE)
    sdb.finish_attempt(conn, "cftc", "2026-07-03", a, NOW_FRI_LATE, "ok")
    due = srun.compute_due(conn, _ctx(NOW_FRI_LATE), REGISTRY_ALL, "data",
                           now_iso=NOW_FRI_LATE)
    assert ("cftc", "2026-07-03") not in _due_names(due)


def test_max_attempts_exhaustion_blocks():
    conn = _fresh_sched()
    for _ in range(3):
        a = sdb.start_attempt(conn, "cftc", "2026-07-03", NOW_FRI_LATE)
        sdb.finish_attempt(conn, "cftc", "2026-07-03", a, NOW_FRI_LATE,
                           "error", "HTTPError")
    due = srun.compute_due(conn, _ctx(NOW_FRI_LATE), REGISTRY_ALL, "data",
                           now_iso=NOW_FRI_LATE)
    assert ("cftc", "2026-07-03") not in _due_names(due)


def test_live_running_blocks_stale_running_does_not():
    conn = _fresh_sched()
    sdb.start_attempt(conn, "cftc", "2026-07-03", "2026-07-03T20:30:00+00:00")
    due = srun.compute_due(conn, _ctx(NOW_FRI_LATE), REGISTRY_ALL, "data",
                           now_iso=NOW_FRI_LATE)          # 30 min old: live
    assert ("cftc", "2026-07-03") not in _due_names(due)
    later = "2026-07-03T23:59:00+00:00"                   # 3.5h old: stale
    due = srun.compute_due(conn, _ctx(later), REGISTRY_ALL, "data",
                           now_iso=later)
    assert ("cftc", "2026-07-03") in _due_names(due)


def test_econ_release_and_chain_keys():
    conn = _fresh_sched()
    now = "2026-07-01T13:00:00+00:00"  # Wed 09:00 ET
    econ = [{"event_type": "cpi_release", "event_date": "2026-07-01",
             "event_time": "08:30", "source": "fred"}]
    due = srun.compute_due(conn, _ctx(now, econ_rows=econ), REGISTRY_ALL,
                           "data", now_iso=now)
    names = _due_names(due)
    assert ("fred", "cpi_release:2026-07-01") in names
    # leads not due yet: no upstream ok run exists
    assert all(j != "leads" for j, _k in names)
    # after fred succeeds, leads becomes due keyed to fred's run
    a = sdb.start_attempt(conn, "fred", "cpi_release:2026-07-01", now)
    sdb.finish_attempt(conn, "fred", "cpi_release:2026-07-01", a, now, "ok")
    due = srun.compute_due(conn, _ctx(now, econ_rows=econ), REGISTRY_ALL,
                           "data", now_iso=now)
    assert ("leads", "after:fred:cpi_release:2026-07-01") in _due_names(due)


def test_earnings_post_close_and_sunday_weekly():
    conn = _fresh_sched()
    earn = [{"event_type": "earnings", "event_date": "2026-07-01",
             "subtype": "AAPL", "source": "stockanalysis"}]
    # Wed 19:00 ET (23:00 UTC): earnings-driven refresh due
    now = "2026-07-01T23:00:00+00:00"
    names = _due_names(srun.compute_due(conn, _ctx(now, earn_rows=earn),
                                        REGISTRY_ALL, "data", now_iso=now))
    assert ("fundamentals", "earnings:2026-07-01") in names
    # Sunday: weekly sweep due even with no earnings events
    sun = "2026-07-05T16:00:00+00:00"  # Sun 12:00 ET
    names = _due_names(srun.compute_due(conn, _ctx(sun), REGISTRY_ALL, "data",
                                        now_iso=sun))
    assert ("stocks", "weekly:2026-07-05") in names


def test_gate_pre_close_shifts_on_equity_early_close():
    conn = _fresh_sched()
    reg = dict(REGISTRY_ALL, gate=lambda argv: None)
    # Black Friday 2026-11-27, 13:05 ET (18:05 UTC EST): early close -> due at 12:30
    mkt = [{"event_type": "early_close", "event_date": "2026-11-27",
            "source": "nyse"}]
    now = "2026-11-27T18:05:00+00:00"
    names = _due_names(srun.compute_due(conn, _ctx(now, mkt_rows=mkt), reg,
                                        "data", now_iso=now))
    assert ("gate_pre_close", "pre_close:2026-11-27") in names
    # same wall time on a normal trading day: 13:05 < 15:30 -> not due
    normal = "2026-11-30T18:05:00+00:00"  # Monday
    names = _due_names(srun.compute_due(conn, _ctx(normal), reg, "data",
                                        now_iso=normal))
    assert all(j != "gate_pre_close" for j, _k in names)


def test_gate_not_due_on_non_trading_day_and_pre_open_opt_in():
    conn = _fresh_sched()
    reg = dict(REGISTRY_ALL, gate=lambda argv: None)
    sat = "2026-07-04T20:00:00+00:00"  # Saturday 16:00 ET
    names = _due_names(srun.compute_due(conn, _ctx(sat), reg, "data",
                                        now_iso=sat))
    assert all(not j.startswith("gate") for j, _k in names)
    mon = "2026-07-06T14:00:00+00:00"  # Monday 10:00 ET
    names = _due_names(srun.compute_due(conn, _ctx(mon), reg, "data",
                                        now_iso=mon))
    assert all(j != "gate_pre_open" for j, _k in names)  # off by default
    names = _due_names(srun.compute_due(conn, _ctx(mon), reg, "data",
                                        window_pre_open=True, now_iso=mon))
    assert ("gate_pre_open", "pre_open:2026-07-06") in names


def test_missing_monitor_db_skips_dependent_jobs():
    conn = _fresh_sched()
    ctx = _ctx(NOW_FRI_LATE)
    ctx["econ"] = None      # econ_calendar.db missing
    ctx["market"] = None    # market_calendar.db missing
    reg = dict(REGISTRY_ALL, gate=lambda argv: None)
    names = _due_names(srun.compute_due(conn, ctx, reg, "data",
                                        now_iso=NOW_FRI_LATE))
    assert all(j != "fred" for j, _k in names)             # needs econ
    assert all(not j.startswith("gate") for j, _k in names)  # needs market
    assert ("cftc", "2026-07-03") in names                 # clock-only job unaffected
