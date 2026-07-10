# stockanalysis.com catalog — what to build from it

Design doc · 2026-07-10 (Phoenix) · branch `feat/stock-research-skills`

## Why this exists

`docs/stockanalysis_data_json_catalog.md` was rewritten this session from the site's own
SvelteKit route table (167 routes) rather than from guesswork, and gained the `_api/endpoints`
surface. The question was then: what should the repo *do* with it?

A 41-agent adversarial study (11 proposals → 1 survived all three lenses, 5 wounded, 5 killed)
answered: **not much, as a database.** The catalog overlaps SEC/FINRA/CBOE — primary sources
the repo already reads — so heavily that most of it would be re-collection, and CLAUDE.md's
official-primary-sources policy exists to prevent exactly that substitution. Every new stored
signal also owes a measured recalibration pass.

The material that *is* additive splits by consumer, not by topic:

- **Storage is for comparison** across time or across names → two units, both of which are
  correctness plumbing rather than signals.
- **Reading is for understanding one company** → one unit, in a skill, with no schema.
- **A live bug** in the reverse-DCF instructions, found while checking the study's claims.

Four units. Units 2 and 4 ship *collection only*; their consumers are separate plans.

## Unit 1 — Fix the reverse-DCF levered/EV mispairing

**Lands in:** `.claude/skills/research-ticker/SKILL.md` Phase 4. Text only.

`SKILL.md` tells the agent to pull `fcf` from `/stocks/<T>/statistics/`, then says *"pass EV as
`--market-cap` and leave `--net-debt` at zero"* — and eleven lines later, *"Levered (equity)
free cash flow pairs with market cap."* These contradict.

Confirmed from data, not prose: `fcf = ncfo + capex` exactly (AAPL TTM 140.222B − 11.048B =
129.174B). `ncfo` is post-interest under US GAAP, so `fcf` is a **levered/equity** flow.
Pairing it with enterprise value is the silent error the skill itself warns about.

Also confirmed, and a second trap: stockanalysis's `leveredFCF` (97.686B) and `unleveredFCF`
(119.201B) are **both different** from plain `fcf` (129.174B) on AAPL TTM. `fcf != leveredFCF`.
The skill's fallback advice must not imply otherwise.

Magnitude, measured with `tools/valuation/reverse_dcf.py`:

| case | levered FCF ÷ market cap (correct) | levered FCF ÷ EV (as instructed) |
|---|---|---|
| AAPL (net **cash**) | 5.65% | 5.69% |
| cap 1000, net debt 500, FCF 100 | 13.04% | **9.38%** |

The skill's own AAPL example is the one case that hides the bug — AAPL's net cash is 1.3% of
market cap. On a levered name the error is **366bps**, biasing *against* leveraged companies.

**Changes:** correct the pairing instruction; replace the worked example with a levered name so
the trap is visible; state `fcf != leveredFCF`. Consider whether `reverse_dcf.py` should stop
accepting an unlabelled value for `--market-cap` — deferred, noted as an open question.

## Unit 2 — `corporate_actions` screener

**Lands in:** new `sources/screeners/corporate_actions/`, registered as `corporate_actions`,
writing `data/corporate_actions.db`. Reuses `stock_analysis_screener.probe` — no second decoder.

### The motivating gap

`sources/combiners/scorer/db.py:21` already documents its own residual:

> `# Sub-threshold splits (3:2, ratio 0.667) pass undetected — accepted residual`

This is **not** a newly-found bug; it was a deliberate trade-off made without a ratio feed. The
guard (`BASIS_BREAK_LO = 0.55`, `HI = 1.8`) holds a graded row pending forever when it sees a
consecutive-date price move outside those bounds, because the ledger stores raw closes with no
adjusted history to correct from.

Measured against the live feed: of 601 splits in the trailing year, **10 fall inside the
guard** — five 3:2 (`1.5 for 1`, price × 0.667 → a fabricated **−33%** forward return, including
`BN` Brookfield, `SNEX`, `SF`, `LINK`, `BNT`) and five stock dividends (`1.02`–`1.07 for 1`,
fabricating −2% to −7%, small enough to look like a real move).

The feed carries the **exact ratio**, which is the one thing needed to close a residual accepted
only because no ratio was available.

### Why it must be stored

All four `/actions/*` routes return a **rolling 365-day window** (verified: splits
2025-07-10 → 2026-07-10, 601 rows; changes 243; delisted 366; bankruptcies 38). **The source
forgets.** The scorer's ledger is permanent. Durable upsert history is the only way to ever hold
more than a year of crosswalk, and every day not collected is a day permanently lost.

### Shape

Not a monitor. `monitor_common.replace_forward_window` only touches `event_date >= today`; this
is a **past-events log**. Follow the FRED `observations` precedent: upsert-keyed permanent
history, **not** snapshot-scoped. `prune` deletes old `snapshots` headers only, never actions.

Payload is uniform across routes — `{action, data, fullCount, props, type}`:

| route | row fields |
|---|---|
| `/actions/splits/` | `date`, `symbol`, `name`, `splitType` (`Forward`\|`Reverse`), `splitRatio` (`"1 for 5"`) |
| `/actions/changes/` | `date`, `oldsymbol`, `newsymbol`, `name` |
| `/actions/delisted/` | `date`, `symbol`, `name` |
| `/actions/bankruptcies/` | `date`, `symbol`, `name` |

`fetch.py` (pure, network behind a `get=` seam) parses:

- `date` `"Jul 10, 2026"` → ISO `2026-07-10`. It is already a calendar date; **no** UTC→Phoenix
  conversion, and never `now_iso[:10]`.
- `splitRatio` `"a for b"` → `share_ratio = a/b` and `price_multiplier = b/a`. Store **both**,
  explicitly named. A `1.5 for 1` forward gives `price_multiplier = 0.667`; a `1 for 5` reverse
  gives `5.0`. Getting this inverted is the single most damaging bug available here.
- Leading `$` stripped from symbols (`$YMAT` → `YMAT`). It appears inconsistently — present on
  `symbol` and `newsymbol`, absent on `oldsymbol`.

Schema:

```sql
snapshots(id, captured_at, source)                       -- provenance header, prunable
actions(
  action_type TEXT,        -- split | change | delisted | bankruptcy
  effective_date TEXT,     -- ISO
  symbol TEXT,             -- oldsymbol for a change
  name TEXT,
  raw_date TEXT,           -- as published, for audit
  split_type TEXT,         -- Forward | Reverse | NULL
  split_ratio_raw TEXT,    -- "1 for 5" | NULL
  share_ratio REAL,        -- a/b
  price_multiplier REAL,   -- b/a
  new_symbol TEXT,         -- change only
  first_seen_at TEXT, last_seen_at TEXT,
  PRIMARY KEY (action_type, effective_date, symbol)
)
```

Views (ELT — signals in SQL): `v_recent_actions`; `v_splits_priced` exposing
`price_multiplier`; `v_symbol_crosswalk` as raw `old → new` edges with dates. Transitive chain
resolution (`A→B→C`) belongs to the resolver, not here.

**Explicitly out of scope:** teaching `scorer` to consume this. That mutates never-pruned
`ticker_outcome`/`regime_outcome` tables and needs its own adversarial look-ahead review — a
split learned today must not retroactively regrade a row that already matured. Separate plan.

## Unit 3 — Research corpus workflow

**Lands in:** `.claude/skills/research-ticker/references/disclosure-hunt.md` (and a pointer from
`SKILL.md`). Prose. No module, no schema, no schedule.

These routes are already reachable via `probe.page_data()`. What is missing is the *method*.

| Route | Gives | Answers the skill's existing instruction |
|---|---|---|
| `/stocks/{T}/transcripts/` | index; AAPL **74** calls, ~18 years | "read many years… learn what management has and has not ever said" |
| `/stocks/{T}/transcripts/{slug}/` | `transcriptTurns[].paragraphs[].{text,startSec,endSec}` | the words themselves |
| `/stocks/{T}/filings/` | 87 AAPL events; typed PDFs `earnings_release`, `slides`, `annual_report`, `quarterly_report`, `proxy`, `press_release` | "IR and EDGAR disclose different things"; `proxy` = DEF 14A = incentives |
| `/stocks/{T}/metrics/{metric}` | Revenue by Segment / Geography, Gross Margin by Type, Opex Breakdown — raw numbers | "unpack how it captures value until the mechanism is concrete"; free path around Pro-gated `financials/segments/` |

### The constraint, stated honestly

One AAPL transcript is ~51k chars; 74 of them is order 1M tokens. **The corpus cannot be read.**
The strategy is therefore **grep-then-read**, never read-then-summarize: the human supplies the
question, the corpus supplies exhaustive recall. Exhaustive search over 20 years is the half of
the job a machine wins outright; generating the question is the half it does not.

The exact sub-questions — where the corpus lands, lazy vs eager fetch, what a hit returns, and
whether prose suffices or a `probe.py` sibling is needed — are **deliberately left open**, and
are the subject of a separate handoff. The adversarial review's "doc-only" verdict is treated as
**unsettled**: its value lens counted only `sources/` consumers and undervalued a human-facing
one.

### Traps the prose must carry

- `{info}`-only payload = gated or invalid slug. `/stocks/AAPL/metrics/not-a-metric/` returns
  **HTTP 200**, not 404. Check for the expected key, never the status alone.
- `/filings/{id}/` returns the *same* payload as `/filings/`; only `selectedId` differs. The
  index already carries every `fileUrl`. Don't fetch per-id.
- `financialData` index 0 is `"TTM"`, not a fiscal year. Check `datekey`.
- `statistics` rows: read `hover` (exact), not `value` (rounded display string).
- **Quartr, not EDGAR.** Transcripts are *transcriptions*; `filings` PDFs are Quartr-hosted. The
  existing rule — confirm a load-bearing number against the filing — matters more here, not
  less. Tier `summaryShort` / `summaryLongHtml` as low-confidence.

## Unit 4 — `etf_holdings` screener

**Lands in:** new `sources/screeners/etf_holdings/`, registered as `etf_holdings`, writing
`data/etf_holdings.db`.

### Why now

The user intends to hold index ETFs; `data/portfolio.db` holds none today (DHR, XOM only).
`advisor` computes book heat and ATR-scaled caps over direct positions and has **no concept of
look-through**: NVDA held outright plus three ETFs at 8% NVDA each reads as diversified. Same
reasoning as the options-blind schema — cheap before the first fill, awkward after.

### The bound, stated rather than hidden

`/etf/{T}/holdings/` returns **only the top 25** of `count` constituents. Verified across the
`__data.json` route, `/api/symbol/e/{T}/holdings`, and every param tried:

| ETF | `count` | rows | top-25 weight | `date` |
|---|---|---|---|---|
| SPY | 505 | 25 | 50.7% | Jul 2, 2026 |
| VOO | 519 | 25 | 52.4% | May 31, 2026 |
| QQQ | 106 | 25 | 70.2% | Jul 7, 2026 |

This does not defeat the purpose. Concentration lives in the top 25 by construction: SPY's 25th
holding is MA at **0.68%**, so a tail name contributes < 0.68% × the ETF's book weight. The
truncation **bounds** the blind spot rather than hiding it — provided coverage is stored, not
assumed. Note `date` is an as-of that can lag by weeks (VOO: May 31).

### Shape

Point-in-time and mutable → **snapshot-scoped**, standard cascade `prune`. Catalog is a curated
ETF symbol list plus `select_ids(only, exclude, add)`; the screener does **not** read
`portfolio.db` (that is a combiner's job).

```sql
snapshots(id, captured_at, source)
etf_meta(snapshot_id, etf, constituent_count, as_of_date, coverage_pct)  -- coverage_pct = Σ top-25 weights
etf_holdings(snapshot_id, etf, rank, holding_symbol, holding_name, weight_pct, shares)
etf_allocation(snapshot_id, etf, kind, label, weight_pct)                -- kind: sector | country | asset
```

Parsing traps for `fetch.py`: `s` carries a `$` prefix (`$NVDA`); `as` is a percent **string**
(`"7.32%"`); `sh` is a comma-separated string (`"294,446,581"`); `date` is `"Jul 2, 2026"`.

`v_coverage` surfaces `coverage_pct` so a consumer can never silently treat 50.7% as 100%.

**Explicitly out of scope:** `advisor` look-through exposure. A look-through number feeding a
size cap is a new signal and owes a calibration pass. Separate plan.

## Cross-cutting

**Invariants.** Timestamps UTC `isoformat()`; calendar dates via `phx_date` — but note both new
sources ingest *already-calendar* dates, so the correct move is to parse, not convert. Time
enters `run()` as injected `now_iso`. Stdlib only. Per-item skip-and-continue: `conn.rollback()`
then print **only** `type(e).__name__` — never `str(e)`/`e.url` (a `HTTPError` carries the URL).
Prune compares fixed-width `captured_at` strings lexicographically.

**Error handling.** A `{info}`-only or layout-only payload is a *successful* HTTP 200 with no
data — both fetchers must detect the expected key and raise, or the screener silently stores
zero rows. This is the failure mode of the earlier "silent empty-fetcher" sweep.

**Testing.** Offline. `fetch.py` takes a `get=`/`page_data=` seam; `run()` takes `fetch_*=`
seams. Mirror the module layout: `tests/test_<name>_{catalog,fetch,db_schema,db_write,db_views,run}.py`,
plus a `test_registry.py` entry each. Split-ratio inversion and `$`-stripping get direct unit
tests; a `1.5 for 1` fixture asserts `price_multiplier == 2/3`.

**Schedule.** Both are daily EOD. Add slots to `deploy/launchd/install.py` and `docs/SCHEDULE.md`.
No ordering dependency on `scorer` yet — that arrives with the resolvers.

## Sequencing

1. **Unit 1** — smallest, and it is wrong *today*. Zero dependencies.
2. **Unit 3** — prose; independent. Its open design questions are handed off separately.
3. **Unit 2** — collection only. Independent of 1 and 3.
4. **Unit 4** — collection only. Independent.
5. *(later, separate plans)* scorer resolver; advisor look-through.

## Not building, with reasons

| | Why |
|---|---|
| `se=` single-name fetch helper | Every field is already a full-precision column in `data/stocks.db.metrics`. Point the skill at a local `SELECT`. |
| Segment/geography **screener** | `stock_analysis_screener/db.py` builds one wide column per scalar id — structurally wrong for company-specific multi-row series (AAPL "Global Active Devices"). No combiner can consume a non-uniform schema. |
| Sector/industry aggregate screener | `sectorPe`/`industryPe` are already per-row columns; `GROUP BY sector` gives the rollup with zero network. |
| Migrating the bulk harvest to `screener/table` | Adds the `i=` currency trap (omit it and market cap arrives in the listing currency) and breaks `run.py`'s truncation check, for nothing. |
| IR filings / transcripts as a **stored source** | No cross-name, cross-time comparison exists to make. Read-time only (Unit 3). |
| Any `/financials/` fundamentals fetcher | Substitutes an aggregator for SEC XBRL primary (`sec_fundamentals`). Policy violation and a single point of failure. |
| Movers, heatmap, trending, IPO calendar, mutual funds, news | Derivable from stored `change`/`volume`/`views` via `ORDER BY`, or no consumer. `trending` double-counts the `reddit` attention signal. |

## Open questions

1. Should `reverse_dcf.py` refuse an unlabelled `--market-cap`, forcing the caller to declare
   levered-vs-unlevered? Would have caught Unit 1's bug at the CLI. Deferred: it changes a
   shipped interface and `tools/` is out of this spec's scope.
2. Which ETFs seed `etf_holdings`'s catalog before the book holds any? A curated index list is
   the obvious default; the alternative — driving it from `portfolio.db` — would invert the
   screener/combiner dependency and is rejected.
3. Do transitive ticker-change chains (`A→B→C`) need resolving at write time or read time? Left
   to the resolver plan; raw edges are stored either way.
