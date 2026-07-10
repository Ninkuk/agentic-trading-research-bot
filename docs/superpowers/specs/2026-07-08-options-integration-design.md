# Options integration — design spike

**Status**: spike output, no code changed. Written 2026-07-09 against commit `5c14446`.
**Revision 2**, after an adversarial review found the first draft's two
load-bearing decisions (Q1's `abs(delta)` heat and Q2's "preserve every view")
each manufactured the silent-wrong-number the spike exists to prevent. The
review also surfaced **Q0**, a question neither the spec nor its plan had asked:
*can the scorer grade an option at all?* It cannot. Q0 now gates everything.
**Scope**: decide *how* options enter this system, before the first option is traded.
**Plan**: `plans/004-options-blind-spot-spike.md`

The maintainer trades equities only today but intends to trade options. The
system is options-blind in three independent places, and every failure mode is
**silent** — a wrong number, not an exception.

---

## Q3 first — what the data actually contains

Answered first because it invalidates one of the plan's own assumptions.

### `option_snapshots` (503,722 rows, 24 underlyings)

```
snapshot_date, occ_symbol, source, underlying, expiration, strike, type,
bid, ask, mark, last, theo, iv, delta, gamma, theta, vega, rho,
open_interest, volume, underlying_price, vol_oi_ratio, fetched_at
```

A real row (`sqlite3 -readonly data/options.db "SELECT * FROM option_snapshots LIMIT 1"`):

```
snapshot_date = 2026-07-02
   occ_symbol = AAPL260706C00205000
   underlying = AAPL
   expiration = 2026-07-06
       strike = 205.0
         type = call
         mark = 103.25
           iv = 1.8182
        delta = 0.9997
        gamma = 0.0
        theta = -0.0022
         vega = 0.0003
          rho = 0.0056
underlying_price = 307.17
```

**The plan assumed greeks might be absent. They are not.** `delta`, `gamma`,
`theta`, `vega`, `rho` are all present, and:

```sql
SELECT COUNT(*), SUM(delta IS NULL), SUM(iv IS NULL) FROM option_snapshots;
-- 503722 | 0 | 0
```

Zero NULLs in `delta` and `iv` across every row. A delta-based heat model needs
**no** pricing model, no risk-free rate, no dividend assumption, and no new
dependency. This removes the single largest cost the plan feared.

**`occ_symbol` format**: `AAPL260706C00205000` = root, `YYMMDD` expiry,
`C`/`P`, then strike × 1000 zero-padded to 8. Note `underlying`, `expiration`,
`strike`, and `type` are **already stored as columns** — no parsing is required
to recover the underlying. That kills Q2's parsing question outright.

**No contract-multiplier column exists.** Standard US equity options are ×100,
but split-adjusted contracts deviate. See Open Questions.

### Depth — the binding constraint

```sql
SELECT COUNT(DISTINCT snapshot_date), MIN(snapshot_date), MAX(snapshot_date) FROM underlying_daily;
-- 5 | 2026-07-02 | 2026-07-08
SELECT COUNT(DISTINCT snapshot_date) FROM option_snapshots;   -- 5
```

Five days. `v_iv_rank`'s own docstring
(`sources/screeners/cboe_options/db.py:136-139`) says it "returns meaningful
values only once history accumulates (needs many days)". It is currently a
random number generator:

```
underlying  n_days  iv_rank
AAPL        4       11.5
MSFT        4       58.3
NVDA        4       100.0     <- "highest IV ever" on a 4-day sample
```

`v_unusual_activity` is structurally single-snapshot, so its docstring claims it
"works from day one". **Measured, that claim does not hold.** 123,360 of 503,722
rows (24.5%) have `open_interest = 0`, and for those the stored `vol_oi_ratio`
is the raw volume, not a ratio (`AMZN260706P00265000`: volume 8312, OI 0,
`vol_oi_ratio` 8312.0). The view's `vol_oi_ratio >= 1.0` filter is therefore
satisfied by *every* zero-OI contract with any volume at all; 243 of its 3,829
rows are that artifact — brand-new weeklies whose OI has not printed yet, i.e.
*normal*, not *unusual*. The view conflates "volume dwarfs established interest"
with "interest has not been reported". It needs an `open_interest > 0` guard (or
a NULL ratio) before it means anything.

**The two views have different failure modes and must never be treated as one
task**: `v_iv_rank` is starved of history; `v_unusual_activity` has a
degenerate divisor.

`underlying_daily` also carries a `close` per underlying per day — an
independent cross-check against `scorer.db`'s `prices` ledger. It was used
exactly that way to verify the plan-000 fix, and is worth keeping as a
recurring assertion.

**Decision:** Use the stored `delta` (and `underlying_price`) directly; no
pricing model. `v_iv_rank` is blocked on ~6+ months of `underlying_daily`
history, which cannot be backfilled from CBOE's endpoint (it serves current
chains only). `v_unusual_activity` is blocked on a correctness fix
(`open_interest > 0`), not on history. **Neither is ready.**

---

## Q0 — can the scorer grade an option at all? (No. This reorders everything.)

**This question was missing from the first draft of this spec and from its
governing plan. An adversarial review surfaced it. It dominates Q1 and Q2.**

`scorer.db`'s price ledger is equity-only:

```sql
CREATE TABLE prices (symbol TEXT, price_date TEXT, close REAL, PRIMARY KEY (symbol, price_date));
```

`ticker_outcomes` is keyed on the underlying `symbol`, and `mature()` computes
`fwd_return` by joining `prices` on that symbol. **There is no option premium
series anywhere in the system.** CBOE chains carry `mark`/`bid`/`ask` per
`snapshot_date`, but they are pruned, cover 24 underlyings, and were never
harvested into a permanent ledger.

So if an option decision is routed through the existing, "unchanged" views:

- `v_decision_outcomes.entry_slippage` is
  `d.fill_price / t.entry_close - 1` (`scorer/db.py:363-365`). For an option
  that divides a **premium** by the **underlying's stock close**: a $2.50
  premium against AAPL's $307 close reads as **−99.2% slippage**. A
  plausible-looking, entirely meaningless number, written to a permanent table.
- `v_flag_response` / `v_human_filter` credit the flag's **underlying stock
  forward return** to the human's option action. A long call that was
  directionally right but bled to zero on theta and IV crush scores as a win.
- The only option-aware figure is `realized_return = exit_fill_price /
  fill_price` (`db.py:366-368`) — fills-only, round-trip-only, unbenchmarked,
  and aggregated into no efficacy view.

The first draft called preserving those views "the single most valuable property
of the design." **It is the opposite.** Preservation is precisely the mechanism
that silently reinterprets an option as its underlying. That is the exact class
of silent-wrong-number this spike exists to prevent.

**Decision:** Before any option fill enters `decisions`, choose one:

- **(i) Grade selection only.** Declare that for `contract_ref IS NOT NULL`
  rows the system grades *which flag the human acted on*, never P&L. Force
  `entry_slippage` and `realized_return` to NULL for those rows, and exclude
  them from `v_flag_response`'s return columns while keeping them in the
  act/pass counts. Cheap, honest, immediately correct.
- **(ii) Add an option premium ledger** — a permanent `(occ_symbol, price_date,
  mark)` table fed from `cboe_options`, so an option grades on its own terms.
  Correct, and a real project: it needs its own harvest job, its own
  never-pruned table, and a policy answer for contracts outside the 24-underlying
  catalog.

**Recommendation: (i) now, (ii) later if options become material.** Do not open
the `decisions` migration until this is decided — a migration that lets option
rows into the efficacy views before their grading semantics exist does not
protect the experiment, it pollutes it permanently.

**Calibration on the "deadline" argument.** `passed_inferred` is real
(`scorer/db.py:401-408`) but narrower than the first draft implied: it fires only
for **flagged** (`|score_sum| >= 4 AND total >= 3`), **matured** opinions on
**composite-covered** underlyings. The urgency is genuine; it does not apply to
"every option trade."

---

## Q1 — what is an option position's "heat"?

`build_position_heat` computes `heat_dollars = quantity × atr` for equities: the
dollars lost on a one-ATR adverse day (`sources/combiners/advisor/db.py`).
Whatever an option's heat is, it must be **commensurable with that**, because
`v_book_heat` sums them and `v_group_heat` collapses them into one bet.

Three candidates:

| model | formula | right for | wrong for |
|---|---|---|---|
| delta-dollars | `delta × mult × qty × ATR(underlying)` | anything with a delta | ignores vega/gamma; understates a long straddle |
| premium at risk | `mark × mult × qty` | long options (max loss = premium) | badly wrong for short options (undefined loss) |
| notional | `strike × mult × qty` | nothing | wildly overstates |

**Delta-dollars wins**, for one structural reason: it makes an option
*share-equivalent*, so it can be combined with equity heat inside
`v_group_heat`. A 0.50-delta AAPL call on 1 contract carries the one-ATR-day
risk of 50 AAPL shares, and if the book also holds AAPL shares those are
genuinely one bet.

### The sign is load-bearing. `abs(delta)` is wrong.

The first draft of this spec proposed `abs(delta) × mult × qty × ATR`. An
adversarial review destroyed it with the single most common retail options
position: a **protective put**.

Hold 100 AAPL shares (heat `100 × ATR`) and buy one long put, delta −0.50.
The put *reduces* one-ATR-day exposure to ~50 share-equivalents. But
`advisor/db.py`'s `v_group_heat` sums per-leg `heat_dollars` with no netting, so
with `abs()`:

```
shares          100 × ATR = 300      (ATR = 3.0)
long put   abs(-0.5)×100×1×ATR = 150
v_group_heat                  = 450     <- reported
true net (100 - 50) × ATR     = 150     <- actual
```

**A 3× overstatement, at the exact moment the book became safer.** `heat_dollars`
is defined as "dollars lost on a one-ATR adverse day"; `abs()` turns that
definition into a false statement. A hedge must reduce heat.

**Decision:** `heat_dollars = delta × contract_multiplier × quantity ×
ATR(underlying)`, **signed**, and `v_group_heat` must **net signed delta-dollars
within a group before taking magnitude** — not sum absolute per-leg heats. This
is a change to `v_group_heat`'s aggregation, not merely an additive column, and
it must be made in the same increment that first admits an option leg.

Short legs: `delta` is signed, so a short call nets correctly against long
shares. But a short option's **tail** loss is unbounded, which no one-ATR-day
number expresses. `v_book_heat.heat_coverage` exists so "missing metrics can
never silently understate heat" (`advisor/db.py:80-83`); a short leg must count
as **uncovered**, driving `heat_coverage` below 1.0, loudly. Do not size a book
containing short options until a tail-risk model exists.

---

## Q2 — how does an option fill match a composite opinion?

`decisions` keys on `symbol` and matches against composite's per-ticker opinion.
An `AAPL260706C00205000` contract is an opinion about `AAPL`.

**Contract → underlying**: solved, no work. `option_snapshots.underlying` is a
stored column, and the MCP returns the underlying with each option order. **Do
not write an OCC parser.**

### Direction needs `position_effect`, not just `side`

The first draft mapped `(broker side × right)` into the existing `buy`/`sell`
domain:

| broker action | right | naive directional intent |
|---|---|---|
| buy | call | bullish |
| buy | put | bearish |
| sell | call | bearish |
| sell | put | bullish |

**Row 3 is a trap.** "sell call" is bearish only when it is *sell-to-open*. A
*sell-to-close* of a long call is an **exit**, not a new bearish opinion. The
broker's `side` alone cannot distinguish them. Robinhood's `get_option_orders`
carries **`position_effect`** (`open`/`close`) and `opening_strategy`; the first
draft ignored both.

Leaving disambiguation to FIFO exit-attachment (`journal.py:199-214`) fails
exactly where it matters: FIFO only fires if the opening leg already exists in
`decisions`. Any option sold-to-close whose open predates the migration falls
through and is recorded as a **bearish OPEN matched to an opinion**, poisoning
`v_flag_response` and `v_human_filter`. The code already warns about this hazard
for equities (`scorer/db.py:386-389`); options make it strictly worse, because
sell-to-open and sell-to-close are both "sell" and genuinely ambiguous.

**Decision:** Ingest `position_effect` and derive direction only for
`position_effect = 'open'`. A `close` fill attaches to its opening decision by
`contract_ref`; it never creates a decision. Never infer open/close from FIFO.

### Multi-leg strategies

A vertical spread is **one** decision and **two** fills with two contracts.
A `contract_ref`-per-leg schema produces two `decisions` rows, each matched to
the same underlying opinion and each graded independently — double-counting one
defined-risk bet, and (per Q0) grading both against the underlying stock.

**Decision:** Carry `opening_strategy` from the MCP into a nullable
`strategy_ref` that groups legs of one order. Grade the **strategy**, not the
leg. Until `strategy_ref` exists, refuse multi-leg fills at the parser rather
than record them as independent single-leg decisions.

### Expiration, assignment, exercise

None of these produce a closing *fill*.

- An option expiring worthless leaves `exit_fill_date` NULL **forever**: the
  decision looks perpetually open, `realized_return` is permanently NULL, and the
  FIFO open-buy is never released — so an unrelated later sell on the same
  contract could mis-attach to it.
- Assignment on a short call converts the option into a stock position with no
  option-side fill at all.
- Exercise is the same problem mirrored.

**Decision:** The journal must synthesize a terminal event at expiry
(`exit_fill_price = 0.0` for a long option expiring OTM) from the contract's
`expiration` date, and must model assignment before any short option is written.
The first draft omitted all three.

### Schema

`decisions` is permanent, never pruned, and holds **2 rows** today.

**Decision:** Add nullable `contract_ref TEXT`, `strategy_ref TEXT`, and
`position_effect TEXT CHECK (position_effect IN ('open','close'))` to
`decisions` (all NULL = equity, preserving every existing row and the
`order_ref` UNIQUE constraint). FIFO exit matching keys on
`COALESCE(contract_ref, symbol)`. Do **not** create a sibling table — every
efficacy view would need a UNION.

**But this migration is gated on Q0.** Adding the columns is cheap; letting
option rows flow into `v_decision_outcomes` / `v_flag_response` before their
grading semantics are decided writes permanent nonsense.

---

## Q4 — the minimum first increment

Four candidate increments. They are **not** equally ready.

### (a) Capture-only — RECOMMENDED FIRST

Extend `.claude/skills/account-positions` to call `get_option_positions`, add a
new `option_positions` child table to `portfolio.db`, and change **no**
downstream math. Advisor keeps ignoring options.

- Why first: `portfolio.db.positions` has `PRIMARY KEY (snapshot_id, symbol)` —
  two AAPL contracts collide *today*. The schema is the blocker, and it is worth
  proving before it matters.
- What breaks if it ships alone: nothing. `build_position_heat` reads
  `v_latest_positions`, which is unchanged.
- Both dispatchers' parsers use `doc.get(key)`
  (`portfolio_screener/fetch.py:33-34`, `scorer/journal.py:59`), so a new
  top-level `option_positions` array is **backward-compatible** — an old
  document still parses.
- Verification gate: an option position appears in `portfolio.db`; `v_book_heat`
  is byte-for-byte unchanged.
- Reversible: yes (drop the table).

### (b) Journal-aware — SECOND, **but gated on Q0**

Extend `journal-sync` + `journal.py` per Q2 — *after* deciding how an option is
graded. The urgency is real (an un-journaled option trade on a flagged, matured,
composite-covered underlying is recorded as `passed_inferred`,
`scorer/db.py:401-408`) but it is **not** a licence to ship the migration first.
Shipping (b) before Q0 trades a false negative for permanent, plausible-looking
garbage in `entry_slippage` and `dir_excess`. Do Q0 decision (i) — NULL out P&L
for `contract_ref IS NOT NULL` rows — in the *same* change as (b).

- Verification gate: an option fill lands in `decisions` with the correct
  directional `side` and a non-NULL `contract_ref`; existing equity rows are
  bit-identical.
- Reversible: the column is additive, but the *data* is permanent. This is the
  increment with a real deadline.

### (c) Heat-aware — THIRD

Teach `build_position_heat` about option legs per Q1, and make `heat_coverage`
count short legs as uncovered.

- What breaks if it ships before (a): nothing to read.
- Verification gate: a long call on a held underlying merges into that
  underlying's `v_group_heat` bet; a short leg drives `heat_coverage` below 1.0.

### (d) Signal — NOT YET

Wire `v_iv_rank` / `v_unusual_activity` into `composite/catalog.py`.

**Should (d) happen before the composite's existing 23 signals have ever been
graded? No.** Taking a position, as the plan demanded:

`v_signal_efficacy` returned zero rows until the plan-000 ledger repair; even
now, no outcome has matured. Nobody knows whether *any* current signal works.
Adding a 24th unmeasured signal to 23 unmeasured signals does not add
information — it adds variance, and it dilutes `ticker_scores.coverage` for
every ticker. `CLAUDE.md` is explicit that signal weighting is a human decision
made by reading measured efficacy; there is nothing to read yet.

Moreover `v_iv_rank` is *arithmetically* not ready (4 days of history; NVDA
reads `iv_rank = 100.0`). `v_unusual_activity` is ready from day one and could
ship earlier — but the ordering argument above still applies.

There is also a live trap, learned the hard way in plan 002: a score-0 ticker
signal must be added to `composite/db.py:INFORMATIONAL_SIGNALS`, or it widens
`ticker_scores.total` and can push a ticker over `v_flagged`'s `total >= 3`
threshold **because** of the annotation. Any options signal must decide,
explicitly, whether it is evidence or annotation.

**Decision:** Answer **Q0 first** (it is a decision, not code). Then sequence
**(a) → (b) → (c)**, with (b) shipping Q0's NULL-out in the same change and (c)
changing `v_group_heat` to net **signed** delta-dollars. Defer **(d)** until
`v_signal_efficacy` has matured rows for the existing catalog, `underlying_daily`
has ≥ ~126 sessions, **and** `v_unusual_activity` gets its `open_interest > 0`
guard. Ship (a) and (b) before the first option trade; (c) before the first
option is *held overnight*.

---

## What we are deliberately not doing

- **No greeks computation.** The source supplies them. No Black-Scholes, no
  `scipy`, no runtime dependency (`CLAUDE.md`: stdlib-only).
- **No OCC symbol parser.** `underlying`, `expiration`, `strike`, `type` are
  stored columns.
- **No `get_option_quotes` as a market-data source.** `get_option_positions` and
  `get_option_orders` are *account state* and are in policy. Using Robinhood for
  *market* data would be a new aggregator and a policy change the maintainer has
  not made. CBOE (`cboe_options`) is the official source and already collects
  chains for 24 underlyings.
- **No sibling `option_decisions` table.** Nullable columns on `decisions`
  preserve every existing equity row. Note this is *not* the same as preserving
  every efficacy view's *meaning* for options — see Q0.
- **No P&L grading of options** until an option premium ledger exists. Selection
  is graded; return is not. Silence beats a plausible wrong number.
- **No multi-leg fills** until `strategy_ref` exists. Refuse at the parser.
- **No `abs()` on delta, anywhere.** A hedge must reduce heat.
- **No sizing of a book containing short options.** NULL heat, visible in
  `heat_coverage`, until a tail-risk model exists.
- **No options signal in composite** until (d)'s two preconditions are met.
- **No order generation, ever.** Decision support only
  (`advisor/catalog.py:1-3`).

---

## Open questions for the maintainer

1. **Contract multiplier.** No column exists. Hard-code 100, or store it per
   contract? Split-adjusted contracts (e.g. post-reverse-split) deviate from 100
   and would silently misstate heat by an integer factor. Recommendation: store
   it, defaulting to 100, and assert it against `mark × mult ≈ market_value`
   reported by the broker.
2. **Will you write short options?** The design refuses to size a book
   containing them. If short premium is part of the plan, a tail-risk model is a
   prerequisite, not a follow-on.
3. **Should an option position's underlying merge into the equity `v_group_heat`
   bet, or be its own bet?** This spec says merge (delta-dollars makes them
   commensurable). That means a long AAPL call plus AAPL shares consume one
   crosswalk group's risk budget. Confirm that matches intent.
4. **`cboe_options` covers 24 underlyings.** If you trade an option outside that
   catalog, there is no IV/flow context and no `underlying_price`. Extend the
   catalog on first trade, or accept the blind spot? Related: an option on an
   underlying with **no composite opinion** (SPX, QQQ index options) matches
   nothing → freelance, never graded. And an option on an ETF already in
   `CROSSWALK` (e.g. SPY) both merges into a `v_group_heat` bet *and* serves as a
   grading benchmark — a double-count.
5. **Q0's fork.** Grade selection only (cheap, honest, immediate), or build the
   option premium ledger (correct, a real project)? This is the single decision
   that unblocks everything else.

---

## Appendix — verification that the blind spots still exist (2026-07-09)

```
$ grep -rhoE '\b[a-z_]+\.db\b' sources/combiners/*/*.py | sort -u | grep -c options
0
$ sqlite3 -readonly data/portfolio.db "SELECT COUNT(*) FROM pragma_table_info('positions')
    WHERE name IN ('strike','expiration','right','underlying');"
0
$ grep -n 'side not in' sources/combiners/scorer/journal.py
70:            or side not in ("buy", "sell")
$ sqlite3 -readonly data/scorer.db "SELECT COUNT(*) FROM decisions;"
2
```

All three hold. `decisions` still has 2 rows — the migration window in Q2 is
still open, and it is the cheapest it will ever be.