---
name: account-positions
description: Snapshot live Robinhood account state (positions, equity, cash, buying power) into data/portfolio.db via the portfolio screener. Use when the user asks to sync/refresh/resolve account positions, or before any sizing review that should see real holdings.
---

# account-positions

Resolve the live brokerage account and store it **as data** in
`data/portfolio.db`. Guiding invariant: Claude may fetch live state via MCP,
but it enters the system only through the `portfolio` dispatcher — downstream
consumers stay offline-testable. Never write SQL against portfolio.db
directly.

## Procedure

1. Fetch via the Robinhood MCP (read-only tools):
   - `get_accounts` → cash, buying power
   - `get_portfolio` → equity (market value)
   - `get_equity_positions` → per-position symbol, quantity, average buy
     price, market value

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
