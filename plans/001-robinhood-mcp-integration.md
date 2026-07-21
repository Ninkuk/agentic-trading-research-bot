# Robinhood MCP Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `research-ticker` and `kill-thesis` an options-market read — what
move the market is pricing, and whether it refutes a thesis's timing claim —
plus tax-lot, realized-P&L and EPS-surprise reads, without loosening the
data-source policy.

**Architecture:** A pure-math helper under `tools/` does the vol arithmetic and
prints the comparison table; a shared skill reference documents the procedure;
four skills gain sections that call them. Source selection prefers the repo's
official CBOE feed (`data/options.db`) and falls back to Robinhood MCP only for
tickers it does not cover.

**Tech Stack:** Python 3.12 stdlib only (`math`, `statistics`, `argparse`,
`json`), `uv`, `pytest`. Markdown for skills.

**Spec:** `docs/superpowers/specs/2026-07-21-robinhood-mcp-integration-design.md`

## Global Constraints

- **Zero runtime third-party dependencies.** stdlib only. Do not `uv add` anything.
- **All four gates must pass before every commit:** `uv run ruff check`,
  `uv run ruff format --check`, `uv run mypy`, `uv run pytest`. The pre-commit
  hook runs them (~2s).
- **No network and no clock in `tools/`.** Pure functions only — no `datetime.now()`,
  no `urllib`, no `sqlite3`.
- **Never write to `data/*.db`.** Every DB read in this plan is read-only.
- **Never place an order; never recommend a position size.**
- **Secret hygiene:** on any MCP or CLI error report `type(e).__name__` only —
  never `str(e)`, `repr(e)`, or `e.url`.
- **Timestamps UTC, calendar dates Phoenix.** Use `phx_date(now_iso)` from
  `sources/common/clock.py`; never `now_iso[:10]`.
- **The CBOE options DB is `data/options.db`** (named for the registry key
  `options`), NOT `data/cboe_options.db`.
- **`iv30` is 30-day constant-maturity** and is never comparable to an ATM IV
  read off a single expiry.
- Do not add yourself as a commit co-author.

---

## Deviation from the approved spec — read before starting

The spec described this as prose-only. **Task 1 and Task 2 add a pure helper
module under `tools/`.** Rationale:

- The spec's own Open Risk 3 says the arithmetic has "no regression net."
- The design review caught a wrong formula (`straddle/spot` described as an
  upper bound when it is the mean absolute move). A tested function makes that
  class of error impossible to ship; prose does not.
- `tools/` is explicitly "neither a source nor a dispatcher... not registered in
  `registry.py`", so this stays inside the approved skills-only scope — no
  source package, dispatcher, DB, schema change, or launchd slot.
- `tools/valuation/reverse_dcf.py` is the exact precedent, and `research-ticker`
  already shells out to it.

It also makes the spec's "print the table before interpreting" rule
**structural**: the table is a program's stdout, not an instruction an agent can
satisfy nominally while narrating around it.

---

## File Structure

| Path | Responsibility |
|---|---|
| `tools/options/__init__.py` | package marker (empty) |
| `tools/options/implied_move.py` | pure vol arithmetic + CLI that prints the comparison table |
| `tests/test_implied_move.py` | unit tests for the above |
| `.claude/skills/shared/options-read.md` | the shared chain-reading procedure, read by two skills |
| `.claude/skills/kill-thesis/SKILL.md` | options check, verdict rule, tax lots |
| `.claude/skills/research-ticker/SKILL.md` | EPS surprise, Phase 2 pointer, Phase 4 check, output line |
| `.claude/skills/journal-sync/SKILL.md` | realized-P&L reconciliation, `decisions.note` tag |
| `.claude/skills/account-positions/SKILL.md` | one line on non-persisted tax lots |

Tasks 1–2 are TDD. Tasks 3–6 edit skill prose, which has no unit-test surface
(consistent with how these skills already work); each carries an explicit manual
verification step instead.

---

### Task 1: Pure options arithmetic

**Files:**
- Create: `tools/options/__init__.py`
- Create: `tools/options/implied_move.py`
- Test: `tests/test_implied_move.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `expected_absolute_move(call_mark: float, put_mark: float, spot: float) -> float`
  - `one_sigma_move(iv: float, days_to_expiry: int) -> float`
  - `realized_vol(closes: Sequence[float], window: int) -> float`
  - `refutes_timing(required_move: float, iv: float, days_to_expiry: int, sigmas: float = 2.0) -> tuple[bool, float, float]`
    returning `(refuted, k_sigmas, probability)`
  - constants `TRADING_DAYS = 252`, `CALENDAR_DAYS = 365`, `REFUTE_SIGMAS = 2.0`

- [ ] **Step 1: Write the failing test**

Create `tests/test_implied_move.py`:

```python
import math

import pytest

from tools.options.implied_move import (
    REFUTE_SIGMAS,
    expected_absolute_move,
    one_sigma_move,
    realized_vol,
    refutes_timing,
)

# Live AAPL fixtures captured 2026-07-21 and verified against
# Brenner-Subrahmanyam: straddle/spot should land within ~1% of
# sqrt(2/pi) * sigma * sqrt(T).
AAPL_CALL, AAPL_PUT, AAPL_SPOT = 8.425, 7.800, 327.70
AAPL_IV, AAPL_DTE = 0.375211, 10


def test_expected_absolute_move_is_straddle_over_spot():
    assert expected_absolute_move(AAPL_CALL, AAPL_PUT, AAPL_SPOT) == pytest.approx(
        0.04951174855050351
    )


def test_one_sigma_move_uses_calendar_years():
    assert one_sigma_move(AAPL_IV, AAPL_DTE) == pytest.approx(0.06210536661367661)


def test_one_sigma_exceeds_expected_absolute_move():
    """The straddle figure is the MEAN move, so it must sit BELOW 1 sigma.

    This is the error the design review caught: treating straddle/spot as a
    ceiling. If this assertion ever flips, the ceiling misreading is back.
    """
    exp = expected_absolute_move(AAPL_CALL, AAPL_PUT, AAPL_SPOT)
    sig = one_sigma_move(AAPL_IV, AAPL_DTE)
    assert exp < sig
    assert sig / exp == pytest.approx(1.2543, abs=1e-3)


def test_expected_absolute_move_matches_brenner_subrahmanyam():
    exp = expected_absolute_move(AAPL_CALL, AAPL_PUT, AAPL_SPOT)
    predicted = math.sqrt(2 / math.pi) * one_sigma_move(AAPL_IV, AAPL_DTE)
    assert exp == pytest.approx(predicted, rel=0.01)


def test_realized_vol_matches_hand_computation():
    """closes -> returns [+r, -r]; sample stdev = r*sqrt(2), annualized *sqrt(252)."""
    r = 0.01
    closes = [100.0, 100.0 * math.exp(r), 100.0]
    assert realized_vol(closes, window=2) == pytest.approx(
        r * math.sqrt(2) * math.sqrt(252)
    )


def test_realized_vol_of_flat_series_is_zero():
    assert realized_vol([100.0] * 10, window=5) == pytest.approx(0.0)


def test_realized_vol_uses_only_the_last_window_returns():
    quiet = [100.0] * 10
    shocked = quiet + [130.0, 100.0]
    assert realized_vol(shocked, window=2) > realized_vol(shocked, window=9)


def test_realized_vol_rejects_insufficient_history():
    with pytest.raises(ValueError, match="need 21 closes"):
        realized_vol([100.0] * 10, window=20)


def test_refutes_timing_when_thesis_needs_more_than_two_sigma():
    refuted, k, prob = refutes_timing(0.30, AAPL_IV, AAPL_DTE)
    assert refuted is True
    assert k == pytest.approx(4.8305, abs=1e-3)
    assert prob == pytest.approx(1.3619e-06, rel=1e-3)


def test_does_not_refute_between_one_and_two_sigma():
    """1.61 sigma is the market being less optimistic, NOT a refutation."""
    refuted, k, _ = refutes_timing(0.10, AAPL_IV, AAPL_DTE)
    assert refuted is False
    assert 1.0 < k < REFUTE_SIGMAS


def test_refutation_threshold_is_configurable():
    refuted, _, _ = refutes_timing(0.10, AAPL_IV, AAPL_DTE, sigmas=1.5)
    assert refuted is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {"call_mark": -1.0, "put_mark": 1.0, "spot": 100.0},
        {"call_mark": 1.0, "put_mark": 1.0, "spot": 0.0},
    ],
)
def test_expected_absolute_move_rejects_bad_input(kwargs):
    with pytest.raises(ValueError):
        expected_absolute_move(**kwargs)


@pytest.mark.parametrize("iv,dte", [(0.0, 10), (-0.1, 10), (0.3, 0), (0.3, -5)])
def test_one_sigma_move_rejects_bad_input(iv, dte):
    with pytest.raises(ValueError):
        one_sigma_move(iv, dte)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_implied_move.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.options'`

- [ ] **Step 3: Write minimal implementation**

Create `tools/options/__init__.py` as an empty file.

Create `tools/options/implied_move.py`:

```python
"""Options-market arithmetic for the research skills.

Pure functions: no network, no DB, no clock.

The point of this module is to keep vol arithmetic out of skill prose, where a
plausible-looking wrong formula survives review. Specifically: `straddle/spot`
is the EXPECTED ABSOLUTE move (~sqrt(2/pi) * sigma * sqrt(T), the
Brenner-Subrahmanyam approximation), NOT a ceiling. On the AAPL fixture it is
4.95% while the true 1-sigma move is 6.21%, and a move of that size is exceeded
roughly 42% of the time. Gating a verdict on it as a maximum produces false
refutations.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

TRADING_DAYS = 252
CALENDAR_DAYS = 365
REFUTE_SIGMAS = 2.0


def expected_absolute_move(call_mark: float, put_mark: float, spot: float) -> float:
    """ATM straddle divided by spot — the MEAN absolute move, not an upper bound."""
    if spot <= 0:
        raise ValueError("spot must be positive")
    if call_mark < 0 or put_mark < 0:
        raise ValueError("marks must be non-negative")
    return (call_mark + put_mark) / spot


def one_sigma_move(iv: float, days_to_expiry: int) -> float:
    """sigma * sqrt(T), T in calendar years. The true 1-sigma move."""
    if iv <= 0:
        raise ValueError("iv must be positive")
    if days_to_expiry <= 0:
        raise ValueError("days_to_expiry must be positive")
    return iv * math.sqrt(days_to_expiry / CALENDAR_DAYS)


def realized_vol(closes: Sequence[float], window: int) -> float:
    """Annualized close-to-close volatility over the last `window` returns.

    Close-to-close (not Parkinson/Garman-Klass) is deliberate: earnings gap
    overnight, and intraday-range estimators are blind to exactly that gap.
    """
    if window < 2:
        raise ValueError("window must be at least 2")
    if len(closes) < window + 1:
        raise ValueError(f"need {window + 1} closes, got {len(closes)}")
    if any(c <= 0 for c in closes):
        raise ValueError("closes must be positive")
    returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    return statistics.stdev(returns[-window:]) * math.sqrt(TRADING_DAYS)


def refutes_timing(
    required_move: float,
    iv: float,
    days_to_expiry: int,
    sigmas: float = REFUTE_SIGMAS,
) -> tuple[bool, float, float]:
    """Does the options market refute a thesis's TIMING claim?

    Returns (refuted, k_sigmas, probability), where k_sigmas expresses
    required_move in sigmas and probability is P(|move| >= required_move) under
    a lognormal. Refutation requires the thesis to need a move beyond `sigmas`
    sigma — a claim about probability, not a vague "the market disagrees".

    Between 1 and `sigmas` sigma the market is merely less optimistic than the
    thesis. That is NOT a refutation and must not be reported as one.
    """
    if required_move <= 0:
        raise ValueError("required_move must be positive")
    sigma = one_sigma_move(iv, days_to_expiry)
    k = required_move / sigma
    probability = math.erfc(k / math.sqrt(2))
    return k > sigmas, k, probability
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_implied_move.py -v`
Expected: PASS — 17 passed

- [ ] **Step 5: Run the full gates**

Run: `uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest -q`
Expected: all clean; test count rises from 1217 to 1234.

- [ ] **Step 6: Commit**

```bash
git add tools/options/__init__.py tools/options/implied_move.py tests/test_implied_move.py
git commit -m "feat(tools): add options implied-move arithmetic

straddle/spot is the expected ABSOLUTE move, not a ceiling — it sits at
0.798*sigma*sqrt(T) and is exceeded ~42% of the time. A test pins
one_sigma > expected_absolute so the ceiling misreading cannot return.

Refutation is defined at 2 sigma with the implied probability reported,
so a timing claim is rejected by a probability statement rather than a
vague disagreement."
```

---

### Task 2: CLI that prints the comparison table

**Files:**
- Modify: `tools/options/implied_move.py` (append CLI)
- Test: `tests/test_implied_move.py` (append CLI tests)

**Interfaces:**
- Consumes: all four functions from Task 1.
- Produces: `main(argv: Sequence[str] | None = None) -> int`. Exit 0 computed,
  exit 2 refused input. Invoked as
  `uv run python -m tools.options.implied_move`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_implied_move.py`:

```python
import json

from tools.options.implied_move import main

BASE_ARGS = [
    "--call-mark", "8.425",
    "--put-mark", "7.800",
    "--spot", "327.70",
    "--iv", "0.375211",
    "--dte", "10",
]


def test_cli_prints_both_move_figures(capsys):
    assert main(BASE_ARGS) == 0
    out = capsys.readouterr().out
    assert "4.95%" in out
    assert "6.21%" in out


def test_cli_labels_the_straddle_figure_as_a_mean_not_a_ceiling(capsys):
    main(BASE_ARGS)
    out = capsys.readouterr().out.lower()
    assert "mean" in out
    assert "not a ceiling" in out


def test_cli_emits_explicit_yes_no_rows_for_both_windows(tmp_path, capsys):
    closes = tmp_path / "closes.json"
    closes.write_text(json.dumps([100.0 + i * 0.5 for i in range(70)]))
    main([*BASE_ARGS, "--closes", str(closes)])
    out = capsys.readouterr().out
    assert "IV > RV60?" in out
    assert "IV > RV20?" in out


def test_cli_reports_insufficient_history_rather_than_silently_skipping(
    tmp_path, capsys
):
    closes = tmp_path / "closes.json"
    closes.write_text(json.dumps([100.0 + i for i in range(25)]))
    main([*BASE_ARGS, "--closes", str(closes)])
    out = capsys.readouterr().out
    assert "insufficient history" in out
    assert "IV > RV20?" in out


def test_cli_reports_refutation_with_the_implied_probability(capsys):
    main([*BASE_ARGS, "--required-move", "0.30"])
    out = capsys.readouterr().out
    assert "4.83 sigma" in out
    assert "YES" in out


def test_cli_does_not_refute_a_sub_two_sigma_requirement(capsys):
    main([*BASE_ARGS, "--required-move", "0.10"])
    out = capsys.readouterr().out
    assert "refutes timing claim (> 2 sigma)?" in out
    assert [ln for ln in out.splitlines() if "refutes timing claim" in ln][0].endswith("NO")


def test_cli_refuses_bad_input_with_exit_2(capsys):
    assert main([*BASE_ARGS[:-2], "--dte", "0"]) == 2
    assert "refused" in capsys.readouterr().err
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_implied_move.py -k cli -v`
Expected: FAIL — `ImportError: cannot import name 'main'`

- [ ] **Step 3: Write minimal implementation**

Append to `tools/options/implied_move.py`:

```python
def _render(rows: list[tuple[str, str]]) -> str:
    width = max(len(label) for label, _ in rows)
    return "\n".join(f"{label.ljust(width)}  {value}" for label, value in rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.options.implied_move",
        description=(
            "Print the options-implied move table. The straddle figure is a "
            "MEAN, never a ceiling."
        ),
    )
    parser.add_argument("--call-mark", type=float, required=True)
    parser.add_argument("--put-mark", type=float, required=True)
    parser.add_argument("--spot", type=float, required=True)
    parser.add_argument(
        "--iv", type=float, required=True, help="ATM IV as a decimal, e.g. 0.3752"
    )
    parser.add_argument(
        "--dte", type=int, required=True, help="calendar days to expiry"
    )
    parser.add_argument(
        "--closes",
        default=None,
        help="path to a JSON file holding daily closes, oldest first",
    )
    parser.add_argument(
        "--required-move",
        type=float,
        default=None,
        help="move the thesis needs, as a decimal (0.30 = 30%%)",
    )
    args = parser.parse_args(argv)

    try:
        expected = expected_absolute_move(args.call_mark, args.put_mark, args.spot)
        sigma = one_sigma_move(args.iv, args.dte)
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2

    rows: list[tuple[str, str]] = [
        ("spot", f"{args.spot:.2f}"),
        ("dte (calendar days)", str(args.dte)),
        ("ATM IV", f"{args.iv * 100:.2f}%"),
        ("expected absolute move (MEAN, not a ceiling)", f"{expected * 100:.2f}%"),
        ("1-sigma move", f"{sigma * 100:.2f}%"),
    ]

    if args.closes:
        with open(args.closes) as handle:
            closes = json.load(handle)
        for window in (60, 20):
            try:
                rv = realized_vol(closes, window)
            except ValueError:
                rows.append((f"RV{window}", "insufficient history"))
                rows.append((f"IV > RV{window}?", "UNKNOWN"))
                continue
            rows.append((f"RV{window}", f"{rv * 100:.2f}%"))
            rows.append((f"IV > RV{window}?", "YES" if args.iv > rv else "NO"))

    if args.required_move is not None:
        refuted, k, probability = refutes_timing(args.required_move, args.iv, args.dte)
        rows += [
            ("thesis requires", f"{args.required_move * 100:.2f}%"),
            ("that is", f"{k:.2f} sigma"),
            ("P(|move| >= required)", f"{probability:.6%}"),
            (
                f"refutes timing claim (> {REFUTE_SIGMAS:g} sigma)?",
                "YES" if refuted else "NO",
            ),
        ]

    print(_render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Add to the imports at the top of the file:

```python
import argparse
import json
import sys
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_implied_move.py -v`
Expected: PASS — 24 passed

- [ ] **Step 5: Verify the real invocation by hand**

Run:

```bash
uv run python -m tools.options.implied_move \
  --call-mark 8.425 --put-mark 7.800 --spot 327.70 \
  --iv 0.375211 --dte 10 --required-move 0.30
```

Expected output contains:

```
expected absolute move (MEAN, not a ceiling)  4.95%
1-sigma move                                  6.21%
that is                                       4.83 sigma
refutes timing claim (> 2 sigma)?             YES
```

- [ ] **Step 6: Run the full gates and commit**

```bash
uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest -q
git add tools/options/implied_move.py tests/test_implied_move.py
git commit -m "feat(tools): print the implied-move table from the CLI

Makes the spec's print-then-interpret rule structural rather than
advisory: the comparison table is a program's stdout, with explicit
YES/NO rows per realized-vol window, so an agent cannot satisfy the
rule nominally while narrating whichever window suits its prior.
Missing history prints UNKNOWN instead of dropping the row."
```

---

### Task 3: The shared options-read reference

**Files:**
- Create: `.claude/skills/shared/options-read.md`

**Interfaces:**
- Consumes: `tools/options/implied_move.py` CLI from Task 2.
- Produces: a file path that Tasks 4 and 5 point at:
  `.claude/skills/shared/options-read.md`.

- [ ] **Step 1: Write the reference file**

Create `.claude/skills/shared/options-read.md` containing, in order:

1. A one-paragraph purpose statement: this answers "what move is the market
   pricing," never "what should I buy."
2. **Source selection**, exactly as the spec's "Source selection" section:
   path 1 is `data/options.db` `v_iv_rank` when the ticker is in the 24-symbol
   CBOE catalog AND `n_days >= 60`; path 2 is Robinhood MCP otherwise. Include
   the full catalog list. State that the DB is `data/options.db`, named for the
   registry key. State that as of 2026-07-21 `n_days` was 13, so every ticker
   takes path 2 until roughly mid-September 2026.
3. **The tenor warning** verbatim from the spec: `iv30` is 30-day
   constant-maturity and is never comparable to a single expiry's ATM IV;
   AAPL 2026-07-21 was 29.6% vs 37.5%.
4. **Path 2 procedure**, steps 1–6 from the spec: resolve chain (absent → stop
   and say so); resolve the catalyst *from the thesis*, abstaining when no
   expiry aligns; honour `event_time` (stored as the literal strings `before open` /
   `after close`); resolve "today" as a Phoenix
   date; find ATM quoting with `expiration_dates` AND `strike_price` always;
   apply the scaled liquidity gate.
5. **The exact command** to compute and print the table:

   ```bash
   uv run python -m tools.options.implied_move \
     --call-mark <mark> --put-mark <mark> --spot <spot> \
     --iv <atm_iv_decimal> --dte <calendar_days> \
     [--closes <closes.json>] [--required-move <decimal>]
   ```

   With the sentence: **"Print this table before writing any interpretation.
   Do not paraphrase its numbers; quote them."**
6. **How to read it:** the straddle row is a mean and is exceeded roughly 42% of
   the time — never call it a ceiling. Write "elevated" only when both
   `IV > RV60?` and `IV > RV20?` read YES; on disagreement the disagreement is
   the finding, and neither averaging the windows nor picking one is permitted.
7. **The stopgap label:** path 2 is weakest exactly when most used, because a
   forward IV spanning a scheduled event is compared against trailing windows
   that may contain none. Say in the write-up which path was used.
8. The four uncalibrated constants (10% of mark, 2 ticks, volume 100, OI 25% of
   the expiry's median) flagged as starting values needing one measurement pass.

- [ ] **Step 2: Verify the file is reachable and complete**

Run:

```bash
test -f .claude/skills/shared/options-read.md && \
grep -c "data/options.db" .claude/skills/shared/options-read.md && \
grep -q "not a ceiling" .claude/skills/shared/options-read.md && \
grep -q "tools.options.implied_move" .claude/skills/shared/options-read.md && \
echo "reference OK"
```

Expected: prints a count ≥ 1, then `reference OK`.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/shared/options-read.md
git commit -m "docs(skills): add the shared options-read procedure

Neutral home so kill-thesis does not reach across research-ticker's
private references/ dir. Path 1 is the official CBOE feed in
data/options.db; Robinhood MCP is the coverage-gap fallback."
```

---

### Task 4: kill-thesis — options check, verdict rule, tax lots

**Files:**
- Modify: `.claude/skills/kill-thesis/SKILL.md`

**Interfaces:**
- Consumes: `.claude/skills/shared/options-read.md` (Task 3).
- Produces: no downstream consumer.

- [ ] **Step 1: Add the conditional options check**

Insert a new step after the existing step 4 ("Run the statistical checks"),
numbered 5, renumbering the existing steps 5 and 6 to 6 and 7. It must contain:

- The trigger: run this only when the thesis makes a **dated** claim AND a chain
  exists. Otherwise skip and record why.
- The pointer sentence: **"Use `.claude/skills/shared/options-read.md` for the
  options procedure."** (Without this sentence the reference is never opened.)
- The one-way valve rule, worded:

  > **Options evidence has a one-way valve: it can only cut, never confirm.**
  > Refutation is measured against the 1-sigma move, never the straddle figure.
  > Refute the timing condition only when the thesis needs a move beyond
  > **2 sigma** — roughly a 5% outcome — and state the sigma multiple and the
  > implied probability in the finding. Between 1 and 2 sigma the market is
  > merely less optimistic than the thesis; that is not a refutation and must
  > not be written as one. Mark the condition FLAWED only above the 2-sigma
  > line, and the refutation stops there — it may not spread to undated
  > conditions, because a thesis can be right about the destination and wrong
  > about the calendar. An implied move that matches or exceeds what the thesis
  > requires is NOT evidence for anything. If you catch yourself writing "the
  > options market agrees" without immediately following it with "which is not
  > evidence for the thesis," delete the sentence.

- The coverage disclosure: when the check could not run — no chain, illiquid,
  no aligned expiry, or path 2 stopgap — **say so in the verdict**, because the
  check only fires on liquid names and silent omission makes a thesis look more
  thoroughly vetted than it was.

- [ ] **Step 2: Add the tax-lot read**

Add to the existing "before adding to a losing position" path: pull
`get_equity_tax_lots` for per-lot cost basis and holding period, which the
blended `average_buy_price` in `portfolio.db` hides. Include verbatim from the
sibling skills: pin the **"Agentic" account (number ending 1936)**, stop and
report if no account matches rather than falling back, and **never paste raw
MCP payloads into the conversation** — on error report the exception type name
only.

- [ ] **Step 3: Add the guardrails**

Append to the existing Guardrails section:

- The options/equity fence, as a reply-script rather than a prohibition:

  > **Options data informs the equity thesis only.** It answers "is the market
  > pricing in this catalyst," never "what should I buy." If asked directly —
  > "should I buy the calls?" — reply with one sentence: this skill does not
  > size or recommend options positions; that decision and its risk are the
  > user's alone. Then stop. Do not follow with a strike or expiry "as
  > information" — that is the same violation wearing a hedge.

- The new source tier: **broker/market microstructure**, below primary filings
  and distinct from `stockanalysis.com`.

- [ ] **Step 4: Verify**

Run:

```bash
grep -q "shared/options-read.md" .claude/skills/kill-thesis/SKILL.md && \
grep -q "one-way valve" .claude/skills/kill-thesis/SKILL.md && \
grep -q "2 sigma" .claude/skills/kill-thesis/SKILL.md && \
grep -q "1936" .claude/skills/kill-thesis/SKILL.md && \
echo "kill-thesis OK"
```

Expected: `kill-thesis OK`

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/kill-thesis/SKILL.md
git commit -m "feat(kill-thesis): add the options-market timing check

Refutation is defined at 2 sigma against the 1-sigma move with the
implied probability stated, so a timing claim dies by a probability
statement rather than a vague disagreement. The valve is one-way:
agreement is never evidence for a thesis. Coverage is disclosed when
the check cannot run, so an unattacked thesis does not read as a
survived one."
```

---

### Task 5: research-ticker — EPS surprise, thread pointer, false precision

**Files:**
- Modify: `.claude/skills/research-ticker/SKILL.md`

**Interfaces:**
- Consumes: `.claude/skills/shared/options-read.md` (Task 3).
- Produces: no downstream consumer.

- [ ] **Step 1: Add EPS surprise history to Phase 0**

After the existing `data/earnings.db` bullet, add a bullet: call
`get_earnings_results` for the trailing 8 quarters of estimate vs actual EPS,
and read the **pattern** — chronic beats by a hair indicate managed guidance,
large misses indicate execution risk. State explicitly that this trailing
surprise series is a different thing from `earnings_calendar`'s forward
`eps_est`, which is a scheduling input that happens to share the name.

- [ ] **Step 2: Add the non-optional Phase 2 pointer**

Add one sentence to Phase 2, using the same shape as the existing
`disclosure-hunt.md` pointer:

> **One thread is not optional** — use `.claude/skills/shared/options-read.md`
> and record its finding (or "no listed options / illiquid / path-2 stopgap")
> even when nothing else in Phase 2 flagged it.

Do not add a paragraph of mechanics here; they live in the reference file.

- [ ] **Step 3: Add the Phase 4 false-precision check**

Add to Phase 4, after the reverse-DCF reading guidance:

> **Check the precision of the implied return against the vol.** When ATM IV
> exceeds 50%, quote the implied discount rate to the nearest whole percent and
> say the range is wide; a figure like "13.32%" on a name the options market
> prices at 60% vol is arithmetic, not knowledge. Never widen a conclusion's
> confidence to match a narrow-looking number.

- [ ] **Step 4: Add the Valuation output line**

In the Output section, item 4 (**Valuation**), add: the options-implied move
where available, with the path used (path 1 CBOE `iv30` percentile, or path 2
Robinhood stopgap) and the DTE — or an explicit "no listed options."

- [ ] **Step 5: Add the guardrails and update the description**

Append to Guardrails: the same options/equity reply-script fence from Task 4
Step 3, plus:

> **`get_financials` is banned** — use `data/sec_fundamentals.db` or live
> EDGAR. This is a **provenance** rule, not a freshness rule: SEC filings are
> the audited primary source for financials specifically, and this does not
> reverse Phase 0's live-over-stale preference for price and statistics data.
> **ATR comes from `advisor`**, which derives it from stockanalysis data for
> its stop and `cap_shares` math — do not call Robinhood's technical-indicator
> endpoint and create a second stop distance for the same name.

Update the frontmatter `description`, appending before the closing quote:
`or whether the options market is already pricing in the move a thesis needs.`

- [ ] **Step 6: Verify**

Run:

```bash
grep -q "shared/options-read.md" .claude/skills/research-ticker/SKILL.md && \
grep -q "get_earnings_results" .claude/skills/research-ticker/SKILL.md && \
grep -q "provenance" .claude/skills/research-ticker/SKILL.md && \
head -4 .claude/skills/research-ticker/SKILL.md | grep -q "options market" && \
echo "research-ticker OK"
```

Expected: `research-ticker OK`

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/research-ticker/SKILL.md
git commit -m "feat(research-ticker): add EPS surprise and options context

Phase 0 gains the trailing 8-quarter estimate-vs-actual series, which
earnings_calendar does not store (it holds a forward eps_est for
scheduling only, sharing the name). Phase 2 gains a non-optional
pointer to the shared options procedure. Phase 4 gains a false-
precision guard so a tight implied return on a high-vol name is not
quoted as knowledge.

The get_financials ban is framed as provenance, not freshness, so it
does not contradict the wire-over-warehouse rule in Phase 0."
```

---

### Task 6: journal-sync reconciliation and account-positions note

**Files:**
- Modify: `.claude/skills/journal-sync/SKILL.md`
- Modify: `.claude/skills/account-positions/SKILL.md`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: no downstream consumer.

- [ ] **Step 1: Add the reconciliation step to journal-sync**

Add a numbered Procedure step after the existing step 4 (ingest), before the
reporting step, so it matches the skill's existing shape (every behaviour is a
numbered step with a concrete command). It must specify:

- Call `get_realized_pnl` for the same window as the sync, scoped to the pinned
  Agentic account, and compare against the journal's recorded fills.
- **Read-only. Report the comparison; never auto-write.** The dispatcher write
  boundary is untouched.
- The tolerance model, so it does not cry wolf:
  - *Expected* divergence — T+1 trade-vs-settlement drift at window edges;
    drip/recurring fills that land in `v_freelance` by design; and
    `scorer.realized_return` being a single-lot FIFO-shaped model derived from
    journaled fill prices while the broker computes per actual closed tax lot,
    possibly under a different lot-selection method.
  - *Unexplained* divergence — investigate and report.
- Restate secret hygiene: never paste raw MCP payloads; on error report the
  exception type name only.

- [ ] **Step 2: Add the gradeability tag**

In the JSON document description, note that a `passes[].note` — and the
`decisions.note` free-text field generally — may carry a short tag recording
that the options check fired at decision time, e.g. `iv_elevated_at_entry`.
State why: without it the check can never be graded against
`v_decision_outcomes`, which is what `scorer` exists for. No schema change.

- [ ] **Step 3: Update the journal-sync description**

Update the frontmatter `description`, appending before the closing quote:
`Also use to reconcile fills against broker realized P&L.`

- [ ] **Step 4: Add the account-positions note**

Add one line to the Rules section of `.claude/skills/account-positions/SKILL.md`:

> Tax lots (`get_equity_tax_lots`) are available live and are **deliberately not
> persisted** — this command writes only the blended position snapshot. Read
> them at decision time via `kill-thesis`, not here.

- [ ] **Step 5: Verify**

Run:

```bash
grep -q "get_realized_pnl" .claude/skills/journal-sync/SKILL.md && \
grep -q "iv_elevated_at_entry" .claude/skills/journal-sync/SKILL.md && \
grep -q "v_freelance" .claude/skills/journal-sync/SKILL.md && \
grep -q "deliberately not" .claude/skills/account-positions/SKILL.md && \
head -4 .claude/skills/journal-sync/SKILL.md | grep -q "realized P&L" && \
echo "journal + positions OK"
```

Expected: `journal + positions OK`

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/journal-sync/SKILL.md .claude/skills/account-positions/SKILL.md
git commit -m "feat(journal-sync): reconcile journaled fills against realized P&L

Read-only comparison with an explicit tolerance model, so T+1 drift,
freelance drip/recurring fills, and the FIFO-vs-tax-lot modelling
difference are labelled expected rather than reported as sync bugs.

Adds a decisions.note tag so the options check becomes gradeable
against v_decision_outcomes without a schema change."
```

---

### Task 7: End-to-end verification on a live ticker

**Files:** none modified.

- [ ] **Step 1: Run the full gates**

Run: `uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest -q`
Expected: all clean, 1241 tests passing.

- [ ] **Step 2: Confirm path selection reports honestly**

Run:

```bash
sqlite3 -readonly data/options.db \
  "SELECT underlying, n_days FROM v_iv_rank WHERE underlying='AAPL';"
```

Expected: `n_days` well below 60, confirming the depth gate routes AAPL to
path 2 today. If `n_days >= 60`, path 1 is now live and the skills should use
it — re-read the spec's tenor warning before comparing any numbers.

- [ ] **Step 3: Exercise kill-thesis end to end**

Invoke `kill-thesis` on a two-sentence dated thesis for a liquid ticker, e.g.
*"AAPL re-rates 30% higher within the next month on services margin
expansion."* Confirm the response:
- prints the implied-move table before any interpretation,
- reports the straddle figure as a mean, never a ceiling,
- states the sigma multiple and implied probability,
- discloses that path 2 (stopgap) was used,
- does not suggest an options trade.

Then ask "so should I buy the calls?" and confirm the reply is the single
refusal sentence with no strike or expiry offered.

- [ ] **Step 4: Exercise research-ticker Phase 0**

Invoke `research-ticker` on a liquid ticker and confirm the EPS surprise series
appears with a read of the pattern, and that Phase 2 records an options finding
or an explicit "no listed options / illiquid / path-2 stopgap".

- [ ] **Step 5: Update the plan status and commit**

Mark this plan DONE in `plans/README.md`.

```bash
git add plans/README.md
git commit -m "docs(plans): mark 001 robinhood-mcp-integration DONE"
```

---

## Self-Review

**Spec coverage.** Every spec section maps to a task: shared reference → 3;
source selection, depth gate, tenor warning → 3; path-2 procedure → 3;
corrected move reporting → 1, 2, 3; realized-vol baseline and print-then-
interpret → 1, 2, 3; kill-thesis verdict rule, coverage disclosure, tax lots
→ 4; research-ticker Phase 0/2/4 and output → 5; journal-sync reconciliation and
gradeability tag → 6; account-positions note → 6; all guardrails → 4, 5;
end-to-end verification → 7.

**Deliberately out of scope**, per the spec's Non-goals: the scanner,
watchlists, `get_equity_price_book`, and index quotes are audited but not
integrated. Spec Open Risks 1 (asymmetric-check ratchet), 3 (no prose test
coverage) and 4 (combiners do not read `data/options.db`) are recorded, not
solved.

**Placeholder scan.** No TBD/TODO. All four liquidity constants carry explicit
values and an explicit uncalibrated flag. The 2-sigma threshold, the 60/252
`n_days` gates, and the 50% IV false-precision trigger are all concrete.

**Type consistency.** `expected_absolute_move`, `one_sigma_move`,
`realized_vol`, `refutes_timing` and `main` keep identical signatures across
Tasks 1, 2 and 3. `refutes_timing` returns `(refuted, k_sigmas, probability)`
in that order everywhere. The DB path is `data/options.db` throughout. The
reference path is `.claude/skills/shared/options-read.md` in Tasks 3, 4 and 5.
