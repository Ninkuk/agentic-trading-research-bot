# Stage 2 — Promotion Gates → Candidates (`promote`)

**Status:** Spec (no implementation plan yet)
**Grounding:** [PIPELINE_ROADMAP.md](../../PIPELINE_ROADMAP.md) Stage 2 ·
[research §3, §5, §8 Q1](../../research/2026-07-03-signal-to-candidate-pipeline.md)
(structure 🟢/🔵; **every numeric threshold here is a 🔵 default to backtest via
Stage 6, not cited law**)

## Purpose

Deterministic Python that turns the lead list into a small candidate list. Reads
`leads.db` + liquidity DBs **read-only**, writes `candidates.db`. Each candidate
carries everything the LLM gate needs: `{det_score, horizon_band, size, stop,
guardrail_bounds}`. No network, fully offline-testable.

## Package shape

`pipeline/promote/`: `catalog.py` (all thresholds as named constants + the gate
config), `extract.py` (read leads + liquidity fields), `db.py` (`candidates.db`),
`run.py` (`"promote"` in `registry.py`).

## Decision: liquidity/sizing data comes from the stockanalysis screener — via TWO DBs

The roadmap's open question ("where does ADV/spread come from") is closed by data the
screener already captures — but **stocks and ETFs are separate stockanalysis screeners**
(`--type s` vs `--type e`, different catalogs), and `stocks.db`'s `v_latest` serves only
the single most recent snapshot, so the two universes cannot share one DB. Therefore:

- **Stocks** (quality leads): `stocks.db` — `price`, `averageVolume`, `dollarVolume`,
  `atr`, `sector`, `nextEarningsDate`.
- **ETFs** (COT leads): **`etfs.db`**, produced by the existing screener with
  `main.py stocks --db etfs.db --type e`. **Live-verified 2026-07-04** (route fix
  shipped in `catalog.route_for`): the 110-metric ETF catalog uses the **same ids**
  for every field this stage needs — `price`, `low`, `volume`, `averageVolume`,
  `dollarVolume`, `atr` — plus `assetClass`/`etfCategory`; all 16 mapped ETFs
  present with values. Note for threshold calibration: SOYB ($1.1M), CORN ($3.6M)
  and CPER ($7.4M) sit under the default $10M dollar-volume floor and will be
  liquidity-rejected until the floor is tuned — by design, not a bug.
- **Spread** → not available from either; the spread gate is **dropped in v1** (the
  $-volume floor is the liquidity proxy). Revisit only if fills prove it necessary.
- A lead whose instrument has no row in the relevant DB gets a `rejections` row with
  gate `data_missing` (not just stdout — every kill is logged).

## `det_score` — one normalized scale (pinned)

Signal-native scores are incomparable (COT index is 0–100, quality `rank_pct` is 0–1)
and both are *small* at the short end. `det_score ∈ [0,1]` is **directional
extremity**:

```
COT lead:      long: index/100          short: 1 − index/100
Quality lead:  long: rank_pct           short: 1 − rank_pct
```

So a short at COT index 5 scores 0.95 — shorts compete on equal footing and
cross-signal scores average sensibly.

## The gate sequence (order matters; each gate logs what it kills)

Rejected groups are written to `rejections` with the gate name — auditability is the
point of a deterministic funnel.

### G1. Group & dedup (was a later step; moved first so every gate sees one row per bet)
Group leads by `(instrument, direction)` → one working row per group carrying the
contributing signals (JSON) and `det_score` = equal-weight mean of the members'
normalized scores (1/N is a legitimate default — "learned weights beat 1/N" was
refuted). `horizon_band` = the longest contributing band. This also makes the
`rejections` PK collision-free: gates reject *groups*, never raw leads.

### G2. Direction filter
`allow_short` config (default **false** — cash account reality). Short groups are
rejected with gate `direction` until shorting is enabled.

### G3. Liquidity screen (all 🔵 defaults)
```
price          >= 5.00        # sub-$5 drop, research §3
dollar_volume  >= 10_000_000  # avg daily $ volume floor
```

### G4. Confluence
Promote a group if **either**:
- **(a)** it contains ≥ 2 distinct signals, or
- **(b)** its single signal is at *strong* extreme: `det_score ≥ 0.95` (equivalently
  COT index ≤ 5 / ≥ 95, quality rank ≥ 0.95 / ≤ 0.05).

**Honest v1 note:** the two legs cover disjoint instruments (COT → ETFs, quality →
SEC-joined stocks), so (a) can never fire in v1 — promotion reduces entirely to (b)
strong extremes. (a) and the G1 multi-signal machinery are deliberate future-proofing
for the momentum/carry legs, not dead code to "fix". The research's "extreme +
confirming price/trend leg" variant needs price history we don't store; documented
future gate. Speculator-divergence values ride along in `details` for the LLM gate
and backtests but don't gate v1 promotion.

### G5. Sector cap (correlation proxy for v1)
Max **2** candidates per group, where group = stockanalysis `sector` for stocks and
the COT market's `asset_class` (carried in the lead's `details` per Stage 1 D2) for
ETFs. Keep the highest `det_score` per group (ties: lexicographic instrument —
deterministic). Pairwise |ρ| > 0.70 clustering (research §8 Q1) needs return series we
don't store — sector-as-same-bet is the v1 proxy (FOLLOWUPS).

### G6. Max positions
Hard cap: top **10** candidates by `det_score` (ties: lexicographic instrument).

## Sizing (research §5 formulas — 🟡 standard, backtest)

```
equity          — --equity flag, else PIPELINE_EQUITY env (documented in .env.example;
                  the env fallback is what the Stage 5 scheduler relies on)
risk_fraction   = 0.01                       # 1% of equity at risk per trade
stop_distance   = atr * 2.0                  # ATR multiple
stop_price      = price -/+ stop_distance    # long/short
risk_dollars    = equity * risk_fraction * regime_scalar   # Stage 1 dial applied here
shares          = floor(risk_dollars / stop_distance)
shares          = min(shares, 0.01 * averageVolume)        # √-law participation cap,
                                                           # well below the ~20% breakdown
realized_risk   = shares * stop_distance     # what the heat check actually sums —
                                             # <= risk_dollars when the ADV cap binds
guardrail_bounds = (size_lo=0, size_hi=shares)             # reduce-only: LLM can never add
```
`shares = 0` (floor or cap degenerate) → `rejections` row with gate `size_zero`; a
zero-share candidate never reaches the gate. Kelly is explicitly **not** used
(research: p/b too noisy on slow signals). **Portfolio heat** (Σ realized risk ≤ 6% of
equity) is *not* enforced here — it runs in Stage 3's Python **after** the LLM clamp,
where the whole approved book is known, summing `final_shares × stop_distance` per
position against this snapshot's `equity`.

## `candidates.db` schema

```sql
snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at TEXT NOT NULL,
          candidate_count INTEGER, rejection_count INTEGER,
          equity REAL NOT NULL, regime_scalar REAL, leads_snapshot_id INTEGER,
          config_hash TEXT NOT NULL);        -- sha256 of the frozen gate config (below)

candidates(snapshot_id INTEGER REFERENCES snapshots(id),
           instrument TEXT NOT NULL, instrument_kind TEXT, direction TEXT NOT NULL,
           det_score REAL NOT NULL, horizon_band TEXT NOT NULL,
           signals TEXT NOT NULL,            -- JSON: contributing signal rows
           price REAL, atr REAL, sector TEXT,        -- sector = asset_class for ETFs
           next_earnings_date TEXT,          -- from stocks.db nextEarningsDate; NULL for ETFs
                                             -- (feeds Stage 3's "earnings in N days" masking)
           shares INTEGER NOT NULL, stop_price REAL NOT NULL,
           stop_distance REAL, risk_dollars REAL, realized_risk REAL,
           size_lo INTEGER NOT NULL, size_hi INTEGER NOT NULL,
           as_of_date TEXT NOT NULL, details TEXT,
           PRIMARY KEY (snapshot_id, instrument, direction));

rejections(snapshot_id INTEGER REFERENCES snapshots(id),
           instrument TEXT, direction TEXT, gate TEXT NOT NULL, reason TEXT,
           PRIMARY KEY (snapshot_id, instrument, direction, gate));
```

Snapshot-scoped, two-child cascade prune (same pattern as Stage 1). Views:
`v_latest_candidates`, `v_rejection_summary` (counts per gate — the funnel's
kill-report), `v_gate_input` (exactly the columns Stage 3 consumes).

## Config discipline

Every threshold above (`price_floor`, `dollar_volume_floor`, `risk_fraction`,
`atr_mult`, `participation_cap`, `sector_cap`, `max_positions`, `strong_extreme`,
`allow_short`) lives in one frozen dataclass in `catalog.py` with a `config_hash()`
(sha256 of its sorted-repr) — written to `snapshots.config_hash` and folded into
Stage 4's `guardrail_config_version`. Changing a threshold is a code change that shows
up in every downstream audit row. When Stage 6 exists, **every value tried gets a
trial-registry entry** (DSR discipline).

## CLI

```
uv run python main.py promote --db candidates.db \
  --leads-db leads.db --stocks-db stocks.db --etfs-db etfs.db \
  [--equity 100000] [--allow-short] [--keep-days 90]
```
`run(db_path, leads_db, stocks_db, etfs_db, equity=None, allow_short=False,
keep_days=None, connect_ro=..., now_iso=None)` — `equity=None` falls back to
`PIPELINE_EQUITY`; missing both is a hard error before any DB write.

## Testing

`tests/test_promote_{catalog,extract,db_schema,db_write,db_views,run}.py` +
`test_registry.py`. Fixtures: build `leads.db`/`stocks.db`/`etfs.db` via the real
`ensure_schema`s; one test per gate proving both the pass and the rejection row
(including `data_missing` and `size_zero`); a det_score normalization test (short at
COT 5 ⇒ 0.95); a sizing test with hand-computed shares incl. the ADV-cap binding case
(`realized_risk < risk_dollars`); a regime-scalar test (0.5 halves `risk_dollars`);
env-fallback equity test.

## Out of scope / deferred

Spread gate; |ρ|-based clustering + cluster exposure caps; price/trend confirming leg;
short-selling mechanics (locates, HTB); options candidates.

## Open questions → Stage 6 trials

All numeric thresholds (G3, G4-b, sizing constants, sector cap, max positions);
whether shorts add value at all once enabled.
