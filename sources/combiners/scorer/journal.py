"""Decision journal: what the human did about composite opinions. Ingests
one JSON doc of fills/passes (built by the journal-sync skill from Robinhood
MCP order history, or dictated manually) and stores decisions permanently in
scorer.db next to the outcomes they are graded against.

Matching is deterministic (headless scheduled runs cannot stop to confirm)
and reads composite.db ATTACHed read-only rather than ticker_outcomes:
registration lags one night (next-day-close entries), so a morning-after
fill would otherwise misclassify as freelance. The opinion exists in
composite.db the night it forms; once matched, the decision's
(composite_snapshot_id, symbol) key joins the scorer's permanent outcome
rows and never needs composite.db again. Decisions are never pruned — they
are the other half of the experiment."""

from datetime import UTC, datetime, timedelta

# Calendar days an opinion stays matchable to a later fill: covers the
# morning-after trade plus a long weekend. Two snapshots in the window
# resolve to the most recent one. (Flag thresholds live in db.py — shared
# with the v_flag_response view.)
MATCH_WINDOW_DAYS = 5


def _phx_date(dt) -> str:
    """Phoenix-local date (UTC-7 fixed, no DST) of an aware datetime — the
    clock composite_date is on (see fetch.read_snapshots). fill_date must
    share it: with a raw UTC date, an extended-hours fill at 5:30pm Phoenix
    lands on the next UTC day and would match that evening's 9:05pm opinion
    — formed AFTER the fill executed (look-ahead)."""
    return (dt.astimezone(UTC) - timedelta(hours=7)).date().isoformat()


def parse_doc(doc) -> tuple:
    """Validate one input document into (fills, passes, skipped_count).
    Rows missing/failing required fields are skipped and counted, never
    fatal. Fills come back chronological (buys before sells on timestamp
    ties) so FIFO exit attachment is deterministic regardless of doc order.
    filled_at must be a full ISO timestamp (naive = UTC); date-only strings
    are rejected — midnight UTC would silently shift to the prior Phoenix
    day."""
    if not isinstance(doc, dict):
        raise ValueError("document must be an object")
    fills, passes, skipped = [], [], 0
    for f in doc.get("fills") or []:
        if not isinstance(f, dict):
            skipped += 1
            continue
        raw = f.get("symbol")
        symbol = raw.strip().upper() if isinstance(raw, str) else ""
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
        try:
            fill_dt = datetime.fromisoformat(filled_at)
        except ValueError:
            skipped += 1
            continue
        if fill_dt.tzinfo is None:
            fill_dt = fill_dt.replace(tzinfo=UTC)
        quantity = f.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, (int, float)):
            quantity = None
        fills.append(
            dict(
                symbol=symbol,
                side=side,
                price=float(price),
                quantity=float(quantity) if quantity is not None else None,
                filled_at=filled_at,
                fill_date=_phx_date(fill_dt),
                order_ref=f.get("order_ref"),
                note=f.get("note"),
            )
        )
    for p in doc.get("passes") or []:
        if not isinstance(p, dict):
            skipped += 1
            continue
        raw = p.get("symbol")
        symbol = raw.strip().upper() if isinstance(raw, str) else ""
        if not symbol:
            skipped += 1
            continue
        passes.append(dict(symbol=symbol, note=p.get("note")))
    fills.sort(key=lambda f: (f["filled_at"], 0 if f["side"] == "buy" else 1))
    return fills, passes, skipped
