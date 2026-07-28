"""The market-open order queue: the repo's ONLY broker write path.

The human queues exact buys (queue, human-only); a headless session executes
them behind deterministic checks (preflight -> plan -> record) and the
afternoon journal slot audits the result (reconcile). Python decides
everything before the MCP calls and audits everything after — the session
only transcribes the plan param-for-param. Money safety rests on:

- the atomic BEGIN IMMEDIATE claim (queued->planned flips exactly once, even
  under wake-coalesced duplicate sessions — there is no flock on macOS),
- the per-order ref_id UUID the broker deduplicates on,
- the limit ceiling ref_price*(1+max_gap_pct) from human-supplied numbers,
- enumerated wrapper Bash grants (queue/resolve are never granted headless).
"""

import argparse
import json
import os
import sqlite3
import sys
import uuid
from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal

from sources.common.clock import phx_date
from sources.monitors.market_calendar import db as cal_db
from sources.screeners.orders import catalog, db, fetch, market_clock
from sources.screeners.orders.catalog import SLIPPAGE, STALE_QUOTE_SEC
from sources.screeners.orders.fetch import PlanInput, Quote


def _write_run(conn: sqlite3.Connection, now_iso: str, phase: str, detail: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO runs (captured_at, phase, detail) VALUES (?, ?, ?)",
        (now_iso, phase, detail),
    )
    return int(cur.lastrowid or 0)


def _calendar_blind(cal_conn: sqlite3.Connection, now_iso: str) -> bool:
    """No future market_holiday events (or no events table at all) means the
    calendar cannot be trusted to say 'holiday' — refuse to fly, don't guess."""
    try:
        (n,) = cal_conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_type='market_holiday' AND event_date >= ?",
            (phx_date(now_iso),),
        ).fetchone()
    except sqlite3.OperationalError:
        return True
    return int(n) == 0


def _trading_day(cal_db_path: str, now_iso: str) -> bool:
    """is_trading_day for today's Phoenix date; raises on a blind calendar."""
    conn = cal_db.connect(cal_db_path)
    try:
        if _calendar_blind(conn, now_iso):
            raise ValueError("market calendar is blind (no future market_holiday events)")
        return bool(cal_db.is_trading_day(conn, phx_date(now_iso)))
    finally:
        conn.close()


def _age_sec(quote_ts: str, now_iso: str) -> float:
    try:
        ts = datetime.fromisoformat(quote_ts)
        now = datetime.fromisoformat(now_iso)
    except ValueError:
        return float("inf")
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return (now - ts).total_seconds()


def _compute_decision(
    row: dict,
    quote: Quote | None,
    now_iso: str,
    limits: catalog.Limits,
    spent_so_far: Decimal,
    settled_cash: float,
) -> tuple[str, str]:
    """Pure per-row decision. Returns ('planned', limit_price_str) or
    (terminal_status, reason)."""
    if row["expires_on"] < phx_date(now_iso):
        return "expired", f"expired {row['expires_on']}"
    if quote is None or quote.ask is None or quote.ask <= 0:
        return "vetoed", "no usable ask (halted/missing quote)"
    if quote.quote_ts is None or _age_sec(quote.quote_ts, now_iso) > STALE_QUOTE_SEC:
        return "vetoed", "stale quote"
    ceiling = Decimal(str(row["ref_price"])) * (
        Decimal("1") + Decimal(str(row["max_gap_pct"])) / Decimal("100")
    )
    if Decimal(str(quote.ask)) > ceiling:
        return "vetoed", f"gapped: ask {quote.ask} > ceiling {ceiling:.2f}"
    limit = min(Decimal(str(quote.ask)) * SLIPPAGE, ceiling).quantize(
        Decimal("0.01"), rounding=ROUND_DOWN
    )
    notional = limit * row["qty"]
    if notional > Decimal(str(limits.max_order_notional)):
        return "vetoed", f"order notional {notional} over cap"
    if spent_so_far + notional > Decimal(str(limits.max_daily_notional)):
        return "vetoed", "daily notional cap"
    if Decimal(str(settled_cash)) - spent_so_far - notional < Decimal(str(limits.cash_floor)):
        return "vetoed", "cash floor"
    return "planned", str(limit)


def run_queue(
    db_path: str,
    cal_db_path: str,
    symbol: str,
    qty: int,
    ref_price: float,
    max_gap_pct: float,
    expires_on: str | None,
    note: str | None,
    now_iso: str,
    stdin_isatty: bool,
    env: dict,
) -> int:
    """Insert one human buy decision. Semantics: buy at the NEXT market open,
    then every open until expires_on (Phoenix date, inclusive)."""
    if not stdin_isatty and env.get("ORDERS_ALLOW_NONINTERACTIVE") != "1":
        raise ValueError(
            "refusing non-interactive queue (set ORDERS_ALLOW_NONINTERACTIVE=1 from"
            " a human-driven session; the headless slot must never gain it)"
        )
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("symbol is empty")
    if qty < 1 or int(qty) != qty:
        raise ValueError("qty must be a positive whole number of shares")
    if ref_price < catalog.MIN_REF_PRICE:
        raise ValueError(f"ref_price below ${catalog.MIN_REF_PRICE} (sub-$1 names unsupported)")
    if not 0 <= max_gap_pct <= 20:
        raise ValueError("max_gap_pct must be within [0, 20]")
    if expires_on is None:
        cal_conn = cal_db.connect(cal_db_path)
        try:
            if _calendar_blind(cal_conn, now_iso):
                raise ValueError(
                    "market calendar is blind — cannot default expiry; pass --expires explicitly"
                )
            expires_on = str(cal_db.next_trading_day(cal_conn, phx_date(now_iso)))
        finally:
            cal_conn.close()
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        (dup,) = conn.execute(
            "SELECT COUNT(*) FROM queue WHERE symbol = ? AND status = 'queued'", (symbol,)
        ).fetchone()
        if dup:
            raise ValueError(f"duplicate open queue row for {symbol}")
        cur = conn.execute(
            "INSERT INTO queue (symbol, qty, ref_price, max_gap_pct, expires_on, note,"
            " queued_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (symbol, qty, ref_price, max_gap_pct, expires_on, note, now_iso),
        )
        conn.commit()
        return int(cur.lastrowid or 0)
    finally:
        conn.close()


def run_preflight(db_path: str, cal_db_path: str, now_iso: str) -> tuple[int, list[str]]:
    """The wrapper's cheap gate. (0, symbols) go; (3, []) quiet stand-down;
    (1, []) loud calendar-blind. Always writes a preflight runs header."""
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        try:
            trading = _trading_day(cal_db_path, now_iso)
        except ValueError:
            _write_run(conn, now_iso, "preflight", "calendar-blind")
            conn.commit()
            return 1, []
        state = market_clock.window_state(now_iso, trading)
        if state != "open":
            _write_run(conn, now_iso, "preflight", f"stand-down: {state}")
            conn.commit()
            return 3, []
        symbols = [r[0] for r in conn.execute("SELECT symbol FROM v_open_queue").fetchall()]
        if not symbols:
            _write_run(conn, now_iso, "preflight", "stand-down: empty queue")
            conn.commit()
            return 3, []
        _write_run(conn, now_iso, "preflight", f"go: {len(symbols)} symbols")
        conn.commit()
        return 0, symbols
    finally:
        conn.close()


def run_plan(db_path: str, cal_db_path: str, doc: dict, now_iso: str, env: dict) -> dict:
    """All safety arithmetic + the atomic claim, in ONE BEGIN IMMEDIATE
    transaction: two concurrent plans cannot claim the same row, and a
    rollback erases the runs header so the wrapper's freshness check fires."""
    limits = catalog.load_limits(env)
    pi: PlanInput = fetch.parse_plan_input(doc)
    trading = _trading_day(cal_db_path, now_iso)
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        planned: list[dict] = []
        conn.execute("BEGIN IMMEDIATE")
        _write_run(conn, now_iso, "plan")
        if market_clock.window_state(now_iso, trading) != "open":
            conn.commit()
            return {"account_number": limits.account_number, "orders": []}
        rows = conn.execute(
            "SELECT id, symbol, qty, ref_price, max_gap_pct, expires_on"
            " FROM queue WHERE status='queued' ORDER BY id"
        ).fetchall()
        spent = Decimal("0")
        for row_t in rows:
            row = dict(
                zip(
                    ("id", "symbol", "qty", "ref_price", "max_gap_pct", "expires_on"),
                    row_t,
                    strict=True,
                )
            )
            status, detail = _compute_decision(
                row, pi.quotes.get(row["symbol"]), now_iso, limits, spent, pi.settled_cash
            )
            if status == "planned":
                ref_id = str(uuid.uuid4())
                spent += Decimal(detail) * row["qty"]
                conn.execute(
                    "UPDATE queue SET status='planned', ref_id=?, planned_limit=?,"
                    " resolved_at=?, resolution_reason='planned'"
                    " WHERE id=? AND status='queued'",
                    (ref_id, detail, now_iso, row["id"]),
                )
                planned.append(
                    {
                        "queue_id": row["id"],
                        "symbol": row["symbol"],
                        "qty": str(row["qty"]),
                        "limit_price": detail,
                        "ref_id": ref_id,
                    }
                )
            else:
                conn.execute(
                    "UPDATE queue SET status=?, resolved_at=?, resolution_reason=?"
                    " WHERE id=? AND status='queued'",
                    (status, now_iso, detail, row["id"]),
                )
        conn.commit()
        return {"account_number": limits.account_number, "orders": planned}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def run_record(db_path: str, doc: dict, now_iso: str, env: dict) -> tuple[int, int]:
    """Audit what the session did. limit_price comes from queue.planned_limit
    (persisted at claim time) — never from the session-authored doc, so the
    audit column cannot be fabricated. Broker errors leave the row planned
    (v_unreconciled + the wrapper's STUCK check surface it same-day)."""
    limits = catalog.load_limits(env)
    results = fetch.parse_record_input(doc)
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        run_id = _write_run(conn, now_iso, "record", f"{len(results)} results")
        placed = errors = 0
        for r in results:
            if r.account_number != limits.account_number:
                raise ValueError(f"account mismatch on queue row {r.queue_id}")
            got = conn.execute(
                "SELECT ref_id, planned_limit FROM queue WHERE id=? AND status='planned'",
                (r.queue_id,),
            ).fetchone()
            if got is None or got[0] != r.ref_id:
                raise ValueError(f"unknown or mismatched ref_id for queue row {r.queue_id}")
            planned_limit = got[1]
            if planned_limit is None:
                raise ValueError(f"queue row {r.queue_id} has no planned_limit")
            conn.execute(
                "INSERT INTO placements (queue_id, run_id, ref_id, account_number,"
                " limit_price, order_id, outcome, raw, recorded_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    r.queue_id,
                    run_id,
                    r.ref_id,
                    r.account_number,
                    planned_limit,
                    r.order_id,
                    "placed" if r.state == "placed" else "error",
                    r.raw,
                    now_iso,
                ),
            )
            if r.state == "placed":
                conn.execute(
                    "UPDATE queue SET status='placed', resolved_at=?,"
                    " resolution_reason='placed' WHERE id=? AND status='planned'",
                    (now_iso, r.queue_id),
                )
                placed += 1
            else:
                errors += 1
        conn.commit()
        return placed, errors
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def run_reconcile(db_path: str, doc: dict, now_iso: str) -> dict:
    """Afternoon cross-check against the broker's own order list: confirm
    placements both directions, flag orphans. An orphan placement (we say
    placed, broker has no order) is always serious; an orphan order carrying
    one of our ref_ids is serious (session placed off-plan); a ref_id-less
    orphan order is likely the human's own manual trade."""
    broker_orders = fetch.parse_reconcile_input(doc)
    by_order_id = {o.order_id: o for o in broker_orders}
    by_ref_id = {o.ref_id: o for o in broker_orders if o.ref_id}
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        _write_run(conn, now_iso, "reconcile", f"{len(broker_orders)} broker orders")
        confirmed = 0
        orphan_placements = []
        known_order_ids: set[str] = set()
        for pid, order_id, ref_id, already in conn.execute(
            "SELECT id, order_id, ref_id, confirmed_at FROM placements WHERE outcome='placed'"
        ).fetchall():
            if order_id:
                known_order_ids.add(order_id)
            match = by_order_id.get(order_id) or by_ref_id.get(ref_id)
            if match is not None:
                if already is None:
                    conn.execute("UPDATE placements SET confirmed_at=? WHERE id=?", (now_iso, pid))
                    confirmed += 1
            elif already is None:
                orphan_placements.append({"order_id": order_id, "ref_id": ref_id})
        our_refs = {r[0] for r in conn.execute("SELECT ref_id FROM placements").fetchall() if r[0]}
        orphan_orders = [
            {
                "order_id": o.order_id,
                "ref_id": o.ref_id,
                "symbol": o.symbol,
                "likely_manual": o.ref_id is None or o.ref_id not in our_refs,
            }
            for o in broker_orders
            if o.order_id not in known_order_ids and (o.ref_id or "") not in our_refs
        ]
        conn.commit()
        return {
            "confirmed": confirmed,
            "orphan_placements": orphan_placements,
            "orphan_orders": orphan_orders,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def run_resolve(
    db_path: str, queue_id: int, as_state: str, order_id: str | None, now_iso: str
) -> None:
    """The sanctioned human-only exit from a stuck planned row (never ad-hoc
    SQL). --as placed writes a confirming placement; --as failed closes the
    row terminally."""
    if as_state not in ("placed", "failed"):
        raise ValueError("resolve --as must be placed|failed")
    if as_state == "placed" and not order_id:
        raise ValueError("resolve --as placed requires --order-id")
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        got = conn.execute(
            "SELECT ref_id, planned_limit FROM queue WHERE id=? AND status='planned'",
            (queue_id,),
        ).fetchone()
        if got is None:
            raise ValueError(f"queue row {queue_id} is not in status 'planned'")
        if as_state == "placed":
            run_id = _write_run(conn, now_iso, "record", "manual resolve")
            conn.execute(
                "INSERT INTO placements (queue_id, run_id, ref_id, account_number,"
                " limit_price, order_id, outcome, confirmed_at, raw, recorded_at)"
                " VALUES (?, ?, ?, 'manual-resolve', ?, ?, 'placed', ?, '{}', ?)",
                (queue_id, run_id, got[0] or "", got[1] or "", order_id, now_iso, now_iso),
            )
            conn.execute(
                "UPDATE queue SET status='placed', resolved_at=?,"
                " resolution_reason='manual resolve' WHERE id=?",
                (now_iso, queue_id),
            )
        else:
            conn.execute(
                "UPDATE queue SET status='failed', resolved_at=?,"
                " resolution_reason='manual' WHERE id=?",
                (now_iso, queue_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _load_doc(path: str) -> dict:
    if path == "-":
        return dict(json.load(sys.stdin))
    with open(path, encoding="utf-8") as f:
        return dict(json.load(f))


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="orders", description="Market-open order queue")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("queue", help="queue a buy for the next market open (human-only)")
    q.add_argument("--db", default="orders.db")
    q.add_argument("--calendar-db", default="market_calendar.db")
    q.add_argument("--symbol", required=True)
    q.add_argument("--qty", type=int, required=True)
    q.add_argument("--ref-price", type=float, required=True)
    q.add_argument("--max-gap-pct", type=float, required=True)
    q.add_argument("--expires", default=None, help="Phoenix date; default next trading day")
    q.add_argument("--note", default=None, help="rationale — carried into the journal")

    for name in ("preflight", "plan", "record", "reconcile"):
        s = sub.add_parser(name)
        s.add_argument("--db", default="orders.db")
        if name == "preflight":
            s.add_argument("--calendar-db", default="market_calendar.db")
        if name == "plan":
            s.add_argument("--calendar-db", default="market_calendar.db")
            s.add_argument("--input", required=True)
        if name in ("record", "reconcile"):
            s.add_argument("--input", required=True)

    r = sub.add_parser("resolve", help="human-only exit from a stuck planned row")
    r.add_argument("--db", default="orders.db")
    r.add_argument("--id", type=int, required=True, dest="queue_id")
    r.add_argument("--as", required=True, choices=("placed", "failed"), dest="as_state")
    r.add_argument("--order-id", default=None)

    a = p.parse_args(argv)
    now_iso = datetime.now(UTC).isoformat()

    try:
        if a.cmd == "queue":
            qid = run_queue(
                a.db,
                a.calendar_db,
                a.symbol,
                a.qty,
                a.ref_price,
                a.max_gap_pct,
                a.expires,
                a.note,
                now_iso,
                sys.stdin.isatty(),
                dict(os.environ),
            )
            print(f"queued #{qid}: {a.symbol.upper()} x{a.qty} into {a.db}")
        elif a.cmd == "preflight":
            code, symbols = run_preflight(a.db, a.calendar_db, now_iso)
            if code == 0:
                for s_ in symbols:
                    print(s_)
            elif code == 3:
                print("stand-down")
            else:
                print("error: calendar-blind — refuse to fly", file=sys.stderr)
            raise SystemExit(code)
        elif a.cmd == "plan":
            plan = run_plan(a.db, a.calendar_db, _load_doc(a.input), now_iso, dict(os.environ))
            print(json.dumps(plan))
        elif a.cmd == "record":
            placed, errors = run_record(a.db, _load_doc(a.input), now_iso, dict(os.environ))
            print(f"recorded: {placed} placed, {errors} errors into {a.db}")
            if errors:
                raise SystemExit(1)
        elif a.cmd == "reconcile":
            report = run_reconcile(a.db, _load_doc(a.input), now_iso)
            print(json.dumps(report))
        elif a.cmd == "resolve":
            run_resolve(a.db, a.queue_id, a.as_state, a.order_id, now_iso)
            print(f"resolved #{a.queue_id} as {a.as_state}")
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    except OSError as e:
        print(f"error: cannot read input: {type(e).__name__}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
