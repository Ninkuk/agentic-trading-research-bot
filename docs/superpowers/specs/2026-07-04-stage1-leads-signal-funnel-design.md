# Stage 1 — Signal Funnel → Ranked Leads (`leads`)

**Status:** Spec (no implementation plan yet)
**Grounding:** [PIPELINE_ROADMAP.md](../../PIPELINE_ROADMAP.md) Stage 1 ·
[research §1–§2](../../research/2026-07-03-signal-to-candidate-pipeline.md) (🟢 verified)

## Purpose

Read the per-source SQLite DBs **read-only**, normalize their strongest signals into a
unified, tagged lead list in `leads.db`. Pure Python + SQL, no network, fully
offline-testable. Downstream (Stage 2 `promote`) consumes only `leads.db` — it never
touches source DBs.

Three legs in v1: **COT extremes → ETF leads**, **quality composite → stock leads**,
**FRED regime dial** (a global scalar, not a lead).

## Package shape

`pipeline/leads/` at repo root (sibling of `sources/` — pipeline stages are consumers,
not sources). Shared pipeline helpers go in `pipeline/common/pipeline_common.py`.

| File | Role (mirrors the four-file shape) |
|---|---|
| `catalog.py` | COT→ETF mapping, quality-composite member metrics, regime thresholds |
| `extract.py` | replaces `fetch.py`: reads source DBs via read-only connections; pure functions with injected `connect=` seam |
| `db.py` | `leads.db` schema, writers, views, prune |
| `run.py` | testable `run(...)` + `main(argv)`; registered as `"leads"` in `registry.py` |

`pipeline_common.connect_ro(path)` opens `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`
— a hard guarantee the funnel cannot write to source DBs.

## Decisions (research-and-recommend; rationale inline)

### D1. COT premise group = commercials (producer/merchant), managed money as confirm
Research §2 [verified]: commercials are the default underlying group. The existing
`cftc_screener` views key on the *speculator* side (`v_cot_index`→`net_noncomm`,
`v_disagg_cot_index`→`net_mm`, `v_tff_cot_index`→`net_lev`). The nets we need already
exist in `v_net.net_comm` and `v_disagg_net.net_prod_merc`.

**Prerequisite change to `sources/screeners/cftc_screener/db.py`** (ELT: signal views
live in the source DB): add commercial-keyed twins of the existing index views, same
156-week window and `100*(net-lo)/(hi-lo)` formula:
- `v_disagg_cot_index_commercial` (keys on `net_prod_merc`) + `_latest`
- `v_tff_cot_index_dealer` (keys on `net_dealer` — TFF has no producer group; the
  dealer side is the hedging analog) + `_latest`

**Family precedence is pinned per asset class** (physical markets exist in both
legacy and disaggregated tables with *different* nets): physicals
(metals/energy/ags/softs) → disaggregated `net_prod_merc`; financials
(equity_index/rates/fx) → TFF `net_dealer`. The legacy `net_comm` is **not** used in
v1 (no legacy twin view); it stays available if a market is ever missing from both
preferred families. The existing speculator-keyed views stay untouched and serve as
the confirm leg.

### D2. COT lead rule: commercial extreme, speculator divergence recorded
- Premise: commercial index ≥ 90 → bullish (commercials most net-long in 3y) → **long**
  lead on the mapped ETF; ≤ 10 → **short** lead. (Index thresholds match the existing
  `v_extremes` convention.)
- The funnel emits the lead whenever the premise fires; the speculator index for the
  same market is stored in `details` JSON, along with the market `code` and its
  `asset_class` (Stage 2's G5 groups ETF candidates by `asset_class` — it never opens
  `cftc.db`, so this field is part of the lead contract). Whether divergence is *required* is a
  Stage 2 confluence decision, not baked in here (research: the index is a
  normalizer/extreme-detector, **not a trigger**).
- Tag: `{type: mean_reversion, implementation: cross_sectional, horizon_band: weeks}`.

### D3. COT → ETF mapping lives in `catalog.py`
`Mapping(code, etf, asset_class, note)` — CFTC contract market code → one liquid,
long-underlying ETF (no inverse/levered ETFs; direction is expressed in the lead's
`direction` field). `asset_class` is copied from the cftc catalog so it travels with
the lead (D2). Initial map — the mapping keys on `code`; codes and exact names to be
confirmed against `cftc_screener/catalog.py.CATALOG` at build time:

| Contract (catalog name) | ETF | | Contract (catalog name) | ETF |
|---|---|---|---|---|
| E-Mini S&P 500 | SPY | | Gold | GLD |
| E-Mini Nasdaq-100 | QQQ | | Silver | SLV |
| E-Mini Russell 2000 | IWM | | Copper | CPER |
| 10-Year T-Note | IEF | | WTI Crude Oil | USO |
| U.S. Treasury Bond | TLT | | Natural Gas (Henry Hub) | UNG |
| 2-Year T-Note | SHY | | Corn / Chicago Wheat (SRW) / Soybeans | CORN / WEAT / SOYB |
| Euro FX | FXE | | Japanese Yen | FXY |

Unmapped catalog markets (VIX, softs without a clean ETF, minor FX) produce **no lead**
— research §2: don't force a signal that doesn't exist. The map is append-only config.

### D4. Quality composite = 3 dimensions in v1 (payout deferred)
QMJ-style (research §2 [verified]) over `sec_fundamentals` + `stock_analysis` sector tags:
- **Profitability** = mean of z(`net_margin`), z(`roe`) — from `v_screener`.
- **Growth** = z(revenue YoY), computed **period_end-aligned from annual facts**: the
  company's latest Revenues fact whose `period_end` has a companion fact ~12 months
  earlier (±35 days), same tag. **Not** keyed on `fiscal_period='FY'` — the default
  frames ingestion path stores `fiscal_period=None`, and bulk-path duration tagging is
  ambiguous (a Q4 and an annual value can share a PK). Tag precedence is **per
  company**: `Revenues` if present, else
  `RevenueFromContractWithCustomerExcludingAssessedTax` — precedence, not the
  MAX-across-both quirk `v_screener` uses. Duration sanity check: skip a pair whose
  ratio is outside [0.2, 5] (catches a quarterly/annual mismatch slipping through).
- **Safety** = z(−`debt_to_equity`).
- **Payout: deferred** — no dividend/buyback tags in `v_screener` today; add as a 4th
  dimension when the tags are captured (FOLLOWUPS).

Composite construction, pinned:
1. Each **member** z-scored cross-sectionally **within stockanalysis `sector`**
   (dummies-only neutralization ≡ group demeaning; SQL window functions, population
   stddev via the `AVG(x*x)−AVG(x)²` moment form already used by
   `fred_screener.v_zscore`).
2. **Composite = mean of the non-NULL dimension scores, requiring ≥ 2 of 3 dimensions
   present** (a plain SQL `+` would NULL the whole composite on one missing member —
   e.g. a growth gap must not silently drop the name). Names with < 2 dimensions drop
   out, with the drop count printed per run.
3. The **outer z and the final `PERCENT_RANK()` are global across the whole universe**
   (sector effects were already removed at the member level). Rank denominator =
   valid (non-NULL composite) names only — the research's drifting-universe rule.

Leads: top decile (`rank_pct ≥ 0.90`) → long; bottom decile (`≤ 0.10`) → short (Stage 2
may drop shorts by config). Tag: `{type: quality, implementation: cross_sectional,
horizon_band: months}`.

### D5. Universe & ticker normalization
Universe = symbols in the **latest** `stock_analysis` snapshot (`v_latest`) with
`isPrimaryListing = 1`, inner-joined to `sec_fundamentals.companies` on normalized
ticker. Normalization: uppercase + `.`→`-` (stockanalysis `BRK.B` ↔ SEC `BRK-B`);
helper in `pipeline_common`. Names failing the join simply drop out (LEFT-JOIN-style
tolerance, consistent with the ELT convention).

### D6. Regime dial = deterministic late-cycle classifier + step scalar
From `fred.db` (all inputs exist): `cpi_yoy` = `v_yoy_change.change_pct` for
`CPIAUCSL`; `unrate` = `v_latest` for `UNRATE`; `yield_curve_inverted` and `hy_spread`
from `v_regime_signals`.

```
late_cycle       = (cpi_yoy > 3.0) AND (unrate < 4.5)          -- defaults, calibrate (🔵)
exposure_scalar  = 0.5 if (late_cycle OR yield_curve_inverted) else 1.0
```
Thresholds and the 0.5 step live in `catalog.py` as named constants — flagged for
Stage 6 calibration. One `regime` row per funnel run; Stage 2 multiplies size by
`exposure_scalar`. Missing inputs (partial FRED run) → NULL fields, scalar defaults to
1.0 with `regime_incomplete = 1` recorded.

## `leads.db` schema

```sql
snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at TEXT NOT NULL,
          lead_count INTEGER, source TEXT);          -- source = 'pipeline/leads'

-- provenance: which source DBs, at what state, fed this run
source_state(snapshot_id INTEGER REFERENCES snapshots(id), source TEXT,
             db_path TEXT, source_captured_at TEXT, max_data_date TEXT,
             PRIMARY KEY (snapshot_id, source));

leads(snapshot_id INTEGER REFERENCES snapshots(id),
      instrument TEXT NOT NULL,            -- ETF or stock ticker, normalized
      instrument_kind TEXT NOT NULL,       -- 'etf' | 'stock'
      signal TEXT NOT NULL,                -- 'cot_commercial_extreme' | 'quality_composite'
      direction TEXT NOT NULL,             -- 'long' | 'short'
      signal_type TEXT NOT NULL,           -- 'mean_reversion' | 'quality'   (§1 tag)
      implementation TEXT NOT NULL,        -- 'cross_sectional' | 'time_series'
      horizon_band TEXT NOT NULL,          -- 'weeks' | 'months'
      score REAL NOT NULL,                 -- signal-native: COT index 0-100, quality z
      rank_pct REAL,                       -- cross-sectional percentile where applicable
      as_of_date TEXT NOT NULL,            -- COT: report_date; quality: date part of the
                                           -- stocks.db snapshot captured_at (universe vintage)
      details TEXT,                        -- JSON: confirm-leg values, member z's, and for
                                           -- COT leads the market code + asset_class (D2)
      PRIMARY KEY (snapshot_id, instrument, signal));

regime(snapshot_id INTEGER PRIMARY KEY REFERENCES snapshots(id),
       as_of_date TEXT, cpi_yoy REAL, unrate REAL, yield_curve_inverted INTEGER,
       hy_spread REAL, late_cycle INTEGER, exposure_scalar REAL NOT NULL,
       regime_incomplete INTEGER NOT NULL DEFAULT 0);
```

Leads and regime are **snapshot-scoped**; package-local `prune` cascades both child
tables then snapshot headers (same pattern as `screener_common.prune`, two children).

Views: `v_latest_leads` (latest snapshot's leads + regime scalar joined),
`v_leads_by_instrument` (grouped, for Stage 2 confluence/dedup).

## Tag vocabulary (pinned, extensible)

- `signal_type`: `mean_reversion`, `quality` (reserved: `momentum`, `carry`)
- `implementation`: `cross_sectional`, `time_series`
- `horizon_band`: `weeks` (weeks-to-months swing), `months` (position)

Enforced by `CHECK` constraints? No — by writer-side validation (a `VOCAB` dict in
`catalog.py`), so adding a value is a code change with a test, not a migration.

## CLI

```
uv run python main.py leads --db leads.db \
  --cftc-db cftc.db --fred-db fred.db --fundamentals-db sec_fundamentals.db \
  --stocks-db stocks.db [--only cot,quality] [--keep-days 90]
```
`run(db_path, cftc_db, fred_db, fundamentals_db, stocks_db, only=None,
keep_days=None, connect_ro=pipeline_common.connect_ro, now_iso=None)`.
Skip-and-continue per leg: a missing/empty source DB prints the leg name +
`type(e).__name__` (secret-hygiene rule) and continues; `regime_incomplete`/absent legs
never abort the run.

## Invariants carried down

Injected `now_iso`; no network anywhere in the package; no wall-clock in views
(everything keys off stored `as_of_date`/`captured_at`); fixed-width UTC isoformat
timestamps for prune; source DBs opened read-only.

## Testing

`tests/test_leads_{catalog,extract,db_schema,db_write,db_views,run}.py` +
`test_registry.py` entry. Tests build tiny fixture source DBs in `tmp_path` using the
*real* source `db.py.ensure_schema` functions (schema drift in a source breaks the
funnel's tests — by design). New cftc commercial views get
`tests/test_cftc_db_views.py` additions.

## Out of scope / deferred

- Momentum/carry legs; log-market-cap OLS neutralization (add only if backtests show
  size leakage); payout dimension (D4); single-stock COT (never).
- Confluence/promotion logic — Stage 2.

## Open questions (calibration, not design)

Regime thresholds (D6), quality decile cutoffs, COT extreme thresholds — all Stage 6
trial-registry material.
