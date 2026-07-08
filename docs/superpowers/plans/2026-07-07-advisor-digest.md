# Advisor Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a plain-text `— advisor —` block to the nightly ntfy digest that presents the advisor combiner's book view (heat, disagreements, size caps, staleness).

**Architecture:** One new pure formatter `format_advisor_lines(...)` and one thin read-only reader `advisor_digest()` in `deploy/launchd/daily_summary.py`, mirroring the existing `signals_digest()`. `build_summary` appends the block after `— signals —`. All formatting logic is in the pure function and is unit-tested with hand-built rows (no DB, no network).

**Tech Stack:** Python 3.12, stdlib only (`sqlite3`, `datetime`), pytest. Managed with `uv`.

## Global Constraints

- **Zero runtime third-party dependencies** — stdlib only (`sqlite3`, `datetime`, `re`, `subprocess`). No new deps.
- **Best-effort, never crash** — the advisor block informs; the health layers alert. Any DB read failure → a single note line; the digest still sends.
- **Read-only DB access** — open `data/advisor.db` with `?mode=ro`, `uri=True`.
- **No markdown** — clean structured plain text (renders correctly on ntfy mobile + web).
- **Offline tests** — no network, no real DB. The suite runs from repo root via `uv run pytest`.
- **All four gates must pass before commit**: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, `uv run pytest`. The pre-commit hook runs them.
- **`·` (U+00B7 middle dot) separator** — match the existing `signals_digest` line style.

---

### Task 1: Pure formatter — book line, source-failure note, no-snapshot

**Files:**
- Modify: `deploy/launchd/daily_summary.py` (add `import datetime as dt` if not present — it is already imported; add helpers + `format_advisor_lines`)
- Test: `tests/test_daily_summary_advisor.py` (create)

**Interfaces:**
- Produces: `format_advisor_lines(book, disagreements, caps, header) -> list[str]`.
  - `book`: mapping with keys `positions:int`, `heat_pct:float|None`, `heat_coverage:float|None`, `equity:float|None` — or `None`.
  - `disagreements`: list of mappings with keys `symbol:str`, `score_sum:int`, `group_name:str|None`, `strong:int`.
  - `caps`: list of mappings with keys `symbol:str`, `cap_shares:float`.
  - `header`: mapping with keys `portfolio_captured_at:str|None`, `captured_at:str|None`, `sources_failed:int` — or `None`.
  - Rows are accessed by string key, so both `dict` and `sqlite3.Row` work.

- [ ] **Step 1: Write the failing tests (test file header + book/no-snapshot cases)**

Create `tests/test_daily_summary_advisor.py`:

```python
"""Tests for the advisor digest block in the nightly ntfy summary.

Exercises the pure `format_advisor_lines` with hand-built dict rows (no DB,
no network) plus one reader-resilience test.
"""

import os
import sqlite3
import sys
import time
from pathlib import Path

import pytest

# daily_summary.py lives in deploy/launchd and inserts the repo root on
# sys.path itself at import; we only need its own dir on the path to import it.
DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import daily_summary  # noqa: E402


@pytest.fixture
def phoenix_tz():
    """Pin the process TZ to America/Phoenix so staleness-date assertions are
    deterministic on any host. The advisor slot runs on a Phoenix Mac mini, so
    this mirrors production; the digest converts UTC timestamps to local dates."""
    old = os.environ.get("TZ")
    os.environ["TZ"] = "America/Phoenix"
    time.tzset()
    yield
    if old is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = old
    time.tzset()


def _book(positions=2, heat_pct=0.0021, heat_coverage=1.0, equity=200.12):
    return {
        "positions": positions,
        "heat_pct": heat_pct,
        "heat_coverage": heat_coverage,
        "equity": equity,
    }


def _header(portfolio_captured_at="2026-07-08T04:12:02+00:00",
            captured_at="2026-07-08T04:12:02+00:00", sources_failed=0):
    return {
        "portfolio_captured_at": portfolio_captured_at,
        "captured_at": captured_at,
        "sources_failed": sources_failed,
    }


def test_no_snapshot_returns_single_line():
    assert daily_summary.format_advisor_lines(None, [], [], None) == [
        "advisor: no snapshot"
    ]


def test_book_line_nominal():
    lines = daily_summary.format_advisor_lines(_book(), [], [], _header())
    assert lines[0] == "book: 0.21% risk · 2 positions · cov 1.0 · equity $200"


def test_book_line_percent_precision():
    assert daily_summary.format_advisor_lines(
        _book(heat_pct=0.00008), [], [], _header()
    )[0].startswith("book: 0.01% risk")
    assert daily_summary.format_advisor_lines(
        _book(heat_pct=0.0), [], [], _header()
    )[0].startswith("book: 0.00% risk")


def test_book_line_singular_position():
    assert "1 position ·" in daily_summary.format_advisor_lines(
        _book(positions=1), [], [], _header()
    )[0]


def test_book_line_null_fields():
    line = daily_summary.format_advisor_lines(
        _book(heat_coverage=None, equity=None), [], [], _header()
    )[0]
    assert "cov n/a" in line
    assert "equity ?" in line


def test_book_line_empty_book():
    # 0 positions → v_book_heat's SUM(heat_pct)/heat_coverage are NULL
    line = daily_summary.format_advisor_lines(
        _book(positions=0, heat_pct=None, heat_coverage=None), [], [], _header()
    )[0]
    assert line == "book: n/a risk · 0 positions · cov n/a · equity $200"


def test_sources_failed_note():
    lines = daily_summary.format_advisor_lines(
        _book(), [], [], _header(sources_failed=2)
    )
    assert "advisor: 2 sources failed" in lines
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_daily_summary_advisor.py -v`
Expected: FAIL with `AttributeError: module 'daily_summary' has no attribute 'format_advisor_lines'`

- [ ] **Step 3: Implement the book/source-failure/no-snapshot portion**

In `deploy/launchd/daily_summary.py`, add above `def build_summary`:

```python
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
    return lines or ["advisor: no snapshot"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_daily_summary_advisor.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/test_daily_summary_advisor.py deploy/launchd/daily_summary.py
git commit --no-gpg-sign -m "feat(digest): advisor book line + source-failure/no-snapshot cases"
```

---

### Task 2: Pure formatter — disagreements, caps, staleness; full nominal block

**Files:**
- Modify: `deploy/launchd/daily_summary.py` (extend `format_advisor_lines`, add helpers)
- Test: `tests/test_daily_summary_advisor.py` (append cases)

**Interfaces:**
- Consumes: `format_advisor_lines`, `_book_line`, `_sources_line` from Task 1.
- Produces: complete `format_advisor_lines` emitting, in order: book line, source-failure note (if any), disagree line(s), cap line(s), staleness note (if stale).

- [ ] **Step 1: Write the failing tests (append to the test file)**

```python
def _dis(symbol="XOM", score_sum=-1, group_name="energy", strong=0):
    return {"symbol": symbol, "score_sum": score_sum,
            "group_name": group_name, "strong": strong}


def _cap(symbol="NVDA", cap_shares=3.2):
    return {"symbol": symbol, "cap_shares": cap_shares}


def test_disagree_weak_with_group():
    lines = daily_summary.format_advisor_lines(_book(), [_dis()], [], _header())
    assert "disagree: XOM -1 weak (energy)" in lines


def test_disagree_strong_uppercase():
    lines = daily_summary.format_advisor_lines(
        _book(), [_dis(score_sum=-5, strong=1)], [], _header()
    )
    assert "disagree: XOM -5 STRONG (energy)" in lines


def test_disagree_null_group_no_parens():
    lines = daily_summary.format_advisor_lines(
        _book(), [_dis(group_name=None)], [], _header()
    )
    assert "disagree: XOM -1 weak" in lines
    assert "(" not in [line for line in lines if line.startswith("disagree")][0]


def test_disagree_multiple_stable_order():
    rows = [_dis(symbol="CVX", score_sum=-1), _dis(symbol="XOM", score_sum=-3)]
    lines = [line for line in daily_summary.format_advisor_lines(
        _book(), rows, [], _header()) if line.startswith("disagree")]
    # ordered by score_sum asc, then symbol: XOM(-3) before CVX(-1)
    assert lines == ["disagree: XOM -3 weak (energy)",
                     "disagree: CVX -1 weak (energy)"]


def test_disagree_none():
    lines = daily_summary.format_advisor_lines(_book(), [], [], _header())
    assert "disagree: none" in lines


def test_caps_present():
    lines = daily_summary.format_advisor_lines(
        _book(), [], [_cap(symbol="AMD", cap_shares=1.5),
                       _cap(symbol="NVDA", cap_shares=3.2)], _header())
    assert "cap: AMD ≤ 1.50sh" in lines
    assert "cap: NVDA ≤ 3.20sh" in lines


def test_caps_none():
    lines = daily_summary.format_advisor_lines(_book(), [], [], _header())
    assert "caps: none tonight" in lines


def test_staleness_same_day_no_note():
    lines = daily_summary.format_advisor_lines(_book(), [], [], _header())
    assert not any(line.startswith("(sized vs portfolio") for line in lines)


def test_staleness_stale_note(phoenix_tz):
    # portfolio Jul 06 10:30 Phoenix, run Jul 07 21:12 Phoenix → 1 day old.
    hdr = _header(portfolio_captured_at="2026-07-06T17:30:00+00:00",
                  captured_at="2026-07-08T04:12:00+00:00")
    lines = daily_summary.format_advisor_lines(_book(), [], [], hdr)
    assert "(sized vs portfolio from Jul 06 — 1d old)" in lines


def test_full_nominal_block(phoenix_tz):
    hdr = _header(portfolio_captured_at="2026-07-06T17:30:00+00:00",
                  captured_at="2026-07-08T04:12:00+00:00")
    lines = daily_summary.format_advisor_lines(_book(), [_dis()], [], hdr)
    assert lines == [
        "book: 0.21% risk · 2 positions · cov 1.0 · equity $200",
        "disagree: XOM -1 weak (energy)",
        "caps: none tonight",
        "(sized vs portfolio from Jul 06 — 1d old)",
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_daily_summary_advisor.py -v`
Expected: FAIL — new cases fail (e.g. `disagree: none` not in output), old 6 still pass.

- [ ] **Step 3: Implement disagreements/caps/staleness**

Add helpers above `format_advisor_lines`:

```python
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
    return [
        f"cap: {r['symbol']} ≤ {r['cap_shares']:.2f}sh"
        for r in sorted(rows, key=lambda r: r["symbol"])
    ]


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
```

Then extend `format_advisor_lines` — replace its body after the `sources` block with:

```python
    if sources:
        lines.append(sources)
    lines += _disagree_lines(disagreements)
    lines += _caps_lines(caps)
    stale = _staleness_line(header)
    if stale:
        lines.append(stale)
    return lines or ["advisor: no snapshot"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_daily_summary_advisor.py -v`
Expected: PASS (all cases). Note the em dash `—` (U+2014) and `≤` (U+2264) and `·` (U+00B7) must match exactly.

- [ ] **Step 5: Commit**

```bash
git add tests/test_daily_summary_advisor.py deploy/launchd/daily_summary.py
git commit --no-gpg-sign -m "feat(digest): advisor disagreements, caps, staleness note"
```

---

### Task 3: Reader `advisor_digest()`, wiring into `build_summary`, resilience

**Files:**
- Modify: `deploy/launchd/daily_summary.py` (add `advisor_digest`, append block in `build_summary`)
- Test: `tests/test_daily_summary_advisor.py` (append resilience test)

**Interfaces:**
- Consumes: `format_advisor_lines` from Tasks 1–2.
- Produces: `advisor_digest() -> list[str]` (reads `data/advisor.db?mode=ro`); `build_summary` appends `["", "— advisor —", *advisor_digest()]`.

- [ ] **Step 1: Write the failing resilience test (append)**

```python
def test_reader_unreadable_returns_note(monkeypatch):
    def boom(*args, **kwargs):
        raise sqlite3.OperationalError("no such table: snapshots")

    monkeypatch.setattr(daily_summary.sqlite3, "connect", boom)
    assert daily_summary.advisor_digest() == [
        "advisor: unreadable (OperationalError)"
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_daily_summary_advisor.py::test_reader_unreadable_returns_note -v`
Expected: FAIL with `AttributeError: module 'daily_summary' has no attribute 'advisor_digest'`

- [ ] **Step 3: Implement the reader and wire it in**

Add above `def build_summary`:

```python
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
                "SELECT symbol, cap_shares FROM v_latest_caps"
            ).fetchall()
        return format_advisor_lines(book, disagreements, caps, header)
    except sqlite3.Error as e:
        return [f"advisor: unreadable ({type(e).__name__})"]
```

In `build_summary`, find:

```python
    digest = signals_digest()
    if digest:
        lines += ["", "— signals —", *digest]
    return healthy, "\n".join(lines)
```

Replace with:

```python
    digest = signals_digest()
    if digest:
        lines += ["", "— signals —", *digest]
    advisor = advisor_digest()
    if advisor:
        lines += ["", "— advisor —", *advisor]
    return healthy, "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_daily_summary_advisor.py -v`
Expected: PASS (all tests including resilience).

- [ ] **Step 5: Run the full gate suite**

Run: `uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest`
Expected: all pass, no regressions.

- [ ] **Step 6: Live smoke test (real advisor.db, read-only, no send)**

Run: `uv run python -c "import sys; sys.path.insert(0, 'deploy/launchd'); import daily_summary; print(chr(10).join(daily_summary.advisor_digest()))"`
Expected: prints tonight's real block, e.g.
```
book: 0.21% risk · 2 positions · cov 1.0 · equity $200
disagree: XOM -1 weak (energy)
caps: none tonight
(sized vs portfolio from Jul 06 — 2d old)
```
(Exact values depend on the current DB; verify it does not raise.)

- [ ] **Step 7: Commit**

```bash
git add tests/test_daily_summary_advisor.py deploy/launchd/daily_summary.py
git commit --no-gpg-sign -m "feat(digest): wire advisor block into nightly summary + reader resilience"
```

---

## Notes for the implementer

- **Non-ASCII glyphs matter.** The lines use `·` (U+00B7), `≤` (U+2264), `—`
  (U+2014). Copy them exactly. The *formatter tests* assert exact strings and
  will catch mismatches — ruff will not (E501/line-length is not enabled; only
  E4/E7/E9), and neither will mypy: `[tool.mypy] files` is `sources`, `main.py`,
  `registry.py`, so `deploy/launchd/` is **out of mypy scope**. The new
  functions stay untyped, consistent with the existing `signals_digest` — do
  not add annotations expecting them to be checked.
- **`data/advisor.db` path is relative** — the launchd wrapper runs from repo
  root, and the smoke test / tests run from repo root too. Don't absolutize it.
- **Do not touch** `sources/combiners/advisor/*` or `notify.py` — this is a
  presentation-only change to the digest.
- **`strong` from `v_disagreements`** is `0`/`1` (SQLite boolean-as-int); treat
  truthy as STRONG.
