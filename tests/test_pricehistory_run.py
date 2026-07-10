import sqlite3

from sources.combiners.scorer import db as scorer_db
from sources.combiners.scorer import pricehistory

# 9:05pm Phoenix on Jul 8 == 04:05Z on Jul 9. The fixture MUST straddle the
# rollover: with a 21:05Z stamp a naive UTC date-slice would coincide with the
# Phoenix date and the settled-only test could not catch a clock mixup.
EVENING = "2026-07-09T04:05:00+00:00"
PHX_TODAY = "2026-07-08"


def _fake(rows):
    """rows: {symbol: [(date, close), ...]} -> a fetch_history stand-in."""

    def fetch(symbol, before_date):
        return [(d, c) for d, c in rows[symbol] if d < before_date]

    return fetch


def _ledger(path):
    conn = sqlite3.connect(path)
    out = dict(conn.execute("SELECT price_date || '|' || symbol, close FROM prices"))
    conn.close()
    return out


def test_run_inserts_rows_into_prices(tmp_path):
    p = str(tmp_path / "scorer.db")
    ok, inserted, failed = pricehistory.run(
        p,
        ["XLE"],
        now_iso=EVENING,
        fetch_history=_fake({"XLE": [("2026-07-06", 50.0), ("2026-07-07", 51.0)]}),
        sleep=lambda _: None,
    )
    assert (ok, inserted, failed) == (1, 2, [])
    assert _ledger(p) == {"2026-07-06|XLE": 50.0, "2026-07-07|XLE": 51.0}


def test_run_is_idempotent(tmp_path):
    p = str(tmp_path / "scorer.db")
    f = _fake({"XLE": [("2026-07-06", 50.0)]})
    pricehistory.run(p, ["XLE"], now_iso=EVENING, fetch_history=f, sleep=lambda _: None)
    _, inserted, _ = pricehistory.run(
        p, ["XLE"], now_iso=EVENING, fetch_history=f, sleep=lambda _: None
    )
    assert inserted == 0, "INSERT OR IGNORE must make a re-run a no-op"


def test_run_never_overwrites_an_existing_forward_row(tmp_path):
    """The real no-overwrite guard. A bare value check against the API cannot
    distinguish 'preserved' from 'overwritten with the same value', so seed a
    deliberately WRONG close and prove it survives."""
    p = str(tmp_path / "scorer.db")
    conn = scorer_db.connect(p)
    scorer_db.ensure_schema(conn)
    scorer_db.insert_prices(conn, [("XLE", "2026-07-07", 999.0)])
    conn.commit()
    conn.close()

    _, inserted, _ = pricehistory.run(
        p,
        ["XLE"],
        now_iso=EVENING,
        fetch_history=_fake({"XLE": [("2026-07-06", 50.0), ("2026-07-07", 51.0)]}),
        sleep=lambda _: None,
    )
    assert inserted == 1, "only the new date is inserted"
    assert _ledger(p)["2026-07-07|XLE"] == 999.0, "existing forward row must win"


def test_run_excludes_todays_bar(tmp_path):
    """A bar dated the run's Phoenix date is the current session — its close is
    a live price while the market is open. It must never enter a permanent table.

    This drives the REAL fetch_history/parse_history over a raw payload; a fake
    that pre-filters by before_date would assert nothing about the filter, and
    the run's Phoenix date must be derived from `now_iso`, not sliced from UTC."""
    p = str(tmp_path / "scorer.db")
    payload = {"data": [{"t": PHX_TODAY, "c": 52.0}, {"t": "2026-07-07", "c": 51.0}]}

    def real_fetch(symbol, before_date):
        return pricehistory.fetch_history(symbol, before_date, get=lambda _s: payload)

    pricehistory.run(
        p,
        ["XLE"],
        now_iso=EVENING,  # 04:05Z Jul 9 == 21:05 Phoenix Jul 8
        fetch_history=real_fetch,
        sleep=lambda _: None,
    )
    ledger = _ledger(p)
    assert ledger == {"2026-07-07|XLE": 51.0}
    assert f"{PHX_TODAY}|XLE" not in ledger, "harvested an unsettled same-day close"


def test_run_skips_and_continues_on_one_symbol_failure(tmp_path, capsys):
    p = str(tmp_path / "scorer.db")

    def fetch(symbol, before_date):
        if symbol == "GLD":
            raise RuntimeError("boom")
        return [("2026-07-06", 50.0)]

    ok, inserted, failed = pricehistory.run(
        p, ["XLE", "GLD", "TLT"], now_iso=EVENING, fetch_history=fetch, sleep=lambda _: None
    )
    assert ok == 2 and inserted == 2 and failed == ["GLD"]
    assert set(_ledger(p)) == {"2026-07-06|XLE", "2026-07-06|TLT"}


def test_run_reports_a_symbol_that_yields_zero_rows_as_failed(tmp_path):
    """Silence is the failure mode this repo names explicitly. A symbol whose
    series is empty must be loud, not counted as a success."""
    p = str(tmp_path / "scorer.db")
    ok, inserted, failed = pricehistory.run(
        p, ["XLE"], now_iso=EVENING, fetch_history=_fake({"XLE": []}), sleep=lambda _: None
    )
    assert (ok, inserted, failed) == (0, 0, ["XLE"])


def test_run_failure_message_does_not_leak_exception_text(tmp_path, capsys):
    """An HTTPError carries the request URL, which may embed a key. Print only
    type(e).__name__."""
    p = str(tmp_path / "scorer.db")

    def fetch(symbol, before_date):
        raise RuntimeError("secret-token-in-url")

    pricehistory.run(p, ["XLE"], now_iso=EVENING, fetch_history=fetch, sleep=lambda _: None)
    out = capsys.readouterr().out
    assert "FAILED XLE: RuntimeError" in out
    assert "secret-token-in-url" not in out


def test_dry_run_writes_nothing(tmp_path):
    p = str(tmp_path / "scorer.db")
    ok, inserted, failed = pricehistory.run(
        p,
        ["XLE"],
        now_iso=EVENING,
        dry_run=True,
        fetch_history=_fake({"XLE": [("2026-07-06", 50.0)]}),
        sleep=lambda _: None,
    )
    assert (ok, inserted, failed) == (1, 0, [])
    assert _ledger(p) == {}


def test_run_sleeps_between_symbols_but_not_before_the_first(tmp_path):
    """Politeness to an unofficial endpoint, without a wasted leading delay."""
    p = str(tmp_path / "scorer.db")
    calls = []
    pricehistory.run(
        p,
        ["XLE", "GLD", "TLT"],
        now_iso=EVENING,
        fetch_history=_fake({s: [("2026-07-06", 1.0)] for s in ("XLE", "GLD", "TLT")}),
        sleep=calls.append,
    )
    assert len(calls) == 2 and all(c > 0 for c in calls)


def test_main_rejects_an_unknown_symbol(tmp_path):
    try:
        pricehistory.main(["--db", str(tmp_path / "s.db"), "--only", "NOPE"])
    except SystemExit as e:
        assert "NOPE" in str(e)
    else:
        raise AssertionError("expected SystemExit")
