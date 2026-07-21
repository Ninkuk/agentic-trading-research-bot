---
name: eval-research-ticker
description: Use when measuring a research-ticker run against external professional research on the same name, benchmarking research quality, or feeding a gap a professional writeup exposed back into the research skills. Not for producing research (that is research-ticker) — only for grading it and improving the system.
---

# eval-research-ticker

Grade one `research-ticker` run against an external professional writeup, then
drive **one** improvement cycle back into the *skills* — never the output file.

**Core principle.** The output thesis is disposable; the skill that produced it
is the asset. When a professional caught something `research-ticker` missed, the
fix belongs in `research-ticker` / `kill-thesis` / `tools/`, proven by a test and
verified by a fresh re-run. A patched `research/<TICKER>.md` teaches nothing and
is gone next run.

**Decision support only.** Never place an order or recommend a size. Read
`data/*.db` read-only.

## The loop — one cycle, then stop

Re-invoke to iterate; the skill never auto-loops.

1. **Fresh run.** Dispatch a fresh-context subagent (Opus) that executes
   `research-ticker <TICKER>` and *returns the thesis as its message*. Tell it
   explicitly **not** to write or commit `research/<TICKER>.md` — a test run must
   not collide with the repo. Use a fresh agent, **not a fork**: a fork inherits
   your conclusions and measures nothing.
2. **Benchmark in.** Ask the user for the professional research (paste or path).
   Required — there is no scoring without a benchmark.
3. **Score** the run on the rubric below.
4. **Classify every divergence** (anti-oracle guard below).
5. **Propose fixes, then stop and ask.** Present only the fixable gaps and the
   proposed *system* change. Wait for approval before editing anything.
6. **TDD-gate each approved fix** by invoking `writing-skills`: a RED baseline
   micro-test (control vs. treatment, ≥5 fresh-context reps, scored by hand)
   that proves the wording changes behavior, *then* the edit + commit. No
   unearned edits — a redundant clause reveals itself here. Dispatch test agents
   **plan-only and without repo write access** so they cannot pollute the tree.
7. **Verify by fresh re-run.** Dispatch a *new* fresh-context `research-ticker`
   run, re-score, report the score delta per dimension. Stop.

## Rubric — fixed core (7 dimensions)

Score the run on each; then set the professional's coverage beside it.

1. **Verdict** — SOUND / FLAWED / UNPROVEN, and whether it converges.
2. **Recency** — did it catch material events dated *after* the last call?
3. **Forensics** — net-income adjustments, FCF quality, float/SBC.
4. **Valuation method** — right FCF↔denominator pairing; margin-lever for
   margin-expansion names; assumptions stated.
5. **Business decomposition** — every segment and revenue line, concretely.
6. **Load-bearing conditions & falsifiers** — enumerated and counted.
7. **UNKNOWNs** — holes marked, never filled with a plausible number.

Add ticker-specific dimensions; never drop a core one.

## Classify every divergence — the professional is not an oracle

The professional writeup is **low-confidence tier**. Divergence is not
deficiency. Tag each difference before it can drive a fix:

- **MISS** — `research-ticker` missed a *verifiable* fact the professional had.
  The only tag that earns a skill fix.
- **JUDGMENT** — a different read of a genuine unknowable (the AV endgame, a
  terminal multiple). Not a gap; both sides can be honestly uncertain.
- **RESEARCH-RIGHT** — the professional was wrong / the run was right. Note it.
  No fix — *unless* the run won by luck rather than process, in which case a
  **hardening** fix (still TDD-gated) makes the win repeatable.

Only `MISS` (and the occasional hardening case) reaches step 5.

## Red flags — stop, you are about to break the skill

- Editing `research/<TICKER>.md` to close a gap. **The artifact is never the
  fix.** The gap goes into the skill.
- Editing a skill without a RED micro-test first. **No unearned edits.**
- Verifying a fix by reasoning instead of a fresh re-run. **Re-run or it did
  not happen.**
- Importing every professional point as a gap. **Classify first; most are
  JUDGMENT.**
- Running the fresh run as a fork of yourself. **It inherits your answers.**
- Dispatching write-capable test agents. **Plan-only, no repo writes** — or they
  edit the very skills you are measuring.

## Guardrails

- **System, not artifact** — fixes land in `research-ticker`, `kill-thesis`, or
  `tools/`, never in `research/`.
- **Every fix TDD-gated** (via `writing-skills`); **every verification a
  fresh-context re-run**.
- **One cycle per invocation.** Report the delta and stop; the human decides
  whether to go again.
