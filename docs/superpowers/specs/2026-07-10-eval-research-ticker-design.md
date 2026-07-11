# eval-research-ticker — design

**Status:** shipped, GREEN-validated (3/3 fresh no-repo agents) · **Date:** 2026-07-10

## Problem

`research-ticker` produces stock theses, but we have no repeatable way to measure
their quality or to feed what we learn back into the skill. This session did it
by hand for UBER — ran the skill, compared against a professional analyst's
research, scored, found two systemic gaps (stale post-call facts; a single-rate
DCF that can't express margin expansion), TDD-gated the fixes into the skill, and
re-ran to verify. `eval-research-ticker` makes that loop a first-class,
repeatable procedure.

Two failures observed during the manual pass are the reason the skill must exist:
1. The instinct was to **patch the research artifact** (`research/UBER-*.md`)
   rather than improve the system — the user had to redirect.
2. Without a verification step, a wording edit can add words that don't change
   behavior. The manual pass caught one such redundant clause only because it
   micro-tested.

## The skill

**Name:** `eval-research-ticker` · **Trigger:** `/eval-research-ticker <TICKER>`

**One cycle per invocation.** Re-invoke to iterate; the skill never auto-loops.

1. **Fresh run.** Dispatch a fresh-context subagent (Opus) running
   `research-ticker <TICKER>`; it returns the thesis and does **not** write or
   commit `research/<TICKER>.md`.
2. **Benchmark in.** Prompt the user to paste or point to the professional
   research. Benchmark-required; no scoring without it.
3. **Score** against the fixed core rubric (below).
4. **Classify every divergence** (anti-oracle guard, below).
5. **Propose fixes, ask the user.** Present only the fixable gaps plus the
   proposed system change. Wait for approval.
6. **TDD-gate via `writing-skills`.** Each approved edit gets a RED baseline
   micro-test (control vs. treatment, ≥5 reps, scored by hand) proving the
   wording changes behavior, then the edit + commit. No unearned edits.
7. **Verify by fresh re-run.** Dispatch a new fresh-context run, re-score,
   report the score delta. Stop.

## Rubric (fixed core — 7 dimensions)

Score each on the research-ticker output, then compare to the professional:

1. **Verdict convergence** — SOUND / FLAWED / UNPROVEN alignment.
2. **Recency / material-developments coverage** — did it catch events dated
   after the last earnings call?
3. **Financial forensics** — net-income adjustments, FCF quality, float/SBC.
4. **Valuation method** — right FCF↔denominator pairing; margin-lever treatment
   for margin-expansion names; assumptions stated.
5. **Business decomposition** — segments and all revenue lines named concretely.
6. **Load-bearing conditions & falsifiers** — enumerated and counted.
7. **Honest UNKNOWNs** — holes marked, not filled with plausible numbers.

Ticker-specific dimensions may be **added**, never subtracted.

## Divergence classification (anti-oracle guard)

The professional research is **low-confidence tier, never an oracle.** Tag each
divergence:

- `MISS` — research-ticker missed a **verifiable** fact the professional had.
  → the only tag that drives a skill fix.
- `JUDGMENT` — different read of a genuine unknowable. → not a gap.
- `RESEARCH-RIGHT` — the professional was wrong / research-ticker was right.
  → note it, no fix.

## Invariants

- **System, not artifact.** Never edit `research/<TICKER>.md` to close a gap.
  Gaps go back into `research-ticker`, `kill-thesis`, or `tools/`.
- **Professional research is never an oracle.** Divergence ≠ deficiency; only a
  `MISS` on a verifiable fact is a gap.
- **Every fix is TDD-gated** (delegated to `writing-skills`); **every
  verification is a fresh-context re-run** (no context inheritance).

## Delegation

- Research → `research-ticker` (via fresh subagent). Not re-implemented.
- Skill editing → `writing-skills` TDD loop. Not re-implemented.

## Build / test plan

Creating this skill obeys `writing-skills`' Iron Law.
- **RED baseline:** fresh agents, no skill, given a research-ticker output + a
  professional writeup, asked to improve future runs. Expected failures: patch
  the artifact, skip verification, treat the professional as an oracle.
- **GREEN:** with the skill, agents target the system, plan a TDD-gated fix,
  classify divergences, and plan a fresh re-run.

## Out of scope (YAGNI)

- Auto-loop to convergence (one cycle only).
- A no-benchmark mode (benchmark is required).
- Grading skills other than `research-ticker`.
