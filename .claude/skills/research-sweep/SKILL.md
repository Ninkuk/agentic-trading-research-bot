---
name: research-sweep
description: Research every candidate-screen name that has no thesis yet, and re-research every thesis whose dated reopen trigger has come due. Use when the user asks to sweep the research backlog, research everything not yet researched, run the reopens that are due, or catch up on the candidate list. Dispatches research-ticker runs behind a human gate.
---

# research-sweep

Two worklists, one gate, capped waves of `research-ticker`.

**Decision support only.** Never place an order, never recommend a size. This
skill selects and dispatches; every judgement is `research-ticker`'s.

## 1. Build the worklist

```bash
uv run python -m tools.research.worklist
```

**A — un-researched candidates:** names on `main.py candidates` with no
`research/<TICKER>-*.md` of any date. No staleness gate — staleness is what
the reopen convention is for, and `research_nightly.py` already sweeps stale
flagged and held names nightly at 10pm.

**B — due reopens:** the newest verdict line per ticker in
`research/verdicts.log` whose dated `reopen=` has arrived (`<= today`,
Phoenix). Not restricted to the candidates screen — a reopen is
thesis-scoped, and held positions are frequently off-screen. `event:`
triggers never appear here; they are undated by design and grep-only.

The two lists are disjoint by construction: a reopen ticker has a thesis, so
it cannot also be un-researched.

**Empty is the normal result.** If both lists are empty, say so and stop. Do
not manufacture work, do not widen the rules to find something.

## 2. Gate — always, no exceptions

Show the human **every** name, the count, and that each run costs roughly
156k–231k tokens. Wait for an explicit go. Never auto-dispatch.

Above **20 names**, re-confirm once and name the risk: the session
web-search budget is shared and cannot be read from inside a session, so a
long sweep may degrade later runs' search quality. Even then, never truncate
— if the human wants a shorter list they pass `--max N`, which prints what
it dropped.

## 3. Dispatch

**Never more than 2 concurrent `research-ticker` runs.** Four at once burned
the entire session web-search budget and tripped SEC EDGAR into blanket
403s, degrading the very runs they were meant to produce. Waves of 2, always.

Use the strong model. A Sonnet fan-out once returned a **buy** on a name
carrying a $2.04B trade-secret retrial worth 46% of its market cap,
disclosed in a 10-Q filed five days earlier.

**New names** — dispatch `/research-ticker <TICKER>`.

**Reopens** — dispatch `/research-ticker <TICKER>` plus this context:

> This is a REOPEN of `research/<TICKER>-<PRIOR_DATE>.md` (trigger:
> `<slug>`, due `<date>`). Read the prior thesis first. Open the new
> writeup with a §0 that answers the reopen question directly — did the
> trigger condition fire, and what does that do to the thesis? — before the
> standard sections. Follow `research/BR-2026-08-04.md` and
> `research/CHKP-2026-08-03.md` for the shape.

A run that fails to land a thesis is reported; the wave continues.

## 4. Report

One table: ticker, kill-thesis verdict, §1 ownership call, new reopen
trigger. Note any run that failed and why.

Each `research-ticker` run writes its own thesis, appends its own
`verdicts.log` line, and journals its own buy/pass. **This skill never does
those on a run's behalf** — no thesis writing, no ledger appends, no
`journal` dispatch, no commits.

## Guardrails

- Never place an order. Never recommend a size — that is `advisor`'s job.
- Never write to `data/*.db`.
- Never truncate a worklist silently.
- Never exceed 2 concurrent runs.
- An empty sweep is a complete and correct outcome.
