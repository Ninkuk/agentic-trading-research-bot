"""Pure parsing of the combined account/positions JSON document. No network:
Claude (the human-triggered command layer) fetches via the Robinhood MCP and
hands the doc to run.py — this module only validates and normalizes it."""
from sources.screeners.portfolio_screener import catalog


def _num(value):
    """Tolerant numeric coercion: int/float/numeric-string -> float; anything
    else (None, '', 'lots', bool) -> None."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first(mapping: dict, aliases: tuple):
    for key in aliases:
        if key in mapping:
            return mapping[key]
    return None


def parse_snapshot(doc) -> tuple:
    """(account, positions, skipped_count) from the combined document
    {"account": {...}, "positions": [...]}. Positions missing a symbol or a
    numeric quantity are skipped and counted (skip-and-continue), never
    fatal; a structurally wrong document raises ValueError."""
    if not isinstance(doc, dict):
        raise ValueError("document must be a JSON object")
    raw_account = doc.get("account") or {}
    raw_positions = doc.get("positions", [])
    if not isinstance(raw_account, dict) or not isinstance(raw_positions, list):
        raise ValueError("account must be an object, positions a list")

    account = {f: _num(raw_account.get(f)) for f in catalog.ACCOUNT_FIELDS}

    positions, skipped = [], 0
    for raw in raw_positions:
        if not isinstance(raw, dict):
            skipped += 1
            continue
        symbol = raw.get("symbol")
        quantity = _num(_first(raw, catalog.POSITION_FIELDS["quantity"]))
        if not symbol or not isinstance(symbol, str) or quantity is None:
            skipped += 1
            continue
        positions.append({
            "symbol": symbol.strip().upper().replace(".", "-"),
            "quantity": quantity,
            "avg_cost": _num(_first(raw, catalog.POSITION_FIELDS["avg_cost"])),
            "market_value": _num(
                _first(raw, catalog.POSITION_FIELDS["market_value"])),
        })
    return account, positions, skipped
