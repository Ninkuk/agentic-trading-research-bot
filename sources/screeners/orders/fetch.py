"""Pure parsing of the JSON documents the execute-queue / journal-sync
sessions pipe in — NO network (inverted slice, like portfolio_screener).
Field names here (ask, quote_ts, settled_cash) are the contract the skills
write; the mandated interactive first run verifies them against live MCP
responses before the launchd job is ever armed. Every structural problem is
a ValueError naming the offending field — callers print type names only."""

import json
from dataclasses import dataclass

__all__ = [
    "Quote",
    "PlanInput",
    "PlacementResult",
    "BrokerOrder",
    "parse_plan_input",
    "parse_record_input",
    "parse_reconcile_input",
]


@dataclass(frozen=True)
class Quote:
    symbol: str
    ask: float | None
    quote_ts: str | None
    state: str | None = None  # broker instrument state; anything non-'active' is vetoed


@dataclass(frozen=True)
class PlanInput:
    as_of: str
    quotes: dict[str, Quote]
    settled_cash: float


@dataclass(frozen=True)
class PlacementResult:
    queue_id: int
    ref_id: str
    account_number: str
    order_id: str | None
    state: str  # 'placed' | 'error'
    raw: str


@dataclass(frozen=True)
class BrokerOrder:
    order_id: str
    ref_id: str | None
    symbol: str
    state: str


def _require(doc: dict, key: str, ctx: str):
    if not isinstance(doc, dict) or key not in doc:
        raise ValueError(f"{ctx} missing {key}")
    return doc[key]


def _number(value, ctx: str) -> float:
    """Accept a number OR a numeric string: the Robinhood MCP returns every
    price as a decimal string ('737.250000', '200.4000') — verified live
    2026-07-27 — and the transcribing session must copy values verbatim, so
    the deterministic layer owns the conversion."""
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"{ctx} is not numeric") from None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{ctx} is not a number")
    return float(value)


def parse_plan_input(doc: dict) -> PlanInput:
    as_of = _require(doc, "as_of", "document")
    if not isinstance(as_of, str) or not as_of:
        raise ValueError("as_of is not a string")
    raw_quotes = _require(doc, "quotes", "document")
    if not isinstance(raw_quotes, list):
        raise ValueError("quotes is not a list")
    quotes: dict[str, Quote] = {}
    for i, q in enumerate(raw_quotes):
        symbol = _require(q, "symbol", f"quotes[{i}]")
        if not isinstance(symbol, str) or not symbol:
            raise ValueError(f"quotes[{i}] symbol is not a string")
        ask = q.get("ask")
        quote_ts = q.get("quote_ts")
        if quote_ts is not None and not isinstance(quote_ts, str):
            raise ValueError(f"quotes[{i}].quote_ts must be a string or null")
        state = q.get("state")
        if state is not None and not isinstance(state, str):
            raise ValueError(f"quotes[{i}].state must be a string or null")
        quotes[symbol] = Quote(
            symbol=symbol,
            ask=None if ask is None else _number(ask, f"quotes[{i}].ask"),
            quote_ts=quote_ts,
            state=state,
        )
    portfolio = _require(doc, "portfolio", "document")
    settled_cash = _number(
        _require(portfolio, "settled_cash", "portfolio"), "portfolio.settled_cash"
    )
    return PlanInput(as_of=as_of, quotes=quotes, settled_cash=settled_cash)


def parse_record_input(doc: dict) -> list[PlacementResult]:
    raw_results = _require(doc, "results", "document")
    if not isinstance(raw_results, list):
        raise ValueError("results is not a list")
    results = []
    for i, r in enumerate(raw_results):
        state = _require(r, "state", f"results[{i}]")
        if state not in ("placed", "error"):
            raise ValueError(f"results[{i}] state must be placed|error")
        queue_id = _require(r, "queue_id", f"results[{i}]")
        if not isinstance(queue_id, int) or isinstance(queue_id, bool):
            raise ValueError(f"results[{i}] queue_id is not an int")
        ref_id = _require(r, "ref_id", f"results[{i}]")
        account = _require(r, "account_number", f"results[{i}]")
        if not isinstance(ref_id, str) or not isinstance(account, str):
            raise ValueError(f"results[{i}] ref_id/account_number must be strings")
        order_id = r.get("order_id")
        if order_id is not None and not isinstance(order_id, str):
            raise ValueError(f"results[{i}] order_id must be a string or null")
        results.append(
            PlacementResult(
                queue_id=queue_id,
                ref_id=ref_id,
                account_number=account,
                order_id=order_id,
                state=state,
                raw=json.dumps(r.get("raw"), sort_keys=True),
            )
        )
    return results


def parse_reconcile_input(doc: dict) -> list[BrokerOrder]:
    raw_orders = _require(doc, "orders", "document")
    if not isinstance(raw_orders, list):
        raise ValueError("orders is not a list")
    orders = []
    for i, o in enumerate(raw_orders):
        order_id = _require(o, "order_id", f"orders[{i}]")
        symbol = _require(o, "symbol", f"orders[{i}]")
        if not isinstance(order_id, str) or not isinstance(symbol, str):
            raise ValueError(f"orders[{i}] order_id/symbol must be strings")
        ref_id = o.get("ref_id")
        if ref_id is not None and not isinstance(ref_id, str):
            raise ValueError(f"orders[{i}] ref_id must be a string or null")
        orders.append(
            BrokerOrder(
                order_id=order_id,
                ref_id=ref_id,
                symbol=symbol,
                state=str(o.get("state", "")),
            )
        )
    return orders
