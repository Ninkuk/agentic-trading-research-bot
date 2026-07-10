# Plan 004: Design spike — specify how options enter this system before the first option is traded

> **Executor instructions**: This is a **DESIGN SPIKE**, not a build plan. Its
> deliverable is a written specification and a small number of *read-only*
> probes. **You will not change any behavior, schema, or signal.** The only
> files you create are the spec document and, optionally, throwaway probe
> scripts under the scratchpad — never under `sources/`.
>
> If you find yourself editing a `db.py`, a `catalog.py`, or a `run.py`, you
> have misread this plan. Stop.
>
> Run every verification command. If anything in the "STOP conditions" section
> occurs, stop and report. When done, update the status row for this plan in
> `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat 5c14446..HEAD -- sources/screeners/cboe_options sources/screeners/portfolio_screener sources/combiners/scorer sources/combiners/advisor`
> If any in-scope-for-reading file changed since this plan was written, compare
> the "Current state" excerpts against the live code before proceeding.

## Status

- **Priority**: P2
- **Effort**: M (spike — investigation and writing, not implementation)
- **Risk**: LOW (produces a document; changes no behavior)
- **Depends on**: none. Informed by, but not blocked on, plan 001.
- **Category**: direction
- **Planned at**: commit `5c14446`, 2026-07-08

## Why this matters

The maintainer does not trade options **yet**, but intends to. Today the system
is options-blind in three separate places at once, and the blindness is
asymmetric in a way that will produce *silently wrong numbers* rather than
errors on the day the first option is bought.

**1. It collects a large amount of options data and consumes none of it.**

- `data/options.db` is 138 MB: 503,722 rows in `option_snapshots` across 24
  underlyings, refreshed hourly on weekdays (`options-intraday`, `options-close`
  in `deploy/launchd/install.py`).
- It has three finished signal views: `v_unusual_activity`, `v_iv_rank`,
  `v_latest_sentiment` (`sources/screeners/cboe_options/db.py:121-164`).
- **No combiner attaches it.** `grep -rhoE '\b[a-z_]+\.db\b' sources/combiners/*/*.py`
  does not list it. Those three views are referenced only by their own tests.

**2. The account snapshot cannot represent an option position.**

`sources/screeners/portfolio_screener/db.py:27-34` stores positions as
`(snapshot_id, symbol, quantity, avg_cost, market_value)` with
`PRIMARY KEY (snapshot_id, symbol)`. There is no strike, no expiration, no
call/put, no underlying. The Robinhood MCP exposes `get_option_positions`; the
`account-positions` skill never calls it.

**3. The decision journal cannot represent an option fill.**

`sources/combiners/scorer/journal.py:65-77` validates a flat equity fill and
constrains `side` to `("buy", "sell")`. There is no `open`/`close`, no contract
identity. The MCP exposes `get_option_orders`; `journal-sync` never calls it.

**The failure mode is silence, not an exception.** On the day an option is held:

- `advisor`'s book heat is `quantity × underlying ATR`
  (`build_position_heat`, `sources/combiners/advisor/db.py`). An option's dollar
  exposure is *not* that. But the option isn't in `portfolio.db` at all, so it
  simply vanishes from `v_book_heat` — and `advisor/db.py:247` states the
  standing assumption plainly: **"the book is long-only"**. Heat, `v_group_heat`,
  and every size cap are then computed against a partial book, understating risk
  precisely when the riskiest instrument is in play.
- An option trade taken off a composite flag never enters `decisions`, so
  `v_flag_response` records it as `passed_inferred` — actively *miscrediting*
  the human-filter experiment that `scorer.db` exists to run.

Doing this as a spike now, before the first trade, is cheap. Doing it after
means reconciling a permanent, never-pruned `decisions` table against a period
where option trades were silently recorded as passes.

## What this spike must produce

A single document, `docs/superpowers/specs/2026-07-08-options-integration-design.md`,
that answers the questions below with enough precision that a later build plan
can be written from it without re-deriving anything. Per `CLAUDE.md`, specs under
`docs/superpowers/specs/` are transient working docs, cleared once the work ships.

The spec must be decision-complete on **four** questions:

### Q1 — What is an option position's "heat"?

`build_position_heat` computes `heat_dollars = quantity × atr` for equities: the
dollar move of a one-ATR adverse day. The spec must choose and justify one of:

- **Delta-dollars × underlying ATR** — `|delta| × contract_multiplier × quantity
  × underlying_ATR`. Treats the option as its share-equivalent. Requires a delta,
  which `cboe_options` may or may not store (see Q3).
- **Premium at risk** — `market_value` of the long option, full stop. A long
  option's max loss is the premium. Simple, exactly right for long calls/puts,
  and badly wrong for short options.
- **Something else**, argued for.

The spec must state what happens for **short** options (undefined/large max
loss) and whether the system will refuse to size a book containing them.
It must also state what `v_book_heat.heat_coverage` — which exists so "missing
metrics can never silently understate heat" (`advisor/db.py:80-83`) — should
report when an option's heat input is unavailable.

### Q2 — How does an option fill match a composite opinion?

`decisions` keys on `symbol` and matches against composite's per-ticker opinion.
An `AAPL 250117C00250000` contract is an opinion about `AAPL`. The spec must specify:

- The contract → underlying mapping, and where it is computed (parse the OCC
  symbol? carry an `underlying` field from the MCP?).
- Whether a long put on `AAPL` counts as *agreeing* with a bearish `AAPL` flag
  (it does, economically) and how `side` (`buy`/`sell`) plus `right` (`call`/`put`)
  combine into the directional `buy`/`sell` the current `decisions.side` CHECK expects.
  Note `decisions` already has `exit_fill_date`/`exit_fill_price`/`exit_order_ref`,
  so round-trips are representable — the gap is contract identity, not exits.
- How FIFO exit-matching (`journal.py`, the `_attach_exits` logic around
  lines 199-214) must change so exits match **within a contract**, not merely
  within a ticker. Holding two different `AAPL` contracts and selling one must not
  close the other.
- Whether `decisions` gains a nullable `contract_ref` column (preserving every
  existing equity row) or whether option decisions live in a sibling table.
  **`decisions` is permanent and never pruned** (`scorer/db.py:1-5`), so this
  choice is effectively irreversible. Argue it.

### Q3 — What does the data actually contain?

Do not design against assumptions. Probe, and record observed values:

```
sqlite3 -readonly data/options.db ".schema option_snapshots"
sqlite3 -readonly data/options.db ".schema underlying_daily"
sqlite3 -readonly data/options.db "SELECT * FROM option_snapshots LIMIT 3;"
sqlite3 -readonly data/options.db "SELECT COUNT(DISTINCT snapshot_date), MIN(snapshot_date), MAX(snapshot_date) FROM underlying_daily;"
sqlite3 -readonly data/options.db "SELECT COUNT(DISTINCT underlying) FROM underlyings;"
```

Answer in the spec:

- Does `option_snapshots` carry a **delta** or any greek? (If not, Q1's
  delta-dollars option requires computing greeks from `iv` — a real cost with no
  stdlib Black-Scholes. Say so.)
- What is the `occ_symbol` format, exactly, from a real row?
- **How deep is `underlying_daily`?** Run the query. At the time this plan was
  written it held **5 distinct `snapshot_date` values**. This matters enormously:
  `v_iv_rank`'s own docstring (`cboe_options/db.py:136-139`) says it "returns
  meaningful values only once history accumulates (needs many days)". An IV-rank
  *signal* is therefore blocked on history depth for exactly the same reason the
  scorer is (see plan 001). The spec must state how many days of `underlying_daily`
  are needed before `v_iv_rank` is trustworthy, and whether that history can be
  backfilled or must accrue.

### Q4 — What is the minimum first increment?

The spec must recommend a **sequenced** build, smallest useful piece first, with
each increment independently shippable and verifiable. Consider at least:

- **(a) Capture-only.** Extend `account-positions` + `portfolio_screener` to
  record option positions in a new child table. Change *no* downstream math yet.
  Advisor keeps ignoring them, but the data starts accruing and the schema is
  proven before it matters. **This is the likely correct first increment** — argue
  for or against.
- **(b) Heat-aware.** Teach `build_position_heat` about option legs per Q1.
- **(c) Journal-aware.** Extend `journal-sync` + `journal.py` per Q2.
- **(d) Signal.** Wire `v_iv_rank` / `v_unusual_activity` into `composite/catalog.py`
  as a ticker-grain signal — gated on the history depth found in Q3, and on the
  scorer being able to grade it (plan 001).

For each increment, state: what breaks if it ships alone, what its verification
gate is, and whether it is reversible.

The spec must also answer: **should (d) happen at all before the composite's
existing 23 signals have ever been graded?** `v_signal_efficacy` currently returns
zero rows. Adding an unmeasured 24th signal to an unmeasured 23 has a real cost.
`CLAUDE.md` is explicit that signal weighting is a human decision made by reading
measured efficacy. Take a position.

## Current state

### The unconsumed views — `sources/screeners/cboe_options/db.py:121-164`

```sql
-- (1) unusual activity on each underlying's per-underlying latest snapshot:
-- contracts where today's volume dwarfs standing open interest. Works from
-- day one.
CREATE VIEW IF NOT EXISTS v_unusual_activity AS
SELECT underlying, occ_symbol, expiration, strike, type,
       volume, open_interest, vol_oi_ratio, iv, snapshot_date
FROM option_snapshots o
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM option_snapshots o2
                       WHERE o2.underlying = o.underlying AND o2.source = 'cboe')
  AND source = 'cboe' AND volume >= 100 AND vol_oi_ratio >= 1.0
ORDER BY vol_oi_ratio DESC;

-- (2) IV Rank/percentile ... Returns meaningful values only once history
-- accumulates (needs many days).
CREATE VIEW IF NOT EXISTS v_iv_rank AS ...
```

Note `v_unusual_activity`'s "Works from day one" versus `v_iv_rank`'s "needs
many days". Those two views have very different readiness. The spec must not
treat them as one thing.

### `underlying_daily` — a small price history in its own right

Columns (observed): `snapshot_date, underlying, underlying_price, close, iv30,
total_call_volume, total_put_volume, put_call_volume_ratio, total_call_oi,
total_put_oi, put_call_oi_ratio`.

It carries a `close` per underlying per day for 24 names. The spec should note
whether this is a useful cross-check against `scorer.db`'s `prices` ledger
(plan 001) — same symbol, same date, two independent sources.

### The equity-only position schema — `sources/screeners/portfolio_screener/db.py:27-34`

```sql
CREATE TABLE IF NOT EXISTS positions (
    snapshot_id  INTEGER NOT NULL REFERENCES snapshots(id),
    symbol       TEXT NOT NULL,
    quantity     REAL NOT NULL,
    avg_cost     REAL,
    market_value REAL,
    PRIMARY KEY (snapshot_id, symbol)
);
```

`PRIMARY KEY (snapshot_id, symbol)` is the structural blocker: two `AAPL`
contracts collide. Any design must address this.

### The equity-only fill parser — `sources/combiners/scorer/journal.py:65-77`

```python
        side = f.get("side")
        price = f.get("price")
        filled_at = f.get("filled_at")
        if (
            not symbol
            or side not in ("buy", "sell")
            or isinstance(price, bool)
            or not isinstance(price, (int, float))
            or not isinstance(filled_at, str)
            or "T" not in filled_at
        ):
            skipped += 1
            continue
```

And `decisions`, from `sqlite3 -readonly data/scorer.db ".schema decisions"`:

```sql
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('acted', 'passed')),
    side TEXT CHECK (side IN ('buy', 'sell')),
    composite_snapshot_id INTEGER, composite_date TEXT,
    opinion_score_sum INTEGER, opinion_total INTEGER,
    fill_date TEXT, fill_price REAL, quantity REAL,
    exit_fill_date TEXT, exit_fill_price REAL,
    order_ref TEXT UNIQUE, exit_order_ref TEXT UNIQUE,
    note TEXT, source TEXT NOT NULL DEFAULT 'mcp' CHECK (source IN ('mcp','manual')),
    recorded_at TEXT NOT NULL, placed_agent TEXT
);
```

It currently holds **2 rows**. Migrating it is cheap *today* and expensive later.
Say so in the spec.

### The MCP surface that exists but is unused

The `account-positions` skill (`.claude/skills/account-positions/`) calls
`get_accounts`, `get_portfolio`, `get_equity_positions`. The `journal-sync` skill
calls `get_equity_orders`. Unused and relevant: `get_option_positions`,
`get_option_orders`, `get_option_quotes`, `get_realized_pnl`, `get_pnl_trade_history`.

**Read both skill files** before writing the spec; they define the JSON contract
that the dispatchers parse, and any schema change must be expressible there.

### Constraints the spec must honor

- **Zero runtime third-party dependencies.** No `scipy`, no options-pricing
  library. If greeks are required and not supplied by the source, that is a cost
  the spec must price honestly (a stdlib Black-Scholes is ~30 lines but needs a
  risk-free rate and a dividend assumption — and `fred.db` has the former).
- **Live account state enters only through the `portfolio` / `journal`
  dispatchers.** Never write SQL against `portfolio.db` directly (`CLAUDE.md`).
- **`decisions` and `scorer.db`'s outcome tables are permanent and never pruned.**
- **Decision support, never order generation.** Nothing designed here may place
  or size an order for transmission.
- **Official-primary-sources policy**: `cboe_options` is CBOE — fine. Robinhood
  is account state, not market data, so `get_option_positions` is in policy;
  `get_option_quotes` as a *market data* source would be a policy change and must
  be flagged as such, not assumed.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Probe options schema | `sqlite3 -readonly data/options.db ".schema option_snapshots"` | DDL |
| Probe depth | `sqlite3 -readonly data/options.db "SELECT COUNT(DISTINCT snapshot_date) FROM underlying_daily;"` | an integer |
| Confirm non-consumption | `grep -rn "options.db\|cboe_options" sources/combiners/` | no matches |
| Tests (unchanged) | `uv run pytest` | all pass — you changed nothing |
| Lint (unchanged) | `uv run ruff check` | exit 0 |

## Scope

**In scope** (the only files you may create or modify):

- `docs/superpowers/specs/2026-07-08-options-integration-design.md` (create) — the deliverable
- `plans/README.md` (modify) — status row

**Out of scope — you may READ these, you may not MODIFY them:**

- `sources/screeners/cboe_options/**`
- `sources/screeners/portfolio_screener/**`
- `sources/combiners/scorer/**` (especially `journal.py` and the `decisions` schema)
- `sources/combiners/advisor/**`
- `sources/combiners/composite/catalog.py`
- `.claude/skills/account-positions/**`, `.claude/skills/journal-sync/**`
- `registry.py`, `main.py`, `deploy/**`
- **Any `data/*.db` file.** Read-only (`sqlite3 -readonly`) probes only. Do not
  run any dispatcher that writes.

Throwaway probe scripts go in the session scratchpad, not the repo.

## Git workflow

- Branch: `advisor/004-options-spike`
- Single commit: `docs(specs): options integration design spike`
- Do **not** add a Co-Authored-By trailer (user's global instruction).
- Do **not** push or open a PR.

## Steps

### Step 1: verify the three blind spots still exist

```
grep -rhoE '\b[a-z_]+\.db\b' sources/combiners/*/*.py | sort -u | grep -c options
sqlite3 -readonly data/portfolio.db "SELECT COUNT(*) FROM pragma_table_info('positions') WHERE name IN ('strike','expiration','right','underlying');"
grep -n 'side not in' sources/combiners/scorer/journal.py
```

**Verify**: first → `0`; second → `0`; third → shows the `("buy", "sell")` tuple.

If any differs, the codebase has drifted; re-read the relevant file before proceeding.

### Step 2: probe the data (Q3)

Run every query in the Q3 section. **Record actual observed output**, including
a real `occ_symbol` and a real `option_snapshots` row, into the spec. Do not
paraphrase — paste the values.

Specifically determine, and write down:
- the exact column list of `option_snapshots`
- whether any greek (delta/gamma/theta/vega) column exists
- the current depth of `underlying_daily` (distinct `snapshot_date` count)
- the current depth of `option_snapshots` (distinct `snapshot_date` count)

**Verify**: the spec's Q3 section contains pasted, real output — not assumptions.

### Step 3: read the two MCP skills

Read `.claude/skills/account-positions/SKILL.md` and
`.claude/skills/journal-sync/SKILL.md` in full. Record in the spec:

- the exact JSON document shape each skill pipes into its dispatcher
- which MCP tools each calls today
- how a new option-position / option-fill array would slot into that document
  without breaking the existing equity parse (i.e. a new top-level key, so an old
  document still parses — argue whether the parsers tolerate unknown keys today;
  check `parse_doc` in `journal.py`)

**Verify**: the spec quotes the current JSON shape from each skill file.

### Step 4: write the spec

Answer Q1, Q2, Q3, Q4 in order, each as its own section, each ending with a
**Decision:** line stating the chosen option in one sentence.

Include, as its own section, **"What we are deliberately not doing"** — at
minimum: no greeks computation if the source supplies none; no `get_option_quotes`
as a market-data source without an explicit policy decision by the maintainer;
no signal wiring (Q4d) until the existing 23 signals have been graded.

Include an **"Open questions for the maintainer"** section for anything you could
not resolve from the code. Keep it short; resolve what you can from the repo first.

**Verify**: the spec has four `**Decision:**` lines, one per question.

### Step 5: confirm you changed nothing

```
git status --porcelain
```
→ shows exactly two paths: the new spec file and `plans/README.md`.

```
uv run pytest && uv run ruff check && uv run mypy
```
→ all pass, unchanged from before you started.

## Test plan

None. This spike writes a document and changes no behavior. The verification is
that the test suite and all three gates are **byte-for-byte unaffected**, and
that `git status` shows only the two expected paths.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `docs/superpowers/specs/2026-07-08-options-integration-design.md` exists
- [ ] It contains exactly four `**Decision:**` lines (Q1–Q4)
- [ ] Its Q3 section contains pasted real output from `data/options.db`, including a real `occ_symbol`
- [ ] It contains a "What we are deliberately not doing" section
- [ ] It contains an "Open questions for the maintainer" section
- [ ] It recommends a sequenced build with a first increment that is independently shippable
- [ ] `git status --porcelain` lists only the spec file and `plans/README.md`
- [ ] `uv run pytest` exits 0 (unchanged)
- [ ] `uv run ruff check` exits 0 (unchanged)
- [ ] `uv run mypy` exits 0 (unchanged)
- [ ] No file under `sources/`, `deploy/`, `.claude/`, or `data/` was modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- **You are about to modify any file under `sources/`.** This is a spike. The
  deliverable is a document.
- Step 1 shows the blind spots no longer exist (someone already wired options in).
- `option_snapshots` turns out to carry no `iv` **and** no greeks, making both
  Q1 heat models unimplementable without a pricing model. Report; this changes
  the recommendation materially.
- `underlying_daily` has fewer than ~60 distinct `snapshot_date` values **and**
  the CBOE source offers no historical endpoint. Then Q4(d) is not merely
  premature but impossible for months, and the spec should say so loudly rather
  than pretend `v_iv_rank` is ready.
- You conclude the right answer requires a market-data source outside the
  official-sources policy (`CLAUDE.md`) — e.g. a third-party greeks feed. That is
  a maintainer decision. Write it into "Open questions"; do not assume it.
- Any probe requires opening a `data/*.db` **without** `-readonly`.

## Maintenance notes

For the human/agent who owns this after the spec lands:

- **The window for a cheap `decisions` migration is now.** The table holds 2 rows
  and is permanent and never pruned. Every day of equity trading makes an
  option-aware schema change marginally more awkward, and the day the first option
  is traded without one, the `v_flag_response` / `v_human_filter` experiment starts
  recording that trade as a `passed_inferred` — a false negative in the human's
  own track record that cannot be reconstructed later.
- **`v_iv_rank` and `v_unusual_activity` have opposite readiness.** The latter
  "works from day one"; the former needs months of `underlying_daily`. Do not let
  a build plan treat "wire up options signals" as one task.
- **Plan 001 interacts with this.** If the price ledger gets backfilled and the
  scorer starts producing efficacy rows, the argument against adding a 24th
  unmeasured signal (Q4d) weakens considerably. Revisit Q4's sequencing after
  plan 001 has run for a few weeks.
- **What a reviewer should scrutinize**: whether Q1's heat model degrades safely
  (a `NULL` heat that `heat_coverage` reports, never a plausible-but-wrong number),
  and whether Q2's `decisions` change preserves every existing equity row and its
  `order_ref` UNIQUE constraint.
