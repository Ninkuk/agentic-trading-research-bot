"""Field maps for the account snapshot (CLAUDE_ROADMAP `account-positions`).

Unlike every other screener, the upstream here is not an HTTP endpoint but a
JSON document Claude assembles from the Robinhood MCP tools (get_accounts /
get_portfolio / get_equity_positions) — data enters the system through this
package's dispatcher, never as live calls, so downstream consumers stay
offline-testable. MCP payload shapes vary between tool versions; each target
field lists its accepted aliases, first match wins."""

ACCOUNT_FIELDS = ("equity", "cash", "buying_power")

POSITION_FIELDS = {
    "quantity": ("quantity", "shares"),
    "avg_cost": ("average_buy_price", "avg_cost", "average_cost"),
    "market_value": ("market_value", "equity"),
}

# get_option_positions payload → option_positions row. Column names follow
# cboe_options (occ_symbol/underlying/type/strike/expiration) so the two
# stores speak the same vocabulary. quantity is SIGNED: short legs negative
# (see fetch.parse_snapshot).
OPTION_POSITION_FIELDS = {
    "occ_symbol": ("occ_symbol", "option_symbol", "occ"),
    "underlying": ("underlying", "chain_symbol", "underlying_symbol"),
    "type": ("type", "right", "option_type"),
    "strike": ("strike", "strike_price"),
    "expiration": ("expiration", "expiration_date"),
    "quantity": ("quantity", "contracts"),
    "avg_cost": ("average_buy_price", "avg_cost", "average_cost", "average_open_price"),
    "market_value": ("market_value", "equity"),
    "multiplier": ("multiplier", "contract_multiplier", "trade_multiplier"),
}
