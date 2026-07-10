# Design: qualitative stock-research skills

**Date**: 2026-07-09
**Status**: approved, not yet planned

## Why

The repo is quantitative end to end. `composite` votes numeric signals into an
opinion, `scorer` grades those signals against forward returns, `advisor` sizes
positions from ATR and book heat. Every column in every table is a number, a
date, or a flag. The single free-text field in the whole pipeline is
`scorer.db decisions.note`.

Four databases — `sec_fundamentals.db`, `earnings.db`, `options.db`, `ats.db` —
are harvested on a schedule and read by nothing but a staleness check.
`plans/README.md` records that wiring `sec_fundamentals` into `composite` was
considered and **rejected**: it "needs a scoring thesis that does not exist."

This design does not invent that scoring thesis. It adds the consumer those
DBs never had: a qualitative research pass, run by Claude and reviewed by the
human, that reads the collected numbers and does the work no view can do —
establish what a business sells, why customers come to it, what stops a
competitor from copying it, and what the market is currently paying for that.

Source material: a transcript from a former Goldman Sachs research analyst and
buy-side stock analyst, describing his research process in four parts (where to
start, what to look for, crafting a thesis, finding the information).

## What is deliberately NOT built

**Idea sourcing (the transcript's Part 1).** Screeners, 13F copying, Substack
ideas, consumer intuition. `composite.v_flagged` already occupies this stage
and is a stronger version of the screener path the analyst himself rates
lowest. Reimplementing it would add nothing.

**A thesis table.** Theses land in git as markdown. A `theses` table in
`scorer.db` is attractive — it would let us eventually test the transcript's
sharpest empirical claim (via David Deutsch): *the more specific a thesis, the
more likely it is to be wrong*, by tagging each thesis with its count of
load-bearing conditions and grading multi-condition theses against simple ones.
But `decisions` is never pruned, a permanent schema regretted is permanent, and
we have not yet written ten theses to learn which fields we actually reach for.
Defer. Revisit once `research/` holds enough documents to see the shape.

**Any scored signal feeding `composite`.** Qualitative judgment does not become
a vote. The research output is human-facing.

## Artifacts

Three, plus one line of `pyproject.toml`.

### 1. `tools/valuation/reverse_dcf.py` + `tests/test_reverse_dcf.py`

The one part of the transcript that is arithmetic rather than judgment. A
language model doing this by hand produces an unreproducible number; a pure
function produces the same number every time and can be mutation-tested.

This is the repo's first module that is **a tool, not a source**. It has no
network, no database, and no wall clock, so it satisfies every invariant in
CLAUDE.md without following the four-file source shape. It is not registered in
`registry.py` — it is not a data pipeline and dispatch would buy nothing.

`pyproject.toml`'s `[tool.mypy] files` is an explicit list; add `"tools"`.

**Interface**

```python
project_cash_flows(base_fcf: float, growth_rates: Sequence[float]) -> list[float]
implied_discount_rate(
    target_value: float,
    cash_flows: Sequence[float],
    terminal_growth: float,
) -> float | None
```

`target_value` is market cap for levered (equity) cash flows, or market cap
plus `net_debt` for unlevered ones. The caller bridges explicitly; the module
never guesses which kind of cash flow it was handed.

**Method.** Bisection, not Newton-Raphson. Present value is strictly monotone
decreasing in the discount rate `r` across the open interval `(g, 1.0]`: as
`r → g⁺` the terminal term `CF_n · (1 + g) / (r − g)` diverges to `+∞`, and at
`r = 1.0` the discounted sum is near zero. A strictly monotone function with a
bracketed sign change is bisection's unconditionally-convergent case. Newton's
method can overshoot below `g`, where the terminal term flips sign and the
function is meaningless. ~40 iterations reach floating-point precision.

**Refusals.** The rule: **malformed input raises; a well-formed question with no
answer returns `None`.** Never return a plausible-looking number.

Raise `ValueError` — the caller made a mistake:

- `base_fcf <= 0`. The transcript is explicit that a loss-making business is a
  harder analysis, not a DCF input. Passing one is a category error.
- `target_value <= 0`, or an empty `cash_flows`.
- `terminal_growth >= 1.0`. No finite present value exists at any `r`.

Return `None` — the input was valid, the equation has no root in the bracket:

- Present value at `r = 1.0` still exceeds `target_value`, i.e. the market
  prices a return above 100%. Report no-solution-in-bracket. **Never clamp to
  the bracket edge**, which would silently report 100% as though it were a
  solution — the exact class of silent-wrong-answer bug this repo's
  no-silent-row-drops invariant exists to prevent.

**Determinism.** Pure. No `datetime.now()`. Growth rates and horizon are
arguments, never defaults derived from the clock.

### 2. `.claude/skills/research-ticker/`

Entry: any ticker symbol. A `composite` flag is one entry path among several,
not a precondition — the analyst's best ideas came from his own consumer
experience, not a screener.

Reads `data/*.db` **read-only**: `sec_fundamentals.db` (`v_screener` —
`net_margin`, `roe`, `debt_to_equity`, revenue and income history, plus the
`companies` table for the ticker→CIK lookup), `stocks.db`, `earnings.db`, and
`composite.db` when the name was flagged.

**Phases**

0. **Triage / fast kill.** Circle of competence; loss-making; leverage. A hard
   STOP: if the business rests on domain science not yet established
   (biotech efficacy, semiconductor process physics), the skill halts and says
   so. It does not bluff through. This is faithful to the transcript's most
   frequently ignored instruction — "you kind of pause right here" — and will
   occasionally refuse a name the user wanted researched. That is the point.

1. **Business.** Value **created** → **captured** → **protected**, derived from
   first principles. The skill explicitly forbids naming SWOT or Porter's Five
   Forces. A filled-in template is a substitute for thinking, and the transcript
   demonstrates that eBay passes the network-effect checkbox while failing the
   actual question.

2. **Frame and threads.** Enumerate the candidate relevant facts (the "frame
   problem": which facts matter is not given in advance), choose the threads
   worth pulling, and investigate each. **Dead ends are recorded, not deleted.**
   A thread that led nowhere is evidence the work was done — "a lot of times
   they lead nowhere; that means you're doing your job well."

3. **Thesis.** Plain language. A thesis need not be clever; "good business,
   defensible, fairly priced" is a complete thesis. Enumerate the load-bearing
   conditions and **count** them. Each additional condition is additional
   surface area to be wrong.

4. **Valuation.** Call `tools/valuation/reverse_dcf.py`. Report the return the
   market is currently pricing in, given stated assumptions — not a price
   target. Optionally the forward multiple, with the transcript's rule of thumb
   that looking beyond three years is not evidence.

5. **Adversarial.** Hand the thesis to `kill-thesis`.

**Output**: `research/<TICKER>-<YYYY-MM-DD>.md`, committed to git. Git supplies
history and diffs, which is most of what a table would have supplied.

**Bundled reference**: `references/disclosure-hunt.md` encodes the transcript's
Part 4 — the ordered question "does this information exist?", then "can I find
it elsewhere?", then "if not, does its absence kill the thesis?". Specifics
worth encoding: SEC EDGAR and the investor-relations site disclose *different*
things (earnings presentations routinely carry numbers absent from the 10-K);
skim the 10-K first to learn what is disclosed at all before reading closely;
triangulation is legitimate (Copart disclosed market share twice in two decades,
tied to another disclosure to bound it); segment redefinitions across years let
you carve out what a number is *not*; search in the company's local language.

### 3. `.claude/skills/kill-thesis/`

Standalone, by design. Takes a thesis from any source: this skill's own output,
a Substack post, a position held for a year. Reusability is the reason it is not
merely phase 5 of `research-ticker`.

Verdict: **SOUND / FLAWED / UNPROVEN** — the same vocabulary the repo's plan
reviewers already use.

Its moves are concrete, not an instruction to think critically:

- Attack each load-bearing condition **independently**; default to *refuted*
  under uncertainty.
- Check the base rate before crediting a result.
- Ask what the short seller sees that the thesis does not.
- Check management's incentives against the thesis's assumptions about them.
- Apply the statistical traps already recorded in project memory: overlapping
  windows, multiple comparisons, effective `n`, and mechanism-claims presented
  as inference-claims.

**Accepted bias.** Defaulting to *refuted* under uncertainty biases toward
inaction. `scorer`'s `v_human_filter` exists partly to measure whether the
human's filter is already too conservative. This is a known, deliberate
trade-off: a false "SOUND" costs real money; a false "UNPROVEN" costs an
opportunity. Revisit if `v_human_filter` shows the filter suppressing winners.

## Guardrails (both skills)

- **Never place orders.** Decision support only — the `advisor` precedent.
- **Never write to `data/*.db`.** Live state enters the system only through the
  `portfolio` and `journal` dispatchers. Research reads; it does not write.
- **Every factual claim carries a source.** A claim without one becomes an
  explicit `UNKNOWN`, never a confident sentence.
- **Source tiers are labeled.** Official primary sources (SEC EDGAR, company
  filings) first. `stockanalysis.com` is the repo's single vetted exception and
  does not generalize to other aggregators. Reddit, YouTube, and expert-network
  material are labeled low-confidence and never launder into fact.

## Testing

`tests/test_reverse_dcf.py` covers: monotonicity of PV in `r`; a hand-checked
round trip (known `r` → cash flows → recovered `r`); each of the three refusals;
the `r ≤ g` boundary; the `net_debt` bridge; and a mutation check that the
bracket edge is never returned as a solution.

Skills are prose and are not unit-tested. Their correctness gate is the
adversarial review of the first real thesis produced.

## Open questions deferred

- Whether `research/` should live at the repo root or under `docs/research/`.
  Root, for now; it is an output, not documentation.
- Whether a `theses` table eventually lands in `scorer.db`, and what its columns
  are. Answer after ~10 documents exist.
