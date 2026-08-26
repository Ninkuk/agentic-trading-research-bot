"""Your-book and ops sections: the advisor's exit suggestions and option-leg
heat, and the order-execution ledger (queue, run results, reconciliation).

SELECT-only. Broker order ids and the human's free-text `note` never leave
the DB — the published document is public (gh-pages), so rows carry only
symbol, size, price band and outcome.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from dashboard_lib.common import col, fetch, tile, verdict

_EXIT_ADVICE_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("quantity", "Shares"),
    col("price", "Price"),
    col("avg_cost", "Avg cost"),
    col("unrealized_pct", "Unrealized %", direction="up-good"),
    col("stop_price", "Suggested stop"),
    col("stop_distance_pct", "Room to stop %"),
    col("score_sum", "Score"),
    col("strong", "Strong disagreement", numeric=False),
    col("trim_shares", "Trim shares"),
    col("atr_stale", "ATR stale", numeric=False),
]


def exit_advice(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT symbol, quantity, price, avg_cost, unrealized_pct, stop_price,"
        " stop_distance_pct, score_sum, strong, trim_shares, atr_stale FROM v_exit_advice"
        " ORDER BY (trim_shares IS NULL), trim_shares DESC, stop_distance_pct, symbol",
    )
    for r in rows:
        for k in ("strong", "atr_stale"):
            r[k] = None if r[k] is None else bool(r[k])
    trims = sum(1 for r in rows if r["trim_shares"])
    tight = sum(
        1 for r in rows if r["stop_distance_pct"] is not None and r["stop_distance_pct"] < 2
    )
    return {
        "verdict": verdict(
            f"{trims} trim suggestion{'s' if trims != 1 else ''} · {tight} within 2% of stop",
            "off" if trims else "mid" if tight else "on",
        )
        if rows
        else None,
        "columns": _EXIT_ADVICE_COLUMNS,
        "rows": rows,
        "caveat": "Decision support only. A stop here is a suggested distance from a"
        " one-ATR adverse day, not an order anywhere.",
        "empty": "no positions in the latest snapshot",
    }


_OPTION_HEAT_COLUMNS = [
    col("underlying", "Underlying", numeric=False),
    col("type", "Type", numeric=False),
    col("expiration", "Expiry", numeric=False),
    col("quantity", "Contracts"),
    col("delta", "Delta"),
    col("share_equiv", "Share-equivalent"),
    col("market_value", "Value"),
    col("heat_dollars", "Heat $", direction="down-good"),
    col("heat_pct", "Heat %", direction="down-good"),
    col("short_leg", "Short leg", numeric=False),
    col("uncovered", "Uncovered", numeric=False),
]


def option_heat(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT underlying, type, expiration, quantity, delta, share_equiv, market_value,"
        " heat_dollars, heat_pct, short_leg, uncovered FROM v_latest_option_heat"
        " ORDER BY ABS(COALESCE(heat_dollars, 0)) DESC, underlying",
    )
    for r in rows:
        for k in ("short_leg", "uncovered"):
            r[k] = None if r[k] is None else bool(r[k])
    return {
        "columns": _OPTION_HEAT_COLUMNS,
        "rows": rows,
        "empty": "no option legs held in the latest snapshot",
    }


# --- orders.db ---------------------------------------------------------------

_QUEUE_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("qty", "Shares"),
    col("notional", "Dollars"),
    col("ref_price", "Reference price"),
    col("max_gap_pct", "Max gap %"),
    col("expires_on", "Expires", numeric=False),
    col("queued_at", "Queued", numeric=False),
]


def open_queue(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT symbol, qty, notional, ref_price, max_gap_pct, expires_on, queued_at"
        " FROM v_open_queue ORDER BY queued_at",
    )
    return {
        "tiles": [tile("queued buys", len(rows), None, "mid" if rows else "on")],
        "columns": _QUEUE_COLUMNS,
        "rows": rows,
        "empty": "the queue is empty; nothing will be placed at the next open",
    }


_RUN_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("qty", "Shares"),
    col("notional", "Dollars"),
    col("status", "Status", numeric=False),
    col("resolution_reason", "Reason", numeric=False),
    col("limit_price", "Limit"),
    col("outcome", "Outcome", numeric=False),
]


def run_results(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT symbol, qty, notional, status, resolution_reason, limit_price, outcome"
        " FROM v_run_results ORDER BY id DESC",
    )
    placed = sum(1 for r in rows if r["status"] == "placed")
    return {
        "tiles": [
            tile("orders processed", len(rows)),
            tile("placed", placed, None, "on" if placed else None),
            tile(
                "vetoed or failed", len(rows) - placed, None, "off" if len(rows) - placed else None
            ),
        ],
        "columns": _RUN_COLUMNS,
        "rows": rows,
        "empty": "no execution runs recorded yet",
    }


_UNRECONCILED_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("status", "Status", numeric=False),
    col("resolution_reason", "Reason", numeric=False),
]


def unreconciled(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT symbol, status, resolution_reason FROM v_unreconciled ORDER BY id DESC",
    )
    return {
        "verdict": verdict(
            f"{len(rows)} placed order{'s' if len(rows) != 1 else ''} with no journal fill"
            if rows
            else "every placed order has a journal fill",
            "off" if rows else "on",
        ),
        "columns": _UNRECONCILED_COLUMNS,
        "rows": rows,
        "empty": "every placed order has been matched to a journal fill",
    }


SECTIONS: list[Any] = [
    (
        "exit-advice",
        "Exit suggestions",
        "advisor.db",
        exit_advice,
        "Your book",
        "For each holding, where a stop would sit and whether the size has outgrown the signals behind it.",
        [
            (
                "How it is computed",
                "The stop is the price after a one-ATR adverse day from"
                " here; 'room to stop' is how far away that is. A trim"
                " appears when the position is larger than the advisor's cap"
                " for its current score.",
            ),
            (
                "What to do with it",
                "Nothing automatic happens. Read a trim as 'the signals no"
                " longer support this size' and a tight stop as 'one bad"
                " day is close' — then decide.",
            ),
        ],
    ),
    (
        "option-heat",
        "Option legs",
        "advisor.db",
        option_heat,
        "Your book",
        "Each option position's share-equivalent exposure and what a one-ATR move would cost.",
        [
            (
                "How it is computed",
                "Delta × contracts × 100 is the share-equivalent; heat is"
                " that many shares moving one ATR. A protective put counts"
                " negative and offsets the shares it covers in the group"
                " view.",
            ),
            (
                "Uncovered legs",
                "A leg with no delta input or a short leg is marked"
                " uncovered — its risk is unknown or open-ended, so the book"
                " heat number above it is a floor, not a total.",
            ),
        ],
    ),
    (
        "order-queue",
        "Order queue",
        "orders.db",
        open_queue,
        "Ops",
        "Buys you have queued that have not yet been placed.",
        [
            (
                "How it works",
                "You queue a buy with a reference price and a maximum gap;"
                " the morning slot places it at the open only if the live"
                " quote is within that band, otherwise it vetoes and the row"
                " lands in the run results.",
            ),
            (
                "Why it is on the page",
                "A queued order is a pending commitment of real money — it"
                " should never be a surprise the next morning.",
            ),
        ],
    ),
    (
        "order-runs",
        "Execution runs",
        "orders.db",
        run_results,
        "Ops",
        "Every queued order the executor has processed and what happened to it.",
        [
            (
                "How to read it",
                "'placed' means an order went to the broker under the limit"
                " ceiling; a veto names the gate that stopped it (price gap,"
                " cap, market closed). Outcome is the broker's final state"
                " where known.",
            ),
        ],
    ),
    (
        "order-reconciliation",
        "Unreconciled orders",
        "orders.db",
        unreconciled,
        "Ops",
        "Orders the executor placed that the journal has not yet seen a fill for.",
        [
            (
                "Why it matters",
                "The journal is what the grades run on. A placed order with"
                " no fill row means either the broker never filled it or"
                " the nightly journal sync missed it — both need a look.",
            ),
        ],
    ),
]
