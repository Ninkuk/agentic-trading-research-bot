---
name: account-positions
description: Snapshot live Robinhood account state (equity and option positions, equity, cash, buying power) into data/portfolio.db via the portfolio screener. Use when the user asks to sync/refresh/resolve account positions, or before any sizing review that should see real holdings.
---

# account-positions

Resolve the live brokerage account and store it **as data** in
`data/portfolio.db`. Guiding invariant: Claude may fetch live state via MCP,
but it enters the system only through the `portfolio` dispatcher — downstream
consumers stay offline-testable. Never write SQL against portfolio.db
directly.

## Procedure

1. Fetch via the Robinhood MCP (read-only tools):
   - `get_accounts` → the **account pin only** (below). It carries neither
     cash nor buying power, and its own tool contract calls its buying-power
     figure unreliable — take both from `get_portfolio`.
   - `get_portfolio` → `total_value` (equity, incl. cash), `cash`,
     `buying_power.buying_power`
   - `get_equity_positions` → per-position symbol, quantity, average buy
     price. It carries **no market price** — see the next bullet.
   - `get_equity_quotes` on the held symbols → per-position `market_value`
     is **derived**: price × quantity. The positions payload dropped
     `market_value` upstream and its guide now says "No market price here"
     (verified 2026-08-04). Omitting this getter from the wrapper's
     allowlist is a silent weekday outage: headless, the denial has nobody
     to approve it, so no snapshot lands and the slot exits 1 — which is
     exactly how 2026-08-03/04 failed.
   - `get_option_positions` → per-contract legs (see the
     `option_positions` bullet below); zero open contracts is normal —
     emit an empty array, don't omit the key

   **Account pin**: always use the **"Agentic" account (number ending
   1936)**. If `get_accounts` returns more than one account, select it by
   name/last-4 and scope the portfolio and positions calls to it; if no
   account matches, stop and report — never fall back to a different
   account.
2. Build ONE combined JSON document in the scratchpad (never paste raw MCP
   payloads into the conversation — they can carry account identifiers):

   ```json
   {"account": {"equity": 205.37, "cash": 12.40, "buying_power": 12.40},
    "positions": [{"symbol": "GLD", "quantity": 0.5,
                   "average_buy_price": 301.20, "market_value": 155.00}]}
   ```

   Field aliases accepted per position: `quantity`/`shares`,
   `average_buy_price`/`avg_cost`/`average_cost`, `market_value`/`equity`
   (see `sources/screeners/portfolio_screener/catalog.py`).

   - `option_positions`: one entry per contract leg —
     `{"occ_symbol", "underlying", "type": "call"|"put", "strike",
     "expiration": "YYYY-MM-DD", "quantity", "position_type":
     "long"|"short", "avg_cost", "market_value", "multiplier"}`.
     `occ_symbol` + `underlying` + numeric `quantity` are required (rows
     missing them are skipped and counted); a `"short"` position_type is
     stored as a **negative** quantity — the sign is load-bearing (advisor
     nets signed delta-dollar heat per group). Legs whose heat inputs are
     missing (contract outside options.db's catalog, stale delta) and ALL
     short legs surface in `v_book_heat.uncovered_option_legs` — mention
     that count in the report when it is non-zero.

   `account.equity` is the account's total value **including cash** (take
   `get_portfolio`'s equity as-is — with zero positions it equals cash, not
   0). To revise the file, re-`Write` the whole document: the headless slot
   allowlists `Write` but not `Edit`, so an `Edit` call dies on a permission
   prompt no one is there to approve (this exact failure produced the
   2026-07-23 stale-snapshot alert).
3. Ingest:

   ```bash
   uv run python main.py portfolio --db data/portfolio.db --input <scratchpad>/portfolio.json --keep-days 365
   ```

4. Report to the user: snapshot id, position count (+ skipped count if any),
   and equity / cash / buying power.

## Rules

- **Secret hygiene**: on any MCP or CLI error report the exception type name
  only — never message bodies, URLs, or payload fragments.
- **Write scope**: this command writes ONLY `data/portfolio.db`, only via
  the dispatcher. Everything else it touches is read-only.
- Positions missing symbol or a numeric quantity are skipped and counted by
  the parser — mention the skip count rather than retrying by hand.
- Tax lots (`get_equity_tax_lots`) are available live and are **deliberately not
  persisted** — this command writes only the blended position snapshot. Read
  them at decision time via `kill-thesis`, not here.
