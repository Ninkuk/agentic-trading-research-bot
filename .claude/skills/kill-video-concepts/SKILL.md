---
name: kill-video-concepts
description: Mine a YouTube video for ideas this repo could actually use — extract every concept, run each through a seven-gate kill gauntlet, and propose only what survives. Use when the user shares a video (a quant-experiment channel, a strategy walkthrough, a finance talk) and asks what is usable in it, whether an idea holds up, or wants it turned into a screener / catalog signal / methodology proposal. Nothing-survived is a valid and common result.
---

# kill-video-concepts

Come at the video from the position that **nothing in it is usable**. A concept
that survives seven honest attacks is worth writing up. A concept that was never
attacked is worth nothing, however clever the video sounded.

The gauntlet only removes. No gate can add evidence, so a concept's standing can
only fall as it walks the seven — which makes **nothing-survived the expected
outcome and a complete one**. Report it plainly, log the corpses, stop. If you
catch yourself looking for one survivor so the run "produced something," that
urge is the exact failure this skill exists to prevent: the corpses *are* the
output.

One video per invocation, then stop. Re-invoke to do the next one.

## Inputs

A YouTube link is primary; a pasted transcript is the fallback. Fetch captions
and metadata into the **scratchpad, never the repo**:

```bash
uvx yt-dlp --skip-download --write-subs --write-auto-subs \
  --sub-langs 'en-orig,en' --sub-format json3 --write-info-json \
  -o '<scratch>/bench.%(ext)s' '<URL>'
uv run python -m tools.research.youtube_captions <scratch>/bench.en.json3
```

`uvx`, not a bare `yt-dlp` — YouTube breaks pinned releases routinely, and `uv`
is already a setup prerequisite. `json3`, never `vtt` — vtt serializes the
rolling caption window, so every line lands twice. Prefer `bench.en.json3`
(human-authored) over `bench.en-orig.json3` (machine) when both exist; the tool
prints which it read.

**Exit 2 means no cues.** There is nothing to mine, so stop — do not score
silence. If the fetch fails at all (offline, age-gated, captions disabled), walk
the user to **"Show transcript"** under the video description and have them copy
from there. Never fetch the watch page hoping for captions; it does not carry
them.

**Read `upload_date` from `bench.info.json` before judging any concept's
recency.** A URL carries no date, and a two-year-old experiment gets attacked as
what it was when it ran, not as if it were published today.

## Triage

Read title, description, `upload_date`, and the transcript. Many videos on a
channel like this carry no concept at all — net-worth updates, gear tours,
student-loan diaries. If nothing of the four kinds below is present, say so and
stop. A triage stop is a clean outcome; it does not go in the ledger.

## Extract before you open the repo

Do this step with the transcript only. Extracting while thinking about
`composite/catalog.py` surfaces only what already fits, and the gauntlet is left
with nothing to do.

Each concept is:

- **one falsifiable sentence** — a thing that could be shown false, not a topic;
- **tagged** `claim` (an empirical assertion) · `signal` (an input or feature) ·
  `methodology` (how something is measured or graded) · `negative-result`;
- **cited** with a `[HH:MM:SS]` from the rendered transcript;
- **slugged** — a short kebab-case name that will key its ledger line.

Cap at ten. Show the full list before attacking anything. Methodology concepts
are usually the high-yield ones; extract them even when the video treats them as
an aside.

## Reopen check — the ledger is read every run, not only written

Immediately **after** the concept list is shown and before gate 2 opens the repo,
read `research/ideas/ledger.log` and pull every `DEFERRED` line. Evaluate each
one's `reopen=` condition with the command or query it names. Any that now passes
is **surfaced alongside this video's concepts** and re-enters the gauntlet at
gate 1 on its own merits; any that still fails is left where it is, silently.

Do this after extraction, never before: the ledger holds slugs and verdicts from
prior runs, and reading it first would seed the extraction with what the repo has
already thought about — the same contamination the extract-before-you-open-the-
repo rule exists to prevent. Extraction stays transcript-only.

A ledger nobody re-reads is a graveyard, and a `DEFERRED` line nobody re-evaluates
is a `DEAD` line with extra ceremony.

## The gauntlet — seven gates, cheapest kill first

Run every concept through the gates in order. **A concept killed at gate N is
never re-argued at N+1** — it gets its ledger line and you move on. Whether that
line reads `DEAD` or `DEFERRED` is decided by the maturity test below.

Every gate below states a **question** and names the **artifact that owns the
answer**. Read the artifact at run time. Do not answer any gate from memory or
from this file: this prose can drift from the code, the code cannot drift from
itself. (Same discipline as `kill-thesis`'s deferral to `REFUTE_SIGMAS` —
whoever owns the number states it, and the skill quotes rather than restates.)

1. **Provenance** — is this the video's own measurement, or a figure it repeated
   from somewhere without a citation? Kill an uncited headline stat, a number
   heard only in a caption, and the video's own conclusion used as its own
   evidence.
   *Owner: the transcript alone. Do not open the repo for this gate.*

2. **Duplication** — does the repo already do this, or already do it better?
   *Owner: `uv run python main.py --list` for what ships; the `sources/` tree for
   how; the SIGNALS structure in `sources/combiners/composite/catalog.py` for what is already
   scored. Grep before you conclude — an absence you did not search for is not
   an absence. This gate covers methodology and constraints, not only signals: a
   concept whose whole content is something this repo already models is a
   duplicate, not a discovery.*

   **Search only shipped capability** — `sources/`, `tools/`, `registry.py`,
   `main.py --list` output, and `data/*.db` schemas. Never skill files,
   `.claude/`, or design docs/plans/specs/notes: a document describing a
   capability is not the capability, and finding your own words in one is an
   echo, not a duplicate.

3. **Source admissibility** — name the exact feed this concept would read, then
   ask whether *that feed* is admissible here. Admissibility is a policy
   question, not an availability question: that data exists and is downloadable
   says nothing about whether this repo may read it. If the video describes how
   it obtained its own data, that description is evidence about the feed's tier
   — weigh it against the policy rather than against convenience.
   *Owner: the data-source policy section of `CLAUDE.md`. It owns the tier list
   and the exceptions; read it rather than recalling which sources are blessed.*

4. **Point-in-time** — was this knowable at the moment a decision would have been
   made? Filing lag, restatement, index reconstitution, survivorship,
   look-ahead in the label.
   *Owner: `publication_lag_days` in `sources/combiners/backtest/` — it owns how
   this repo models the delay between an observation and its availability. Read
   it rather than assuming.*

5. **Architecture fit** — can it be expressed as SQL over one attached source DB,
   or does it need a runtime dependency, a trained model, or a parser for a
   format the repo cannot read?
   *Owner: the `sources/combiners/composite/catalog.py` module docstring — it owns the row
   contract; and `CLAUDE.md` for what may be imported at runtime. Verify the
   shape of the real feed before assuming a field exists — fetch it and inspect
   what it actually contains, rather than trusting the video's account of its
   own dataset.*

6. **Statistical viability** — what is the null, and does the design survive it?
   Wrong null, overlapping forward windows, thin effective n, a threshold picked
   by hand, uncorrected multiple comparisons.
   *Owner: `v_signal_efficacy` / `v_signal_recommendation` in
   `sources/combiners/scorer/db.py` — read the SQL and its comments for the null
   and the interval this repo actually uses before declaring a concept's method
   novel or broken.*

7. **Measurability & priority** — could `scorer` or `backtest` ever grade it, and
   does it displace anything worth displacing? Most salvages die here: feasible
   and worthless.
   *Owner: `docs/SCHEDULE.md` and `deploy/launchd/install.py` for what already
   occupies the schedule and what a new job would cost.*

## DEAD or DEFERRED — the maturity test

Every kill, at **any** of the seven gates, gets one more question before it is
written down:

> **Would this objection still hold if the repo's data were mature?**

- **No** — the objection is about how much history, how many matured rows, or how
  deep a universe the repo happens to hold today. The verdict is **`DEFERRED`**.
- **Yes** — the objection is about the concept. The verdict is **`DEAD`**.

**A concept is `DEAD` when it is wrong. It is `DEFERRED` when it is early.** A
kill that rests on row counts is a fact with an expiry date; filing it as `DEAD`
buries it permanently by the very mechanism meant to prevent waste.

**A `DEFERRED` line MUST carry a `reopen=` condition that a command or query can
decide.** Not prose, not a season, not a judgement call — something the reopen
check can run and get a boolean from. "when we have more data" is inadmissible;
it is a graveyard with extra steps. `reopen=ticker_outcomes.matured@21d>=200` is
admissible. If you cannot write a decidable condition, you did not actually
identify a maturity objection, and the verdict is `DEAD`.

Two traps this token introduces, both worth naming:

- **`DEFERRED` is not a soft `SURVIVED`.** It writes no proposal file, it is not
  a landing zone, and it is not a "closest call." Reaching for it to make a run
  feel productive reintroduces the exact pressure the nothing-survived rule
  removes.
- **`DEFERRED` is not a soft `DEAD` either.** A concept that is wrong on the
  merits does not become deferrable because the data is *also* thin. Apply the
  test to the objection you actually made, not to the most flattering one
  available.

## The salvage rule

Weakening a concept until it passes is this skill's main fabrication risk.
Therefore:

- Salvage is allowed **once** per concept.
- It is written explicitly as `SALVAGED: <original> → <weakened>`.
- The weakened variant **re-enters at gate 1** and faces all seven, gate 7
  included.
- **A gate is never lowered to produce a survivor.** If the weakened variant is
  feasible but worthless, gate 7 kills it, and that is the correct result.
- The weakened variant takes the maturity test like anything else, so a salvage
  can itself end `DEFERRED` — with its own `reopen=`, on its own `-salvaged`
  line. Note what that costs: the salvage budget for that concept is already
  spent, so when the condition passes, the variant reopens and the concept as
  stated stays dead.

An unlabelled salvage — quietly narrowing a concept mid-gauntlet and carrying the
narrowed version forward — is a failed run even if the verdict happens to be
right.

## Named traps

- **Benchmark-relative metrics are not base-rate violations.** Before crying
  "base rate is not 0.5," check whether the metric is *already* benchmark-
  relative — if the underlying hit column compares against a benchmark rather
  than against zero, 0.5 is the correct null and there is nothing to kill.
  *Dated example, 2026-07: `v_signal_recommendation` tested a hit-rate CI
  against 0.5 and looked like a violation; its `hit` column was already
  `fwd_return > bench_fwd_return`, so the test was right. That is one instance,
  not the rule — re-read the SQL, do not assume this still describes it.*

- **A negative result in the video is evidence about the video's
  implementation**, not about the concept. What actually got tested was one
  parameterisation, on one universe, over one window, coded by one person. Kill
  the concept on a gate, not on the video's disappointment — and equally, do not
  resurrect it because the author's code looked sloppy.

- **ASR discipline.** Auto-captions fail fluently rather than loudly: negations
  drop, tickers mutate, figures shift a digit. A figure, ticker, or date read off
  a caption is confirmed at a primary source or it is not used. A concept whose
  only support is an unconfirmed caption number dies at gate 1.

- **Data-sufficiency judgments run on the data's own clock, never wall-clock.**
  A gate-6/7 question about rows matured, history depth, or horizons covered must
  be measured against the store's own latest observation, not `date('now')` — the
  same determinism invariant `CLAUDE.md` already states for the sources, applied
  to this skill's own grepping and querying of the repo.
  *Dated example, 2026-07-26: an apparent gap in a maturation ledger vanished
  when re-measured against the store's own latest observation — 33
  apparently-overdue rows became 0.* A check that agrees with the finding it is
  checking has not verified it if it ran the same query; an independent check
  must vary the method, not just the operator.

## Outputs

**Every concept**, survivor or corpse, gets one line appended to
`research/ideas/ledger.log`:

```
<YYYY-MM-DD> <video_id> <concept-slug> DEAD|DEFERRED|SALVAGED|SURVIVED gate=<n:name> [reopen=<condition>]
```

Gate names: `1:provenance` `2:duplication` `3:source` `4:point-in-time`
`5:architecture` `6:statistics` `7:priority`. `gate=` is the gate that killed it
and is **omitted on a `SURVIVED` line**. `reopen=` appears on `DEFERRED` lines
and nowhere else — it is mandatory there and forbidden everywhere else.

**The corpse rule splits by token.** `DEAD` is never re-proposed; that is what
makes the gauntlet cheap to run twice. `DEFERRED` **is** re-proposed, exactly
once its `reopen=` condition passes, via the reopen check at the top of the next
run. Nothing else re-enters.

One line per concept **as the video stated it**. When a concept is salvaged, the
parent line's verdict token is `SALVAGED` — never `DEAD`, never `DEFERRED` — and
its `gate=` names the gate that killed the concept as stated. A salvage writes a
*second* line with a `-salvaged` slug suffix carrying its own verdict and its own
`gate=`, so the original's death stays on the record — a weakened variant that
survives must never erase the fact that the concept as stated did not. Worked
examples, one of each shape:

```
<YYYY-MM-DD> <video_id> example-concept SALVAGED gate=3:source
<YYYY-MM-DD> <video_id> example-concept-salvaged DEAD gate=5:architecture
<YYYY-MM-DD> <video_id> other-concept DEFERRED gate=7:priority reopen=ticker_outcomes.matured@21d>=200
```

**Each survivor** additionally gets `research/ideas/<YYYY-MM-DD>-<slug>.md`
stating:

- **landing zone** — new screener/monitor · composite catalog signal ·
  `scorer`/`backtest` methodology fix · research-skill hardening;
- **shape** — the table or view it would take;
- **measurement plan** — the null, the horizon, the effective n, and the
  threshold sweep. Thresholds are chosen after data, never before.

**A `DEFERRED` concept gets a ledger line and nothing else.** No proposal file,
no landing zone, no measurement plan — its `reopen=` condition *is* its entire
forward artifact. Writing it up now is how it stops being deferred and starts
being a survivor that never earned it.

Then **stop and ask**. The human decides whether any of it gets implemented.
Nothing here is an implementation mandate.

## Design note: the gate budget is frozen (2026-07-26)

Seven one-way gates are a ratchet: every gate can only lower a concept's
survival probability, nothing in the design pushes back, and each addition is
individually defensible. Mirrors the same freeze in `kill-thesis`.

- **The seven gates are frozen at their current strength.** Do not add an eighth
  and do not sharpen an existing one mid-run.
- **Adding a gate requires a measured miss** — a concept this gauntlet passed
  that proved junk, or a ledger showing it under-kills. "A reviewer thought of
  another failure mode" is the exact accumulation this note exists to stop.

**The twenty-concept revisit trigger fired on 2026-07-26 and the budget stays at
seven.** A ten-video validation run produced 116 ledger lines in one day, far
past the trigger. Its distribution, re-sliced from the shipped
`research/ideas/ledger.log` *after* that run's two survivors were adjudicated
away at gate 6: gate 1 ×36, gate 2 ×24, gate 3 ×16, gate 4 ×3, gate 5 ×12,
**gate 6 ×16**, gate 7 ×9, **survivors 0**. An earlier reading of that run as
`gate 6 ×14, survivors 2` predates the adjudications and is retracted. Re-slice
it yourself before quoting it; this file does not own the ledger.
**Every gate has now demonstrably killed
something**, so no gate is inert and none is a candidate for removal. Gate 4 in
particular fired three times — a look-ahead training label, a monthly series
looked up daily, and a derived spectral feature — which retracts an earlier
four-video reading that concluded it never fires. Four videos was too small a
sample to see a gate whose base rate is ~3%.

**The live-gauntlet evidence is the 18-video ledger, not that run.** 210 lines
from 179 concepts as stated plus 31 `-salvaged` variants: **2 `SURVIVED`, 6
`DEFERRED`**, and every one of the seven gates has killed something. Two
survivors in 210 lines is a live gauntlet, not a wall, so nothing argues for
loosening either.

- **Revisit at 450 lines in `research/ideas/ledger.log`.** Derived, not asserted:
  the file holds 211 lines today (210 concepts over 18 videos ≈ 11.7 lines per
  video), so 450 is **≈20 more videos** out. A 300-line trigger would fire in
  ≈8 videos — too soon for the freeze to do any work. 450 is far enough out to be
  the next point at which a genuinely rare gate could be shown inert. The
  measured-miss rule for *adding* a gate is unchanged and is not relaxed by this
  ruling.

The skill can improve itself: research-skill hardening is a landing zone, so a
concept whose real value is a check this gauntlet lacks lands as a proposal
against `kill-video-concepts` — which then goes through `writing-skills`' TDD
gate like any other skill edit.

## Guardrails

- **Never write to `data/*.db`.** Read-only, always. The only writes this skill
  makes are inside `research/ideas/`.
- **Never place an order** and never recommend a position size. Decision support
  only.
- **YouTube is low-confidence tier and never launders into fact.** A claim that
  entered through a caption leaves through a citation or does not leave.
- **Nothing-survived is a complete, successful outcome.** Do not pad it, do not
  apologise for it, do not offer a "closest call" as a consolation survivor.
