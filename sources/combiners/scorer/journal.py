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

from sources.combiners.scorer import db

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


# composite_date, exactly as the scorer registers it (Phoenix shift; see
# fetch.read_snapshots for the rationale). MUST stay identical or journal
# keys won't join registered_snapshots.
_CDATE = "substr(datetime(s.captured_at, '-7 hours'), 1, 10)"


def match_opinion(conn, symbol, fill_date):
    """Most recent composite opinion on `symbol` strictly BEFORE fill_date
    (the opinion forms at 9:05pm, after that day's close) and at most
    MATCH_WINDOW_DAYS old. Direction-agnostic: the views classify by
    alignment. Returns (composite_snapshot_id, composite_date, score_sum,
    total) — the score is captured because composite.db prunes and weekend
    reruns can differ from the graded window owner — or None (freelance)."""
    row = conn.execute(
        f"SELECT s.id, {_CDATE}, t.score_sum, t.total FROM src.snapshots s"
        f" JOIN src.ticker_scores t ON t.snapshot_id = s.id AND t.symbol = ?"
        f" WHERE {_CDATE} < ? AND ? <= date({_CDATE}, ?)"
        f" ORDER BY s.id DESC LIMIT 1",
        (symbol, fill_date, fill_date, f"+{MATCH_WINDOW_DAYS} days"),
    ).fetchone()
    return tuple(row) if row else None


def match_flagged(conn, symbol, as_of_date):
    """Like match_opinion but only flagged opinions (a pass must answer a
    real flag), and same-evening passes are allowed (cdate <= as_of)."""
    row = conn.execute(
        f"SELECT s.id, {_CDATE}, t.score_sum, t.total FROM src.snapshots s"
        f" JOIN src.ticker_scores t ON t.snapshot_id = s.id AND t.symbol = ?"
        f" AND ABS(t.score_sum) >= ? AND t.total >= ?"
        f" WHERE {_CDATE} <= ? AND ? <= date({_CDATE}, ?)"
        f" ORDER BY s.id DESC LIMIT 1",
        (
            symbol,
            db.FLAG_MIN_ABS_SCORE,
            db.FLAG_MIN_TOTAL,
            as_of_date,
            as_of_date,
            f"+{MATCH_WINDOW_DAYS} days",
        ),
    ).fetchone()
    return tuple(row) if row else None


def _seen(conn, ref):
    return (
        ref is not None
        and conn.execute(
            "SELECT 1 FROM decisions WHERE order_ref = ? OR exit_order_ref = ? LIMIT 1",
            (ref, ref),
        ).fetchone()
        is not None
    )


def ingest(conn, fills, passes, now_iso, skipped=0) -> dict:
    """One transaction: every decision row plus the journal_runs header
    commit together or not at all. Requires composite.db attached as `src`
    when fills/passes are present. Fills must be chronological (parse_doc
    guarantees it) so FIFO exit attachment is deterministic."""
    matched = freelance = exits = passes_n = dupes = 0
    # Phoenix clock, like fill_date/composite_date: an evening-dictated pass
    # (after the 9:05pm snapshot = next day UTC) answers THAT evening's flag.
    as_of_date = _phx_date(datetime.fromisoformat(now_iso))
    with conn:
        for f in fills:
            if _seen(conn, f["order_ref"]):
                dupes += 1
                continue
            if f["side"] == "sell":
                open_buy = conn.execute(
                    "SELECT id FROM decisions WHERE symbol = ? AND action = 'acted'"
                    " AND side = 'buy' AND exit_fill_date IS NULL"
                    " AND fill_date <= ? ORDER BY fill_date, id LIMIT 1",
                    (f["symbol"], f["fill_date"]),
                ).fetchone()
                if open_buy:
                    conn.execute(
                        "UPDATE decisions SET exit_fill_date = ?,"
                        " exit_fill_price = ?, exit_order_ref = ? WHERE id = ?",
                        (f["fill_date"], f["price"], f["order_ref"], open_buy[0]),
                    )
                    exits += 1
                    continue
            m = match_opinion(conn, f["symbol"], f["fill_date"])
            conn.execute(
                "INSERT INTO decisions (symbol, action, side,"
                " composite_snapshot_id, composite_date, opinion_score_sum,"
                " opinion_total, fill_date, fill_price, quantity, order_ref,"
                " note, source, recorded_at)"
                " VALUES (?, 'acted', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f["symbol"],
                    f["side"],
                    m[0] if m else None,
                    m[1] if m else None,
                    m[2] if m else None,
                    m[3] if m else None,
                    f["fill_date"],
                    f["price"],
                    f["quantity"],
                    f["order_ref"],
                    f["note"],
                    "mcp" if f["order_ref"] else "manual",
                    now_iso,
                ),
            )
            matched += 1 if m else 0
            freelance += 0 if m else 1
        for p in passes:
            m = match_flagged(conn, p["symbol"], as_of_date)
            if m is None:
                skipped += 1
                print(f"skip pass {p['symbol']}: no flagged opinion in window")
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO decisions (symbol, action,"
                " composite_snapshot_id, composite_date, opinion_score_sum,"
                " opinion_total, note, source, recorded_at)"
                " VALUES (?, 'passed', ?, ?, ?, ?, ?, 'manual', ?)",
                (p["symbol"], m[0], m[1], m[2], m[3], p["note"], now_iso),
            )
            passes_n += cur.rowcount
        cur = conn.execute(
            "INSERT INTO journal_runs (ran_at, fills_seen, matched, freelance,"
            " exits_attached, passes_recorded, duplicates_skipped, skipped)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (now_iso, len(fills), matched, freelance, exits, passes_n, dupes, skipped),
        )
        return dict(
            run_id=cur.lastrowid,
            fills_seen=len(fills),
            matched=matched,
            freelance=freelance,
            exits_attached=exits,
            passes_recorded=passes_n,
            duplicates_skipped=dupes,
            skipped=skipped,
        )
