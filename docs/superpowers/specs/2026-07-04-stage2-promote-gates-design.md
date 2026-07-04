# Stage 2 — Promotion Gates → Candidates (`promote`)

**Status:** Spec (no implementation plan yet)
**Grounding:** [PIPELINE_ROADMAP.md](../../PIPELINE_ROADMAP.md) Stage 2 ·
[research §3, §5, §8 Q1](../../research/2026-07-03-signal-to-candidate-pipeline.md)
(structure 🟢/🔵; **every numeric threshold here is a 🔵 default to backtest via
Stage 6, not cited law**)

## Purpose

Deterministic Python that turns the lead list into a small candidate list. Reads
`leads.db` + `stocks.db` **read-only**, writes `candidates.db`. Each candidate carries
everything the LLM gate needs: `{det_score, horizon_band, size, stop,
guardrail_bounds}`. No network, fully offline-testable.

## Package shape

`pipeline/promote/`: `catalog.py` (all thresholds as named constants + the gate
config), `extract.py` (read leads + liquidity fields), `db.py` (`candidates.db`),
`run.py` (`"promote"` in `registry.py`).

## Decision: liquidity/sizing data comes from `stock_analysis_screener` (roadmap's open question)

The `stocks.db` `metrics` wide table already carries per-symbol `price`,
`averageVolume`, `dollarVolume`, `atr`, `sector`, `beta` (via `v_latest`). That closes
the "where does ADV/spread come from" question without a new screener:

- **ADV / dollar volume** → `averageVolume`, `dollarVolume`
- **Volatility for stops** → `atr` (no price-history computation needed)
- **Spread** → not available; the spread gate is **dropped in v1** (the $-volume floor
  is the liquidity proxy). Revisit only if fills prove it necessary.
- ETFs (COT leads) must therefore be present in the stocks screener universe; if a
  mapped ETF is missing from `stocks.db`, the lead is skipped with a printed notice
  (skip-and-continue), and the ETF gets added to the screener universe as data work.

## The gate sequence (order matters; each gate logs what it kills)

Every lead passes through, in order. A rejected lead is written to
`rejections` with the gate name — auditability is the point of a deterministic funnel.

### G1. Direction filter
`allow_short` config (default **false** — cash account reality). Short leads are
rejected with gate `direction` until shorting is enabled.

### G2. Liquidity screen (all 🔵 defaults)
```
price          >= 5.00        # sub-$5 drop, research §3
dollar_volume  >= 10_000_000  # avg daily $ volume floor
```

### G3. Confluence
Promote an instrument+direction if **either**:
- **(a)** ≥ 2 distinct signals agree on it (e.g. COT + quality on the same ETF/stock), or
- **(b)** a single signal at *strong* extreme: COT commercial index ≤ 5 / ≥ 95, or
  quality `rank_pct ≥ 0.95` (long) / `≤ 0.05` (short).

The research's "extreme + confirming price/trend leg" variant needs price history we
don't store; it's a documented future gate, not v1. Speculator-divergence values ride
along in `details` for the LLM gate and for backtests, but don't gate v1 promotion.

### G4. Cross-signal dedup
Same instrument+direction from multiple signals → **one** candidate.
`det_score` = equal-weight mean of the signals' percentile scores (1/N is a legitimate
default — "learned weights beat 1/N" was refuted). `horizon_band` = the longest
contributing band. Contributing signals recorded in `signals` JSON.

### G5. Sector cap (correlation proxy for v1)
Max **2** candidates per group, where group = stockanalysis `sector` for stocks and
the COT market's `asset_class` (carried in the lead's `details`) for ETFs — an ETF has
no meaningful stockanalysis sector. Keep the highest `det_score` per group.
Pairwise |ρ| > 0.70 clustering (research §8 Q1) needs return series we don't store —
sector-as-same-bet is the v1 proxy; the real correlation gate is deferred until a
price-history source exists (FOLLOWUPS).

### G6. Max positions
Hard cap: top **10** candidates by `det_score` (auditability of the book).

## Sizing (research §5 formulas — 🟡 standard, backtest)

```
equity          — required --equity argument (no broker link; explicit input)
risk_fraction   = 0.01                       # 1% of equity at risk per trade
stop_distance   = atr * 2.0                  # ATR multiple
stop_price      = price -/+ stop_distance    # long/short
risk_dollars    = equity * risk_fraction * regime_scalar   # Stage 1 dial applied here
shares          = floor(risk_dollars / stop_distance)
shares          = min(shares, 0.01 * averageVolume)        # √-law participation cap,
                                                           # well below the ~20% breakdown
guardrail_bounds = (size_lo=0, size_hi=shares)             # reduce-only: LLM can never add
```
Kelly is explicitly **not** used (research: p/b too noisy on slow signals).
**Portfolio heat** (Σ risk_dollars ≤ 6% of equity) is *not* enforced here — it runs in
Stage 3's Python **after** the LLM clamp, where the whole approved book is known. The
per-candidate `risk_dollars` written here is what that check sums.

## `candidates.db` schema

```sql
snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at TEXT NOT NULL,
          candidate_count INTEGER, rejection_count INTEGER,
          equity REAL, regime_scalar REAL, leads_snapshot_id INTEGER);

candidates(snapshot_id INTEGER REFERENCES snapshots(id),
           instrument TEXT NOT NULL, instrument_kind TEXT, direction TEXT NOT NULL,
           det_score REAL NOT NULL, horizon_band TEXT NOT NULL,
           signals TEXT NOT NULL,            -- JSON: contributing signal rows
           price REAL, atr REAL, sector TEXT,
           shares INTEGER NOT NULL, stop_price REAL NOT NULL,
           stop_distance REAL, risk_dollars REAL,
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
`atr_mult`, `participation_cap`, `sector_cap`, `max_positions`, `strong_extreme`
bounds, `allow_short`) lives in one frozen dataclass in `catalog.py` with a
`config_hash()` (sha256 of its sorted-repr) — written into each snapshot's `details`
and later hash-pinned in Stage 4's decision log. Changing a threshold is a code change
that shows up in every downstream audit row. When Stage 6 exists, **every value tried
gets a trial-registry entry** (DSR discipline).

## CLI

```
uv run python main.py promote --db candidates.db \
  --leads-db leads.db --stocks-db stocks.db --equity 100000 \
  [--allow-short] [--keep-days 90]
```
`run(db_path, leads_db, stocks_db, equity, allow_short=False, keep_days=None,
connect_ro=..., now_iso=None)`.

## Testing

`tests/test_promote_{catalog,extract,db_schema,db_write,db_views,run}.py` +
`test_registry.py`. Fixtures: build `leads.db`/`stocks.db` via the real
`ensure_schema`s; one test per gate proving both the pass and the rejection row; a
sizing test with hand-computed shares; a regime-scalar test (0.5 halves
`risk_dollars`).

## Out of scope / deferred

Spread gate; |ρ|-based clustering + cluster exposure caps; price/trend confirming leg;
short-selling mechanics (locates, HTB); options candidates.

## Open questions → Stage 6 trials

All numeric thresholds (G2, G3-b, sizing constants, sector cap, max positions);
whether shorts add value at all once enabled.
