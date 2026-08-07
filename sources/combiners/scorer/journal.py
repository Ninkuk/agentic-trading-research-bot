"""Decision journal: what the human did about composite opinions. Ingests
one JSON doc of fills/passes/verdicts (built by the journal-sync skill from
Robinhood MCP order history, or dictated manually) and stores decisions
permanently in scorer.db next to the outcomes they are graded against.

Matching is deterministic (headless scheduled runs cannot stop to confirm)
and reads composite.db ATTACHed read-only rather than ticker_outcomes:
registration lags one night (next-day-close entries), so a morning-after
fill would otherwise misclassify as freelance. The opinion exists in
composite.db the night it forms; once matched, the decision's
(composite_snapshot_id, symbol) key joins the scorer's permanent outcome
rows and never needs composite.db again. Decisions are never pruned — they
are the other half of the experiment. Verdicts are the research-ticker
skill's buy/pass calls — its own graded actor, distinct from the human's
decisions."""

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, date, datetime

from sources.combiners.scorer import db, fetch
from sources.common.clock import phx_date

# Calendar days an opinion stays matchable to a later fill: covers the
# morning-after trade plus a long weekend. Two snapshots in the window
# resolve to the most recent one. (Flag thresholds live in db.py — shared
# with the v_flag_response view.)
MATCH_WINDOW_DAYS = 5

# Broker order origins that are nobody's decision. Automatic fills are
# journaled (labeled via decisions.placed_agent) but never matched to an
# opinion and never attach as a decision's exit — a dividend reinvestment
# answering a flag would be coincidence, not judgment, and a human sell
# exiting a $5 DRIP lot would grade the wrong entry.
AUTOMATIC_AGENTS = ("drip", "recurring")


def _phx_date(dt) -> str:
    """Phoenix-local date of an aware datetime — the clock composite_date is on
    (see fetch.read_snapshots). fill_date must share it: with a raw UTC date, an
    extended-hours fill at 5:30pm Phoenix lands on the next UTC day and would
    match that evening's 9:05pm opinion — formed AFTER the fill executed
    (look-ahead)."""
    return phx_date(dt)


def _bare_date(s) -> bool:
    """True only for a bare YYYY-MM-DD calendar-date string (no timestamp)."""
    if not isinstance(s, str) or len(s) != 10:
        return False
    try:
        date.fromisoformat(s)
    except ValueError:
        return False
    return True


def _numeric(value) -> float | None:
    """A number OR a numeric string, else None. The broker returns every
    price/quantity as a decimal string ('178.141500', '0.056135' — fractional
    fills especially) and the transcribing session copies values verbatim, so
    the deterministic layer owns the conversion (same rule as orders fetch)."""
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def parse_doc(doc) -> tuple:
    """Validate one input document into (fills, passes, verdicts, skipped_count).
    Rows missing/failing required fields are skipped and counted, never
    fatal. Fills come back chronological (buys before sells on timestamp
    ties) so FIFO exit attachment is deterministic regardless of doc order.
    filled_at must be a full ISO timestamp (naive = UTC); date-only strings
    are rejected — midnight UTC would silently shift to the prior Phoenix
    day. verdict_date must be a bare YYYY-MM-DD Phoenix calendar date;
    timestamps are rejected."""
    if not isinstance(doc, dict):
        raise ValueError("document must be an object")
    fills, passes, verdicts, skipped = [], [], [], 0
    for f in doc.get("fills") or []:
        if not isinstance(f, dict):
            skipped += 1
            continue
        raw = f.get("symbol")
        symbol = raw.strip().upper() if isinstance(raw, str) else ""
        side = f.get("side")
        price = _numeric(f.get("price"))
        filled_at = f.get("filled_at")
        if (
            not symbol
            or side not in ("buy", "sell")
            or price is None
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
        quantity = _numeric(f.get("quantity"))
        agent = f.get("placed_agent")
        # Option fills: contract_ref marks one. side is remapped to the
        # DIRECTIONAL intent for opens (buy put = bearish = 'sell'); a close
        # keeps the broker side and needs no right/expiration — it only ever
        # attaches to its opening decision, never creates one. Multi-leg
        # orders are refused (spec: grade the strategy or nothing — two
        # independently-graded legs double-count one defined-risk bet).
        contract = f.get("contract_ref")
        position_effect = expiration = None
        if contract is not None or f.get("position_effect") is not None:
            position_effect = f.get("position_effect")
            if (
                not isinstance(contract, str)
                or not contract
                or f.get("multi_leg")
                or position_effect not in ("open", "close")
            ):
                skipped += 1
                continue
            expiration = f.get("expiration")
            if not _bare_date(expiration):
                expiration = None
            if position_effect == "open":
                right = f.get("right")
                if right not in ("call", "put") or expiration is None:
                    skipped += 1
                    continue
                side = "buy" if (side == "buy") == (right == "call") else "sell"
        sref = f.get("strategy_ref")
        fills.append(
            dict(
                symbol=symbol,
                side=side,
                price=price,
                quantity=quantity,
                filled_at=filled_at,
                fill_date=_phx_date(fill_dt),
                order_ref=f.get("order_ref"),
                note=f.get("note"),
                placed_agent=agent if isinstance(agent, str) else None,
                contract_ref=contract if position_effect else None,
                strategy_ref=sref if isinstance(sref, str) else None,
                position_effect=position_effect,
                expiration=expiration,
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
    for v in doc.get("verdicts") or []:
        if not isinstance(v, dict):
            skipped += 1
            continue
        raw = v.get("symbol")
        symbol = raw.strip().upper() if isinstance(raw, str) else ""
        verdict = v.get("verdict")
        vdate = v.get("verdict_date")
        # A bare Phoenix calendar date, NOT a timestamp: research-ticker
        # stamps the run's Phoenix date directly, so unlike filled_at there
        # is no UTC instant to convert — a timestamp here is a bug upstream.
        if not symbol or verdict not in ("buy", "pass") or not _bare_date(vdate):
            skipped += 1
            continue
        # `corrects` is a free-text REASON, and its presence is what licenses
        # overwriting an already-recorded call (see db.verdict_corrections).
        # A non-string is dropped rather than skipping the row: the verdict is
        # still valid, it just does not authorise a correction.
        corrects = v.get("corrects")
        verdicts.append(
            dict(
                symbol=symbol,
                verdict=verdict,
                verdict_date=vdate,
                doc=v.get("doc"),
                note=v.get("note"),
                corrects=corrects if isinstance(corrects, str) and corrects.strip() else None,
            )
        )
    fills.sort(key=lambda f: (f["filled_at"], 0 if f["side"] == "buy" else 1))
    return fills, passes, verdicts, skipped


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


def _dedup_ref(f) -> str:
    """The idempotency key for a fill. A broker-supplied order_ref if present;
    otherwise a deterministic synthetic key over the fill's identifying fields,
    so re-ingesting the same manually-dictated fill is a no-op instead of a
    double-book. Prefixed 'manual:' so the stored source can be recovered."""
    ref = f.get("order_ref")
    if ref:
        return ref
    canon = "|".join(str(f.get(k)) for k in ("symbol", "filled_at", "side", "price", "quantity"))
    # Appended only when present so every pre-options equity key is unchanged.
    if f.get("contract_ref"):
        canon += "|" + f["contract_ref"]
    return "manual:" + hashlib.sha1(canon.encode("utf-8")).hexdigest()[:16]


def ingest(conn, fills, passes, verdicts, now_iso, skipped=0) -> dict:
    """One transaction: every decision row plus the journal_runs header
    commit together or not at all. Requires composite.db attached as `src`
    when fills/passes are present. Fills must be chronological (parse_doc
    guarantees it) so FIFO exit attachment is deterministic."""
    matched = freelance = exits = passes_n = verdicts_n = dupes = expired = corrected = 0
    # Phoenix clock, like fill_date/composite_date: an evening-dictated pass
    # (after the 9:05pm snapshot = next day UTC) answers THAT evening's flag.
    as_of_date = _phx_date(datetime.fromisoformat(now_iso))
    with conn:
        for f in fills:
            ref = _dedup_ref(f)
            if _seen(conn, ref):
                dupes += 1
                continue
            automatic = f.get("placed_agent") in AUTOMATIC_AGENTS
            contract = f.get("contract_ref")
            if contract and f.get("position_effect") == "close":
                # A close attaches to ITS contract's open decision — never
                # another contract on the same underlying, and it never
                # creates a decision (an open that predates the journal is
                # a skip to fix by hand, not a bearish opinion).
                open_row = conn.execute(
                    "SELECT id FROM decisions WHERE contract_ref = ?"
                    " AND action = 'acted' AND exit_fill_date IS NULL"
                    " AND fill_date <= ? ORDER BY fill_date, id LIMIT 1",
                    (contract, f["fill_date"]),
                ).fetchone()
                if open_row:
                    conn.execute(
                        "UPDATE decisions SET exit_fill_date = ?,"
                        " exit_fill_price = ?, exit_order_ref = ? WHERE id = ?",
                        (f["fill_date"], f["price"], ref, open_row[0]),
                    )
                    exits += 1
                else:
                    skipped += 1
                    print(f"skip close {contract}: no open decision")
                continue
            if f["side"] == "sell" and not automatic and not contract:
                open_buy = conn.execute(
                    "SELECT id FROM decisions WHERE symbol = ? AND action = 'acted'"
                    " AND side = 'buy' AND contract_ref IS NULL"
                    " AND exit_fill_date IS NULL"
                    " AND (placed_agent IS NULL OR placed_agent NOT IN (?, ?))"
                    " AND fill_date <= ? ORDER BY fill_date, id LIMIT 1",
                    (f["symbol"], *AUTOMATIC_AGENTS, f["fill_date"]),
                ).fetchone()
                if open_buy:
                    conn.execute(
                        "UPDATE decisions SET exit_fill_date = ?,"
                        " exit_fill_price = ?, exit_order_ref = ? WHERE id = ?",
                        (f["fill_date"], f["price"], ref, open_buy[0]),
                    )
                    exits += 1
                    continue
            m = None if automatic else match_opinion(conn, f["symbol"], f["fill_date"])
            conn.execute(
                "INSERT INTO decisions (symbol, action, side,"
                " composite_snapshot_id, composite_date, opinion_score_sum,"
                " opinion_total, fill_date, fill_price, quantity, order_ref,"
                " note, placed_agent, contract_ref, strategy_ref,"
                " position_effect, expiration, source, recorded_at)"
                " VALUES (?, 'acted', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                    ref,
                    f["note"],
                    f.get("placed_agent"),
                    contract,
                    f.get("strategy_ref"),
                    f.get("position_effect"),
                    f.get("expiration"),
                    "manual" if ref.startswith("manual:") else "mcp",
                    now_iso,
                ),
            )
            matched += 1 if m else 0
            freelance += 0 if m else 1
        # Terminal-event sweep: an option expiring un-closed produces no fill,
        # so without this its decision looks open forever and blocks close
        # attachment for a later round trip on the same contract. Premium
        # 0.0 stands in for expired-worthless; an exercised/assigned contract
        # (stock appears instead of a closing fill) must be corrected by
        # hand. P&L is NULLed for option rows in the views either way.
        cur = conn.execute(
            "UPDATE decisions SET exit_fill_date = expiration,"
            " exit_fill_price = 0.0,"
            " exit_order_ref = 'expired:' || contract_ref || ':' || id"
            " WHERE action = 'acted' AND contract_ref IS NOT NULL"
            " AND exit_fill_date IS NULL AND expiration IS NOT NULL"
            " AND expiration < ?",
            (as_of_date,),
        )
        expired = cur.rowcount
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
        for v in verdicts:
            cur = conn.execute(
                "INSERT OR IGNORE INTO research_verdicts"
                " (symbol, verdict, verdict_date, doc, note, recorded_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (v["symbol"], v["verdict"], v["verdict_date"], v["doc"], v["note"], now_iso),
            )
            verdicts_n += cur.rowcount
            if cur.rowcount:
                continue
            # The row already exists. Default stays INSERT OR IGNORE (a counted
            # duplicate); only an explicit `corrects` reason may overwrite a
            # recorded call, and it books the prior value for audit first.
            reason = v.get("corrects")
            prior = conn.execute(
                "SELECT verdict FROM research_verdicts WHERE symbol=? AND verdict_date=?",
                (v["symbol"], v["verdict_date"]),
            ).fetchone()
            if not reason or not prior or prior[0] == v["verdict"]:
                dupes += 1  # no reason given, or nothing actually changed
                continue
            conn.execute(
                "INSERT INTO verdict_corrections (symbol, verdict_date, old_verdict,"
                " new_verdict, reason, corrected_at) VALUES (?, ?, ?, ?, ?, ?)",
                (v["symbol"], v["verdict_date"], prior[0], v["verdict"], reason, now_iso),
            )
            conn.execute(
                "UPDATE research_verdicts SET verdict=?, doc=?, note=?, recorded_at=?"
                " WHERE symbol=? AND verdict_date=?",
                (v["verdict"], v["doc"], v["note"], now_iso, v["symbol"], v["verdict_date"]),
            )
            corrected += 1
        cur = conn.execute(
            "INSERT INTO journal_runs (ran_at, fills_seen, matched, freelance,"
            " exits_attached, passes_recorded, verdicts_recorded,"
            " duplicates_skipped, skipped, expired_closed)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                now_iso,
                len(fills),
                matched,
                freelance,
                exits,
                passes_n,
                verdicts_n,
                dupes,
                skipped,
                expired,
            ),
        )
        return dict(
            run_id=cur.lastrowid,
            fills_seen=len(fills),
            matched=matched,
            freelance=freelance,
            exits_attached=exits,
            passes_recorded=passes_n,
            verdicts_recorded=verdicts_n,
            duplicates_skipped=dupes,
            corrected=corrected,
            skipped=skipped,
            expired_closed=expired,
        )


def run(db_path, doc, composite_db=None, now_iso=None) -> dict:
    """Parse + ingest one document. composite.db is attached only when
    something needs matching; a missing composite.db is then a HARD error —
    silently freelancing every fill would corrupt the filter-value
    evidence. An empty doc still writes a run header (the "ran and found
    nothing" signal for the schedule's freshness check)."""
    now_iso = now_iso or datetime.now(UTC).isoformat()
    fills, passes, verdicts, skipped = parse_doc(doc)
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        need_match = bool(fills or passes)
        if need_match:
            if not composite_db:
                raise FileNotFoundError("composite db path required for matching")
            fetch.attach_ro(conn, composite_db)
        try:
            return ingest(conn, fills, passes, verdicts, now_iso, skipped=skipped)
        finally:
            if need_match:
                fetch.detach(conn)
    finally:
        conn.close()


def main(argv=None) -> None:
    p = argparse.ArgumentParser(
        prog="journal",
        description="Record human decisions (fills/passes) against composite"
        " opinions (reads composite.db read-only for matching)",
    )
    p.add_argument("--db", default="scorer.db")
    p.add_argument(
        "--composite-db", default=None, help="composite.db path (default: alongside --db)"
    )
    p.add_argument("--input", help="path to the JSON document, or - for stdin")
    p.add_argument(
        "--last-run", action="store_true", help="print the latest run timestamp and exit"
    )
    p.add_argument(
        "--transfer",
        type=float,
        default=None,
        help="record an external cash flow: signed dollars, + deposit,"
        " - withdrawal (requires --date; ignores --input)",
    )
    p.add_argument(
        "--date", default=None, help="Phoenix calendar date (YYYY-MM-DD) the flow landed"
    )
    p.add_argument("--note", default=None, help="optional transfer annotation")
    a = p.parse_args(argv)

    if a.last_run:
        conn = db.connect(a.db)
        try:
            db.ensure_schema(conn)
            row = conn.execute("SELECT MAX(ran_at) FROM journal_runs").fetchone()
        finally:
            conn.close()
        print(row[0] or "never")
        return
    if a.transfer is not None:
        if a.transfer == 0:
            p.error("--transfer must be nonzero")
        if not a.date or not _bare_date(a.date):
            p.error("--transfer requires --date as a bare YYYY-MM-DD Phoenix date")
        conn = db.connect(a.db)
        try:
            db.ensure_schema(conn)
            tid = db.record_transfer(
                conn, a.date, a.transfer, a.note, datetime.now(UTC).isoformat()
            )
        finally:
            conn.close()
        kind = "deposit" if a.transfer > 0 else "withdrawal"
        print(f"transfer {tid}: {kind} {abs(a.transfer):.2f} on {a.date}, into {a.db}")
        return
    if not a.input:
        p.error("--input is required unless --last-run")

    try:
        if a.input == "-":
            doc = json.load(sys.stdin)
        else:
            with open(a.input, encoding="utf-8") as f:
                doc = json.load(f)
    except Exception as e:
        print(f"error: cannot read input: {type(e).__name__}", file=sys.stderr)
        raise SystemExit(1) from None

    composite_path = a.composite_db or os.path.join(os.path.dirname(a.db) or ".", "composite.db")
    try:
        c = run(a.db, doc, composite_db=composite_path)
    except FileNotFoundError:
        print("error: composite db not found (fills need matching)", file=sys.stderr)
        raise SystemExit(1) from None
    except ValueError as e:
        print(f"error: bad document: {type(e).__name__}", file=sys.stderr)
        raise SystemExit(1) from None
    print(
        f"journal run {c['run_id']}: {c['matched']} matched,"
        f" {c['freelance']} freelance, {c['exits_attached']} exits,"
        f" {c['passes_recorded']} passes, {c['verdicts_recorded']} verdicts,"
        f" {c['duplicates_skipped']} duplicates, {c.get('corrected', 0)} corrected,"
        f" {c['skipped']} skipped, {c['expired_closed']} expired, into {a.db}"
    )


if __name__ == "__main__":
    main()
