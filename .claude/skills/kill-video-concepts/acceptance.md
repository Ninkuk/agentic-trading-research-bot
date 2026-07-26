# kill-video-concepts — acceptance suite

**Never give this file to an agent under test.** It lists the expected
verdicts. An acceptance run gets the SKILL.md and the transcript, nothing
else — same discipline as eval-research-ticker's fresh-agent rule.

This file is pre-registered *before* SKILL.md exists (see git history: this
commit predates the skill file). Its purpose is the opposite of SKILL.md's
"no repo facts" rule — every expectation below is a verified, dated,
cited fact, so a future editor can re-check rather than trust.

## Fetch (rerun does not depend on a session scratchpad)

```bash
uvx yt-dlp --skip-download --write-subs --write-auto-subs \
  --sub-langs 'en-orig,en' --sub-format json3 --write-info-json \
  -o '<scratch>/v_<ID>.%(ext)s' 'https://www.youtube.com/watch?v=<ID>'
uv run python -m tools.research.youtube_captions <scratch>/v_<ID>.en.json3
```

## The four cases

`required` must hold or the run fails; `advisory` is recorded for the ledger
distribution but does not fail the run.

### Case A — `fS86gf6E4jg`, "Can Politician Trading Beat the Market?", 2026-03-28

| Concept | Expected | Basis |
|---|---|---|
| `politicians-beat-market-10pct` | DEAD gate 1 — *required* | headline stat, uncited in video |
| `politician-trades-per-ticker` | DEAD gate 5 — *required* | verified 2026-07-26: `disclosures-clerk.house.gov/public_disc/financial-pdfs/2025FD.zip` returns HTTP 200, TSV+XML, fields `Prefix, Last, First, Suffix, FilingType, StateDst, Year, FilingDate, DocID` — **no ticker, amount, or transaction**. Trades are per-DocID PDFs; repo is stdlib-only. Video's own dataset is a third-party scrape (gate 3). |
| `politician-filing-velocity` | SALVAGED line present, re-gated — *required*; verdict *advisory* | the salvage trap. Failure is an unlabelled salvage or one that skips gate 7. |
| `stock-act-45-day-lag` | DEAD gate 2 — *required* | `publication_lag_days` in `sources/combiners/backtest/` |
| `random-portfolio-null` | DEAD gate 2 — *advisory* | `v_signal_efficacy` is already benchmark-relative with a Wilson CI |

**Hard fail:** proposing a per-ticker politician screener as a survivor. That means gate 5 did not fire on a verified fact — the exact fabrication this skill exists to prevent.

### Case B — `JBLG_ywrca0`, "Actually Validating The Best MACD Strategy [86%?]", 2025-11-02

| Concept | Expected | Basis |
|---|---|---|
| `macd-cross-200dma-filter` | DEAD — *required*; gate 1 or 6 — *advisory* | 86% is another YouTuber's uncited claim; the video measures 46% and underperforms buy-and-hold |

**Hard fail:** any survivor from this video. It is a pure negative result.

### Case C — `Q6vgadS1HiE`, "I Backtested the Most Accepted Lie In Investing", 2026-07-04

| Concept | Expected | Basis |
|---|---|---|
| `risk-adjusted-signal-grading` | reaches gate 7 — *required*; final verdict *advisory* | verified 2026-07-26: `grep -ril "sortino\|drawdown\|risk_adjusted" sources/` returns nothing. Gate 2 must not kill it. This case proves the gauntlet is not a wall. |
| `benchmark-drops-unscoreable-tickers` | verdict cites the actual text of `v_benchmark_baseline` and `v_signal_efficacy` — *required*; verdict itself *advisory* | genuinely undetermined at design time. Process is graded, not outcome. |

**Hard fail:** killing `risk-adjusted-signal-grading` at gate 2 on a duplicate that does not exist.

### Case D — `Y-YRgim2D3g`, "I Used Company Reviews to Predict Stock Crashes"

| Concept | Expected | Basis |
|---|---|---|
| `glassdoor-review-trend` | DEAD gate 3 — *required* | video states its data is a Kaggle dump and that acquiring it means "violating terms of service" / "illegal web scraper" |
| `always-buy-baseline` | DEAD gate 2 — *required* | `v_benchmark_baseline` in `sources/combiners/backtest/db.py` computes `p_up`/`p_down`; its comment already carries the identical lesson |

**Hard fail:** proposing a Glassdoor scraper. Gate 3 is a bright line.

## Verification of cited bases (re-run before trusting this file)

```bash
curl -sS -o /tmp/h.zip -w "%{http_code}\n" \
  "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2025FD.zip" && unzip -l /tmp/h.zip
grep -ril "sortino\|drawdown\|risk_adjusted" sources/            # expect: no output
grep -n "v_benchmark_baseline" -A 10 sources/combiners/backtest/db.py
grep -rn "publication_lag_days" sources/combiners/backtest/ | head -3
```

Expected: HTTP 200 with `2025FD.txt` + `2025FD.xml`; empty grep for
risk-adjusted; both views present.

**Re-verified 2026-07-26** (same day as the table above): all four commands
matched the table with no corrections needed.

- HTTP 200; zip contains exactly `2025FD.txt` (138814 bytes) and `2025FD.xml`
  (725346 bytes). `2025FD.txt` header row confirmed verbatim:
  `Prefix  Last  First  Suffix  FilingType  StateDst  Year  FilingDate  DocID`
  — no ticker/amount/transaction column, as the Case A basis claims.
- `grep -ril "sortino\|drawdown\|risk_adjusted" sources/` → no output (exit 1).
- `v_benchmark_baseline` (lines 235–250 of `sources/combiners/backtest/db.py`)
  computes `p_up`/`p_down` as claimed. Its preceding comment (lines 235–239)
  reads: "Comparing hit_rate to 0.5 is wrong: SP500 rose 68.5% of 21-day
  windows in this sample, so ANY bullish flag 'wins' ~0.69 by doing nothing" —
  this is the "identical lesson" the Case D basis refers to.
- `publication_lag_days` found in `sources/combiners/backtest/run.py:106` and
  `sources/combiners/backtest/catalog.py:58,65`, confirming the Case A basis.
- Also spot-checked (not part of the required four, but cited as bases
  above): `v_signal_efficacy` in `sources/combiners/scorer/db.py` uses a
  Wilson score interval (`WILSON_Z = 1.96`, `_wilson()` helper), confirming
  the `random-portfolio-null` basis in Case A.

## 2026-07-26 — acceptance run 1 contamination note

Run 1 (4 of 4 cases) had gate 2 grep the whole repo, which reached this
file plus the gitignored design docs/plans for this skill — all three
hold the same pre-registered expectations, so gate 2 was reading the
answer key. Every agent disclosed it, but the exposure is structural,
not incidental. Remedy: gate 2's scope in SKILL.md is now `sources/`,
`tools/`, `registry.py`, `main.py --list`, and `data/*.db` — capability,
not prose about capability. Any run's results predating this fix are not
admissible evidence of the skill's gate-2 behavior.

---

# Validation results — 2026-07-26

Everything above this line is **frozen pre-registration** and is not edited by
this section. Three runs, all 2026-07-26, all Opus, all dispatched by a
controller that held the answer key and never showed it to an agent.

| run | videos | scope | admissible |
|---|---|---|---|
| 1 | the 4 cases | gate 2 grepped the whole repo | **no — contaminated** |
| 2 | the same 4 cases | gate 2 scoped to shipped capability | yes |
| 3 | 6 further videos | same, no pre-registration | yes (exploratory) |

## Run 1 — CONTAMINATED, not admissible

Gate 2's duplication grep reached the answer key inside the repo — this file and
`docs/superpowers/` both hold the pre-registered verdicts. **All four agents
disclosed it unprompted**, which is the only reason the contamination is
measurable at all rather than silently priced into four passing runs. Remedy:
commit `9af0bf0` scoped gate 2 to shipped capability (`sources/`, `tools/`,
`registry.py`, `main.py --list`, `data/*.db`) and forbade skill files, `.claude/`
and design docs. See the contamination note above for the structural argument.
Run 1's four reports are retained as `acceptance-run-*.md` but prove nothing
about gate-2 behavior.

## Run 2 — the four cases, CLEAN

**4/4 no leak · 4/4 nothing survived · 0/4 hard fail.** Every agent volunteered a
leak-check section; the two near-misses recorded (a filename in an `ls`, a
mis-quoted glob that never executed) are disclosed in the reports and neither
displayed answer-key content.

### Required rows, expected vs actual

| case | pre-registered row | actual | |
|---|---|---|---|
| A | `politicians-beat-market-10pct` DEAD gate 1 | DEAD `gate=1:provenance` | met |
| A | `politician-trades-per-ticker` DEAD gate 5 | video's scraped dataset DEAD `gate=3:source`; salvaged to the official feed, that DEAD `gate=5:architecture` | met via salvage lineage — **correction 2** |
| A | `politician-filing-velocity` SALVAGED line present, re-gated | two labelled salvages, both re-entered at gate 1; one walked to gate 7 and died there | met |
| A | `stock-act-45-day-lag` DEAD gate 2 | DEAD `gate=1:provenance` | met as DEAD, gate differs — **correction 1** |
| B | `macd-cross-200dma-filter` DEAD (gate 1 or 6 advisory) | parent DEAD `gate=1:provenance`, salvage DEAD `gate=6:statistics` | met, both advisory gates fired |
| C | `risk-adjusted-signal-grading` reaches gate 7, not killed at gate 2 | gate 2 passed on a measured zero-hit grep; DEAD `gate=5:architecture`; salvage reached and died at `gate=7:priority` | met |
| C | `benchmark-drops-unscoreable-tickers` cites actual text of `v_benchmark_baseline` and `v_signal_efficacy` | agent split it in two: `drop-unvaluable-from-benchmark` quotes `v_signal_efficacy`'s `CASE WHEN bench_fwd_return IS NULL`; `benchmark-survivorship-check` quotes `v_benchmark_baseline` over `v_spine` | met across the pair |
| D | `glassdoor-review-trend` DEAD gate 3 | DEAD `gate=3:source` | met |
| D | `always-buy-baseline` DEAD gate 2 | DEAD `gate=2:duplication` | met |

Advisory rows: Case A's `random-portfolio-null` was registered DEAD gate 2; the
clean run salvaged it at gate 6 and killed the variant at gate 7 — a different
route, and gate 2 was passed on a measured absence rather than assumed.

**One format defect, no verdict effect.** Case D's report wrote the salvage
parent as `rolling-window-scaled-to-review-volume DEAD gate=3:source` while also
writing its `-salvaged` child. The format rule requires `SALVAGED` on a salvaged
parent; the run produced an orphaned child line. It is the only such line in 116.

### Corrections to the frozen pre-registration

These correct **the expectations**, not the runs. The frozen rows above stay as
written so the drift is visible.

1. **`stock-act-45-day-lag` was registered `DEAD gate 2`; both runs independently
   killed it at `gate 1:provenance`.** Mis-registered. The concept *as the video
   states it* is an uncited causal claim, and provenance fires before duplication
   under cheapest-kill-first. The duplication argument (`publication_lag_days`)
   is real but is never reached. The agents were right; one even recorded the
   gate-2 argument as unused. The registration reasoned from the repo artifact
   backwards to a gate, which is the wrong direction.
2. **`politician-trades-per-ticker` was registered `DEAD gate 5`; the clean run
   killed the video's scraped dataset at `gate 3:source`, salvaged to the
   official feed, and killed that at `gate 5:architecture`.** The expectation
   skipped a gate: cheapest-kill-first requires gate 3 to fire first on an
   inadmissible feed, so gate 5 can only be reached by a salvage that swaps the
   feed. The basis's own text anticipates this ("Video's own dataset is a
   third-party scrape (gate 3)") without carrying it into the expected verdict.

## Run 3 — six further videos, CLEAN, no pre-registration

Exploratory, run to widen the sample. No expectations existed, so nothing here
grades the skill against a key; it grades the ledger's shape.

| video | concepts | salvages | outcome |
|---|---|---|---|
| `acPrzDh_Xr0` | 10 | 1 | nothing survived (11 lines) |
| `AZ-H7Fp2cDk` | 9 | 1 | nothing survived (10 lines) |
| `rv0cAfJbBNU` | 10 | 3 | nothing survived (13 lines) |
| `t2f0vyfABdM` | 10 | 1 | **1 SURVIVED** (11 lines) |
| `vQ0_90Ko6LE` | 10 | 1 | **1 SURVIVED** (11 lines) |
| `XZwnrpSOUvU` | 10 | 3 | nothing survived (13 lines) |

**Two concepts survived, both methodology fixes to the scorer's measurement
layer** — neither is a signal, and neither came from the videos' headline claims.

- **`fund-survivorship-bias`** (`vQ0_90Ko6LE`) — the efficacy denominator is
  silently censored. Every efficacy view filters `matured_at IS NOT NULL`, and a
  row whose symbol stops printing can never satisfy the maturation deadline, so
  it leaves the sample with nothing counting it. Bear flags are the rows most
  likely to be removed by the outcome they predict.
- **`random-portfolio-null`** (`t2f0vyfABdM`) — SPY is the wrong benchmark for a
  stock-picking signal. The null for a picker is the same-day equal-weight mean
  of the universe it scored, which separates "the screeners surfaced a falling
  cohort" from "the scores rank correctly inside it."

Both are being written up separately as `research/ideas/` proposals; the run
reports are dry runs and wrote nothing.

### Reconciliation — the agents' counts do not all reproduce

Re-queried independently against `data/scorer.db` on 2026-07-26. **Flagged, not
papered over.**

- `random-portfolio-null`'s demonstration table **reproduces exactly** against
  `v_bucket_performance` (bear/5 n=23 hit 0.870; bull/5 n=36 hit 0.250; bear/10
  n=20 0.700; bull/10 n=19 0.158), as does its 13 distinct `composite_date`s. Its
  universe-size claim is wrong at the top end: **702–1511** symbols per
  `composite_date`, not the stated 702–860.
- `fund-survivorship-bias`'s framing numbers reproduce (10,605 matured
  `ticker_outcomes`; `v_pending` = 45,644) but **its headline 71 censored rows
  does not.** Three operational definitions give three answers: **0** under the
  hard deadline (`julianday(exit) - julianday(entry_date) <= horizon*2+7`) —
  earliest `entry_date` is 2026-07-07 and the shortest deadline is 17 days, i.e.
  2026-07-24, one day past the ledger max of 2026-07-23, so *no row has yet
  crossed its deadline at all*; **71** by the agent's count; **136** rows across
  17 symbols under a "symbol stopped printing before the ledger max" reading.
  The direction of the finding stands — the denominator is censored and the
  censoring is invisible to `v_pending`'s consumers — but the magnitude is not
  reproducible and must be re-derived with a stated definition before it is
  cited. This is exactly the failure mode a survivor proposal is supposed to
  make checkable, and it was caught by re-running the query rather than by
  reading the report.

That zero-under-the-hard-deadline result also dates the ledger: the censoring the
survivor describes has not materialized yet. It is a prediction about a
three-week-old store, not a measurement of one.

## Kill distribution across all 10 videos

Derived from the 116 ledger lines in the run-2 and run-3 report files
(`grep -hE '^2026-07-26 ' acceptance-run2-*.md gauntlet-*.md`), not from memory.

| gate | kills | share |
|---|---|---|
| 1 provenance | 36 | 31% |
| 2 duplication | 24 | 21% |
| 3 source | 16 | 14% |
| 4 point-in-time | 3 | 3% |
| 5 architecture | 12 | 10% |
| 6 statistics | 14 | 12% |
| 7 priority | 9 | 8% |
| — survived | 2 | 2% |

116 lines total = 98 `DEAD` + 16 `SALVAGED` + 2 `SURVIVED`, from ~99 concepts as
stated plus 17 `-salvaged` variants. Per video: 10–13 lines.

Two readings worth keeping:

- **Gate 4 is not inert.** Three kills — a look-ahead training label, a monthly
  series looked up daily, and a derived spectral feature. A four-video reading
  that concluded it never fires was too small a sample for a ~3% base rate and is
  retracted. Every gate has now killed something, which is the evidence behind
  the freeze ruling in SKILL.md.
- **Gate 1 alone kills a third of everything.** The cheapest gate is doing the
  most work, which is what cheapest-kill-first is supposed to produce. It also
  means a third of these corpses were never repo questions at all.

## What this run changed in SKILL.md

The `DEFERRED` verdict. Several run-2 and run-3 kills rest entirely on the
repo's data being three weeks old rather than on the concept being wrong — a
21-day horizon with zero matured rows, a benchmark uncomputable before
2026-07-02, 18 of 11,196 ledger symbols with a year of closes. Filed as `DEAD`
those are buried permanently by the mechanism meant to prevent waste, and they
become viable on their own in a few months. `DEFERRED` requires a `reopen=`
condition a query can decide, and the reopen check makes the ledger something the
skill reads, not only appends to.

---

# Run 4 — eight further videos, 2026-07-26, CLEAN

Videos 11–18, exercising the **corrected** skill (gate-2 scoping + the `DEFERRED`
verdict + the reopen check + the tightened salvage-parent token). No
pre-registration; this grades the ledger's shape and the new verdict's first
exercise, not the skill against a key. Nothing above the previous `---` is edited.

| video | concepts | salvages | lines | verdicts |
|---|---|---|---|---|
| `kRa3PUxNBTM` | 10 | 1 | 11 | 9 DEAD · 1 SALVAGED · **1 SURVIVED** |
| `Lh1vrIcpJN4` | 10 | 2 | 12 | 10 DEAD · 2 SALVAGED |
| `mjVmd4MJ_tc` | 10 | 1 | 11 | 10 DEAD · 1 SALVAGED |
| `SgQ-RwC97us` | 10 | 2 | 12 | 9 DEAD · 2 SALVAGED · 1 DEFERRED |
| `ZEkArL1Oh8c` | 10 | 0 | 10 | 9 DEAD · 1 DEFERRED |
| `DVVVvlK2O_k` | 10 | 3 | 13 | 9 DEAD · 3 SALVAGED · 1 DEFERRED |
| `RNScyMTq-wE` | 10 | 3 | 13 | 9 DEAD · 3 SALVAGED · 1 DEFERRED |
| `oJQqiogr6S0` | 10 | 2 | 12 | 8 DEAD · 2 SALVAGED · 1 DEFERRED · **1 SURVIVED** |

94 lines from 80 concepts plus 14 `-salvaged` variants. Run-4 gates: 1 ×26, 2 ×30,
3 ×9, 4 ×0, 5 ×5, 6 ×14, 7 ×8.

## `DEFERRED`'s first exercise — 5 lines across 5 videos

Every one at gate 6, every one carrying a query-decidable `reopen=`; none produced a
proposal file, which is the rule working.

- `SgQ-RwC97us random-ticker-group-null` — `ticker_outcomes.distinct_composite_date@21d_matured>=120`
- `ZEkArL1Oh8c same-universe-equal-weight-baseline` — `ticker_outcomes.flagged_dates@10d>=120`
- `DVVVvlK2O_k share-of-conversation-normalization-salvaged` — `scorer.signal_outcomes[reddit_trending@5d].matured>=120`
- `RNScyMTq-wE high-confidence-binary-filter-salvaged` — `scorer.signal_outcomes.distinct_composite_date@5d>=150`
- `oJQqiogr6S0 computable-universe-benchmark-salvaged` — a bias-beats-noise test on `v_benchmark_baseline`

**Count correction:** the ledger-writing brief said four across four videos. The
measured count is five; the brief's enumeration of the random-null family excluded
`oJQqiogr6S0`'s line, which is a date-space rather than universe-space variant. Five
is what the ledger holds.

## Inter-rater check — two deliberate near-duplicate pairs

Two Reddit/sentiment videos (`DVVVvlK2O_k`, `RNScyMTq-wE`) and two intrinsic-value
videos (`SgQ-RwC97us`, `ZEkArL1Oh8c`) were run by independent agents that never saw
each other's output.

- **Both pairs agreed on outcome shape.** Reddit pair: 13 lines each, 3 salvages
  each, nothing survived, one `DEFERRED`. Intrinsic-value pair: nothing survived, one
  `DEFERRED` each.
- **Both pairs deferred the same concept family.** The Reddit pair both deferred a
  Reddit-derived filter on scorer maturity at the 5-day horizon; the intrinsic-value
  pair both deferred a universe-relative null on matured flagged-date counts, and
  the two conditions they independently derived land on the same threshold (120).

## Retraction — `fund-survivorship-bias` is recorded DEAD, not SURVIVED

`vQ0_90Ko6LE`'s run returned `SURVIVED` on a censored-denominator concept, citing 71
rows past their maturation deadline (33 `ticker_outcomes`, 38 `signal_outcomes`).
Re-measured against the **ledger's own clock** rather than wall-clock:

```sql
-- data/scorer.db, mode=ro
SELECT MAX(price_date) FROM prices;                                  -- 2026-07-23
WITH m AS (SELECT MAX(price_date) mx FROM prices)
SELECT COUNT(*) FROM ticker_outcomes, m
 WHERE matured_at IS NULL
   AND julianday(m.mx) - julianday(entry_date) > horizon*2+7;        -- 0
-- same query over signal_outcomes                                   -- 0
```

**Zero** rows have crossed their deadline. The 33 "censored" ticker rows were simply
not due yet. The concept has no measured instance in this store, so it is recorded
`DEAD gate=6:statistics`. This is the dated trap in SKILL.md — data-sufficiency
judgments run on the data's own clock — firing on a survivor that the run itself
produced, and it is the second time this same concept failed re-measurement (see the
run-3 reconciliation above, where three definitions gave 0 / 71 / 136).

**Second adjudication:** the random-null / universe-relative-benchmark family is
recorded `DEFERRED`, not `SURVIVED`. Four independent agents examined variants and
returned `SURVIVED` once (`t2f0vyfABdM`), `DEAD gate=2` once (`Lh1vrIcpJN4`), and
`DEFERRED gate=6` twice (`SgQ-RwC97us`, `ZEkArL1Oh8c`). A verdict that cannot be
reproduced across independent runs is not a proposal. `t2f0vyfABdM`'s line takes the
deferring agents' own reopen condition and no proposal file was written for it.

**One format defect corrected on the way into the ledger.** Run 2's
`Y-YRgim2D3g rolling-window-scaled-to-review-volume` was written `DEAD gate=3:source`
while also carrying a `-salvaged` child. SKILL.md requires `SALVAGED` on a salvaged
parent; the ledger line reads `SALVAGED gate=3:source`. The gate is unchanged, so the
kill distribution is unaffected; the run-3 tally above (98 DEAD + 16 SALVAGED) becomes
98 DEAD + 17 SALVAGED + 1 DEFERRED once the adjudications are applied.

## 18-video totals — `research/ideas/ledger.log`, 210 lines

| gate | kills | share |
|---|---|---|
| 1 provenance | 62 | 30% |
| 2 duplication | 54 | 26% |
| 3 source | 25 | 12% |
| 4 point-in-time | 3 | 1% |
| 5 architecture | 17 | 8% |
| 6 statistics | 30 | 14% |
| 7 priority | 17 | 8% |
| — survived | 2 | 1% |

210 lines = 171 `DEAD` + 31 `SALVAGED` + 6 `DEFERRED` + 2 `SURVIVED`, from ~179
concepts as stated plus 31 `-salvaged` variants, 10–13 lines per video.

Three readings:

- **Two survivors in 210 lines (1%).** The gauntlet is live, not a wall, and not a
  rubber stamp. Both survivors are methodology/measurement, neither is a headline
  claim from any video.
- **Gate 4 fired 3 times in 18 videos and 0 times in run 4.** Its ~1% base rate is
  now measured over twice the sample that produced the freeze ruling. Still not
  inert; still the rarest.
- **Gate 1 and gate 2 together kill 56% of everything.** The two cheapest gates do
  the majority of the work, which is what cheapest-kill-first is supposed to produce.

The gate-budget revisit threshold in SKILL.md is 300 lines. At 210 it has not fired.
