---
name: eval-research-ticker
description: Use when measuring a research-ticker run against external professional research on the same name, benchmarking research quality, or feeding a gap a professional writeup exposed back into the research skills. The benchmark may be pasted text, a file path, or a YouTube link — captions are fetched and rendered into a timestamped transcript. Not for producing research (that is research-ticker) — only for grading it and improving the system.
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
2. **Benchmark in.** Ask the user for the professional research — pasted text, a
   file path, or a **YouTube link** (see below). Required — there is no scoring
   without a benchmark.
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

## A YouTube link as the benchmark

Interviews, conference talks, and fund-manager walkthroughs are benchmarks too.
Fetch captions and metadata into the **scratchpad, never the repo**:

```bash
uvx yt-dlp --skip-download --write-subs --write-auto-subs \
  --sub-langs 'en-orig,en' --sub-format json3 --write-info-json \
  -o '<scratch>/bench.%(ext)s' '<URL>'
uv run python -m tools.research.youtube_captions <scratch>/bench.en.json3
```

`uvx`, not a bare `yt-dlp` — `uv` is already a setup prerequisite, so this needs
no install on a fresh clone and fetches a current build each time. That matters:
YouTube breaks old yt-dlp releases routinely, and a pinned one fails months
later on a machine nobody is maintaining.

`json3`, never `vtt` — vtt serializes the rolling caption window, so every line
lands twice. Prefer `bench.en.json3` (human-authored) over `bench.en-orig.json3`
(machine) when both exist; the tool prints which one it read. Exit 2 means no
cues: there is no benchmark, so stop rather than score against silence.

**If the fetch fails at all** (offline, age-gated, captions disabled), do not
ask for a paste blind — walk the user to **"Show transcript"** under the video's
description on youtube.com and have them copy from there. Never fetch the watch
page hoping for captions; it does not carry them.

**Read `upload_date` from `bench.info.json` before scoring Recency.** A URL
carries no date. Grading a run against a six-month-old talk books every event
since as a MISS the professional never had.

**Discount the transcript, not the professional.** Their authority is whatever
it was; the *words* are lossy. ASR fails fluently rather than loudly — on a
control video it rendered "Never gonna let you down" as "I'm going to let you
down", the negation dropped and the claim inverted. So:

- A figure, ticker, or date read off a caption earns a `MISS` only once
  confirmed at a primary source (filing, call transcript, press release).
- Auto-captions carry no speaker labels. In an interview the host's speculation
  reads exactly like the guest's claim, and a point you cannot attribute cannot
  be a `MISS` — tag it `JUDGMENT` or drop it.

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
- Booking a `MISS` on a number heard in a caption. **ASR mishears figures and
  drops negations — confirm at the source or it is not a MISS.**

## Guardrails

- **System, not artifact** — fixes land in `research-ticker`, `kill-thesis`, or
  `tools/`, never in `research/`.
- **Every fix TDD-gated** (via `writing-skills`); **every verification a
  fresh-context re-run**.
- **One cycle per invocation.** Report the delta and stop; the human decides
  whether to go again.
