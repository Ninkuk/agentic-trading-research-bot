from pipeline.scheduler import catalog


def test_job_names_unique_and_kinds_valid():
    names = [j.name for j in catalog.JOBS]
    assert len(set(names)) == len(names)
    kinds = {"daily", "cftc_weekly", "econ_release", "earnings", "chain", "gate"}
    assert all(j.kind in kinds for j in catalog.JOBS)


def test_catalog_order_puts_chains_after_their_upstreams():
    pos = {j.name: i for i, j in enumerate(catalog.JOBS)}
    for j in catalog.JOBS:
        for up in j.after:
            assert pos[up] < pos[j.name], (j.name, up)


def test_daily_maintenance_covers_five_monitors_plus_etfs_refresh():
    daily = {j.name for j in catalog.JOBS if j.kind == "daily"}
    assert daily == {"earnings", "econ_calendar", "fomc", "market_calendar",
                     "treasury", "etfs"}


def test_argv_for_leads_passes_all_source_dbs():
    job = catalog.JOB_BY_NAME["leads"]
    argv = catalog.argv_for(job, "data")
    assert argv[:2] == ["--db", "data/leads.db"]
    for flag in ("--cftc-db", "--fred-db", "--fundamentals-db", "--stocks-db"):
        assert flag in argv


def test_argv_for_promote_passes_all_source_dbs():
    job = catalog.JOB_BY_NAME["promote"]
    argv = catalog.argv_for(job, "data")
    assert argv[:2] == ["--db", "data/candidates.db"]
    for flag, val in (("--leads-db", "data/leads.db"),
                      ("--stocks-db", "data/stocks.db"),
                      ("--etfs-db", "data/etfs.db")):
        assert flag in argv
        assert argv[argv.index(flag) + 1] == val


def test_argv_for_etfs_passes_own_db_and_type():
    job = catalog.JOB_BY_NAME["etfs"]
    argv = catalog.argv_for(job, "data")
    assert argv[:2] == ["--db", "data/etfs.db"]
    assert argv[-2:] == ["--type", "e"]


def test_argv_for_gate_carries_window():
    argv = catalog.argv_for(catalog.JOB_BY_NAME["gate_pre_close"], "data")
    assert argv[-2:] == ["--window", "pre_close"]


def test_argv_for_gate_passes_candidates_db():
    argv = catalog.argv_for(catalog.JOB_BY_NAME["gate_pre_close"], "data")
    assert argv[argv.index("--candidates-db") + 1] == "data/candidates.db"
    assert argv[-2:] == ["--window", "pre_close"]


def test_constants_match_spec():
    assert catalog.MAX_ATTEMPTS == 3
    assert catalog.STALE_RUNNING_HOURS == 2
    assert catalog.FIXPOINT_LIMIT == 3
    assert catalog.RELEASE_LAG_MIN == 15
    assert (catalog.PRE_CLOSE_ET, catalog.PRE_CLOSE_EARLY_ET) == ("15:30", "12:30")
