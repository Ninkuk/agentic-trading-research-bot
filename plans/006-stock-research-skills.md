# Qualitative Stock-Research Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the numeric pipeline a qualitative counterpart — a reverse-DCF solver plus two skills that research a business and then try to destroy the resulting thesis.

**Architecture:** One pure-stdlib Python module under a new `tools/` tree (a tool, not a source: no network, no DB, no clock), and two prose skills under `.claude/skills/`. The skills read `data/*.db` read-only and write a markdown thesis to `research/`. Nothing writes to a database; nothing places an order.

**Tech Stack:** Python 3.12 stdlib only (`argparse`, `collections.abc`), `pytest`, `ruff`, `mypy`, `uv`.

Spec: `docs/superpowers/specs/2026-07-09-stock-research-skills-design.md`

## Global Constraints

- **Zero runtime third-party dependencies.** stdlib only. `ruff`/`mypy`/`pytest` are dev-group.
- **Line length 100** (`[tool.ruff] line-length = 100`).
- **Ruff lint selects** `E4,E7,E9,F,I,B,UP,SIM,DTZ`. `DTZ` bans naive datetimes — this module must contain no `datetime` at all.
- **mypy** runs with `check_untyped_defs`, `warn_unused_ignores`, `no_implicit_optional`. Its `files` key is an explicit list and must gain `"tools"`.
- **Determinism:** no wall-clock reads anywhere in `tools/`. Horizon and growth rates are arguments.
- **Never write to `data/*.db`** from a skill. Live state enters only via the `portfolio` / `journal` dispatchers.
- **Never place orders.** Decision support only.
- All four gates must pass before each commit: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, `uv run pytest`. The pre-commit hook runs all four.
- **Code blocks in this plan are written for reading, not to byte-match the formatter.** Run `uv run ruff format` (in place) before the `--check` gate; take its output as canonical and do not hand-fight it.

---

### Task 1: Cash-flow projection

**Files:**
- Create: `tools/__init__.py` (empty)
- Create: `tools/valuation/__init__.py` (empty)
- Create: `tools/valuation/reverse_dcf.py`
- Create: `tests/test_reverse_dcf.py`
- Modify: `pyproject.toml` (`[tool.mypy] files`)

**Interfaces:**
- Consumes: nothing.
- Produces: `project_cash_flows(base_fcf: float, growth_rates: Sequence[float]) -> list[float]`

- [ ] **Step 1: Add `tools` to mypy's file list**

In `pyproject.toml`, change:

```toml
files = ["sources", "main.py", "registry.py", "deploy"]
```

to:

```toml
files = ["sources", "main.py", "registry.py", "deploy", "tools"]
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_reverse_dcf.py`:

```python
import pytest

from tools.valuation.reverse_dcf import project_cash_flows


def test_project_applies_growth_compounding() -> None:
    flows = project_cash_flows(100.0, [0.10, 0.10])
    assert flows == pytest.approx([110.0, 121.0])


def test_project_empty_growth_yields_no_flows() -> None:
    assert project_cash_flows(100.0, []) == []


def test_project_rejects_non_positive_base_fcf() -> None:
    # A loss-making business is a harder analysis, not a DCF input.
    with pytest.raises(ValueError, match="base_fcf"):
        project_cash_flows(0.0, [0.10])
    with pytest.raises(ValueError, match="base_fcf"):
        project_cash_flows(-5.0, [0.10])


def test_project_rejects_total_wipeout_growth() -> None:
    # g <= -1.0 drives the flow to zero or negative; the terminal term is then nonsense.
    with pytest.raises(ValueError, match="growth_rates"):
        project_cash_flows(100.0, [-1.0])
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_reverse_dcf.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools'`

- [ ] **Step 4: Create the package and minimal implementation**

Create empty `tools/__init__.py` and `tools/valuation/__init__.py`.

Create `tools/valuation/reverse_dcf.py`:

```python
"""Reverse DCF: solve for the discount rate a market price already implies.

A multiple is shorthand for a DCF. Rather than guess the "right" multiple, hold
the cash-flow assumptions fixed and ask what rate of return the current market
value is pricing in. A low implied return on optimistic assumptions is a bad
bet; a high implied return on conservative ones is an interesting one.

Pure: no network, no database, no wall clock. Every input is an argument.
"""

from collections.abc import Sequence


def project_cash_flows(base_fcf: float, growth_rates: Sequence[float]) -> list[float]:
    """Compound `base_fcf` forward, one flow per entry in `growth_rates`.

    Raises ValueError on a non-positive base (a loss-making business is not a
    DCF input) or on a growth rate that wipes the flow out entirely.
    """
    if base_fcf <= 0:
        raise ValueError(f"base_fcf must be positive, got {base_fcf}")

    flows: list[float] = []
    cash_flow = base_fcf
    for growth in growth_rates:
        if growth <= -1.0:
            raise ValueError(f"growth_rates entries must exceed -1.0, got {growth}")
        cash_flow *= 1.0 + growth
        flows.append(cash_flow)
    return flows
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_reverse_dcf.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Run all gates**

Run: `uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest`
Expected: all pass; mypy reports one more file than before.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml tools/ tests/test_reverse_dcf.py
git commit -m "feat(valuation): project cash flows for the reverse DCF

First module under tools/ — a tool, not a source: no network, no DB, no
clock, so it satisfies the repo invariants without the four-file shape.
A non-positive base FCF raises rather than returning a number, because a
loss-making business is a different analysis, not a DCF input."
```

---

### Task 2: Present value, and its monotonicity in the discount rate

**Files:**
- Modify: `tools/valuation/reverse_dcf.py`
- Modify: `tests/test_reverse_dcf.py`

**Interfaces:**
- Consumes: `project_cash_flows` from Task 1.
- Produces: `present_value(cash_flows: Sequence[float], rate: float, terminal_growth: float) -> float`

Present value discounts each explicit flow, then adds a Gordon-growth terminal
value `CF_n * (1 + g) / (r - g)` discounted back over `n` periods. It is only
defined for `r > g`; at `r <= g` the terminal term is infinite or negative.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_reverse_dcf.py` (and extend the import line at the top to
`from tools.valuation.reverse_dcf import present_value, project_cash_flows`):

```python
def test_present_value_discounts_a_single_flow_with_terminal() -> None:
    # One flow of 110 at r=10%, g=0%.
    #   explicit: 110 / 1.1                      = 100.0
    #   terminal: (110 * 1.0 / 0.10) / 1.1       = 1000.0
    assert present_value([110.0], 0.10, 0.0) == pytest.approx(1100.0)


def test_present_value_is_strictly_decreasing_in_rate() -> None:
    # This monotonicity is what makes bisection valid. Guard it.
    flows = project_cash_flows(100.0, [0.05] * 5)
    rates = [0.06, 0.08, 0.10, 0.15, 0.30, 0.60, 1.0]
    values = [present_value(flows, r, 0.02) for r in rates]
    assert values == sorted(values, reverse=True)
    assert len({round(v, 9) for v in values}) == len(values)  # strictly, not weakly


def test_present_value_diverges_as_rate_approaches_terminal_growth() -> None:
    flows = project_cash_flows(100.0, [0.0])
    near = present_value(flows, 0.02 + 1e-9, 0.02)
    far = present_value(flows, 0.50, 0.02)
    assert near > 1e9
    assert far < 1e3


def test_present_value_rejects_rate_at_or_below_terminal_growth() -> None:
    with pytest.raises(ValueError, match="rate must exceed terminal_growth"):
        present_value([100.0], 0.02, 0.02)
    with pytest.raises(ValueError, match="rate must exceed terminal_growth"):
        present_value([100.0], 0.01, 0.02)


def test_present_value_rejects_empty_cash_flows() -> None:
    with pytest.raises(ValueError, match="cash_flows"):
        present_value([], 0.10, 0.02)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_reverse_dcf.py -v`
Expected: FAIL — `ImportError: cannot import name 'present_value'`

- [ ] **Step 3: Implement `present_value`**

Append to `tools/valuation/reverse_dcf.py`:

```python
def present_value(
    cash_flows: Sequence[float],
    rate: float,
    terminal_growth: float,
) -> float:
    """Discount `cash_flows` at `rate`, plus a Gordon-growth terminal value.

    Strictly decreasing in `rate` over `(terminal_growth, inf)` — the property
    that makes bisection an unconditionally convergent solver here.
    """
    if not cash_flows:
        raise ValueError("cash_flows must not be empty")
    if rate <= terminal_growth:
        raise ValueError(
            f"rate must exceed terminal_growth for a finite value; "
            f"got rate={rate}, terminal_growth={terminal_growth}"
        )

    value = 0.0
    for period, cash_flow in enumerate(cash_flows, start=1):
        value += cash_flow / (1.0 + rate) ** period

    horizon = len(cash_flows)
    terminal = cash_flows[-1] * (1.0 + terminal_growth) / (rate - terminal_growth)
    value += terminal / (1.0 + rate) ** horizon
    return value
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_reverse_dcf.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Run all gates**

Run: `uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add tools/valuation/reverse_dcf.py tests/test_reverse_dcf.py
git commit -m "feat(valuation): present value with a Gordon terminal

Tested for strict monotonicity in the discount rate, which is the
precondition the bisection solver in the next commit relies on. r <= g
raises rather than returning an infinite or negative terminal value."
```

---

### Task 3: The bisection solver, and its refusals

**Files:**
- Modify: `tools/valuation/reverse_dcf.py`
- Modify: `tests/test_reverse_dcf.py`

**Interfaces:**
- Consumes: `present_value`, `project_cash_flows`.
- Produces:
  - `MAX_RATE: float` (module constant, `1.0`)
  - `implied_discount_rate(target_value: float, cash_flows: Sequence[float], terminal_growth: float) -> float | None`

**The contract, restated from the spec.** Malformed input **raises**. A
well-formed question with no answer in the bracket **returns `None`**. The
solver must never clamp to a bracket edge and report it as a solution.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_reverse_dcf.py` (extend the import to include
`MAX_RATE, implied_discount_rate`):

```python
def test_implied_rate_round_trips_a_known_rate() -> None:
    # Build a target value from a known rate, then recover that rate.
    flows = project_cash_flows(100.0, [0.08, 0.08, 0.08, 0.08, 0.08])
    target = present_value(flows, 0.11, 0.025)
    assert implied_discount_rate(target, flows, 0.025) == pytest.approx(0.11, abs=1e-9)


def test_implied_rate_falls_when_price_rises() -> None:
    # Pay more for the same cash flows, earn less. The whole point of the tool.
    flows = project_cash_flows(100.0, [0.05] * 5)
    cheap = implied_discount_rate(1_000.0, flows, 0.02)
    dear = implied_discount_rate(3_000.0, flows, 0.02)
    assert cheap is not None and dear is not None
    assert cheap > dear


def test_implied_rate_returns_none_when_priced_above_the_bracket() -> None:
    # A market cap so low that even a 100% discount rate overvalues it:
    # no root in (g, 1.0]. Report no-solution, never clamp to 1.0.
    flows = project_cash_flows(100.0, [0.05] * 5)
    result = implied_discount_rate(1.0, flows, 0.02)
    assert result is None


def test_implied_rate_never_returns_the_bracket_edge_as_a_solution() -> None:
    # Mutation guard. An implementation that clamped instead of refusing would
    # return MAX_RATE here, and MAX_RATE is a *valid-looking* rate. Assert on
    # value, never identity: `is not MAX_RATE` is true even when the value is
    # 1.0, so an identity check would pass against the very bug it guards.
    flows = project_cash_flows(100.0, [0.05] * 5)
    result = implied_discount_rate(1.0, flows, 0.02)
    assert result is None, f"clamped to {result} instead of refusing"


def test_implied_rate_stays_strictly_inside_the_bracket_when_solvable() -> None:
    # The other side of the same guard: a solvable input must land strictly
    # between the bounds, never on MAX_RATE.
    flows = project_cash_flows(100.0, [0.05] * 5)
    rate = implied_discount_rate(200.0, flows, 0.02)
    assert rate is not None
    assert 0.02 < rate < MAX_RATE


def test_implied_rate_solution_always_exceeds_terminal_growth() -> None:
    flows = project_cash_flows(100.0, [0.03] * 5)
    rate = implied_discount_rate(8_000.0, flows, 0.025)
    assert rate is not None
    assert rate > 0.025


def test_implied_rate_rejects_non_positive_target_value() -> None:
    flows = project_cash_flows(100.0, [0.05])
    with pytest.raises(ValueError, match="target_value"):
        implied_discount_rate(0.0, flows, 0.02)
    with pytest.raises(ValueError, match="target_value"):
        implied_discount_rate(-100.0, flows, 0.02)


def test_implied_rate_rejects_terminal_growth_at_or_above_max_rate() -> None:
    flows = project_cash_flows(100.0, [0.05])
    with pytest.raises(ValueError, match="terminal_growth"):
        implied_discount_rate(1_000.0, flows, 1.0)


def test_implied_rate_rejects_empty_cash_flows() -> None:
    with pytest.raises(ValueError, match="cash_flows"):
        implied_discount_rate(1_000.0, [], 0.02)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_reverse_dcf.py -v`
Expected: FAIL — `ImportError: cannot import name 'MAX_RATE'`

- [ ] **Step 3: Implement the solver**

Insert the constants directly after the `from collections.abc import Sequence`
import in `tools/valuation/reverse_dcf.py`:

```python
MAX_RATE = 1.0
"""Top of the search bracket. A 100%/yr implied return needs no more precision."""

_BRACKET_EPSILON = 1e-9
"""Nudge above terminal_growth, where present value diverges."""

_ITERATIONS = 200
"""Bisection halves the bracket each pass; 200 is far past float64 precision."""
```

Append the solver:

```python
def implied_discount_rate(
    target_value: float,
    cash_flows: Sequence[float],
    terminal_growth: float,
) -> float | None:
    """Solve for the discount rate at which `cash_flows` are worth `target_value`.

    `target_value` is the market capitalisation for levered (equity) cash flows,
    or enterprise value for unlevered ones. The caller bridges; this function
    never guesses which kind of cash flow it was handed.

    Returns the implied rate, or None when no rate in `(terminal_growth, MAX_RATE]`
    prices the flows at `target_value` — i.e. the market implies a return above
    MAX_RATE. Returning None rather than clamping to MAX_RATE is deliberate: a
    clamped edge is a wrong answer wearing the costume of a right one.

    Raises ValueError on malformed input.
    """
    if not cash_flows:
        raise ValueError("cash_flows must not be empty")
    if target_value <= 0:
        raise ValueError(f"target_value must be positive, got {target_value}")
    if terminal_growth >= MAX_RATE:
        raise ValueError(
            f"terminal_growth must be below MAX_RATE={MAX_RATE}, got {terminal_growth}"
        )

    low = terminal_growth + _BRACKET_EPSILON
    high = MAX_RATE

    # present_value is strictly decreasing in rate, so a root exists in
    # [low, high] iff pv(high) <= target <= pv(low).
    if present_value(cash_flows, high, terminal_growth) > target_value:
        return None
    if present_value(cash_flows, low, terminal_growth) < target_value:
        return None

    for _ in range(_ITERATIONS):
        midpoint = (low + high) / 2.0
        if present_value(cash_flows, midpoint, terminal_growth) > target_value:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2.0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_reverse_dcf.py -v`
Expected: PASS (18 passed)

- [ ] **Step 5: Run all gates**

Run: `uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add tools/valuation/reverse_dcf.py tests/test_reverse_dcf.py
git commit -m "feat(valuation): bisection solver for the implied discount rate

Bisection, not Newton: present value is strictly monotone in r over
(g, MAX_RATE], so a bracketed sign change converges unconditionally,
while Newton can overshoot below g where the terminal term flips sign.

No root in the bracket returns None. It never clamps to MAX_RATE — a
clamped edge is a wrong answer wearing the costume of a right one, the
same failure class as the plan-000 ledger off-by-one."
```

---

### Task 4: Enterprise-value bridge and the CLI

**Files:**
- Modify: `tools/valuation/reverse_dcf.py`
- Modify: `tests/test_reverse_dcf.py`

**Interfaces:**
- Consumes: `implied_discount_rate`, `project_cash_flows`.
- Produces:
  - `enterprise_value(market_cap: float, net_debt: float = 0.0) -> float`
  - `main(argv: Sequence[str] | None = None) -> int`

The skill invokes this as
`uv run python -m tools.valuation.reverse_dcf --market-cap … --base-fcf … --growth … --terminal-growth …`.
It is **not** registered in `registry.py`: it is not a data pipeline and
dispatch would buy nothing.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_reverse_dcf.py` (extend the import to include
`enterprise_value, main`):

```python
def test_enterprise_value_bridges_net_debt() -> None:
    assert enterprise_value(1_000.0, 250.0) == pytest.approx(1_250.0)
    assert enterprise_value(1_000.0, -100.0) == pytest.approx(900.0)  # net cash
    assert enterprise_value(1_000.0) == pytest.approx(1_000.0)


def test_main_prints_the_implied_rate(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        [
            "--market-cap", "1000",
            "--base-fcf", "100",
            "--growth", "0.05", "0.05", "0.05",
            "--terminal-growth", "0.02",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "implied_discount_rate" in out


def test_main_reports_no_solution_without_pretending(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(
        [
            "--market-cap", "1",
            "--base-fcf", "100",
            "--growth", "0.05", "0.05", "0.05",
            "--terminal-growth", "0.02",
        ]
    )
    assert code == 1
    out = capsys.readouterr().out
    assert "no solution" in out.lower()
    # It must not also print a rate. A clamping CLI would emit both.
    assert "implied_discount_rate" not in out


def test_main_reports_a_refusal_without_a_traceback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(
        [
            "--market-cap", "1000",
            "--base-fcf", "-5",
            "--growth", "0.05",
            "--terminal-growth", "0.02",
        ]
    )
    assert code == 2
    assert "base_fcf" in capsys.readouterr().err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_reverse_dcf.py -v`
Expected: FAIL — `ImportError: cannot import name 'enterprise_value'`

- [ ] **Step 3: Implement the bridge and the CLI**

Add `import argparse` and `import sys` above the `collections.abc` import in
`tools/valuation/reverse_dcf.py`, then append:

```python
def enterprise_value(market_cap: float, net_debt: float = 0.0) -> float:
    """Bridge equity value to enterprise value.

    Pair unlevered (firm) cash flows with this; pair levered (equity) cash flows
    with `market_cap` alone. Mixing the two is the classic silent DCF error, so
    the caller states the bridge explicitly rather than the solver assuming it.
    """
    return market_cap + net_debt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reverse_dcf",
        description="Solve for the annual return a market price already implies.",
    )
    parser.add_argument("--market-cap", type=float, required=True)
    parser.add_argument("--net-debt", type=float, default=0.0,
                        help="Positive for net debt, negative for net cash. "
                             "Supply only when --base-fcf is unlevered.")
    parser.add_argument("--base-fcf", type=float, required=True,
                        help="Trailing free cash flow. Must be positive.")
    parser.add_argument("--growth", type=float, nargs="+", required=True,
                        help="One growth rate per explicit forecast year, e.g. 0.08 0.06 0.04")
    parser.add_argument("--terminal-growth", type=float, required=True)
    args = parser.parse_args(argv)

    try:
        flows = project_cash_flows(args.base_fcf, args.growth)
        target = enterprise_value(args.market_cap, args.net_debt)
        rate = implied_discount_rate(target, flows, args.terminal_growth)
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2

    if rate is None:
        print(
            f"no solution in ({args.terminal_growth}, {MAX_RATE}] — "
            f"the price implies a return above {MAX_RATE:.0%}"
        )
        return 1

    print(f"implied_discount_rate: {rate:.4f}  ({rate:.2%} per year)")
    print(f"horizon_years: {len(flows)}  terminal_growth: {args.terminal_growth:.2%}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_reverse_dcf.py -v`
Expected: PASS (22 passed)

- [ ] **Step 5: Verify the CLI by hand**

Run:

```bash
uv run python -m tools.valuation.reverse_dcf \
  --market-cap 1000 --base-fcf 100 --growth 0.05 0.05 0.05 --terminal-growth 0.02
```

Expected: a line beginning `implied_discount_rate:` reading `0.1304  (13.04% per year)`.

- [ ] **Step 6: Run all gates, then commit**

Run: `uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest`

```bash
git add tools/valuation/reverse_dcf.py tests/test_reverse_dcf.py
git commit -m "feat(valuation): EV bridge and a CLI for the reverse DCF

Levered flows pair with market cap, unlevered with enterprise value.
The caller states the bridge; the solver never infers which kind of cash
flow it holds, because silently mixing the two is the classic DCF error.

Exit codes: 0 solved, 1 no solution in bracket, 2 refused input."
```

---

### Task 5: The `kill-thesis` skill

**Files:**
- Create: `.claude/skills/kill-thesis/SKILL.md`

**Interfaces:**
- Consumes: nothing (standalone by design — it must run against a thesis from any source).
- Produces: a verdict vocabulary — `SOUND` / `FLAWED` / `UNPROVEN` — reused by `research-ticker`'s phase 5.

- [ ] **Step 1: Write the skill**

Create `.claude/skills/kill-thesis/SKILL.md`:

```markdown
---
name: kill-thesis
description: Adversarially attack an investment thesis and return a SOUND / FLAWED / UNPROVEN verdict. Use when the user wants a thesis stress-tested, asks "what am I missing", shares a thesis from Substack/Twitter, or after research-ticker drafts one. Also use before adding to a losing position.
---

# kill-thesis

Come at this from the position that you want to **destroy the investment**.
A thesis that survives an honest attempt to kill it is worth something. A
thesis that was never attacked is worth nothing, however well written.

You are not the author's ally here. Do not soften. The author asked for this.

## Inputs

A thesis: a `research/*.md` file, a pasted argument, a Substack post, or a
position the user already holds. If the user gives you only a ticker and a
direction ("I'm long X"), ask them to state the thesis in two sentences first
— you cannot attack a claim nobody has made.

## Procedure

1. **Enumerate the load-bearing conditions.** Restate the thesis as a numbered
   list of claims that must *each* be true for it to pay off. If the author
   did not enumerate them, do it for them, and show the list before attacking
   — a thesis often dies right here, when its author sees it has six legs.

   Count them. **More conditions means more surface area to be wrong.** A
   thesis resting on one condition ("this is a good business at a fair price")
   is far more likely to be right than one resting on five, even when every
   step of the five sounds clever. Say the count out loud in the verdict.

2. **Attack each condition independently.** For each, spend real effort trying
   to make it false. Under genuine uncertainty, **default to refuted** — say
   the condition is unsupported, not that it is probably fine. (Known bias:
   this pushes toward inaction. Accepted deliberately — a false SOUND costs
   money, a false UNPROVEN costs an opportunity.)

3. **Run the standing checks.** Every thesis gets all of these:

   - **Base rate.** What normally happens to companies in this position?
     Rapidly extended credit to borrowers with no history usually ends badly.
     Turnarounds usually don't. Say the base rate before crediting the story.
   - **The short case.** What does someone short this stock see? Not a
     strawman — the strongest version. If you cannot construct one, you do
     not understand the business well enough to be long it.
   - **Management incentives.** What is management compensated on, and does
     the thesis quietly assume they will act against that incentive?
   - **Disconfirming search.** Go looking for evidence *against*, not for.
     A search that only returns support was a search for support.
   - **Is the moat a checkbox or a mechanism?** "It has a network effect" is
     a label. *What specifically stops a competitor tomorrow?* eBay passes the
     network-effect checkbox and fails the question.

4. **Run the statistical checks** whenever a claim rests on data — a backtest,
   a hit rate, a screen, a signal from this repo:

   - **Base rate is not 0.5.** Equities drift up. "It rose 60% of the time"
     may be worse than doing nothing. Compare against the benchmark, never
     against a coin.
   - **Overlapping windows.** Forward returns sampled daily over 20-day
     windows are ~20x less independent than they look.
   - **Multiple comparisons.** Testing 48 signals uncorrected guarantees
     "significant" ones.
   - **Effective n.** Not the row count.
   - **Mechanism claims are not inference claims.** "The API returns column
     X" is verifiable. "X predicts returns" is an inference and needs a null.

5. **Ask what would change the author's mind**, and whether it is observable.
   A thesis with no falsifier is not a thesis. If the author cannot name the
   evidence that would make them sell, they have a position, not an argument.

6. **Missing information is a finding.** When a load-bearing number does not
   exist in any disclosure, do not assume a value. State it as UNKNOWN and
   answer: *does its absence kill the thesis?* Sometimes the honest verdict is
   "I can't know this," and that is a complete and useful answer.

## Verdict

Close with exactly one, matching the vocabulary this repo's plan reviewers use:

- **SOUND** — every load-bearing condition survived a real attack. Say which
  attack came closest to landing.
- **FLAWED** — at least one load-bearing condition is refuted. Name it, show
  the evidence, and say whether the thesis is repairable or dead.
- **UNPROVEN** — no condition was refuted, but at least one could not be
  checked. Name what is missing and where it would have to come from. This is
  a real verdict, not a failure to reach one.

Then state, in one sentence, what evidence would flip your verdict.

## Guardrails

- **Never place an order** and never recommend a position size. Decision
  support only.
- **Never write to `data/*.db`.** Read-only, always.
- **Cite every factual claim.** A claim without a source becomes an explicit
  UNKNOWN, never a confident sentence.
- **Label source tiers.** SEC filings and company disclosures are primary.
  `stockanalysis.com` is this repo's one vetted exception and does not
  generalise. Reddit, YouTube, and expert-network colour are labelled
  low-confidence and never launder into fact.
- **Do not be agreeable.** If the thesis is good, the verdict is SOUND — but
  arrive there by failing to kill it, not by declining to swing.
```

- [ ] **Step 2: Verify the skill is discoverable**

Run: `uv run pytest` (unchanged, still passes — skills are prose, not tested)
Then confirm the frontmatter parses: the file must begin with `---`, contain
`name:` and `description:` keys, and close with `---`.

Run: `head -4 .claude/skills/kill-thesis/SKILL.md`
Expected: the three frontmatter lines plus the closing `---`.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/kill-thesis/
git commit -m "feat(skills): kill-thesis, an adversarial pass over any thesis

Standalone rather than a phase of research-ticker, so it can be aimed at
a thesis from Substack or at a position held for a year. Verdicts reuse
the plan-reviewer vocabulary: SOUND / FLAWED / UNPROVEN.

Defaults to refuted under uncertainty. That biases toward inaction, which
is a known and accepted trade: a false SOUND costs money, a false UNPROVEN
costs an opportunity. Revisit if v_human_filter shows the filter is
suppressing winners."
```

---

### Task 6: The `research-ticker` skill and its disclosure reference

**Files:**
- Create: `.claude/skills/research-ticker/SKILL.md`
- Create: `.claude/skills/research-ticker/references/disclosure-hunt.md`
- Create: `research/README.md`

**Interfaces:**
- Consumes: `tools/valuation/reverse_dcf.py` CLI (Task 4); the `kill-thesis` skill (Task 5).
- Produces: `research/<TICKER>-<YYYY-MM-DD>.md`.

- [ ] **Step 1: Create the output directory with a README**

Create `research/README.md`:

```markdown
# research/

One markdown thesis per ticker per research session, written by the
`research-ticker` skill and reviewed by a human:
`research/<TICKER>-<YYYY-MM-DD>.md`.

These are **decision support, not decisions**, and not a data source. Nothing
in `sources/` reads this directory. Git supplies the history and the diffs.

A `theses` table in `scorer.db` is deliberately deferred until enough
documents exist here to show which fields are actually reached for — see
`docs/superpowers/specs/2026-07-09-stock-research-skills-design.md`.
```

- [ ] **Step 2: Write the disclosure-hunt reference**

Create `.claude/skills/research-ticker/references/disclosure-hunt.md`:

```markdown
# Finding the number

Three questions, in order. Do not skip to the third.

## 1. Does this information exist?

Skim the 10-K **before** reading it closely. The first pass is not for
understanding the business — it is for learning what the company discloses at
all: segments, geographies, the shape of the revenue split. You cannot know
what is missing until you know what is there.

Then, in order:

- **SEC EDGAR** (`https://www.sec.gov/cgi-bin/browse-edgar`) — 10-K, 10-Q, 8-K,
  DEF 14A (compensation, and therefore incentives), S-1 for recent listings.
  This repo's `sec_fundamentals.db` `companies` table maps ticker to CIK.
  Respect the shared 9 req/s SEC rate limit; a descriptive User-Agent is
  mandatory or you get a 403.
- **The investor-relations site.** Critically, IR and EDGAR **disclose
  different things**. Earnings *presentations* and *press releases* routinely
  carry segment numbers, unit economics, and cohort charts that appear in no
  10-K. Check all of them; assume neither is a superset.
- **Investor days**, when they exist. The single best document for how
  management frames the business — the transcript and the deck both.
- **Earnings-call transcripts.** For a deep look, read many years. The point
  is not the quarter; it is learning what management has and has not ever said.

## 2. If it isn't disclosed, can it be triangulated or found elsewhere?

- **Triangulate.** A number disclosed once, long ago, can be tied to a number
  disclosed regularly. Copart named its market share exactly twice, in 2003 and
  2004, and never again — but cross-tied to a still-reported disclosure, it
  bounds the answer today. Old disclosures do not expire.
- **Segment redefinitions** let you carve out what a number is *not*. When a
  company merges or splits segments, the overlap year prints both.
- **Search in the local language** for a foreign issuer. Korean sources on a
  Korean retailer say things the English ones don't.
- **The Wayback Machine** for pages, guidance, and pricing that were quietly
  removed.
- **Low-confidence, clearly labelled:** Reddit, YouTube reviews, LinkedIn,
  X/Substack write-ups, expert networks. Google does not index the walled
  gardens; search them directly. **None of this ever becomes a fact.** It is
  colour that tells you where to look next, and it is labelled as such in
  the write-up, every time.

## 3. If it cannot be found — does its absence kill the thesis?

This is the question that matters, and the one most often skipped.

Bound it. "Adobe's enterprise revenue is somewhere between 20% and 50%" is a
real finding, and if the thesis needs it to be above 45%, the thesis is
UNPROVEN and you should say so.

Never fill the hole with a plausible number. Write **UNKNOWN**, state what
would resolve it, and say plainly whether you can proceed without it.
Sometimes the right answer is: *I don't know how I feel about this one.*
There are other companies. Go back to the list.
```

- [ ] **Step 3: Write the main skill**

Create `.claude/skills/research-ticker/SKILL.md`:

```markdown
---
name: research-ticker
description: Research a stock end-to-end — business, moat, thesis, reverse-DCF valuation, adversarial review — and write a thesis to research/<TICKER>-<DATE>.md. Use when the user asks to research/analyse/dig into a ticker, wants a thesis on a name, or asks whether a composite-flagged ticker is actually worth owning.
---

# research-ticker

Qualitative research to complement the numeric pipeline. `composite` can tell
you a name scores +6 across nine signals. It cannot tell you what the company
sells, why customers come back, or what stops a competitor from copying it.
That is this skill's job.

**Decision support only.** Never place an order, never recommend a size.
Read `data/*.db` **read-only**; live state enters the system only through the
`portfolio` and `journal` dispatchers.

Entry is **any ticker**. A `composite` flag is one path in, not a requirement —
the best ideas often come from noticing a product you use, not from a screen.

## Phase 0 — Triage, and the fast kill

The goal of this phase is to **kick the stock out quickly**. Most research
should end here.

Read, read-only:

- `data/sec_fundamentals.db` — `v_screener` for `net_margin`, `roe`,
  `debt_to_equity`, revenue and income history; `companies` for ticker→CIK.
- `data/stocks.db` — price and market-cap metrics.
- `data/earnings.db` — next report date (do not research into an earnings print
  and pretend the timing is irrelevant).
- `data/composite.db` — if the name was flagged, read `ticker_scores` and
  `signal_values` so you know what the machine already thinks and why.

Kill it now if:

- **Persistently loss-making.** Not disqualifying, but it is a genuinely harder
  analysis and a bad place to start. Say so, and ask the user whether to go on.
- **Heavy leverage** relative to its cash generation.

**STOP CLAUSE — this one is not optional.** If the business rests on domain
science you have not established — biotech efficacy, semiconductor process
physics, a novel chemistry — **stop and say so**. Do not proceed and do not
bluff. The right next step is to go learn the domain, not to write a thesis
whose foundations are decorative. Tell the user plainly:

> I can't research this responsibly without understanding <domain> first.
> Everything downstream would be confidence without competence.

Then offer to research the domain instead, or a different name.

## Phase 1 — What is the business?

From first principles. **Do not name SWOT, Porter's Five Forces, or any
framework.** A filled-in template substitutes for thinking: "eBay has a network
effect" ticks the box and gets the answer wrong.

Answer three questions, in this order:

1. **How does it create value?** What does the customer actually get, and why
   do they come here rather than anywhere else? What preferences are being
   satisfied — price, speed, convenience, trust, status? When a customer gets
   more than they pay for, that surplus is usually a good sign.
2. **How does it capture value?** Not "advertising" — *how, specifically*.
   Amazon does not take "a commission": it takes a different commission per
   category, plus logistics fees, plus advertising fees. That is three
   businesses. Unpack until the mechanism is concrete.
3. **How does it protect value?** What stops a competitor doing this tomorrow?
   Ask it as a mechanism, never as a label. **If there is no good answer, that
   silence is itself the answer** — write it down.

## Phase 2 — The frame problem, and pulling threads

You cannot know in advance which facts are relevant. Nobody hands you the list.

- Enumerate the candidate relevant facts you have collected. Say which look
  load-bearing and which look decorative.
- Pick the threads worth pulling: the things that set off an alarm. *"Credit
  card issuance is accelerating into a population with no credit history"* is
  a thread. Go investigate it — check delinquencies, provisioning, underwriting
  commentary, the competitive environment.
- **Record the dead ends.** A thread that led nowhere is evidence the work was
  done, not clutter to delete. Most threads lead nowhere. That is the job
  going well.

Use `references/disclosure-hunt.md` for *where to look*. Its three questions,
in order: does the information exist; can it be triangulated or found
elsewhere; and if not, does its absence kill the thesis?

## Phase 3 — The thesis

Write it in plain language. **It does not need to be clever.** "This is a good
business, it is defensible, the price is fair, and management is unlikely to
destroy the cash flow" is a complete thesis. The elaborate, specific,
impressive-sounding thesis — a bottleneck migrating from GPUs to memory,
therefore margins of 65% — is *more likely to be wrong*, because every added
specific is another thing that has to go right.

Then, explicitly:

- **Enumerate the load-bearing conditions and count them.** Print the count.
- **Name the falsifiers.** What observable evidence would make you sell? A
  thesis with no falsifier is a position, not an argument.
- **Mark every UNKNOWN.** Never fill a hole with a plausible number.

## Phase 4 — What return is already priced in?

Do not guess the "right" multiple. A multiple is shorthand for a DCF. Instead,
hold the assumptions fixed and solve for the return the market already implies:

```bash
uv run python -m tools.valuation.reverse_dcf \
  --market-cap <mkt cap> --base-fcf <trailing FCF> \
  --growth 0.08 0.06 0.04 --terminal-growth 0.025
```

Levered (equity) free cash flow pairs with market cap. Unlevered (firm) cash
flow pairs with enterprise value — pass `--net-debt`. Mixing them is the
classic silent DCF error.

Read the output honestly:

- A **low** implied return on **optimistic** assumptions is a bad bet.
- A **high** implied return on **conservative** assumptions is interesting.
- `no solution` (exit 1) means the price implies a return above 100%/yr. That
  is information, not an error.
- `refused` (exit 2) means the input was a category error — usually a
  loss-making base FCF. Go back to Phase 0.

State the assumptions in the write-up. The number is worthless without them.
If you also quote a forward multiple, do not look out more than ~3 years —
beyond that it is not evidence.

## Phase 5 — Try to destroy it

Invoke the **kill-thesis** skill on what you just wrote. Do not skip this
because the thesis is yours; skip it and the whole document is unearned.

Record the verdict — SOUND / FLAWED / UNPROVEN — in the write-up, along with
the attack that came closest to landing.

## Output

Write `research/<TICKER>-<YYYY-MM-DD>.md` with these sections, then commit it:

1. **Verdict and thesis** — the conclusion first, in two sentences, with the
   kill-thesis verdict and the load-bearing condition count.
2. **Business** — created / captured / protected.
3. **Threads pulled** — including the dead ends, and what they ruled out.
4. **Valuation** — the implied return, and every assumption behind it.
5. **Falsifiers** — what would make you sell.
6. **UNKNOWNs** — what could not be found, where it would come from, and
   whether its absence kills the thesis.
7. **Sources** — every claim, tiered: primary filings; `stockanalysis.com`
   (this repo's one vetted exception); low-confidence colour.

## Guardrails

- **Never place an order.** Never recommend a position size — that is
  `advisor`'s job, from ATR and book heat, not from prose.
- **Never write to `data/*.db`.**
- **Every factual claim carries a source.** Unsourced becomes an explicit
  UNKNOWN, never a confident sentence.
- **Official primary sources first.** `stockanalysis.com` is the single vetted
  exception and does not generalise to other aggregators. Reddit, YouTube, and
  expert-network material are labelled low-confidence, always.
- **It is a complete and respectable outcome to say "I don't know how I feel
  about this one."** There are other companies. Go back to the list.
```

- [ ] **Step 4: Verify**

Run: `uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest`
Expected: all pass — no Python changed, gates confirm nothing regressed.

Run: `head -4 .claude/skills/research-ticker/SKILL.md`
Expected: valid frontmatter with `name:` and `description:`.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/research-ticker/ research/README.md
git commit -m "feat(skills): research-ticker, the qualitative counterpart

composite can say a name scores +6 across nine signals. It cannot say what
the company sells or what stops a competitor copying it. Six phases:
triage, business (create/capture/protect), threads, thesis, reverse DCF,
adversarial review — output to research/<TICKER>-<DATE>.md.

Finally gives sec_fundamentals.db, stocks.db and earnings.db a reader:
they have been harvested on a schedule and consumed by nothing but a
staleness check.

Phase 0 carries a hard STOP: a business resting on domain science we have
not established gets refused, not bluffed through."
```

---

### Task 7: Index the plan and document the tools tree

**Files:**
- Modify: `plans/README.md` (status table + a "What happened" note)
- Modify: `CLAUDE.md` (file tree, commands)

**Interfaces:**
- Consumes: everything above.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Add the row to `plans/README.md`**

Add to the status table:

```markdown
| 006 | [Qualitative stock-research skills](006-stock-research-skills.md) | P2 | M | — | **DONE** |
```

- [ ] **Step 2: Update `CLAUDE.md`**

In the **File tree** section, after the `sources/` tree, add:

```markdown
`tools/` holds code that is neither a source nor a dispatcher — pure helpers with no
network, no DB, and no clock. Today: `tools/valuation/reverse_dcf.py`, the bisection
solver behind the `research-ticker` skill. Not registered in `registry.py`; it is not
a data pipeline.
```

In the **Commands** section, after the test commands, add:

```bash
# Reverse DCF: what annual return does today's price already imply?
uv run python -m tools.valuation.reverse_dcf \
  --market-cap 1000 --base-fcf 100 --growth 0.05 0.05 0.05 --terminal-growth 0.02
# exit 0 solved · 1 no solution in (g, 1.0] · 2 refused input
```

Add a line to the **Workflow** section noting that `research/` holds
`research-ticker` output and is read by nothing in `sources/`.

- [ ] **Step 3: Run all gates**

Run: `uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest`
Expected: all pass. Confirm the test count rose by 22 from the pre-plan baseline
of 1151 → **1173**.

- [ ] **Step 4: Commit**

```bash
git add plans/README.md CLAUDE.md
git commit -m "docs: index plan 006 and document the tools/ tree

tools/ is the repo's first code that is neither a source nor a dispatcher:
no network, no DB, no clock, so it keeps every invariant without following
the four-file shape."
```

---

## Verification

After Task 7, from a clean tree:

```bash
uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest
uv run python -m tools.valuation.reverse_dcf \
  --market-cap 1000 --base-fcf 100 --growth 0.05 0.05 0.05 --terminal-growth 0.02
```

Expected: four green gates, 1173 tests, and an implied rate of 13.04%.

Then the real gate, which no test can supply: run `research-ticker` against one
ticker you already hold and one you passed on, and read the two documents. If
the thesis for the name you hold does not survive `kill-thesis`, that is the
system working.
