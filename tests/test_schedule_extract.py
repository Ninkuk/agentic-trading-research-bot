from pipeline.scheduler import extract
from sources.common import monitor_common

NOW = "2026-07-04T12:00:00+00:00"


def _monitor_conn(rows):
    conn = monitor_common.connect(":memory:")
    monitor_common.ensure_schema(conn)
    monitor_common.upsert_events(conn, rows, NOW)
    return conn


def test_et_parts_summer_edt():
    # 2026-07-03 20:30 UTC == 16:30 ET (EDT, UTC-4); Friday
    assert extract.et_parts("2026-07-03T20:30:00+00:00") == ("2026-07-03", "16:30", 4)


def test_et_parts_winter_est():
    # 2026-01-09 20:30 UTC == 15:30 ET (EST, UTC-5); Friday
    assert extract.et_parts("2026-01-09T20:30:00+00:00") == ("2026-01-09", "15:30", 4)


def test_et_parts_crosses_date_line():
    # 2026-07-04 01:00 UTC is still 2026-07-03 21:00 ET
    d, hhmm, _wd = extract.et_parts("2026-07-04T01:00:00+00:00")
    assert (d, hhmm) == ("2026-07-03", "21:00")


def test_plus_minutes():
    assert extract.plus_minutes("08:30", 15) == "08:45"
    assert extract.plus_minutes("09:55", 15) == "10:10"


def test_econ_released_respects_lag_and_default_time():
    conn = _monitor_conn([
        {"event_type": "cpi_release", "event_date": "2026-07-04",
         "event_time": "08:30", "source": "fred"},
        {"event_type": "gdp_release", "event_date": "2026-07-04",
         "event_time": "10:00", "source": "fred"},          # not yet + lag
        {"event_type": "jolts_release", "event_date": "2026-07-04",
         "event_time": None, "source": "fred"},             # default 08:30
        {"event_type": "ppi_release", "event_date": "2026-07-05",
         "event_time": "08:30", "source": "fred"},          # wrong day
    ])
    due = extract.econ_released(conn, "2026-07-04", "10:05",
                                lag_min=15, default_time="08:30")
    assert sorted(due) == [("cpi_release", "2026-07-04"),
                           ("jolts_release", "2026-07-04")]


def test_earnings_count_scopes_to_type_and_day():
    conn = _monitor_conn([
        {"event_type": "earnings", "event_date": "2026-07-04", "subtype": "AAPL",
         "source": "stockanalysis"},
        {"event_type": "earnings", "event_date": "2026-07-04", "subtype": "MSFT",
         "source": "stockanalysis"},
        {"event_type": "earnings", "event_date": "2026-07-05", "subtype": "NVDA",
         "source": "stockanalysis"},
    ])
    assert extract.earnings_count(conn, "2026-07-04") == 2


def test_equity_early_close_excludes_bond_early_close():
    conn = _monitor_conn([
        {"event_type": "bond_early_close", "event_date": "2026-07-02",
         "source": "sifma"},
        {"event_type": "early_close", "event_date": "2026-11-27",
         "source": "nyse"},
    ])
    assert not extract.equity_early_close(conn, "2026-07-02")
    assert extract.equity_early_close(conn, "2026-11-27")


def test_is_trading_day_reexport_weekend_and_holiday():
    conn = _monitor_conn([
        {"event_type": "market_holiday", "event_date": "2026-07-03",
         "source": "nyse"},
    ])
    assert not extract.is_trading_day(conn, "2026-07-04")  # Saturday
    assert not extract.is_trading_day(conn, "2026-07-03")  # holiday
    assert extract.is_trading_day(conn, "2026-07-06")      # Monday
