"""Pure parsing of the combined account/positions JSON document. No network:
Claude (the human-triggered command layer) fetches via the Robinhood MCP and
hands the doc to run.py — this module only validates and normalizes it."""

from datetime import date

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


def _bare_date(s):
    """s if it is a bare YYYY-MM-DD calendar-date string, else None."""
    if not isinstance(s, str) or len(s) != 10:
        return None
    try:
        date.fromisoformat(s)
    except ValueError:
        return None
    return s


def parse_snapshot(doc) -> tuple:
    """(account, positions, option_positions, skipped_count) from the
    combined document {"account": {...}, "positions": [...],
    "option_positions": [...]}. Rows missing identity or a numeric quantity
    are skipped and counted (skip-and-continue), never fatal; a structurally
    wrong document raises ValueError. option_positions is capture-only:
    nothing downstream reads it yet (advisor heat stays equity-only until
    increment (c) of the options spec)."""
    if not isinstance(doc, dict):
        raise ValueError("document must be a JSON object")
    raw_account = doc.get("account") or {}
    raw_positions = doc.get("positions", [])
    raw_options = doc.get("option_positions", [])
    if (
        not isinstance(raw_account, dict)
        or not isinstance(raw_positions, list)
        or not isinstance(raw_options, list)
    ):
        raise ValueError("account must be an object, positions/option_positions lists")

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
        positions.append(
            {
                "symbol": symbol.strip().upper().replace(".", "-"),
                "quantity": quantity,
                "avg_cost": _num(_first(raw, catalog.POSITION_FIELDS["avg_cost"])),
                "market_value": _num(_first(raw, catalog.POSITION_FIELDS["market_value"])),
            }
        )

    option_positions = []
    f = catalog.OPTION_POSITION_FIELDS
    for raw in raw_options:
        if not isinstance(raw, dict):
            skipped += 1
            continue
        occ = _first(raw, f["occ_symbol"])
        underlying = _first(raw, f["underlying"])
        quantity = _num(_first(raw, f["quantity"]))
        if (
            not occ
            or not isinstance(occ, str)
            or not underlying
            or not isinstance(underlying, str)
            or quantity is None
        ):
            skipped += 1
            continue
        # Sign is pinned HERE: a short leg stores a negative quantity, so
        # downstream (signed delta-dollar heat) never re-derives direction.
        ptype = _first(raw, ("position_type", "side"))
        if isinstance(ptype, str) and ptype.lower() == "short":
            quantity = -abs(quantity)
        elif isinstance(ptype, str) and ptype.lower() == "long":
            quantity = abs(quantity)
        otype = _first(raw, f["type"])
        otype = otype.lower() if isinstance(otype, str) else None
        option_positions.append(
            {
                "occ_symbol": occ.strip().upper(),
                "underlying": underlying.strip().upper().replace(".", "-"),
                "type": otype if otype in ("call", "put") else None,
                "strike": _num(_first(raw, f["strike"])),
                "expiration": _bare_date(_first(raw, f["expiration"])),
                "quantity": quantity,
                "avg_cost": _num(_first(raw, f["avg_cost"])),
                "market_value": _num(_first(raw, f["market_value"])),
                "multiplier": _num(_first(raw, f["multiplier"])),
            }
        )
    return account, positions, option_positions, skipped
