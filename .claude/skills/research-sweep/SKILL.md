---
name: research-sweep
description: Research every candidate-screen name that has no thesis yet, and re-research every thesis whose dated reopen trigger has come due. Also lists open event-type reopen triggers and, on request, verifies them (thesis read, then quotes, then earnings, then at most one search each) and dispatches the fired ones. Use when the user asks to sweep the research backlog, research everything not yet researched, run the reopens that are due, check whether event triggers fired, or catch up on the candidate list. Dispatches research-ticker runs behind a human gate.
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
flagged and held names nightly at 10pm. The header names the stocks.db
snapshot date and its age — the screener does not run at weekends, so a
Sunday sweep is reading Friday's list.

**B — due reopens:** the newest verdict line per ticker in
`research/verdicts.log` whose dated `reopen=` has arrived (`<= today`,
Phoenix). Not restricted to the candidates screen — a reopen is
thesis-scoped, and held positions are frequently off-screen.

**C — open event triggers:** every `reopen=event:` on a newest verdict line.
Undated by design: the CLI can list them but never decide them. They are a
verification worklist, not a dispatch list — see §1.5. Only run §1.5 when
the human asked for it ("check the event triggers", "which reopens fired")
or when A and B are empty and the human wants more; a routine sweep reports
the C count and stops.

The lists are disjoint by construction: a reopen ticker has a thesis, so it
cannot also be un-researched.

**Empty is the normal result.** If A and B are empty, say so and stop
(reporting C's count). Do not manufacture work, do not widen the rules to
find something.

## 1.5 Verify event triggers — cheapest evidence first

The goal is to spend near-zero search budget proving a trigger did NOT fire.
Escalate only while a cheaper tier leaves it plausibly fired:

1. **Read the thesis falsifier section first (free).** The slug compresses
   it; the thesis defines it. Decode multi-quarter conditions ("two
   consecutive quarters of organic growth") and compute the earliest report
   date that could satisfy them — a trigger that cannot yet have fired needs
   no further checking. Note that earliest date in the report.
2. **Price legs (one batched call).** Robinhood `get_equity_quotes` for every
   name with a price leg, one call. A quote far from the level closes that
   leg.
3. **Quarterly-report legs.** `get_earnings_results` says whether the awaited
   report is out. Not out → not fired; out → the report itself is the
   evidence to read.
4. **Discrete news legs (at most ONE web search per name).** Only for
   triggers still plausibly fired after tiers 1–3. The search budget is
   shared with the `research-ticker` runs this sweep exists to dispatch —
   burning it on verification degrades them.

A trigger is **fired** only when the thesis's own stated condition is met by
verifiable evidence — a headline that rhymes with the slug is not enough.
Fired triggers join the §2 gate as reopens (cite the evidence in the
dispatch context). Everything else is reported with the blocking fact and
stays open. All-open-none-fired is the normal result.

**An `!` line is not empty — it is blind.** Any `!` (or the `INCOMPLETE`
verdict) means a source could not be read: stop and report what failed. A
failed overnight `stocks` run yields zero candidates, which is not the same
fact as an empty backlog.

## 2. Gate — always, no exceptions

Show the human **every** name, the count, and that each run costs roughly
156k–231k tokens. Wait for an explicit go. Never auto-dispatch.

When the CLI prints its own `LARGE SWEEP` warning — above
`worklist.SWEEP_LARGE` names, which owns the threshold — re-confirm once and
name the risk: the session web-search budget is shared and cannot be read
from inside a session, so a long sweep may degrade later runs' search
quality. Even then, never truncate — if the human wants a shorter list they
pass `--max N` (at least 1), which prints what it dropped.

## 3. Dispatch

**Never more than 2 concurrent `research-ticker` runs.** Four at once burned
the entire session web-search budget and tripped SEC EDGAR into blanket
403s, degrading the very runs they were meant to produce. Waves of 2, always.

Use the strong model. A Sonnet fan-out once returned a **buy** on a name
carrying a $2.04B trade-secret retrial worth 46% of its market cap,
disclosed in a 10-Q filed five days earlier.

**New names** — dispatch `/research-ticker <TICKER>`.

**Reopens** — dispatch `/research-ticker <TICKER>` plus this context (for a
fired event trigger, replace `due <date>` with the evidence that fired it):

> This is a REOPEN of `research/<TICKER>-<PRIOR_DATE>.md` (trigger:
> `<slug>`, due `<date>`). Read the prior thesis first. Open the new
> writeup with a §0 that answers the reopen question directly — did the
> trigger condition fire, and what does that do to the thesis? — before the
> standard sections. The reopen shape (title suffix, provenance block, §0
> falsifier-status table) is fixed in
> `.claude/skills/research-ticker/references/thesis-template.md`.

A run that fails to land a thesis is reported; the wave continues.

## 4. Report

One table: ticker, kill-thesis verdict, §1 ownership call, new reopen
trigger. Note any run that failed and why.

Each `research-ticker` run writes its own thesis, appends its own
`verdicts.log` line, and journals its own buy/pass. **This skill never does
those on a run's behalf** — no thesis writing, no ledger appends, no
`journal` dispatch.

**Committing is the one exception.** A dispatched subagent cannot reliably
commit (constrained write access; gpg signing hangs non-interactive), so an
interactive `research-ticker` run commits its own thesis but a sweep run does
not. After the report, land one batch commit of the wave's `research/*.md`
plus `verdicts.log`, with `--no-gpg-sign`:
`research(sweep): <n> theses from the <date> sweep (<TICKERS>)`.
Commit only what this wave produced — never sweep up unrelated dirty files.

## Guardrails

- Never place an order. Never recommend a size — that is `advisor`'s job.
- Never write to `data/*.db`.
- Never truncate a worklist silently.
- Never exceed 2 concurrent runs.
- An empty sweep is a complete and correct outcome.
