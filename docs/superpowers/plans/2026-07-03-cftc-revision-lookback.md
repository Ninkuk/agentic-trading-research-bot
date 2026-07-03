# CFTC Revision Lookback + Write Robustness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CFTC re-runs re-fetch a recent lookback window (with a `--full` escape hatch) so upstream revisions are re-absorbed by the upsert, and move the DB writes inside the per-item try/except in both the CFTC and FRED run loops so a single write failure no longer aborts the whole run.

**Architecture:** Two isolated changes, both in run-orchestration code. CFTC: replace the strict `since = max_stored` incremental with an inclusive lookback floor (`max_stored − 10 weeks`, or the CLI `--start`/full history when `--full` or first run). Both screeners: widen the per-item `try` to cover writes and `conn.rollback()` on failure.

**Tech Stack:** Python 3 stdlib, pytest. No new dependencies. No change to `fetch.py`, `db.py`, `catalog.py`, `http_client.py`, or any view.

## Global Constraints

- **Lookback constant:** `_LOOKBACK_WEEKS = 10` in `cftc_screener/run.py`.
- **CFTC fetch floor is inclusive** (`>=`): pass it as `fetch_rows(..., start=floor)`; do NOT pass `since=` from run anymore.
- **`--full`** (and `full=True`) ignores stored data and uses the CLI `--start` (None = full history).
- **Skip-and-continue** now covers writes: on any per-item exception, `conn.rollback()` then log `type(e).__name__` ONLY (never `str(e)`/URL/key), then `continue`.
- **`fetch.py` untouched** — its strict `since` primitive stays and stays tested.
- Full suite green (was 169; +3 new, 1 updated → 172).

---

### Task 1: CFTC lookback + `--full` + write robustness

**Files:**
- Modify: `cftc_screener/run.py` (whole file — new `_LOOKBACK_WEEKS`, `_fetch_floor`, restructured loop, `--full` flag)
- Test: `tests/test_cftc_run.py` (update 1 test, add 3)

**Interfaces:**
- Consumes: `db.max_report_date(conn, code) -> str|None`, `fetch.fetch_market_rows(code, app_token=, since=, start=)` (called with `start=` only), `db.upsert_markets`, `db.write_cot`.
- Produces: `run(..., full=False, ...)`; `_fetch_floor(conn, code, start, full) -> str|None`.

- [ ] **Step 1: Update the incremental test + add the new tests**

In `tests/test_cftc_run.py`, REPLACE `test_run_passes_since_from_max_stored_date` with the lookback version below, and ADD the three tests after it. (The existing `test_run_happy_path_counts`, `test_run_skips_failing_market_and_continues`, `test_run_all_fail_writes_zero_snapshot`, `test_run_only_selects_subset` are unchanged — their `fake_fetch(code, app_token=None, since=None, start=None)` still works since run now passes `start=` and omits `since=`.)

```python
def test_run_passes_lookback_floor_as_start(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Market("A", "Alpha", "metals")])
    seen = {}

    def fake_fetch(code, app_token=None, since=None, start=None):
        seen.setdefault("start", []).append(start)
        return _rows(code, [("2026-06-16", 1), ("2026-06-23", 2)])

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)   # empty db -> full (start=None)
    run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)   # incremental -> max - 10 weeks
    # 2026-06-23 minus 10 weeks (70 days) = 2026-04-14
    assert seen["start"] == [None, "2026-04-14"]


def test_run_full_ignores_stored_max(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Market("A", "Alpha", "metals")])
    seen = {}

    def fake_fetch(code, app_token=None, since=None, start=None):
        seen.setdefault("start", []).append(start)
        return _rows(code, [("2026-06-23", 2)])

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)  # populate
    run_mod.run(dbp, start="2020-01-01", full=True, now_iso=NOW,
                fetch_rows=fake_fetch)                     # full -> CLI start, not lookback
    assert seen["start"] == [None, "2020-01-01"]


def test_run_skips_failing_write_and_continues(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_mod.catalog, "CATALOG",
                        [Market("GOOD", "G", "metals"), Market("BADW", "B", "metals")])

    def fake_fetch(code, app_token=None, since=None, start=None):
        return _rows(code, [("2026-06-23", 5)])

    orig_write = run_mod.db.write_cot

    def flaky_write(conn, code, rows):
        if code == "BADW":
            raise RuntimeError("disk full")
        return orig_write(conn, code, rows)

    monkeypatch.setattr(run_mod.db, "write_cot", flaky_write)
    dbp = str(tmp_path / "cftc.db")
    sid, mc, rc = run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)
    assert mc == 1                                   # only GOOD counted a success
    assert "BADW" in capsys.readouterr().err
    conn = db.connect(dbp)
    assert [r[0] for r in conn.execute(
        "SELECT DISTINCT code FROM cot")] == ["GOOD"]  # BADW's facts rolled back
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1  # snapshot still written
```

- [ ] **Step 2: Run the updated/new tests to verify they fail**

Run: `python -m pytest tests/test_cftc_run.py -v`
Expected: FAIL — `test_run_passes_lookback_floor_as_start` fails (run still passes `since=`, not the lookback `start`); `test_run_full_ignores_stored_max` fails (`run()` has no `full=` param → TypeError); `test_run_skips_failing_write_and_continues` fails (write error currently aborts the run, uncaught).

- [ ] **Step 3: Rewrite `cftc_screener/run.py`**

Replace the ENTIRE file with:

```python
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

from cftc_screener import catalog, db, fetch

# On incremental re-runs, re-fetch this many recent weeks per market so the
# (code, report_date) upsert re-absorbs CFTC's revisions to already-stored
# weeks. --full ignores this and re-pulls from --start (or full history).
_LOOKBACK_WEEKS = 10


def _fetch_floor(conn, code, start, full):
    """Inclusive report-date floor to fetch from for one market. A full re-pull
    (or a first-ever pull with no stored data) uses the caller's ``start`` (None
    = full history). Otherwise re-fetch a recent lookback window ending at the
    latest stored week."""
    if full:
        return start
    last = db.max_report_date(conn, code)
    if last is None:
        return start
    return (datetime.fromisoformat(last)
            - timedelta(weeks=_LOOKBACK_WEEKS)).date().isoformat()


def run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
        app_token=None, full=False, fetch_rows=fetch.fetch_market_rows,
        now_iso=None):
    """Fetch selected CFTC markets into SQLite, upserting weekly COT history.
    Incremental runs re-fetch the last _LOOKBACK_WEEKS weeks per market to catch
    revisions; full=True re-pulls from ``start`` (or full history).
    Returns (snapshot_id, market_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    app_token = app_token or os.environ.get("CFTC_APP_TOKEN")  # optional; may be None

    asset = {m.code: m.asset_class for m in catalog.CATALOG}
    all_codes = [m.code for m in catalog.CATALOG]
    codes = catalog.select_ids(all_codes, only, exclude, add=add)

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        successes = 0
        total_rows = 0
        for code in codes:
            try:
                floor = _fetch_floor(conn, code, start, full)
                rows = fetch_rows(code, app_token=app_token, start=floor)
                if rows:
                    name = rows[-1].get("name")  # ordered ascending -> newest last
                    db.upsert_markets(conn, [{"code": code, "name": name,
                                              "asset_class": asset.get(code, "custom")}],
                                      now_iso)
                    total_rows += db.write_cot(conn, code, rows)
                successes += 1
            except Exception as e:  # skip-and-continue on any per-market failure
                # Roll back the failed market's uncommitted writes, then log only
                # the exception class — never str(e)/e.url, which may echo the
                # request URL or token.
                conn.rollback()
                print(f"warning: skipping {code}: {type(e).__name__}",
                      file=sys.stderr)
                continue

        if successes == 0:
            print("warning: no CFTC markets fetched successfully; "
                  "wrote empty snapshot", file=sys.stderr)

        snapshot_id = db.write_snapshot(conn, now_iso, successes, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, successes, total_rows


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="cftc",
        description="Pull curated CFTC COT positioning into SQLite")
    p.add_argument("--db", default="cftc.db")
    p.add_argument("--only", default=None,
                   help="comma-separated contract codes to pull (default: catalog)")
    p.add_argument("--exclude", default=None,
                   help="comma-separated contract codes to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra contract code not in the catalog (repeatable)")
    p.add_argument("--start", default=None,
                   help="earliest report date YYYY-MM-DD (default: full history)")
    p.add_argument("--full", action="store_true",
                   help="re-pull from --start (or full history), ignoring the "
                        "incremental lookback")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    only = a.only.split(",") if a.only else None
    exclude = a.exclude.split(",") if a.exclude else None
    _, mc, rc = run(a.db, only=only, exclude=exclude, add=a.add, start=a.start,
                    keep_days=a.keep_days, full=a.full)
    print(f"stored {rc} weekly rows across {mc} markets into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the CFTC run tests to verify they pass**

Run: `python -m pytest tests/test_cftc_run.py -v`
Expected: PASS (all — the 4 unchanged tests, the updated lookback test, and the 3 new tests). If `test_run_passes_lookback_floor_as_start` fails on the date, recompute: `datetime.fromisoformat("2026-06-23") - timedelta(weeks=10)` = `2026-04-14`.

- [ ] **Step 5: Update the original CFTC design spec's incremental note**

In `docs/superpowers/specs/2026-07-03-cftc-screener-design.md`, find the fetch bullet describing incremental behavior (the `**Incremental**` line under the Fetch section) and append a sentence pointing to the lookback:

Change the incremental description to note: re-runs re-fetch the last `_LOOKBACK_WEEKS` (10) weeks with an inclusive `>=` floor so CFTC's revisions to prior weeks are re-absorbed by the upsert, and `--full` forces a complete re-pull. (See `2026-07-03-cftc-revision-lookback-design.md`.)

Make the edit as a short parenthetical/sentence; do not restructure the doc.

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS — full suite green (all CFTC + unchanged FRED/edgar/http_client/registry).

- [ ] **Step 7: Commit**

```bash
git add cftc_screener/run.py tests/test_cftc_run.py docs/superpowers/specs/2026-07-03-cftc-screener-design.md
git commit -m "feat(cftc): incremental lookback window + --full; write inside skip-and-continue"
```

---

### Task 2: FRED write robustness

**Files:**
- Modify: `fred_screener/run.py` (per-series loop body)
- Test: `tests/test_fred_run.py` (add 1)

**Interfaces:**
- Consumes: `db.upsert_series`, `db.write_observations`, `conn.rollback()`.
- Produces: no signature change — same skip-and-continue behavior, now covering writes.

- [ ] **Step 1: Add the failing test**

Add to `tests/test_fred_run.py`:

```python
def test_run_skips_failing_write_and_continues(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_mod.catalog, "CATALOG",
                        [Series("GOOD", "rates"), Series("BADW", "rates")])
    orig_write = run_mod.db.write_observations

    def flaky_write(conn, series_id, obs_rows):
        if series_id == "BADW":
            raise RuntimeError("disk full")
        return orig_write(conn, series_id, obs_rows)

    monkeypatch.setattr(run_mod.db, "write_observations", flaky_write)
    dbp = str(tmp_path / "fred.db")
    _, sc, _ = run_mod.run(dbp, api_key="K", now_iso=NOW,
                           fetch_series=_ok_series, fetch_obs=_ok_obs)
    assert sc == 1                                   # only GOOD counted
    assert "BADW" in capsys.readouterr().err
    conn = db.connect(dbp)
    assert [r[0] for r in conn.execute(
        "SELECT DISTINCT series_id FROM observations")] == ["GOOD"]  # BADW rolled back
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_fred_run.py::test_run_skips_failing_write_and_continues -v`
Expected: FAIL — the write error currently propagates and aborts `run` (the writes are outside the try), so the assertion is never reached (test errors with `RuntimeError: disk full`).

- [ ] **Step 3: Move the FRED writes inside the per-series try**

In `fred_screener/run.py`, the per-series loop currently reads:

```python
        for series_id in ids:
            try:
                meta = fetch_series(series_id, api_key)
                obs = fetch_obs(series_id, api_key, start=start)
            except Exception as e:  # skip-and-continue on any per-series failure
                # Print only the exception class, never str(e)/e.url: a urllib
                # HTTPError carries the request URL (which embeds api_key) in
                # its message and .url attribute. Do not log those here.
                print(f"warning: skipping {series_id}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            meta = {**meta, "theme": themes.get(series_id, "custom")}
            db.upsert_series(conn, [meta], now_iso)
            total_obs += db.write_observations(conn, series_id, obs)
            successes += 1
```

Replace that block with (writes moved inside the `try`, `conn.rollback()` added):

```python
        for series_id in ids:
            try:
                meta = fetch_series(series_id, api_key)
                obs = fetch_obs(series_id, api_key, start=start)
                meta = {**meta, "theme": themes.get(series_id, "custom")}
                db.upsert_series(conn, [meta], now_iso)
                total_obs += db.write_observations(conn, series_id, obs)
                successes += 1
            except Exception as e:  # skip-and-continue on any per-series failure
                # Roll back the failed series' uncommitted writes. Print only the
                # exception class, never str(e)/e.url: a urllib HTTPError carries
                # the request URL (which embeds api_key) in its message and .url
                # attribute. Do not log those here.
                conn.rollback()
                print(f"warning: skipping {series_id}: {type(e).__name__}",
                      file=sys.stderr)
                continue
```

- [ ] **Step 4: Run the FRED run tests to verify they pass**

Run: `python -m pytest tests/test_fred_run.py -v`
Expected: PASS — the new write-skip test plus all existing FRED run tests (happy path, skip-failing-series, all-fail-zero-snapshot, only-subset, second-run-upsert, missing-key) still green.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS — full suite green (172 tests).

- [ ] **Step 6: Commit**

```bash
git add fred_screener/run.py tests/test_fred_run.py
git commit -m "fix(fred): move per-series writes inside skip-and-continue with rollback"
```

---

## Notes for the implementer

- **Why `start` not `since`:** the lookback floor must be *inclusive* (re-fetch the boundary week and everything after), which is `start`'s `>=` semantics; `since` is exclusive `>`. Run now passes `start=` only. `fetch._build_url`/`fetch_market_rows` keep the `since` parameter (still unit-tested in `tests/test_cftc_fetch.py`) — just unused by run.
- **Partial-write nuance:** each writer commits internally, so if `upsert_markets` commits and then `write_cot` raises, the market dimension row persists with no facts (harmless; a later run fills it). `conn.rollback()` clears only the failed writer's uncommitted statements. Tests assert on the fact tables (`cot` / `observations`), which correctly exclude the failed item.
- **Date math:** `datetime.fromisoformat("2026-06-23") - timedelta(weeks=10)` → `2026-04-14`. `.date().isoformat()` yields the `YYYY-MM-DD` string.
