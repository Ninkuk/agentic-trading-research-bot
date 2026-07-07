"""scorer.db: the permanent efficacy dataset. prices is an append-only,
never-pruned close ledger (the system's only growing price history — also
the future backtest store); outcome tables are never pruned either — they
ARE the experiment. decisions/journal_runs (the decision journal) are permanent
for the same reason.

Entries are next-day closes: a snapshot registers only once the ledger
holds a close AFTER its composite_date (registration defers otherwise), so
grading never pockets the overnight gap the opinion couldn't have traded.
A snapshot that registers late (e.g. after an outage) still enters at its
historically exact next close while the ledger retains it; beyond the
price-prune window its symbols skip via the forward entry guard."""

import sqlite3
from datetime import datetime, timedelta

# Basis-break guard bounds: the ledger stores each day's close on that day's
# price basis with no adjusted history to correct from, so a split shows up
# as a consecutive-date ratio near 1/2, 1/3, 2, 5, ... — outside these
# bounds. Multiplication (not division) so a zero prev-close flags
# conservatively. Sub-threshold splits (3:2, ratio 0.667) pass undetected —
# accepted residual, see docs/superpowers/specs/2026-07-06-scorer-basis-
# guard-design.md.
BASIS_BREAK_LO = 0.55  # forward splits >= 2:1 land below this
BASIS_BREAK_HI = 1.8  # reverse splits >= 1:2 land above this

# Guardrail constants for the efficacy views. Wilson (not Wald): Wald
# collapses to zero width on small all-hit samples (5/5 -> "100% +/- 0"),
# which is exactly the n=12-looks-brilliant failure these views must not
# have. Crude by design — with ~144 simultaneous rows (24 signals x 3
# horizons x crosswalk split), ~7 look significant at 95% by chance alone;
# the human reads the CI with that in mind. sqrt() needs SQLite math
# functions (present in CPython 3.12's bundled SQLite 3.45+).
WILSON_Z = 1.96  # 95% score interval on hit_rate
RELIABLE_MIN_N = 30  # benchmarked-sample floor for the reliable flag

# Flag thresholds, mirroring composite v_flagged (|score_sum| >= 4 AND
# total >= 3). Both are hand-tunable; test_journal_matching pins these to
# composite's view text so the journal and composite drift together.
FLAG_MIN_ABS_SCORE = 4
FLAG_MIN_TOTAL = 3


def _wilson(sign: str) -> str:
    """Wilson score bound (+1 upper / -1 lower via sign) as a SQL aggregate
    fragment over a 0/1 `hit` column; NULL hits are excluded by COUNT/AVG."""
    z, n, p = str(WILSON_Z), "COUNT(hit)", "AVG(hit)"
    return (
        f"CASE WHEN {n} > 0 THEN"
        f" ({p} + {z}*{z}/(2.0*{n})"
        f" {sign} {z} * sqrt({p}*(1-{p})/{n} + {z}*{z}/(4.0*{n}*{n})))"
        f" / (1 + {z}*{z}/{n}) END"
    )


_TABLES = """
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    harvested   INTEGER NOT NULL DEFAULT 0,
    registered  INTEGER NOT NULL DEFAULT 0,
    matured     INTEGER NOT NULL DEFAULT 0,
    skipped     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS prices (
    symbol     TEXT NOT NULL,
    price_date TEXT NOT NULL,
    close      REAL NOT NULL,
    PRIMARY KEY (symbol, price_date)
);

-- Registration marker: a composite snapshot is registered atomically with
-- all its outcome rows, or not at all.
CREATE TABLE IF NOT EXISTS registered_snapshots (
    composite_snapshot_id INTEGER PRIMARY KEY,
    composite_date        TEXT NOT NULL,
    entry_date            TEXT,     -- ledger window anchor (MIN price_date > composite_date); registration defers while none exists
    registered_at         TEXT NOT NULL,
    ticker_rows           INTEGER NOT NULL,
    signal_rows           INTEGER NOT NULL,
    skipped               INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ticker_outcomes (
    composite_snapshot_id INTEGER NOT NULL,
    composite_date        TEXT NOT NULL,
    symbol                TEXT NOT NULL,
    score_sum             INTEGER NOT NULL,
    total                 INTEGER NOT NULL,
    bullish               INTEGER NOT NULL,
    bearish               INTEGER NOT NULL,
    in_portfolio          INTEGER NOT NULL DEFAULT 0,
    horizon               INTEGER NOT NULL,
    entry_date            TEXT NOT NULL,
    entry_close           REAL NOT NULL,
    bench_entry_close     REAL,
    exit_date             TEXT,
    exit_close            REAL,
    fwd_return            REAL,
    bench_fwd_return      REAL,
    matured_at            TEXT,
    PRIMARY KEY (composite_snapshot_id, symbol, horizon)
);

-- benchmark: the symbol this row's bench_* legs are graded against.
-- Direct rows get the global benchmark (SPY); crosswalked rows get their
-- matched class benchmark; NULL = explicitly unbenchmarked (class proxies
-- and unknown crosswalk tickers) -- graded on raw return only.
CREATE TABLE IF NOT EXISTS signal_outcomes (
    composite_snapshot_id INTEGER NOT NULL,
    composite_date        TEXT NOT NULL,
    signal_id             TEXT NOT NULL,
    entity                TEXT NOT NULL,
    score                 INTEGER NOT NULL,
    via_crosswalk         INTEGER NOT NULL DEFAULT 0,
    horizon               INTEGER NOT NULL,
    entry_date            TEXT NOT NULL,
    entry_close           REAL NOT NULL,
    benchmark             TEXT,
    bench_entry_close     REAL,
    exit_date             TEXT,
    exit_close            REAL,
    fwd_return            REAL,
    bench_fwd_return      REAL,
    matured_at            TEXT,
    PRIMARY KEY (composite_snapshot_id, signal_id, entity, horizon)
);

CREATE TABLE IF NOT EXISTS regime_outcomes (
    composite_snapshot_id INTEGER NOT NULL,
    composite_date        TEXT NOT NULL,
    regime                TEXT,
    horizon               INTEGER NOT NULL,
    entry_date            TEXT NOT NULL,
    bench_entry_close     REAL NOT NULL,
    exit_date             TEXT,
    bench_exit_close      REAL,
    bench_fwd_return      REAL,
    matured_at            TEXT,
    PRIMARY KEY (composite_snapshot_id, horizon)
);

-- Decision journal: what the human did about each opinion (roadmap item 5).
-- Permanent evidence like the outcome tables; never pruned. order_ref /
-- exit_order_ref are broker order UUIDs (random ids, not account
-- identifiers) stored only for idempotent re-ingest; UNIQUE tolerates the
-- NULLs manual entries carry. composite_snapshot_id NULL = freelance trade
-- (nothing recommended it). opinion_score_sum/opinion_total are the MATCHED
-- opinion's score captured at ingest: weekend reruns can flip sign vs the
-- window owner's graded rows, alignment must judge the opinion the human
-- actually saw, and composite.db prunes — so capture now or never.
-- placed_agent is the broker's order origin (user/agentic/drip/recurring):
-- automatic fills (journal.AUTOMATIC_AGENTS) are journaled for the record
-- but never matched to an opinion and never exit-attached — a reinvestment
-- answering a flag would be coincidence, not judgment. NULL = recorded
-- before the column existed (treated as non-automatic).
CREATE TABLE IF NOT EXISTS decisions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol                TEXT NOT NULL,
    action                TEXT NOT NULL CHECK (action IN ('acted', 'passed')),
    side                  TEXT CHECK (side IN ('buy', 'sell')),
    composite_snapshot_id INTEGER,
    composite_date        TEXT,
    opinion_score_sum     INTEGER,
    opinion_total         INTEGER,
    fill_date             TEXT,
    fill_price            REAL,
    quantity              REAL,
    exit_fill_date        TEXT,
    exit_fill_price       REAL,
    order_ref             TEXT UNIQUE,
    exit_order_ref        TEXT UNIQUE,
    note                  TEXT,
    placed_agent          TEXT,
    source                TEXT NOT NULL DEFAULT 'mcp'
                          CHECK (source IN ('mcp', 'manual')),
    recorded_at           TEXT NOT NULL
);

-- One explicit pass per MATCHED flag (SQLite treats NULL snapshot ids as
-- distinct, but ingest never writes a pass without a match).
CREATE UNIQUE INDEX IF NOT EXISTS idx_decisions_pass
    ON decisions (composite_snapshot_id, symbol) WHERE action = 'passed';

-- Backstop for the journal views' window re-keying: at most one
-- outcome-owning snapshot per entry window. register_snapshot's dedupe
-- already guarantees this sequentially; the index makes it durable.
CREATE UNIQUE INDEX IF NOT EXISTS idx_owner_window
    ON registered_snapshots (entry_date) WHERE ticker_rows > 0;

CREATE TABLE IF NOT EXISTS journal_runs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    ran_at             TEXT NOT NULL,
    fills_seen         INTEGER NOT NULL DEFAULT 0,
    matched            INTEGER NOT NULL DEFAULT 0,
    freelance          INTEGER NOT NULL DEFAULT 0,
    exits_attached     INTEGER NOT NULL DEFAULT 0,
    passes_recorded    INTEGER NOT NULL DEFAULT 0,
    duplicates_skipped INTEGER NOT NULL DEFAULT 0,
    skipped            INTEGER NOT NULL DEFAULT 0
);
"""

_VIEWS = f"""
-- Bucketing lives in views (ELT): stored rows keep raw score_sum/total.
-- Buckets: strong_bull >= +4, bull +2..+3, neutral -1..+1, bear -3..-2,
-- strong_bear <= -4; rows with total < 2 bucket as 'thin' regardless.
-- hit = excess in the score's direction (bull: excess > 0; bear: < 0);
-- score_sum = 0 rows have no direction and contribute NULL hits. Buckets
-- are SPY-benchmarked throughout (ticker rows carry no crosswalk
-- provenance), so n_bench counts rows with a computable hit (a gradable
-- SPY leg AND a direction).
DROP VIEW IF EXISTS v_bucket_performance;
CREATE VIEW v_bucket_performance AS
WITH m AS (
    SELECT CASE WHEN total < 2 THEN 'thin'
                WHEN score_sum >= 4 THEN 'strong_bull'
                WHEN score_sum >= 2 THEN 'bull'
                WHEN score_sum <= -4 THEN 'strong_bear'
                WHEN score_sum <= -2 THEN 'bear'
                ELSE 'neutral' END AS bucket,
           horizon, fwd_return,
           fwd_return - bench_fwd_return AS excess,
           CASE WHEN bench_fwd_return IS NULL THEN NULL
                WHEN score_sum > 0 THEN (fwd_return > bench_fwd_return)
                WHEN score_sum < 0 THEN (fwd_return < bench_fwd_return) END AS hit
    FROM ticker_outcomes WHERE matured_at IS NOT NULL
)
SELECT bucket, horizon, COUNT(*) AS n_matured,
       AVG(fwd_return) AS avg_fwd_return,
       AVG(excess) AS avg_excess,
       AVG(hit) AS hit_rate,
       COUNT(hit) AS n_bench,
       {_wilson("-")} AS hit_ci_lo,
       {_wilson("+")} AS hit_ci_hi,
       (COUNT(hit) >= {RELIABLE_MIN_N}) AS reliable
FROM m GROUP BY bucket, horizon;

-- Per-signal grade, direction-adjusted: excess * sign(score). Crosswalked
-- evidence is split out so mapped scores are graded separately. Guardrails:
-- n_bench is the binomial n (rows with a gradable benchmark; hit_rate,
-- avg_directional_excess and the CI only see those); n_matured - n_bench
-- is the unbenchmarked count, which avg_directional_return (raw, no
-- benchmark) still covers. reliable gates on n_bench, not n_matured.
DROP VIEW IF EXISTS v_signal_efficacy;
CREATE VIEW v_signal_efficacy AS
WITH m AS (
    SELECT signal_id, via_crosswalk, horizon, benchmark,
           (fwd_return - bench_fwd_return)
               * (CASE WHEN score > 0 THEN 1 ELSE -1 END) AS dir_excess,
           fwd_return * (CASE WHEN score > 0 THEN 1 ELSE -1 END) AS dir_return,
           CASE WHEN bench_fwd_return IS NULL THEN NULL
                WHEN score > 0 THEN (fwd_return > bench_fwd_return)
                ELSE (fwd_return < bench_fwd_return) END AS hit
    FROM signal_outcomes WHERE matured_at IS NOT NULL
)
SELECT signal_id, via_crosswalk, horizon,
       COUNT(*) AS n_matured,
       AVG(dir_excess) AS avg_directional_excess,
       AVG(hit) AS hit_rate,
       AVG(dir_return) AS avg_directional_return,
       COUNT(hit) AS n_bench,
       {_wilson("-")} AS hit_ci_lo,
       {_wilson("+")} AS hit_ci_hi,
       (COUNT(hit) >= {RELIABLE_MIN_N}) AS reliable,
       GROUP_CONCAT(DISTINCT benchmark) AS benchmarks
FROM m
GROUP BY signal_id, via_crosswalk, horizon;

DROP VIEW IF EXISTS v_regime_performance;
CREATE VIEW v_regime_performance AS
SELECT regime, horizon, COUNT(*) AS n_matured,
       AVG(bench_fwd_return) AS avg_bench_return,
       MIN(bench_fwd_return) AS min_bench_return,
       MAX(bench_fwd_return) AS max_bench_return
FROM regime_outcomes WHERE matured_at IS NOT NULL
GROUP BY regime, horizon;

-- Split-shaped consecutive-date moves anywhere in the ledger: the audit
-- trail for rows the basis guard holds pending (join v_pending on the
-- entity to tell "quarantined" from merely "young"). Thresholds are the
-- same BASIS_BREAK_* constants mature() binds as :lo/:hi.
DROP VIEW IF EXISTS v_basis_breaks;
CREATE VIEW v_basis_breaks AS
SELECT a.symbol,
       b.price_date AS prev_date, b.close AS prev_close,
       a.price_date, a.close,
       a.close / b.close AS ratio
FROM prices a
JOIN prices b ON b.symbol = a.symbol
 AND b.price_date = (SELECT MAX(c.price_date) FROM prices c
                     WHERE c.symbol = a.symbol AND c.price_date < a.price_date)
WHERE a.close < b.close * {BASIS_BREAK_LO} OR a.close > b.close * {BASIS_BREAK_HI};

-- Registered but not yet matured: what's cooking and roughly when.
DROP VIEW IF EXISTS v_pending;
CREATE VIEW v_pending AS
SELECT 'ticker' AS kind, composite_date, symbol AS entity, horizon,
       entry_date FROM ticker_outcomes WHERE matured_at IS NULL
UNION ALL
SELECT 'signal', composite_date, signal_id || ':' || entity, horizon,
       entry_date FROM signal_outcomes WHERE matured_at IS NULL
UNION ALL
SELECT 'regime', composite_date, COALESCE(regime, '?'), horizon,
       entry_date FROM regime_outcomes WHERE matured_at IS NULL;

-- Decision-journal views. Window re-keying: the scorer grades ONE snapshot
-- per ledger window (weekend/rerun siblings register marker-only with
-- ticker_rows = 0; idx_owner_window is the backstop), so a decision matched
-- to a sibling must grade against the window owner's outcome rows. A
-- decision whose snapshot isn't registered yet has no registered_snapshots
-- row and shows NULL paper legs until the nightly scorer catches up — the
-- view heals itself.
-- ONE ROW PER HORIZON: filter or group by horizon before aggregating, or
-- every decision counts len(HORIZONS) times.
-- aligned judges the decision against the opinion the human actually SAW
-- (d.opinion_score_sum, captured at ingest) — a weekend rerun's score can
-- flip sign vs the owner's graded row (owner_score_sum, also exposed).
-- entry_slippage is signed so positive is always cost (buys: paid above
-- paper entry; sells: received below it); fill_lag_days tells true
-- slippage from drift on late fills. realized_return is fills-only.
DROP VIEW IF EXISTS v_decision_outcomes;
CREATE VIEW v_decision_outcomes AS
SELECT d.id AS decision_id, d.symbol, d.side, d.source, d.placed_agent,
       d.composite_snapshot_id, d.composite_date,
       d.opinion_score_sum, d.opinion_total,
       d.fill_date, d.fill_price, d.quantity,
       d.exit_fill_date, d.exit_fill_price, d.note,
       t.horizon, t.score_sum AS owner_score_sum, t.total AS owner_total,
       t.entry_date, t.entry_close,
       t.fwd_return, t.bench_fwd_return, t.matured_at,
       julianday(d.fill_date) - julianday(t.entry_date) AS fill_lag_days,
       CASE WHEN d.opinion_score_sum IS NULL THEN NULL
            WHEN d.side = 'buy' THEN (d.opinion_score_sum > 0)
            ELSE (d.opinion_score_sum < 0) END AS aligned,
       CASE WHEN t.entry_close IS NULL THEN NULL
            WHEN d.side = 'sell' THEN 1 - d.fill_price / t.entry_close
            ELSE d.fill_price / t.entry_close - 1 END AS entry_slippage,
       CASE WHEN d.exit_fill_price IS NULL THEN NULL
            WHEN d.side = 'sell' THEN 1 - d.exit_fill_price / d.fill_price
            ELSE d.exit_fill_price / d.fill_price - 1 END AS realized_return
FROM decisions d
LEFT JOIN registered_snapshots r
       ON r.composite_snapshot_id = d.composite_snapshot_id
LEFT JOIN registered_snapshots owner
       ON owner.entry_date = r.entry_date AND owner.ticker_rows > 0
LEFT JOIN ticker_outcomes t
       ON t.composite_snapshot_id = owner.composite_snapshot_id
      AND t.symbol = d.symbol
WHERE d.action = 'acted';

-- Every matured flagged opinion and what the human did about it. Thresholds
-- are the shared FLAG_MIN_* constants (same ones the pass matcher binds;
-- pinned to composite v_flagged by test_journal_matching). The decision
-- lookup re-keys through the window (any sibling snapshot's decision
-- answers the owner's flag). A decision counts as acting on the flag ONLY
-- when its direction aligns with the flag (buy on bull, sell on bear):
-- exit-shaped sells (first sell of a pre-journal holding, second lot of a
-- scale-out) fall through exit-attachment as sell decisions and would
-- otherwise flip a bull flag to 'acted', poisoning v_human_filter — the
-- exact comparison this view exists for. Non-aligned trades stay visible
-- in v_decision_outcomes (aligned = 0); they just don't answer the flag.
-- MIN(action) is the precedence trick: 'acted' < 'passed' alphabetically,
-- so acting ever beats passing. dir_excess is excess return in the flag's
-- direction.
DROP VIEW IF EXISTS v_flag_response;
CREATE VIEW v_flag_response AS
SELECT t.composite_snapshot_id, t.composite_date, t.symbol,
       t.score_sum, t.total, t.horizon,
       t.fwd_return, t.bench_fwd_return,
       CASE WHEN t.bench_fwd_return IS NULL THEN NULL
            WHEN t.score_sum > 0 THEN t.fwd_return - t.bench_fwd_return
            ELSE t.bench_fwd_return - t.fwd_return END AS dir_excess,
       COALESCE(
           (SELECT MIN(d.action) FROM decisions d
            JOIN registered_snapshots sib
              ON sib.composite_snapshot_id = d.composite_snapshot_id
            WHERE sib.entry_date = owner.entry_date AND d.symbol = t.symbol
              AND (d.action = 'passed'
                   OR (d.side = 'buy') = (t.score_sum > 0))),
           'passed_inferred') AS response
FROM ticker_outcomes t
JOIN registered_snapshots owner ON owner.composite_snapshot_id = t.composite_snapshot_id
WHERE t.matured_at IS NOT NULL
  AND ABS(t.score_sum) >= {FLAG_MIN_ABS_SCORE} AND t.total >= {FLAG_MIN_TOTAL};

-- The headline: does acting beat passing? Plain averages + n day one; the
-- Wilson helpers can grade this once samples justify it.
DROP VIEW IF EXISTS v_human_filter;
CREATE VIEW v_human_filter AS
SELECT response, horizon, COUNT(*) AS n,
       AVG(dir_excess) AS avg_dir_excess,
       AVG(fwd_return) AS avg_fwd_return
FROM v_flag_response
GROUP BY response, horizon;

-- Trades nothing recommended: acted decisions with no matched opinion.
-- Includes automatic fills (drip/recurring, never matched by design) —
-- filter on placed_agent to see only deliberate freelance trades.
DROP VIEW IF EXISTS v_freelance;
CREATE VIEW v_freelance AS
SELECT id AS decision_id, symbol, side, fill_date, fill_price, quantity,
       exit_fill_date, exit_fill_price,
       CASE WHEN exit_fill_price IS NULL THEN NULL
            WHEN side = 'sell' THEN 1 - exit_fill_price / fill_price
            ELSE exit_fill_price / fill_price - 1 END AS realized_return,
       note, placed_agent, source, recorded_at
FROM decisions WHERE action = 'acted' AND composite_snapshot_id IS NULL;
"""


def connect(path: str) -> sqlite3.Connection:
    # uri=True so ATTACH 'file:...?mode=ro' works (plain paths still fine).
    conn = sqlite3.connect(path, uri=True)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_schema(conn) -> None:
    """Tables, then the idempotent column migrations, then views. Views are
    DROP+CREATEd every run so edits deploy nightly; the ALTERs must precede
    them because views reference signal_outcomes.benchmark and
    decisions.placed_agent."""
    conn.executescript(_TABLES)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(signal_outcomes)")}
    if "benchmark" not in cols:
        conn.execute("ALTER TABLE signal_outcomes ADD COLUMN benchmark TEXT")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(decisions)")}
    if "placed_agent" not in cols:
        conn.execute("ALTER TABLE decisions ADD COLUMN placed_agent TEXT")
    conn.executescript(_VIEWS)
    conn.commit()


def write_snapshot(conn, now_iso: str) -> int:
    cur = conn.execute("INSERT INTO snapshots (captured_at) VALUES (?)", (now_iso,))
    conn.commit()  # survive later rollbacks
    return cur.lastrowid


def finish_snapshot(conn, sid, harvested, registered, matured, skipped):
    conn.execute(
        "UPDATE snapshots SET harvested=?, registered=?, matured=?, skipped=? WHERE id=?",
        (harvested, registered, matured, skipped, sid),
    )


def insert_prices(conn, rows) -> int:
    n = 0
    for symbol, price_date, close in rows:
        if symbol is None or price_date is None or close is None:
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO prices (symbol, price_date, close) VALUES (?, ?, ?)",
            (symbol, price_date, close),
        )
        n += cur.rowcount
    return n


def entry_for(conn, symbol, composite_date, max_age_days):
    """First ledger close STRICTLY AFTER composite_date — the earliest price
    the opinion could actually be acted on. The composite forms its opinion
    at 9:05pm using data through that day's close, so entering at that same
    close would silently pocket the overnight gap (look-ahead). The forward
    guard refuses thin/halted symbols whose next print lands more than
    max_age_days after the opinion (7 covers any holiday weekend)."""
    row = conn.execute(
        "SELECT price_date, close FROM prices WHERE symbol=?"
        " AND price_date > ? AND price_date <= date(?, ?)"
        " ORDER BY price_date ASC LIMIT 1",
        (symbol, composite_date, composite_date, f"+{int(max_age_days)} days"),
    ).fetchone()
    return (row[0], row[1]) if row else None


def _bench_close(conn, benchmark, price_date):
    row = conn.execute(
        "SELECT close FROM prices WHERE symbol=? AND price_date=?",
        (benchmark, price_date),
    ).fetchone()
    return row[0] if row else None


def register_snapshot(
    conn,
    csid,
    composite_date,
    ticker_rows,
    signal_rows,
    regime,
    horizons,
    benchmark,
    max_age_days,
    now_iso,
    crosswalk_benchmark=None,
) -> tuple:
    """All-or-nothing registration of one composite snapshot: the marker row
    and every outcome row commit together. Returns (registered, skipped).

    Entries are next-day closes (no look-ahead), so on the night a snapshot
    is created its entry close doesn't exist yet: registration DEFERS —
    returns (0, 0) without writing the marker — and the nightly loop's
    registered_ids diff naturally retries it once the ledger advances.
    Steady state therefore registers each night's snapshot the following
    night.

    One grading per trading window (adversarial-review F3): weekend and
    same-day-rerun composite snapshots share a ledger window anchor; only
    the first snapshot for that anchor registers outcome rows — later
    ones write a marker-only row so the dedupe is durable and the loop
    never revisits them. Multi-counting duplicate windows would let
    v_bucket_performance treat copies of one window as independent samples.

    The dedupe key is the ledger's window anchor (MIN price_date >
    composite_date across ALL symbols) rather than the benchmark's own
    entry date: if the benchmark's price for the window never lands (e.g.
    an etfs-only harvest failure) while ticker prices for that day exist,
    keying off the benchmark's entry would silently fall back to another
    day's close and collide with an already-registered window, durably
    discarding an otherwise gradeable night as marker-only.

    Per-row benchmarks: a direct signal row is graded against `benchmark`
    (SPY); a crosswalked row against crosswalk_benchmark[entity] — its
    matched asset-class proxy. A class proxy maps to None and an unknown
    crosswalk ticker resolves to None (never silently SPY): both grade
    unbenchmarked (raw return only). ticker/regime rows stay on `benchmark`.
    """
    registered = skipped = 0
    with conn:  # transaction
        window_anchor = conn.execute(
            "SELECT MIN(price_date) FROM prices WHERE price_date > ?",
            (composite_date,),
        ).fetchone()[0]
        if window_anchor is None:
            print(f"defer composite snapshot {csid}: ledger not past {composite_date}")
            return 0, 0
        duplicate_window = (
            window_anchor is not None
            and conn.execute(
                "SELECT 1 FROM registered_snapshots WHERE entry_date = ? LIMIT 1",
                (window_anchor,),
            ).fetchone()
            is not None
        )
        conn.execute(
            "INSERT INTO registered_snapshots (composite_snapshot_id,"
            " composite_date, entry_date, registered_at, ticker_rows,"
            " signal_rows, skipped) VALUES (?, ?, ?, ?, 0, 0, 0)",
            (csid, composite_date, window_anchor, now_iso),
        )
        if duplicate_window:
            print(f"skip composite snapshot {csid}: window {window_anchor} already graded")
            return 0, 0
        bench_entry = entry_for(conn, benchmark, composite_date, max_age_days)
        for r in ticker_rows:
            entry = entry_for(conn, r["symbol"], composite_date, max_age_days)
            if entry is None:
                skipped += 1
                continue
            bench = _bench_close(conn, benchmark, entry[0])
            for h in horizons:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO ticker_outcomes"
                    " (composite_snapshot_id, composite_date, symbol,"
                    "  score_sum, total, bullish, bearish, in_portfolio,"
                    "  horizon, entry_date, entry_close, bench_entry_close)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        csid,
                        composite_date,
                        r["symbol"],
                        r["score_sum"],
                        r["total"],
                        r["bullish"],
                        r["bearish"],
                        r["in_portfolio"],
                        h,
                        entry[0],
                        entry[1],
                        bench,
                    ),
                )
                registered += cur.rowcount
        for r in signal_rows:
            entry = entry_for(conn, r["entity"], composite_date, max_age_days)
            if entry is None:
                skipped += 1
                continue
            if r["via_crosswalk"]:
                row_bench = (crosswalk_benchmark or {}).get(r["entity"])
            else:
                row_bench = benchmark
            bench = _bench_close(conn, row_bench, entry[0]) if row_bench else None
            for h in horizons:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO signal_outcomes"
                    " (composite_snapshot_id, composite_date, signal_id,"
                    "  entity, score, via_crosswalk, horizon, entry_date,"
                    "  entry_close, benchmark, bench_entry_close)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        csid,
                        composite_date,
                        r["signal_id"],
                        r["entity"],
                        r["score"],
                        r["via_crosswalk"],
                        h,
                        entry[0],
                        entry[1],
                        row_bench,
                        bench,
                    ),
                )
                registered += cur.rowcount
        if bench_entry is None:
            skipped += 1
        else:
            for h in horizons:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO regime_outcomes"
                    " (composite_snapshot_id, composite_date, regime,"
                    "  horizon, entry_date, bench_entry_close)"
                    " VALUES (?,?,?,?,?,?)",
                    (
                        csid,
                        composite_date,
                        regime,
                        h,
                        bench_entry[0],
                        bench_entry[1],
                    ),
                )
                registered += cur.rowcount
        conn.execute(
            "UPDATE registered_snapshots SET ticker_rows=?, signal_rows=?,"
            " skipped=? WHERE composite_snapshot_id=?",
            (len(ticker_rows), len(signal_rows), skipped, csid),
        )
    return registered, skipped


def registered_ids(conn):
    return {r[0] for r in conn.execute("SELECT composite_snapshot_id FROM registered_snapshots")}


# Maturation: the Nth distinct ledger date after entry, per symbol.
# NOTE: SQLite rejects a correlated OFFSET ("LIMIT 1 OFFSET t.horizon - 1"
# fails with "no such column"), so the Nth date is selected via a
# COUNT-correlated WHERE instead (adversarial-review F1, verified).
# The julianday bound (F2) refuses to mature across a ledger gap wider
# than the horizon could plausibly span (~2 calendar days per trading day
# + a holiday week) — a gapped row stays pending and visible forever
# rather than silently grading the wrong window into the permanent record.
# The basis guard applies the same refuse-to-grade principle to price
# basis: a split inside the window would fabricate a return (2:1 -> -50%),
# so any window containing a BASIS_BREAK_* consecutive-date move — on the
# graded leg or the benchmark leg — stays pending forever. v_basis_breaks
# is the audit trail for what was held and why.
# signal_outcomes rows grade against their own stored benchmark column
# ({bench} slot): the benchmark-leg break scan self-disables when
# benchmark IS NULL (a.symbol = NULL matches nothing), so unbenchmarked
# rows mature with bench_fwd_return NULL, while a break in a matched
# benchmark (e.g. XLE splits) holds its dependent rows pending — the
# same refuse-to-grade principle as SPY today.

# One break scan, embedded per leg: TRUE when any consecutive-date pair
# whose later date falls in (entry_date, x.xdate] moves outside the
# BASIS_BREAK bounds (:lo/:hi) for {who}'s ledger.
_BREAK_SCAN = """EXISTS (
      SELECT 1 FROM prices a JOIN prices b
        ON b.symbol = a.symbol
       AND b.price_date = (SELECT MAX(c.price_date) FROM prices c
                           WHERE c.symbol = a.symbol
                             AND c.price_date < a.price_date)
      WHERE a.symbol = {who}
        AND a.price_date > {t}.entry_date AND a.price_date <= x.xdate
        AND (a.close < b.close * :lo OR a.close > b.close * :hi))"""

_MATURE_SYMBOL = (
    """
UPDATE {table} SET
  exit_date = x.xdate,
  exit_close = (SELECT close FROM prices
                WHERE symbol = {table}.{sym} AND price_date = x.xdate),
  fwd_return = (SELECT close FROM prices
                WHERE symbol = {table}.{sym} AND price_date = x.xdate)
               / entry_close - 1,
  bench_fwd_return = CASE WHEN bench_entry_close IS NOT NULL THEN
      (SELECT close FROM prices
       WHERE symbol = {bench} AND price_date = x.xdate)
      / bench_entry_close - 1 END,
  matured_at = :now
FROM (SELECT t.rowid AS rid,
             (SELECT p.price_date FROM prices p
              WHERE p.symbol = t.{sym} AND p.price_date > t.entry_date
                AND (SELECT COUNT(*) FROM prices q
                     WHERE q.symbol = t.{sym}
                       AND q.price_date > t.entry_date
                       AND q.price_date <= p.price_date) = t.horizon
              LIMIT 1) AS xdate
      FROM {table} t WHERE t.exit_date IS NULL) AS x
WHERE {table}.rowid = x.rid AND x.xdate IS NOT NULL
  AND julianday(x.xdate) - julianday({table}.entry_date)
      <= {table}.horizon * 2 + 7
  AND NOT """
    + _BREAK_SCAN.format(who="{table}.{sym}", t="{table}")
    + """
  AND NOT """
    + _BREAK_SCAN.format(who="{bench}", t="{table}")
    + "\n"
)

_MATURE_REGIME = (
    """
UPDATE regime_outcomes SET
  exit_date = x.xdate,
  bench_exit_close = (SELECT close FROM prices
                      WHERE symbol = :bench AND price_date = x.xdate),
  bench_fwd_return = (SELECT close FROM prices
                      WHERE symbol = :bench AND price_date = x.xdate)
                     / bench_entry_close - 1,
  matured_at = :now
FROM (SELECT t.rowid AS rid,
             (SELECT p.price_date FROM prices p
              WHERE p.symbol = :bench AND p.price_date > t.entry_date
                AND (SELECT COUNT(*) FROM prices q
                     WHERE q.symbol = :bench
                       AND q.price_date > t.entry_date
                       AND q.price_date <= p.price_date) = t.horizon
              LIMIT 1) AS xdate
      FROM regime_outcomes t WHERE t.exit_date IS NULL) AS x
WHERE regime_outcomes.rowid = x.rid AND x.xdate IS NOT NULL
  AND julianday(x.xdate) - julianday(regime_outcomes.entry_date)
      <= regime_outcomes.horizon * 2 + 7
  AND NOT """
    + _BREAK_SCAN.format(who=":bench", t="regime_outcomes")
    + "\n"
)


def mature(conn, now_iso, benchmark="SPY") -> int:
    n = 0
    params = {
        "now": now_iso,
        "bench": benchmark,
        "lo": BASIS_BREAK_LO,
        "hi": BASIS_BREAK_HI,
    }
    for table, sym, bench in (
        ("ticker_outcomes", "symbol", ":bench"),
        ("signal_outcomes", "entity", "signal_outcomes.benchmark"),
    ):
        cur = conn.execute(_MATURE_SYMBOL.format(table=table, sym=sym, bench=bench), params)
        n += cur.rowcount
    n += conn.execute(_MATURE_REGIME, params).rowcount
    conn.commit()
    return n


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Run headers only. The prices ledger and the outcome tables are both
    permanent — outcomes ARE the experiment, and the ledger is the backtest
    evidence (a few hundred MB/year; pruning it would discard history no
    source can re-serve)."""
    header_cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    n = conn.execute("DELETE FROM snapshots WHERE captured_at < ?", (header_cutoff,)).rowcount
    conn.commit()
    return n
