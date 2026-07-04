import sqlite3

from sources.monitors.earnings_calendar import run as runmod

NOW = "2026-07-06T00:00:00+00:00"


def _row(ticker, date):
    return {"ticker": ticker, "name": ticker, "date": date, "timing": "amc",
            "eps_est": None, "eps_growth": None, "rev_est": None,
            "rev_growth": None, "mktcap": 1e9}


def test_run_end_to_end_counts_and_snapshots(tmp_path):
    db_path = str(tmp_path / "e.db")
    sid, count = runmod.run(
        db_path, fetch_forward=lambda: [_row("A", "2026-07-08"),
                                        _row("B", "2026-07-09")], now_iso=NOW)
    assert count == 2
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1


def test_run_only_filters_to_watchlist(tmp_path):
    db_path = str(tmp_path / "e.db")
    runmod.run(db_path, only=["A"],
               fetch_forward=lambda: [_row("A", "2026-07-08"),
                                      _row("B", "2026-07-09")],
               confirm=lambda *a, **k: set(), now_iso=NOW)
    conn = sqlite3.connect(db_path)
    tickers = {r[0] for r in conn.execute("SELECT subtype FROM events")}
    assert tickers == {"A"}


def test_run_transient_feed_failure_preserves_calendar_hides_secret(
        tmp_path, capsys):
    db_path = str(tmp_path / "e.db")
    runmod.run(db_path, fetch_forward=lambda: [_row("A", "2026-07-08")],
               now_iso=NOW)

    def boom():
        raise RuntimeError("https://stockanalysis?k=SECRET boom")

    runmod.run(db_path, fetch_forward=boom, now_iso=NOW)
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRET" not in err
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_run_estimates_missing_watched_ticker_via_edgar_cadence(tmp_path):
    db_path = str(tmp_path / "e.db")
    # Watch A (covered by the feed) and Z (NOT in the feed). Z has a regular
    # ~91-day Item-2.02 cadence -> it gets a cadence-based scheduled estimate.
    hist = {"Z": ["2026-01-15", "2026-04-16", "2026-07-16"]}

    runmod.run(
        db_path, only=["A", "Z"],
        fetch_forward=lambda: [_row("A", "2026-07-08")],
        confirm=lambda *a, **k: set(),
        history=lambda tickers: {t: hist[t] for t in tickers if t in hist},
        now_iso=NOW)

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT event_date, status, source FROM events "
                       "WHERE subtype='Z'").fetchone()
    assert row == ("2026-10-15", "scheduled", "edgar-estimate")
    # the covered ticker is unaffected and stays the aggregator forward date
    assert conn.execute("SELECT source FROM events WHERE subtype='A'"
                       ).fetchone() == ("stockanalysis",)


def test_run_estimate_only_for_missing_names_not_covered_ones(tmp_path):
    db_path = str(tmp_path / "e.db")
    called = {"tickers": None}

    def history(tickers):
        called["tickers"] = list(tickers)
        return {}

    runmod.run(
        db_path, only=["A", "Z"],
        fetch_forward=lambda: [_row("A", "2026-07-08")],
        confirm=lambda *a, **k: set(), history=history, now_iso=NOW)
    # only the uncovered watched name (Z) is looked up for estimation
    assert called["tickers"] == ["Z"]


def test_run_estimate_respects_horizon(tmp_path):
    db_path = str(tmp_path / "e.db")
    hist = {"Z": ["2026-01-15", "2026-04-16", "2026-07-16"]}   # est 2026-10-15

    runmod.run(
        db_path, only=["A", "Z"], horizon_days=30,             # cutoff ~2026-08-05
        fetch_forward=lambda: [_row("A", "2026-07-08")],
        confirm=lambda *a, **k: set(),
        history=lambda tickers: {t: hist[t] for t in tickers if t in hist},
        now_iso=NOW)

    conn = sqlite3.connect(db_path)
    # the estimate (2026-10-15) is beyond the 30-day horizon -> not stored
    assert conn.execute("SELECT COUNT(*) FROM events WHERE subtype='Z'"
                       ).fetchone()[0] == 0


def test_run_keep_days_prunes_snapshots_not_events(tmp_path):
    db_path = str(tmp_path / "e.db")
    runmod.run(db_path, fetch_forward=lambda: [_row("A", "2026-07-08")],
               now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, fetch_forward=lambda: [_row("A", "2026-07-08")],
               now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] >= 1
