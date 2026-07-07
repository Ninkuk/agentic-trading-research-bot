# Decision Journal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record what the human did about each composite opinion (acted/passed, fill prices) in scorer.db, with live views measuring realized-vs-paper and whether the human filter adds value.

**Architecture:** New `sources/combiners/scorer/journal.py` module + tables/views in `scorer/db.py`, registered as its own `journal` dispatcher (`main.py journal --input <file|->`, portfolio-style inverted slice). Trade→opinion matching is deterministic Python reading composite.db ATTACHed read-only; the persistent views join `decisions` to `ticker_outcomes` inside scorer.db, re-keyed through the grading window's owner snapshot. Spec: `docs/superpowers/specs/2026-07-06-decision-journal-design.md`.

**Tech Stack:** Python 3.12 stdlib only (`sqlite3`, `json`, `argparse`), pytest (dev-only), uv.

## Global Constraints

- Zero runtime third-party dependencies; stdlib only.
- No network and no wall-clock in the hot path: `run(...)` takes injected `now_iso`; tests are fully offline.
- Secret hygiene: on error print `type(e).__name__` only — never `str(e)`, `repr(e)`, or URLs.
- Timestamps stored are UTC `isoformat()` (fixed width incl. `+00:00`).
- `decisions` / `journal_runs` are **never pruned** — permanent evidence like the outcome tables. Do not touch `scorer.db`'s `prune`.
- `composite_date` is ALWAYS derived as `substr(datetime(captured_at, '-7 hours'), 1, 10)` (Phoenix shift — must match `fetch.read_snapshots` exactly or keys won't join).
- All four gates must pass before each commit (pre-commit hook runs them): `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, `uv run pytest`.
- Commit with `git commit --no-gpg-sign` (gpg+1Password hangs non-interactive commits).
- Every `--db` default is a bare filename; real invocations pass `data/scorer.db`.

---

### Task 1: Schema — `decisions` and `journal_runs` tables in scorer/db.py

**Files:**
- Modify: `sources/combiners/scorer/db.py` (append to `_TABLES`, extend module docstring)
- Test: `tests/test_journal_db_schema.py` (create)

**Interfaces:**
- Produces: tables `decisions` (columns exactly as DDL below) and `journal_runs` in scorer.db, created by the existing `db.ensure_schema(conn)`. Tasks 3–5 insert into them; Task 4's views read them.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_journal_db_schema.py`:

```python
import sqlite3

import pytest

from sources.combiners.scorer import db

NOW = "2026-07-06T21:10:00+00:00"


def _conn(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    return conn


def test_tables_exist(tmp_path):
    conn = _conn(tmp_path)
    names = {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {"decisions", "journal_runs"} <= names


def test_ensure_schema_idempotent(tmp_path):
    conn = _conn(tmp_path)
    db.ensure_schema(conn)  # second run must not raise


def test_action_and_side_checked(tmp_path):
    conn = _conn(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO decisions (symbol, action, recorded_at) VALUES ('XLE', 'held', ?)",
            (NOW,),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO decisions (symbol, action, side, recorded_at)"
            " VALUES ('XLE', 'acted', 'short', ?)",
            (NOW,),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO decisions (symbol, action, source, recorded_at)"
            " VALUES ('XLE', 'acted', 'api', ?)",
            (NOW,),
        )


def test_order_ref_unique_but_nulls_ok(tmp_path):
    conn = _conn(tmp_path)
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, order_ref, recorded_at)"
        " VALUES ('XLE', 'acted', 'buy', 'ref-1', ?)",
        (NOW,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO decisions (symbol, action, side, order_ref, recorded_at)"
            " VALUES ('XLE', 'acted', 'buy', 'ref-1', ?)",
            (NOW,),
        )
    # manual entries: repeated NULL order_refs are fine
    for _ in range(2):
        conn.execute(
            "INSERT INTO decisions (symbol, action, side, recorded_at)"
            " VALUES ('GLD', 'acted', 'buy', ?)",
            (NOW,),
        )


def test_one_explicit_pass_per_flag(tmp_path):
    conn = _conn(tmp_path)
    conn.execute(
        "INSERT INTO decisions (symbol, action, composite_snapshot_id, recorded_at)"
        " VALUES ('GLD', 'passed', 7, ?)",
        (NOW,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO decisions (symbol, action, composite_snapshot_id, recorded_at)"
            " VALUES ('GLD', 'passed', 7, ?)",
            (NOW,),
        )
    # same symbol, different flag: fine; acted rows unconstrained
    conn.execute(
        "INSERT INTO decisions (symbol, action, composite_snapshot_id, recorded_at)"
        " VALUES ('GLD', 'passed', 8, ?)",
        (NOW,),
    )
    for _ in range(2):
        conn.execute(
            "INSERT INTO decisions (symbol, action, side, composite_snapshot_id,"
            " recorded_at) VALUES ('GLD', 'acted', 'buy', 7, ?)",
            (NOW,),
        )


def test_prune_never_touches_journal(tmp_path):
    conn = _conn(tmp_path)
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, recorded_at)"
        " VALUES ('XLE', 'acted', 'buy', '2020-01-01T00:00:00+00:00')"
    )
    conn.execute(
        "INSERT INTO journal_runs (ran_at) VALUES ('2020-01-01T00:00:00+00:00')"
    )
    conn.commit()
    db.prune(conn, keep_days=1, now_iso=NOW)
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM journal_runs").fetchone()[0] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_journal_db_schema.py -v`
Expected: FAIL — `sqlite3.OperationalError: no such table: decisions` (ensure_schema doesn't create it yet).

- [ ] **Step 3: Add the tables to `_TABLES` in `sources/combiners/scorer/db.py`**

Append to the `_TABLES` string (after the `regime_outcomes` block, before the closing `"""`):

```sql
-- Decision journal: what the human did about each opinion (roadmap item 5).
-- Permanent evidence like the outcome tables; never pruned. order_ref /
-- exit_order_ref are broker order UUIDs (random ids, not account
-- identifiers) stored only for idempotent re-ingest; UNIQUE tolerates the
-- NULLs manual entries carry. composite_snapshot_id NULL = freelance trade
-- (nothing recommended it).
CREATE TABLE IF NOT EXISTS decisions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol                TEXT NOT NULL,
    action                TEXT NOT NULL CHECK (action IN ('acted', 'passed')),
    side                  TEXT CHECK (side IN ('buy', 'sell')),
    composite_snapshot_id INTEGER,
    composite_date        TEXT,
    fill_date             TEXT,
    fill_price            REAL,
    quantity              REAL,
    exit_fill_date        TEXT,
    exit_fill_price       REAL,
    order_ref             TEXT UNIQUE,
    exit_order_ref        TEXT UNIQUE,
    note                  TEXT,
    source                TEXT NOT NULL DEFAULT 'mcp'
                          CHECK (source IN ('mcp', 'manual')),
    recorded_at           TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_decisions_pass
    ON decisions (composite_snapshot_id, symbol) WHERE action = 'passed';

CREATE TABLE IF NOT EXISTS journal_runs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    ran_at             TEXT NOT NULL,
    fills_seen         INTEGER NOT NULL DEFAULT 0,
    matched            INTEGER NOT NULL DEFAULT 0,
    freelance          INTEGER NOT NULL DEFAULT 0,
    exits_attached     INTEGER NOT NULL DEFAULT 0,
    passes_recorded    INTEGER NOT NULL DEFAULT 0,
    duplicates_skipped INTEGER NOT NULL DEFAULT 0,
    skipped            INTEGER NOT NULL DEFAULT 0
);
```

Also extend the module docstring's first paragraph with one sentence: `decisions/journal_runs (the decision journal) are permanent for the same reason.`

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_journal_db_schema.py tests/test_scorer_db_schema.py -v` (second file guards against regressions in the shared `_TABLES` string).
Expected: PASS.

- [ ] **Step 5: Gates + commit**

```bash
uv run ruff check && uv run ruff format && uv run mypy && uv run pytest
git add sources/combiners/scorer/db.py tests/test_journal_db_schema.py
git commit --no-gpg-sign -m "feat(journal): decisions + journal_runs tables in scorer.db"
```

---

### Task 2: `parse_doc` — validate the input document

**Files:**
- Create: `sources/combiners/scorer/journal.py`
- Test: `tests/test_journal_parse.py` (create)

**Interfaces:**
- Produces: `journal.parse_doc(doc) -> tuple[list, list, int]` — `(fills, passes, skipped)`. Each fill dict has keys `symbol, side, price, quantity, filled_at, fill_date, order_ref, note`; each pass dict has `symbol, note`. Fills are sorted chronologically (`filled_at`, buys before sells on ties). Raises `ValueError` if `doc` is not a dict.
- Produces: module constants `MATCH_WINDOW_DAYS = 5`, `FLAG_MIN_ABS_SCORE = 4`, `FLAG_MIN_TOTAL = 3` (Tasks 3–4 use them).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_journal_parse.py`:

```python
import pytest

from sources.combiners.scorer import journal


def _fill(**kw):
    base = dict(
        symbol="XLE",
        side="buy",
        price=94.30,
        quantity=2,
        filled_at="2026-07-07T14:31:00+00:00",
        order_ref="ref-1",
    )
    base.update(kw)
    return base


def test_valid_doc():
    fills, passes, skipped = journal.parse_doc(
        {"fills": [_fill()], "passes": [{"symbol": "gld", "note": "crowded"}]}
    )
    assert skipped == 0
    assert fills[0]["symbol"] == "XLE"
    assert fills[0]["fill_date"] == "2026-07-07"
    assert fills[0]["quantity"] == 2.0
    assert passes[0]["symbol"] == "GLD"  # symbols normalized upper


def test_missing_fields_skip_and_count():
    doc = {
        "fills": [
            _fill(symbol=""),
            _fill(side="short"),
            _fill(price="94.30"),  # string price is invalid
            _fill(filled_at=None),
            "not-a-dict",
            _fill(order_ref=None, note=None),  # still valid: refs optional
        ],
        "passes": [{"note": "no symbol"}, {"symbol": "TLT"}],
    }
    fills, passes, skipped = journal.parse_doc(doc)
    assert len(fills) == 1 and fills[0]["order_ref"] is None
    assert len(passes) == 1 and passes[0]["symbol"] == "TLT"
    assert skipped == 6


def test_non_numeric_quantity_becomes_none():
    fills, _, skipped = journal.parse_doc({"fills": [_fill(quantity="two")]})
    assert skipped == 0 and fills[0]["quantity"] is None


def test_fills_sorted_chronologically_buys_first_on_tie():
    doc = {
        "fills": [
            _fill(order_ref="r3", filled_at="2026-07-08T14:00:00+00:00", side="sell"),
            _fill(order_ref="r2", filled_at="2026-07-08T14:00:00+00:00"),
            _fill(order_ref="r1", filled_at="2026-07-07T14:00:00+00:00"),
        ]
    }
    fills, _, _ = journal.parse_doc(doc)
    assert [f["order_ref"] for f in fills] == ["r1", "r2", "r3"]


def test_missing_sections_ok():
    assert journal.parse_doc({}) == ([], [], 0)


def test_non_dict_doc_raises():
    with pytest.raises(ValueError):
        journal.parse_doc(["not", "a", "dict"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_journal_parse.py -v`
Expected: FAIL — `ImportError: cannot import name 'journal'` / module not found.

- [ ] **Step 3: Create `sources/combiners/scorer/journal.py` with `parse_doc`**

```python
"""Decision journal: what the human did about composite opinions. Ingests
one JSON doc of fills/passes (built by the journal-sync skill from Robinhood
MCP order history, or dictated manually) and stores decisions permanently in
scorer.db next to the outcomes they are graded against.

Matching is deterministic (headless scheduled runs cannot stop to confirm)
and reads composite.db ATTACHed read-only rather than ticker_outcomes:
registration lags one night (next-day-close entries), so a morning-after
fill would otherwise misclassify as freelance. The opinion exists in
composite.db the night it forms; once matched, the decision's
(composite_snapshot_id, symbol) key joins the scorer's permanent outcome
rows and never needs composite.db again. Decisions are never pruned — they
are the other half of the experiment."""

# Calendar days an opinion stays matchable to a later fill: covers the
# morning-after trade plus a long weekend. Two snapshots in the window
# resolve to the most recent one.
MATCH_WINDOW_DAYS = 5

# Mirror of composite v_flagged (|score_sum| >= 4 AND total >= 3). Both are
# hand-tunable; test_journal_matching pins them equal so they drift together.
FLAG_MIN_ABS_SCORE = 4
FLAG_MIN_TOTAL = 3


def parse_doc(doc) -> tuple:
    """Validate one input document into (fills, passes, skipped_count).
    Rows missing required fields are skipped and counted, never fatal.
    Fills come back chronological (buys before sells on timestamp ties) so
    FIFO exit attachment is deterministic regardless of doc order."""
    if not isinstance(doc, dict):
        raise ValueError("document must be an object")
    fills, passes, skipped = [], [], 0
    for f in doc.get("fills") or []:
        if not isinstance(f, dict):
            skipped += 1
            continue
        symbol = (f.get("symbol") or "").strip().upper()
        side = f.get("side")
        price = f.get("price")
        filled_at = f.get("filled_at")
        if (
            not symbol
            or side not in ("buy", "sell")
            or not isinstance(price, (int, float))
            or not isinstance(filled_at, str)
            or len(filled_at) < 10
        ):
            skipped += 1
            continue
        quantity = f.get("quantity")
        fills.append(
            dict(
                symbol=symbol,
                side=side,
                price=float(price),
                quantity=float(quantity) if isinstance(quantity, (int, float)) else None,
                filled_at=filled_at,
                fill_date=filled_at[:10],
                order_ref=f.get("order_ref"),
                note=f.get("note"),
            )
        )
    for p in doc.get("passes") or []:
        symbol = (p.get("symbol") or "").strip().upper() if isinstance(p, dict) else ""
        if not symbol:
            skipped += 1
            continue
        passes.append(dict(symbol=symbol, note=p.get("note")))
    fills.sort(key=lambda f: (f["filled_at"], 0 if f["side"] == "buy" else 1))
    return fills, passes, skipped
```

(No imports yet — `parse_doc` and the constants are pure. Task 5 adds the imports its `run`/`main` need; adding them earlier would fail `ruff check` F401.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_journal_parse.py -v`
Expected: PASS.

- [ ] **Step 5: Gates + commit**

```bash
uv run ruff check && uv run ruff format && uv run mypy && uv run pytest
git add sources/combiners/scorer/journal.py tests/test_journal_parse.py
git commit --no-gpg-sign -m "feat(journal): parse_doc validates fill/pass documents"
```

---

### Task 3: Matching + ingest (the core)

**Files:**
- Modify: `sources/combiners/scorer/journal.py`
- Test: `tests/test_journal_matching.py` (create)

**Interfaces:**
- Consumes: `parse_doc` fills/passes dicts (Task 2), tables from Task 1, existing `fetch.attach_ro(conn, path)` / `fetch.detach(conn)` (alias `src`).
- Produces:
  - `journal.match_opinion(conn, symbol, fill_date) -> tuple[int, str] | None` — `(composite_snapshot_id, composite_date)`.
  - `journal.match_flagged(conn, symbol, as_of_date) -> tuple[int, str] | None`.
  - `journal.ingest(conn, fills, passes, now_iso, skipped=0) -> dict` with keys `run_id, fills_seen, matched, freelance, exits_attached, passes_recorded, duplicates_skipped, skipped`. Task 5's `run()` calls it.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_journal_matching.py`:

```python
from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import db, journal

NOW = "2026-07-08T21:40:00+00:00"


def _mini_composite(path, opinions):
    """opinions: list of (date, {symbol: (score_sum, total)}). captured_at is
    written as <date>T21:05:00+00:00, which the Phoenix shift maps back to
    <date> — same convention as test_scorer_run."""
    conn = composite_db.connect(str(path))
    composite_db.ensure_schema(conn)
    sids = []
    for date, scores in opinions:
        conn.execute(
            "INSERT INTO snapshots (captured_at, signals_expected) VALUES (?, 1)",
            (f"{date}T21:05:00+00:00",),
        )
        sid = conn.execute("SELECT MAX(id) FROM snapshots").fetchone()[0]
        for sym, (score_sum, total) in scores.items():
            conn.execute(
                "INSERT INTO ticker_scores (snapshot_id, symbol, total, score_sum)"
                " VALUES (?, ?, ?, ?)",
                (sid, sym, total, score_sum),
            )
        sids.append(sid)
    conn.commit()
    conn.close()
    return sids


def _scorer_with_composite(tmp_path, opinions):
    sids = _mini_composite(tmp_path / "composite.db", opinions)
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    conn.execute("ATTACH DATABASE ? AS src", (f"file:{tmp_path / 'composite.db'}?mode=ro",))
    return conn, sids


def _fill(**kw):
    base = dict(
        symbol="XLE",
        side="buy",
        price=94.30,
        quantity=2.0,
        filled_at="2026-07-07T14:31:00+00:00",
        fill_date="2026-07-07",
        order_ref="ref-1",
        note=None,
    )
    base.update(kw)
    return base


def test_match_most_recent_in_window(tmp_path):
    conn, sids = _scorer_with_composite(
        tmp_path,
        [("2026-07-02", {"XLE": (5, 4)}), ("2026-07-06", {"XLE": (4, 3)})],
    )
    assert journal.match_opinion(conn, "XLE", "2026-07-07") == (sids[1], "2026-07-06")


def test_match_window_edges(tmp_path):
    conn, sids = _scorer_with_composite(tmp_path, [("2026-07-02", {"XLE": (5, 4)})])
    # day 5 after the opinion: still matchable
    assert journal.match_opinion(conn, "XLE", "2026-07-07") == (sids[0], "2026-07-02")
    # day 6: expired
    assert journal.match_opinion(conn, "XLE", "2026-07-08") is None
    # same-day fill: the opinion forms at 9:05pm, after the close — excluded
    assert journal.match_opinion(conn, "XLE", "2026-07-02") is None


def test_match_requires_symbol_scored(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    assert journal.match_opinion(conn, "GLD", "2026-07-07") is None


def test_match_flagged_needs_thresholds(tmp_path):
    conn, sids = _scorer_with_composite(
        tmp_path,
        [("2026-07-05", {"GLD": (3, 3)}), ("2026-07-06", {"GLD": (4, 3)})],
    )
    # score 3 isn't a flag; the 07-06 flag matches, and same-day is allowed
    assert journal.match_flagged(conn, "GLD", "2026-07-06") == (sids[1], "2026-07-06")
    assert journal.match_flagged(conn, "GLD", "2026-07-05") is None


def test_flag_thresholds_pinned_to_composite_view():
    assert f"ABS(score_sum) >= {journal.FLAG_MIN_ABS_SCORE}" in composite_db._SCHEMA
    assert f"total >= {journal.FLAG_MIN_TOTAL}" in composite_db._SCHEMA


def test_ingest_buy_matched_and_freelance(tmp_path):
    conn, sids = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [_fill(), _fill(symbol="NVDA", order_ref="ref-2")]
    counts = journal.ingest(conn, fills, [], NOW)
    assert counts["matched"] == 1 and counts["freelance"] == 1
    rows = conn.execute(
        "SELECT symbol, composite_snapshot_id, composite_date, source"
        " FROM decisions ORDER BY symbol"
    ).fetchall()
    assert rows[0] == ("NVDA", None, None, "mcp")
    assert rows[1] == ("XLE", sids[0], "2026-07-06", "mcp")


def test_ingest_sell_attaches_fifo_exit(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [
        _fill(order_ref="b1", filled_at="2026-07-07T14:00:00+00:00"),
        _fill(order_ref="b2", filled_at="2026-07-08T14:00:00+00:00", fill_date="2026-07-08"),
        _fill(
            order_ref="s1",
            side="sell",
            price=99.10,
            filled_at="2026-07-09T15:00:00+00:00",
            fill_date="2026-07-09",
        ),
    ]
    counts = journal.ingest(conn, fills, [], NOW)
    assert counts["exits_attached"] == 1
    exited = conn.execute(
        "SELECT order_ref, exit_fill_date, exit_fill_price, exit_order_ref"
        " FROM decisions WHERE exit_fill_date IS NOT NULL"
    ).fetchall()
    assert exited == [("b1", "2026-07-09", 99.10, "s1")]  # oldest open buy first


def test_ingest_sell_without_open_buy_is_own_decision(tmp_path):
    conn, sids = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (-4, 3)})])
    fills = [_fill(side="sell", order_ref="s9")]
    counts = journal.ingest(conn, fills, [], NOW)
    assert counts["matched"] == 1 and counts["exits_attached"] == 0
    row = conn.execute(
        "SELECT side, composite_snapshot_id FROM decisions"
    ).fetchone()
    assert row == ("sell", sids[0])  # direction-agnostic matching


def test_ingest_duplicate_order_ref_idempotent(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [_fill()]
    journal.ingest(conn, fills, [], NOW)
    counts = journal.ingest(conn, fills, [], NOW)  # same doc replayed
    assert counts["duplicates_skipped"] == 1
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1


def test_ingest_exit_ref_also_dedupes(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    buy = _fill(order_ref="b1")
    sell = _fill(
        order_ref="s1",
        side="sell",
        filled_at="2026-07-08T15:00:00+00:00",
        fill_date="2026-07-08",
    )
    journal.ingest(conn, [buy, sell], [], NOW)
    counts = journal.ingest(conn, [sell], [], NOW)
    assert counts["duplicates_skipped"] == 1
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1


def test_ingest_pass_needs_flag(tmp_path):
    conn, sids = _scorer_with_composite(
        tmp_path,
        [("2026-07-06", {"GLD": (4, 3), "TLT": (1, 3)})],
    )
    counts = journal.ingest(
        conn,
        [],
        [dict(symbol="GLD", note="crowded"), dict(symbol="TLT", note=None)],
        "2026-07-06T21:40:00+00:00",
    )
    assert counts["passes_recorded"] == 1 and counts["skipped"] == 1
    row = conn.execute(
        "SELECT symbol, action, composite_snapshot_id, note, source FROM decisions"
    ).fetchone()
    assert row == ("GLD", "passed", sids[0], "crowded", "manual")
    # replaying the same pass is a no-op (partial unique index + OR IGNORE)
    counts = journal.ingest(conn, [], [dict(symbol="GLD", note="crowded")], NOW)
    assert counts["passes_recorded"] == 0


def test_ingest_writes_run_header(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    counts = journal.ingest(conn, [_fill()], [], NOW, skipped=2)
    row = conn.execute(
        "SELECT ran_at, fills_seen, matched, freelance, exits_attached,"
        " passes_recorded, duplicates_skipped, skipped FROM journal_runs"
    ).fetchone()
    assert row == (NOW, 1, 1, 0, 0, 0, 0, 2)
    assert counts["run_id"] == 1


def test_manual_fill_source(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    journal.ingest(conn, [_fill(order_ref=None)], [], NOW)
    assert conn.execute("SELECT source FROM decisions").fetchone()[0] == "manual"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_journal_matching.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'match_opinion'`.

- [ ] **Step 3: Implement matching + ingest in `journal.py`**

Append to `sources/combiners/scorer/journal.py`:

```python
# composite_date, exactly as the scorer registers it (Phoenix shift; see
# fetch.read_snapshots for the rationale). MUST stay identical or journal
# keys won't join registered_snapshots.
_CDATE = "substr(datetime(s.captured_at, '-7 hours'), 1, 10)"


def match_opinion(conn, symbol, fill_date):
    """Most recent composite opinion on `symbol` strictly BEFORE fill_date
    (the opinion forms at 9:05pm, after that day's close) and at most
    MATCH_WINDOW_DAYS old. Direction-agnostic: alignment is a view concern.
    Returns (composite_snapshot_id, composite_date) or None (freelance)."""
    row = conn.execute(
        f"SELECT s.id, {_CDATE} FROM src.snapshots s"
        f" JOIN src.ticker_scores t ON t.snapshot_id = s.id AND t.symbol = ?"
        f" WHERE {_CDATE} < ? AND ? <= date({_CDATE}, ?)"
        f" ORDER BY s.id DESC LIMIT 1",
        (symbol, fill_date, fill_date, f"+{MATCH_WINDOW_DAYS} days"),
    ).fetchone()
    return (row[0], row[1]) if row else None


def match_flagged(conn, symbol, as_of_date):
    """Like match_opinion but only flagged opinions (a pass must answer a
    real flag), and same-evening passes are allowed (cdate <= as_of)."""
    row = conn.execute(
        f"SELECT s.id, {_CDATE} FROM src.snapshots s"
        f" JOIN src.ticker_scores t ON t.snapshot_id = s.id AND t.symbol = ?"
        f" AND ABS(t.score_sum) >= ? AND t.total >= ?"
        f" WHERE {_CDATE} <= ? AND ? <= date({_CDATE}, ?)"
        f" ORDER BY s.id DESC LIMIT 1",
        (
            symbol,
            FLAG_MIN_ABS_SCORE,
            FLAG_MIN_TOTAL,
            as_of_date,
            as_of_date,
            f"+{MATCH_WINDOW_DAYS} days",
        ),
    ).fetchone()
    return (row[0], row[1]) if row else None


def _seen(conn, ref):
    return (
        ref is not None
        and conn.execute(
            "SELECT 1 FROM decisions WHERE order_ref = ? OR exit_order_ref = ? LIMIT 1",
            (ref, ref),
        ).fetchone()
        is not None
    )


def ingest(conn, fills, passes, now_iso, skipped=0) -> dict:
    """One transaction: every decision row plus the journal_runs header
    commit together or not at all. Requires composite.db attached as `src`
    when fills/passes are present. Fills must be chronological (parse_doc
    guarantees it) so FIFO exit attachment is deterministic."""
    matched = freelance = exits = passes_n = dupes = 0
    as_of_date = now_iso[:10]
    with conn:
        for f in fills:
            if _seen(conn, f["order_ref"]):
                dupes += 1
                continue
            if f["side"] == "sell":
                open_buy = conn.execute(
                    "SELECT id FROM decisions WHERE symbol = ? AND action = 'acted'"
                    " AND side = 'buy' AND exit_fill_date IS NULL"
                    " AND fill_date <= ? ORDER BY fill_date, id LIMIT 1",
                    (f["symbol"], f["fill_date"]),
                ).fetchone()
                if open_buy:
                    conn.execute(
                        "UPDATE decisions SET exit_fill_date = ?,"
                        " exit_fill_price = ?, exit_order_ref = ? WHERE id = ?",
                        (f["fill_date"], f["price"], f["order_ref"], open_buy[0]),
                    )
                    exits += 1
                    continue
            m = match_opinion(conn, f["symbol"], f["fill_date"])
            conn.execute(
                "INSERT INTO decisions (symbol, action, side,"
                " composite_snapshot_id, composite_date, fill_date, fill_price,"
                " quantity, order_ref, note, source, recorded_at)"
                " VALUES (?, 'acted', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f["symbol"],
                    f["side"],
                    m[0] if m else None,
                    m[1] if m else None,
                    f["fill_date"],
                    f["price"],
                    f["quantity"],
                    f["order_ref"],
                    f["note"],
                    "mcp" if f["order_ref"] else "manual",
                    now_iso,
                ),
            )
            matched += 1 if m else 0
            freelance += 0 if m else 1
        for p in passes:
            m = match_flagged(conn, p["symbol"], as_of_date)
            if m is None:
                skipped += 1
                print(f"skip pass {p['symbol']}: no flagged opinion in window")
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO decisions (symbol, action,"
                " composite_snapshot_id, composite_date, note, source,"
                " recorded_at) VALUES (?, 'passed', ?, ?, ?, 'manual', ?)",
                (p["symbol"], m[0], m[1], p["note"], now_iso),
            )
            passes_n += cur.rowcount
        cur = conn.execute(
            "INSERT INTO journal_runs (ran_at, fills_seen, matched, freelance,"
            " exits_attached, passes_recorded, duplicates_skipped, skipped)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (now_iso, len(fills), matched, freelance, exits, passes_n, dupes, skipped),
        )
        return dict(
            run_id=cur.lastrowid,
            fills_seen=len(fills),
            matched=matched,
            freelance=freelance,
            exits_attached=exits,
            passes_recorded=passes_n,
            duplicates_skipped=dupes,
            skipped=skipped,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_journal_matching.py -v`
Expected: PASS (12 tests).

- [ ] **Step 5: Gates + commit**

```bash
uv run ruff check && uv run ruff format && uv run mypy && uv run pytest
git add sources/combiners/scorer/journal.py tests/test_journal_matching.py
git commit --no-gpg-sign -m "feat(journal): deterministic fill/pass matching + transactional ingest"
```

---

### Task 4: Views — `v_decision_outcomes`, `v_flag_response`, `v_human_filter`, `v_freelance`

**Files:**
- Modify: `sources/combiners/scorer/db.py` (append to `_VIEWS`)
- Test: `tests/test_journal_db_views.py` (create)

**Interfaces:**
- Consumes: `decisions` (Task 1), existing `registered_snapshots` / `ticker_outcomes`.
- Produces: the four views below in scorer.db, recreated by `ensure_schema` each run.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_journal_db_views.py`. The fixture plants a graded window owned by snapshot 1 (Friday 2026-07-03), a marker-only sibling snapshot 2 (Sunday 2026-07-05, same entry window), and outcome rows for XLE (flagged bull) and GLD (flagged bull) at horizon 5:

```python
from sources.combiners.scorer import db

NOW = "2026-07-20T21:10:00+00:00"


def _seeded(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    conn.execute(
        "INSERT INTO registered_snapshots (composite_snapshot_id, composite_date,"
        " entry_date, registered_at, ticker_rows, signal_rows, skipped)"
        " VALUES (1, '2026-07-03', '2026-07-06', ?, 2, 0, 0)",
        (NOW,),
    )
    conn.execute(  # weekend sibling: marker-only, same window
        "INSERT INTO registered_snapshots (composite_snapshot_id, composite_date,"
        " entry_date, registered_at, ticker_rows, signal_rows, skipped)"
        " VALUES (2, '2026-07-05', '2026-07-06', ?, 0, 0, 0)",
        (NOW,),
    )
    for sym, score in (("XLE", 5), ("GLD", 4)):
        conn.execute(
            "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date,"
            " symbol, score_sum, total, bullish, bearish, horizon, entry_date,"
            " entry_close, bench_entry_close, exit_date, exit_close, fwd_return,"
            " bench_fwd_return, matured_at)"
            " VALUES (1, '2026-07-03', ?, ?, 4, 4, 0, 5, '2026-07-06',"
            " 100.0, 500.0, '2026-07-13', 104.0, 0.04, 0.01, ?)",
            (sym, score, NOW),
        )
    conn.commit()
    return conn


def _decide(conn, **kw):
    cols = dict(
        symbol="XLE",
        action="acted",
        side="buy",
        composite_snapshot_id=1,
        composite_date="2026-07-03",
        fill_date="2026-07-06",
        fill_price=101.0,
        recorded_at=NOW,
    )
    cols.update(kw)
    keys = [k for k, v in cols.items() if v is not None]
    conn.execute(
        f"INSERT INTO decisions ({', '.join(keys)})"
        f" VALUES ({', '.join('?' for _ in keys)})",
        [cols[k] for k in keys],
    )
    conn.commit()


def test_decision_outcomes_slippage_and_paper_legs(tmp_path):
    conn = _seeded(tmp_path)
    _decide(conn)
    row = conn.execute(
        "SELECT entry_slippage, fwd_return, bench_fwd_return, aligned,"
        " realized_return FROM v_decision_outcomes WHERE horizon = 5"
    ).fetchone()
    assert abs(row[0] - 0.01) < 1e-9  # paid 101 vs paper 100 = +1% cost
    assert row[1] == 0.04 and row[2] == 0.01
    assert row[3] == 1  # buy on a bull flag
    assert row[4] is None  # no exit yet


def test_decision_outcomes_realized_round_trip(tmp_path):
    conn = _seeded(tmp_path)
    _decide(conn, exit_fill_date="2026-07-13", exit_fill_price=103.0)
    row = conn.execute(
        "SELECT realized_return FROM v_decision_outcomes WHERE horizon = 5"
    ).fetchone()
    assert abs(row[0] - (103.0 / 101.0 - 1)) < 1e-9


def test_decision_outcomes_sell_slippage_sign(tmp_path):
    conn = _seeded(tmp_path)
    _decide(conn, side="sell", fill_price=99.0)
    row = conn.execute(
        "SELECT entry_slippage, aligned FROM v_decision_outcomes WHERE horizon = 5"
    ).fetchone()
    assert abs(row[0] - 0.01) < 1e-9  # sold at 99 vs paper 100: 1% cost
    assert row[1] == 0  # sell against a bull flag


def test_window_rekeying_marker_only_snapshot(tmp_path):
    conn = _seeded(tmp_path)
    # decision matched to Sunday's marker-only snapshot 2
    _decide(conn, composite_snapshot_id=2, composite_date="2026-07-05")
    row = conn.execute(
        "SELECT fwd_return FROM v_decision_outcomes WHERE horizon = 5"
    ).fetchone()
    assert row[0] == 0.04  # graded against the owning snapshot's rows


def test_freelance_rows_have_null_paper_legs(tmp_path):
    conn = _seeded(tmp_path)
    _decide(conn, symbol="NVDA", composite_snapshot_id=None, composite_date=None)
    rows = conn.execute(
        "SELECT fwd_return, entry_slippage FROM v_decision_outcomes"
        " WHERE symbol = 'NVDA'"
    ).fetchall()
    assert rows == [(None, None)]
    assert conn.execute("SELECT symbol FROM v_freelance").fetchall() == [("NVDA",)]


def test_flag_response_three_states(tmp_path):
    conn = _seeded(tmp_path)
    _decide(conn)  # acted on XLE; GLD has no row -> inferred pass
    rows = dict(
        conn.execute("SELECT symbol, response FROM v_flag_response").fetchall()
    )
    assert rows == {"XLE": "acted", "GLD": "passed_inferred"}
    _decide(conn, symbol="GLD", action="passed", side=None, fill_date=None, fill_price=None)
    rows = dict(
        conn.execute("SELECT symbol, response FROM v_flag_response").fetchall()
    )
    assert rows["GLD"] == "passed"


def test_flag_response_rekeys_pass_on_sibling_snapshot(tmp_path):
    conn = _seeded(tmp_path)
    _decide(
        conn,
        symbol="GLD",
        action="passed",
        side=None,
        fill_date=None,
        fill_price=None,
        composite_snapshot_id=2,
        composite_date="2026-07-05",
    )
    rows = dict(
        conn.execute("SELECT symbol, response FROM v_flag_response").fetchall()
    )
    assert rows["GLD"] == "passed"  # Sunday's pass answers Friday's graded flag


def test_human_filter_aggregates(tmp_path):
    conn = _seeded(tmp_path)
    _decide(conn)
    rows = {
        r[0]: (r[2], r[3])
        for r in conn.execute(
            "SELECT response, horizon, n, avg_dir_excess FROM v_human_filter"
        )
    }
    assert rows["acted"] == (1, 0.03)  # bull flag: 0.04 - 0.01
    assert rows["passed_inferred"] == (1, 0.03)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_journal_db_views.py -v`
Expected: FAIL — `no such table: v_decision_outcomes`.

- [ ] **Step 3: Append the views to `_VIEWS` in `sources/combiners/scorer/db.py`**

```sql
-- Decision-journal views. Window re-keying: the scorer grades ONE snapshot
-- per ledger window (weekend/rerun siblings register marker-only with
-- ticker_rows = 0), so a decision matched to a sibling must grade against
-- the window owner's outcome rows. A decision whose snapshot isn't
-- registered yet has no registered_snapshots row and shows NULL paper legs
-- until the nightly scorer catches up — the view heals itself.
-- entry_slippage is signed so positive is always cost (buys: paid above
-- paper entry; sells: received below it). realized_return is fills-only.
DROP VIEW IF EXISTS v_decision_outcomes;
CREATE VIEW v_decision_outcomes AS
SELECT d.id AS decision_id, d.symbol, d.side, d.source,
       d.composite_snapshot_id, d.composite_date,
       d.fill_date, d.fill_price, d.quantity,
       d.exit_fill_date, d.exit_fill_price, d.note,
       t.horizon, t.score_sum, t.total, t.entry_date, t.entry_close,
       t.fwd_return, t.bench_fwd_return, t.matured_at,
       CASE WHEN t.score_sum IS NULL THEN NULL
            WHEN d.side = 'buy' THEN (t.score_sum > 0)
            ELSE (t.score_sum < 0) END AS aligned,
       CASE WHEN t.entry_close IS NULL THEN NULL
            WHEN d.side = 'sell' THEN 1 - d.fill_price / t.entry_close
            ELSE d.fill_price / t.entry_close - 1 END AS entry_slippage,
       CASE WHEN d.exit_fill_price IS NULL THEN NULL
            WHEN d.side = 'sell' THEN 1 - d.exit_fill_price / d.fill_price
            ELSE d.exit_fill_price / d.fill_price - 1 END AS realized_return
FROM decisions d
LEFT JOIN registered_snapshots r
       ON r.composite_snapshot_id = d.composite_snapshot_id
LEFT JOIN registered_snapshots owner
       ON owner.entry_date = r.entry_date AND owner.ticker_rows > 0
LEFT JOIN ticker_outcomes t
       ON t.composite_snapshot_id = owner.composite_snapshot_id
      AND t.symbol = d.symbol
WHERE d.action = 'acted';

-- Every matured flagged opinion and what the human did about it. Thresholds
-- mirror composite v_flagged (pinned by test_journal_matching). The
-- decision lookup re-keys through the window (any sibling snapshot's
-- decision answers the owner's flag); MIN(action) is the precedence trick:
-- 'acted' < 'passed' alphabetically, so acting ever beats passing.
-- dir_excess is excess return in the flag's direction.
DROP VIEW IF EXISTS v_flag_response;
CREATE VIEW v_flag_response AS
SELECT t.composite_snapshot_id, t.composite_date, t.symbol,
       t.score_sum, t.total, t.horizon,
       t.fwd_return, t.bench_fwd_return,
       CASE WHEN t.bench_fwd_return IS NULL THEN NULL
            WHEN t.score_sum > 0 THEN t.fwd_return - t.bench_fwd_return
            ELSE t.bench_fwd_return - t.fwd_return END AS dir_excess,
       COALESCE(
           (SELECT MIN(d.action) FROM decisions d
            JOIN registered_snapshots sib
              ON sib.composite_snapshot_id = d.composite_snapshot_id
            WHERE sib.entry_date = owner.entry_date AND d.symbol = t.symbol),
           'passed_inferred') AS response
FROM ticker_outcomes t
JOIN registered_snapshots owner ON owner.composite_snapshot_id = t.composite_snapshot_id
WHERE t.matured_at IS NOT NULL
  AND ABS(t.score_sum) >= 4 AND t.total >= 3;

-- The headline: does acting beat passing? Plain averages + n day one; the
-- Wilson helpers can grade this once samples justify it.
DROP VIEW IF EXISTS v_human_filter;
CREATE VIEW v_human_filter AS
SELECT response, horizon, COUNT(*) AS n,
       AVG(dir_excess) AS avg_dir_excess,
       AVG(fwd_return) AS avg_fwd_return
FROM v_flag_response
GROUP BY response, horizon;

-- Trades nothing recommended: acted decisions with no matched opinion.
DROP VIEW IF EXISTS v_freelance;
CREATE VIEW v_freelance AS
SELECT id AS decision_id, symbol, side, fill_date, fill_price, quantity,
       exit_fill_date, exit_fill_price,
       CASE WHEN exit_fill_price IS NULL THEN NULL
            WHEN side = 'sell' THEN 1 - exit_fill_price / fill_price
            ELSE exit_fill_price / fill_price - 1 END AS realized_return,
       note, source, recorded_at
FROM decisions WHERE action = 'acted' AND composite_snapshot_id IS NULL;
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_journal_db_views.py tests/test_journal_db_schema.py -v`
Expected: PASS.

- [ ] **Step 5: Gates + commit**

```bash
uv run ruff check && uv run ruff format && uv run mypy && uv run pytest
git add sources/combiners/scorer/db.py tests/test_journal_db_views.py
git commit --no-gpg-sign -m "feat(journal): realized-vs-paper views with window re-keying"
```

---

### Task 5: Dispatcher — `run()`, `main()`, registry entry

**Files:**
- Modify: `sources/combiners/scorer/journal.py`
- Modify: `registry.py` (import + `"journal"` entry after `"scorer"`)
- Test: `tests/test_journal_run.py` (create), `tests/test_registry.py` (add one assertion)

**Interfaces:**
- Consumes: `parse_doc` / `ingest` (Tasks 2–3), `fetch.attach_ro` / `fetch.detach`.
- Produces: `journal.run(db_path, doc, composite_db=None, now_iso=None) -> dict` (ingest counts) and `journal.main(argv)` with `--db` (default `scorer.db`), `--composite-db` (default: `composite.db` next to `--db`), `--input <file|->`, `--last-run`. Registry name: `journal`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_journal_run.py`:

```python
import json

import pytest

from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import db, journal

NOW = "2026-07-08T21:40:00+00:00"


def _mini_composite(path, date="2026-07-06", symbol="XLE"):
    conn = composite_db.connect(str(path))
    composite_db.ensure_schema(conn)
    conn.execute(
        "INSERT INTO snapshots (captured_at, signals_expected) VALUES (?, 1)",
        (f"{date}T21:05:00+00:00",),
    )
    conn.execute(
        "INSERT INTO ticker_scores (snapshot_id, symbol, total, score_sum)"
        " VALUES (1, ?, 4, 5)",
        (symbol,),
    )
    conn.commit()
    conn.close()


DOC = {
    "as_of": NOW,
    "fills": [
        {
            "symbol": "XLE",
            "side": "buy",
            "price": 94.30,
            "quantity": 2,
            "filled_at": "2026-07-07T14:31:00+00:00",
            "order_ref": "ref-1",
        }
    ],
}


def test_run_ingests(tmp_path):
    _mini_composite(tmp_path / "composite.db")
    counts = journal.run(
        str(tmp_path / "scorer.db"),
        DOC,
        composite_db=str(tmp_path / "composite.db"),
        now_iso=NOW,
    )
    assert counts["matched"] == 1


def test_run_empty_doc_needs_no_composite(tmp_path):
    counts = journal.run(str(tmp_path / "scorer.db"), {}, now_iso=NOW)
    assert counts["fills_seen"] == 0 and counts["run_id"] == 1


def test_run_missing_composite_is_loud(tmp_path):
    with pytest.raises(FileNotFoundError):
        journal.run(
            str(tmp_path / "scorer.db"),
            DOC,
            composite_db=str(tmp_path / "composite.db"),
            now_iso=NOW,
        )
    conn = db.connect(str(tmp_path / "scorer.db"))
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM journal_runs").fetchone()[0] == 0


def test_main_file_input_and_default_composite_path(tmp_path, capsys):
    _mini_composite(tmp_path / "composite.db")
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(DOC))
    journal.main(["--db", str(tmp_path / "scorer.db"), "--input", str(doc_path)])
    out = capsys.readouterr().out
    assert "1 matched" in out


def test_main_stdin_input(tmp_path, capsys, monkeypatch):
    import io

    _mini_composite(tmp_path / "composite.db")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(DOC)))
    journal.main(["--db", str(tmp_path / "scorer.db"), "--input", "-"])
    assert "1 matched" in capsys.readouterr().out


def test_main_last_run(tmp_path, capsys):
    journal.main(["--db", str(tmp_path / "scorer.db"), "--last-run"])
    assert capsys.readouterr().out.strip() == "never"
    journal.run(str(tmp_path / "scorer.db"), {}, now_iso=NOW)
    journal.main(["--db", str(tmp_path / "scorer.db"), "--last-run"])
    assert capsys.readouterr().out.strip() == NOW


def test_main_bad_input_exits_nonzero(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(SystemExit):
        journal.main(["--db", str(tmp_path / "scorer.db"), "--input", str(bad)])
    err = capsys.readouterr().err
    assert "JSONDecodeError" in err


def test_main_missing_composite_exits_nonzero(tmp_path, capsys):
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(DOC))
    with pytest.raises(SystemExit):
        journal.main(["--db", str(tmp_path / "scorer.db"), "--input", str(doc_path)])
    assert "composite" in capsys.readouterr().err
```

Add to `tests/test_registry.py` (match the file's existing style — one entry assertion):

```python
def test_journal_registered():
    from registry import REGISTRY

    assert "journal" in REGISTRY
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_journal_run.py tests/test_registry.py -v`
Expected: FAIL — `AttributeError: ... no attribute 'run'` and the registry assertion.

- [ ] **Step 3: Implement `run` + `main` in `journal.py`; register**

Add the imports at the top of `sources/combiners/scorer/journal.py` (directly after the module docstring):

```python
import argparse
import json
import os
import sys
from datetime import UTC, datetime

from sources.combiners.scorer import db, fetch
```

Then append:

```python
def run(db_path, doc, composite_db=None, now_iso=None) -> dict:
    """Parse + ingest one document. composite.db is attached only when
    something needs matching; a missing composite.db is then a HARD error —
    silently freelancing every fill would corrupt the filter-value
    evidence. An empty doc still writes a run header (the "ran and found
    nothing" signal for the schedule's freshness check)."""
    now_iso = now_iso or datetime.now(UTC).isoformat()
    fills, passes, skipped = parse_doc(doc)
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        need_match = bool(fills or passes)
        if need_match:
            fetch.attach_ro(conn, composite_db)
        try:
            return ingest(conn, fills, passes, now_iso, skipped=skipped)
        finally:
            if need_match:
                fetch.detach(conn)
    finally:
        conn.close()


def main(argv=None) -> None:
    p = argparse.ArgumentParser(
        prog="journal",
        description="Record human decisions (fills/passes) against composite"
        " opinions (reads composite.db read-only for matching)",
    )
    p.add_argument("--db", default="scorer.db")
    p.add_argument(
        "--composite-db", default=None, help="composite.db path (default: alongside --db)"
    )
    p.add_argument("--input", help="path to the JSON document, or - for stdin")
    p.add_argument(
        "--last-run", action="store_true", help="print the latest run timestamp and exit"
    )
    a = p.parse_args(argv)

    if a.last_run:
        conn = db.connect(a.db)
        try:
            db.ensure_schema(conn)
            row = conn.execute("SELECT MAX(ran_at) FROM journal_runs").fetchone()
        finally:
            conn.close()
        print(row[0] or "never")
        return
    if not a.input:
        p.error("--input is required unless --last-run")

    try:
        if a.input == "-":
            doc = json.load(sys.stdin)
        else:
            with open(a.input, encoding="utf-8") as f:
                doc = json.load(f)
    except Exception as e:
        print(f"error: cannot read input: {type(e).__name__}", file=sys.stderr)
        raise SystemExit(1) from None

    composite_path = a.composite_db or os.path.join(
        os.path.dirname(a.db) or ".", "composite.db"
    )
    try:
        c = run(a.db, doc, composite_db=composite_path)
    except FileNotFoundError:
        print("error: composite db not found (fills need matching)", file=sys.stderr)
        raise SystemExit(1) from None
    except ValueError as e:
        print(f"error: bad document: {type(e).__name__}", file=sys.stderr)
        raise SystemExit(1) from None
    print(
        f"journal run {c['run_id']}: {c['matched']} matched,"
        f" {c['freelance']} freelance, {c['exits_attached']} exits,"
        f" {c['passes_recorded']} passes, {c['duplicates_skipped']} duplicates,"
        f" {c['skipped']} skipped, into {a.db}"
    )


if __name__ == "__main__":
    main()
```

In `registry.py` add (alphabetical with the other combiner imports):

```python
from sources.combiners.scorer.journal import main as journal_main
```

and in `REGISTRY`, after `"scorer": scorer_main,`:

```python
    "journal": journal_main,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_journal_run.py tests/test_registry.py -v`
Expected: PASS.

- [ ] **Step 5: Smoke-test the real CLI end to end**

```bash
uv run python main.py --list | grep journal
uv run python main.py journal --db data/scorer.db --last-run
echo '{}' | uv run python main.py journal --db data/scorer.db --input -
uv run python main.py journal --db data/scorer.db --last-run
```

Expected: `journal` listed; `never`; `journal run 1: 0 matched, ... into data/scorer.db`; then a timestamp. (This writes one empty run header to the real db — harmless and honest: the journal did run.)

- [ ] **Step 6: Gates + commit**

```bash
uv run ruff check && uv run ruff format && uv run mypy && uv run pytest
git add sources/combiners/scorer/journal.py registry.py tests/test_journal_run.py tests/test_registry.py
git commit --no-gpg-sign -m "feat(journal): dispatcher (run/main/--last-run) + registry entry"
```

---

### Task 6: Entry skill + launchd schedule + SCHEDULE.md

**Files:**
- Create: `.claude/skills/journal-sync/SKILL.md`
- Create: `deploy/launchd/journal_sync.sh` (mode 755)
- Modify: `deploy/launchd/install.py` (one `JOBS` entry)
- Modify: `docs/SCHEDULE.md` (one row)

**Interfaces:**
- Consumes: the `journal` dispatcher (Task 5), Robinhood MCP tools `get_accounts` / `get_equity_orders`, the existing `env.sh` + freshness-check pattern from `portfolio_snapshot.sh`.

- [ ] **Step 1: Write the skill**

Create `.claude/skills/journal-sync/SKILL.md`:

```markdown
---
name: journal-sync
description: Sync Robinhood equity fills into the decision journal (data/scorer.db) via the journal dispatcher, and record explicit passes on flagged tickers. Use when the user asks to sync/journal trades, log a pass, or backfill trade history.
---

# journal-sync

Record what the human DID about composite opinions. Guiding invariant
(same as account-positions): Claude may fetch live state via MCP, but it
enters the system only through the `journal` dispatcher — never write SQL
against scorer.db directly.

## Procedure

1. Since-bound:

   ```bash
   uv run python main.py journal --db data/scorer.db --last-run
   ```

   Prints an ISO timestamp or `never` (→ use 7 days ago).
2. Fetch via the Robinhood MCP (read-only tools):
   - `get_accounts` → pin the **"Agentic" account (number ending 1936)**;
     if no account matches, stop and report — never fall back.
   - `get_equity_orders` scoped to it: **filled** orders updated since the
     bound. Never paste raw MCP payloads into the conversation (they can
     carry account identifiers).
3. Build ONE JSON document in the scratchpad:

   ```json
   {"as_of": "<UTC now isoformat>",
    "fills": [{"symbol": "XLE", "side": "buy", "price": 94.30,
               "quantity": 2, "filled_at": "<order executed-at UTC ISO>",
               "order_ref": "<order id>"}],
    "passes": [{"symbol": "GLD", "note": "too crowded"}]}
   ```

   - `order_ref` = the order's id — the idempotency key; re-syncing an
     overlapping window is safe (duplicates are counted and skipped).
   - `passes` only when the user dictates them; a pass must answer a
     currently-flagged ticker or it is skipped with a message.
   - Zero fills is normal: ingest the empty doc anyway — the run header is
     the "ran and found nothing" signal the schedule's freshness check reads.
4. Ingest:

   ```bash
   uv run python main.py journal --db data/scorer.db --input <scratchpad>/journal.json
   ```

5. Report the printed counts (matched / freelance / exits / passes /
   duplicates / skipped).

## Manual path

The user dictates a trade ("bought 2 XLE at 94.30 Tuesday morning"): build
the same document without `order_ref` (rows record as `source: manual`).
Manual rows have no idempotency key — check `v_decision_outcomes` for an
existing row before re-dictating.

## Rules

- **Secret hygiene**: on any MCP or CLI error report the exception type
  name only — never message bodies, URLs, or payload fragments.
- **Write scope**: this command writes ONLY `data/scorer.db`, only via the
  dispatcher. Everything else it touches is read-only.
- Reading views (`v_decision_outcomes`, `v_flag_response`, `v_human_filter`,
  `v_freelance`) to answer questions is fine — reading is not writing.
```

- [ ] **Step 2: Write the launchd script**

Create `deploy/launchd/journal_sync.sh` (copy the shape of `portfolio_snapshot.sh`):

```bash
#!/bin/bash
# Afternoon decision-journal sync via headless claude (subscription auth) ->
# Robinhood MCP order history -> main.py journal. Same silent failure mode
# as the portfolio slot (a claude session can "succeed" with stale MCP
# auth), and the same loud check: an empty-fill day still writes a
# journal_runs header, so a missing header means the sync itself failed.
set -uo pipefail
source "$(dirname "$0")/env.sh"

echo "[$(date '+%F %T')] start: journal sync"
claude -p "/journal-sync" \
    --model haiku \
    --allowedTools "mcp__claude_ai_Robinhood_MCP__get_accounts,mcp__claude_ai_Robinhood_MCP__get_equity_orders,Write,Bash(uv run python main.py journal *)" \
    --output-format json

FRESH=$(sqlite3 data/scorer.db \
    "SELECT COUNT(*) FROM journal_runs WHERE ran_at >= datetime('now', '-2 hours');" \
    2>/dev/null || echo 0)
if [ "${FRESH:-0}" -lt 1 ]; then
    echo "[$(date '+%F %T')] STALE: no journal run in the last 2h — check Robinhood MCP auth" >&2
    exit 1
fi
echo "[$(date '+%F %T')] journal sync fresh"
```

Then: `chmod 755 deploy/launchd/journal_sync.sh`

- [ ] **Step 3: Register the job and document it**

In `deploy/launchd/install.py`, add to `JOBS` directly below the `"portfolio"` entry:

```python
    "journal": (script("journal_sync.sh"), weekly(MON_FRI, 14, 40)),
```

In `docs/SCHEDULE.md`, add a row below the `portfolio` row (match the table's column style):

```markdown
| `journal` | 2:40pm | Headless `claude -p "/journal-sync"` → Robinhood MCP order history → `main.py journal`. Ten minutes after portfolio so a stale-auth failure shows up twice. Empty-fill days still write a run header (that's what the freshness check reads). Journal matching reads composite.db; decisions land in scorer.db (never pruned) |
```

Also check `docs/SCHEDULE.md` for any "jobs" count or summary line near the top — if one exists, increment it.

- [ ] **Step 4: Verify install.py still parses and renders**

```bash
uv run python -c "from deploy.launchd.install import JOBS; print(sorted(JOBS))"
```

Expected: list includes `'journal'`. Do NOT run the installer itself (it would touch live launchd state); the user installs on their own schedule.

- [ ] **Step 5: Gates + commit**

```bash
uv run ruff check && uv run ruff format && uv run mypy && uv run pytest
git add .claude/skills/journal-sync/SKILL.md deploy/launchd/journal_sync.sh deploy/launchd/install.py docs/SCHEDULE.md
git commit --no-gpg-sign -m "feat(journal): journal-sync skill + 2:40pm launchd slot"
```

---

### Task 7: Roadmap graduation + final verification

**Files:**
- Modify: `docs/ROADMAP.md` (item 5 graduates to a shipped note, per the file's own convention)
- Modify: `CLAUDE.md` (one line: scorer.db now also holds the decision journal; `journal` dispatcher exists)

**Interfaces:** none — documentation only.

- [ ] **Step 1: Update ROADMAP.md**

Replace the whole `### 5. Decision journal` section (problem/done-when/size lines included) with a shipped note in the same style as items 1–4, under the `## Next — evaluation hardening` header:

```markdown
*(Item 5, decision journal: `decisions` in scorer.db keyed to composite
opinions — fills auto-matched from Robinhood order history (headless
2:40pm `/journal-sync` slot), passes inferred in `v_flag_response` with
explicit override; `v_decision_outcomes` (slippage, realized-vs-paper),
`v_human_filter` (acted vs passed). Shipped 2026-07-06.)*
```

- [ ] **Step 2: Update CLAUDE.md**

In the combiner paragraph of `CLAUDE.md` (the one describing `composite` and `scorer`), extend the scorer sentence:

```markdown
The `scorer` combiner grades composite opinions against forward returns and
never feeds back — re-weighting the catalog is a human decision made by
reading `v_signal_efficacy`/`v_bucket_performance`. The scorer package also
owns the decision journal (`main.py journal --input <file|->`, fed by the
`.claude/skills/journal-sync` MCP skill like `portfolio`): human fills and
passes land in scorer.db `decisions` (never pruned) and are compared to
paper outcomes in `v_decision_outcomes`/`v_flag_response`/`v_human_filter`.
```

- [ ] **Step 3: Full verification**

```bash
uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest
uv run python main.py --list
```

Expected: all gates green; `journal` in the dispatcher list.

- [ ] **Step 4: Commit**

```bash
git add docs/ROADMAP.md CLAUDE.md
git commit --no-gpg-sign -m "docs(roadmap): item 5 shipped — decision journal"
```
