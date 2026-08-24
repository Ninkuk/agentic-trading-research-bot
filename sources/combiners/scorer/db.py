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

from sources.combiners.scorer import catalog

# Basis-break guard bounds: the ledger stores each day's close on that day's
# price basis with no adjusted history to correct from, so a split shows up
# as a consecutive-date ratio near 1/2, 1/3, 2, 5, ... — outside these
# bounds. Multiplication (not division) so a zero prev-close flags
# conservatively. Sub-threshold splits (3:2, ratio 0.667) pass undetected —
# accepted residual.
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
# The floor applies THREE times: benchmarked rows, distinct composite
# dates, AND non-overlapping blocks. Same-day rows are one cross-sectional
# episode, not independent draws — si_spike carried n_bench=2,599 over 8
# distinct dates and wore the badge (measured live). Distinct dates
# are not independent either: consecutive sessions share 4/5 of a 5-day
# forward window, so 30 nightly runs are ~5 independent observations, not
# 30. The binomial CI assumes independence; the nearest unit to an
# independent observation here is the non-overlapping forward window.
RELIABLE_MIN_N = 30  # benchmarked-sample floor for the reliable flag
# Blocks are the independent unit, so the n>=30 rule of thumb attaches
# HERE; the row/date floors above are kept as explicit backstops. The
# value was carried from RELIABLE_MIN_N deliberately — strict-by-default —
# and may only be re-chosen DOWNWARD after a measured calibration pass
# (a pre-data choice must never grant a badge, only withhold one).
RELIABLE_MIN_BLOCKS = 30  # non-overlapping-window floor for reliable

# Flag thresholds, mirroring composite v_flagged (|score_sum| >= 3 AND
# total >= 2). Both are hand-tunable; test_journal_matching pins these to
# composite's view text so the journal and composite drift together.
FLAG_MIN_ABS_SCORE = 3
FLAG_MIN_TOTAL = 2


def _wilson(sign: str, n: str = "COUNT(hit)", p: str = "AVG(hit)") -> str:
    """Wilson score bound (+1 upper / -1 lower via sign) as a SQL fragment.
    Defaults aggregate a 0/1 `hit` column (NULL hits excluded by COUNT/AVG);
    pass n=/p= to compute the same bound from pre-aggregated columns — the
    efficacy views bind n to the BLOCK count, so thousands of
    overlapping-window rows widen nothing."""
    z = str(WILSON_Z)
    return (
        f"CASE WHEN {n} > 0 THEN"
        f" ({p} + {z}*{z}/(2.0*{n})"
        f" {sign} {z} * sqrt({p}*(1-{p})/{n} + {z}*{z}/(4.0*{n}*{n})))"
        f" / (1 + {z}*{z}/{n}) END"
    )


# The hit definition shared by v_signal_efficacy and
# v_signal_efficacy_by_date (one fragment so the two cannot drift): a
# bullish call hits when the entity beat its benchmark, a bearish one when
# it lagged. Rows with no gradable benchmark contribute NULL. score = 0
# rows never reach signal_outcomes (fetch.read_signal_rows filters them),
# so the ELSE branch only ever sees bearish scores.
_SIGNAL_HIT = (
    "CASE WHEN s.bench_fwd_return IS NULL THEN NULL"
    " WHEN s.score > 0 THEN (s.fwd_return > s.bench_fwd_return)"
    " ELSE (s.fwd_return < s.bench_fwd_return) END"
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

-- Permanent account-equity ledger, one row per Phoenix date, harvested out
-- of portfolio.db's prunable snapshots before the cascade eats them (same
-- settled-ledger pattern as prices). NEVER pruned. transfers records
-- external cash flows (signed: + deposit, − withdrawal) so the scorecard's
-- time-weighted chaining can neutralize deposit timing; without it a
-- deposit reads as alpha. NEVER pruned.
CREATE TABLE IF NOT EXISTS equity_ledger (
    obs_date    TEXT PRIMARY KEY,
    equity      REAL NOT NULL,
    cash        REAL,
    captured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transfers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    obs_date    TEXT NOT NULL,
    amount      REAL NOT NULL,
    note        TEXT,
    recorded_at TEXT NOT NULL
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
    -- Option identity (all NULL = equity row; 2026-07 options migration).
    -- symbol stays the UNDERLYING (matching is per-ticker) and side is the
    -- DIRECTIONAL intent derived from (broker side, right) at parse time.
    -- Option rows grade SELECTION only in these views; their dollars live
    -- in premium_flows / v_option_pnl. contract_ref is the OCC symbol; strategy_ref
    -- groups legs of one multi-leg order (refused at the parser today);
    -- expiration feeds the journal's terminal-event sweep.
    contract_ref          TEXT,
    strategy_ref          TEXT,
    position_effect       TEXT CHECK (position_effect IN ('open', 'close')),
    expiration            TEXT,
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
    skipped            INTEGER NOT NULL DEFAULT 0,
    expired_closed     INTEGER NOT NULL DEFAULT 0
);

-- Option premium ledger (never pruned). cash is signed dollars from the
-- BROKER side (buy debit -, sell credit +) — decisions.side is remapped
-- to directional intent and cannot give the sign. Long vs short is the
-- open flow's sign. Multiplier fixed at 100 (OCC standard).
CREATE TABLE IF NOT EXISTS premium_flows (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER NOT NULL REFERENCES decisions(id),
    flow_date   TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('open','close','expire','exercise','assign')),
    premium     REAL NOT NULL CHECK (premium >= 0),
    contracts   REAL NOT NULL CHECK (contracts > 0),
    cash        REAL NOT NULL,
    order_ref   TEXT UNIQUE,
    recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_premium_flows_decision
    ON premium_flows (decision_id);

-- Research-verdict ledger: the research-ticker skill's own graded filter
-- (skill analog of the decision journal). One row
-- per (symbol, verdict_date) — the idempotency key; INSERT OR IGNORE makes
-- re-ingest a counted duplicate. verdict_date is a Phoenix calendar date
-- (bare YYYY-MM-DD, clock invariant). doc names the research/<T>-<D>.md
-- writeup as provenance TEXT only — nothing in sources/ reads research/.
-- Never pruned: verdicts are the other half of the research experiment.
CREATE TABLE IF NOT EXISTS research_verdicts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT NOT NULL,
    verdict      TEXT NOT NULL CHECK (verdict IN ('buy', 'pass')),
    verdict_date TEXT NOT NULL,
    doc          TEXT,
    note         TEXT,
    recorded_at  TEXT NOT NULL,
    UNIQUE (symbol, verdict_date)
);

-- Withdrawing a verdict recorded on a defective analysis. INSERT OR IGNORE
-- above makes re-ingest a counted duplicate, which is the right default -- but
-- alone it would mean a wrong call could never be withdrawn, grading a known
-- defect forever.
--
-- A verdict carrying `corrects: "<reason>"` UPDATEs the row and books the
-- prior value here. The original is preserved deliberately: v_research_filter
-- exists to measure the research skill honestly, and silently erasing that a
-- buy was once issued would flatter it. Never pruned, same as the verdicts
-- and decisions themselves.
CREATE TABLE IF NOT EXISTS verdict_corrections (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT NOT NULL,
    verdict_date TEXT NOT NULL,
    old_verdict  TEXT NOT NULL,
    new_verdict  TEXT NOT NULL,
    reason       TEXT NOT NULL,
    corrected_at TEXT NOT NULL
);

-- Forward outcomes per verdict x horizon, anchored on the VERDICT date
-- (not a composite snapshot). Column names deliberately mirror
-- ticker_outcomes so the generic _MATURE_SYMBOL template grades this
-- table with zero forked SQL; symbol is denormalized for its {sym} slot.
-- Registration reuses entry_for (first close STRICTLY AFTER verdict_date,
-- forward guard included): a symbol outside price coverage registers
-- nothing and is retried nightly. Never pruned.
CREATE TABLE IF NOT EXISTS verdict_outcomes (
    verdict_id        INTEGER NOT NULL,
    symbol            TEXT NOT NULL,
    horizon           INTEGER NOT NULL,
    entry_date        TEXT NOT NULL,
    entry_close       REAL NOT NULL,
    bench_entry_close REAL,
    exit_date         TEXT,
    exit_close        REAL,
    fwd_return        REAL,
    bench_fwd_return  REAL,
    matured_at        TEXT,
    PRIMARY KEY (verdict_id, horizon)
);

-- Candidate-screen appearance ledger: one row per (symbol, screen_date) the
-- quality screen surfaced, recorded nightly from stocks.db read-only.
-- screen_date is the Phoenix date of the stocks.db snapshot behind v_latest
-- (weekend runs re-see Friday's snapshot; OR IGNORE makes that free).
-- Metrics are stored as-seen for later re-analysis; via_rsi/via_drawdown
-- name the dislocation branch(es) that admitted the name; screen_version
-- stamps the gate set so efficacy never mixes gate regimes. Never pruned:
-- this ledger is the screen's only point-in-time record (stocks.db keeps
-- ~3 weeks of snapshots, and no vendor serves screener vintages).
CREATE TABLE IF NOT EXISTS candidate_appearances (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol         TEXT NOT NULL,
    screen_date    TEXT NOT NULL,
    screen_version TEXT NOT NULL,
    fcf_yield      REAL,
    rsi            REAL,
    high52ch       REAL,
    fscore         REAL,
    via_rsi        INTEGER NOT NULL DEFAULT 0,
    via_drawdown   INTEGER NOT NULL DEFAULT 0,
    -- Every quality gate, not just the timing fields: a rising fcf yield
    -- with falling roic/fScore is a falling knife, invisible to level gates
    -- and readable only from this ledger (v_candidate_quality_trend).
    roic           REAL,
    roic5y         REAL,
    rev_growth_3y  REAL,
    net_debt_ebitda REAL,
    shares_yoy     REAL,
    accruals_pct_assets REAL,
    recorded_at    TEXT NOT NULL,
    UNIQUE (symbol, screen_date)
);

-- Forward outcomes per list-ENTRY episode x horizon. Columns mirror
-- verdict_outcomes so the generic _MATURE_SYMBOL template grades this
-- table with zero forked SQL. Only entries grade (see register_candidates);
-- continuation sightings never get rows here. Never pruned.
CREATE TABLE IF NOT EXISTS candidate_outcomes (
    appearance_id     INTEGER NOT NULL,
    symbol            TEXT NOT NULL,
    horizon           INTEGER NOT NULL,
    entry_date        TEXT NOT NULL,
    entry_close       REAL NOT NULL,
    bench_entry_close REAL,
    exit_date         TEXT,
    exit_close        REAL,
    fwd_return        REAL,
    bench_fwd_return  REAL,
    matured_at        TEXT,
    PRIMARY KEY (appearance_id, horizon)
);
"""

# Migrated onto pre-existing ledgers by ensure_schema; the CREATE above
# carries them for fresh DBs.
_APPEARANCE_QUALITY_COLS = (
    "roic",
    "roic5y",
    "rev_growth_3y",
    "net_debt_ebitda",
    "shares_yoy",
    "accruals_pct_assets",
)

_VIEWS = f"""
-- Bucketing lives in views (ELT): stored rows keep raw score_sum/total.
-- Buckets: strong_bull >= +4, bull +2..+3, neutral -1..+1, bear -3..-2,
-- strong_bear <= -4; rows with total < 2 bucket as 'thin' regardless.
-- hit = excess in the score's direction (bull: excess > 0; bear: < 0);
-- score_sum = 0 rows have no direction and contribute NULL hits. Buckets
-- are SPY-benchmarked throughout (ticker rows carry no crosswalk
-- provenance), so n_bench counts rows with a computable hit (a gradable
-- SPY leg AND a direction).
-- Sample-size honesty (both graded views): n_bench counts rows, n_dates
-- distinct benchmarked dates, n_blocks NON-OVERLAPPING forward windows —
-- the greedy chain over each group's per-date [MIN(entry), MAX(exit)]
-- window bounds (a new block starts at the first date whose entry_date >=
-- the running block's exit_date; equal is independent — touching windows
-- share a close, not a return interval). Consecutive nightly sessions
-- overlap ~(h-1)/h of their windows, so rows and dates both overstate the
-- sample; the Wilson CI is therefore computed on n_blocks with a
-- DATE-MEAN center (one date, one weight — see the dg CTEs), within-block
-- correlation treated as 1 — crude and conservative, in the same spirit
-- as the rest of this header.
DROP VIEW IF EXISTS v_bucket_performance;
CREATE VIEW v_bucket_performance AS
WITH RECURSIVE m AS (
    SELECT CASE WHEN t.total < 2 THEN 'thin'
                WHEN t.score_sum >= 4 THEN 'strong_bull'
                WHEN t.score_sum >= 2 THEN 'bull'
                WHEN t.score_sum <= -4 THEN 'strong_bear'
                WHEN t.score_sum <= -2 THEN 'bear'
                ELSE 'neutral' END AS bucket,
           t.horizon AS horizon, t.fwd_return AS fwd_return,
           t.fwd_return - t.bench_fwd_return AS excess,
           CASE WHEN t.bench_fwd_return IS NULL THEN NULL
                WHEN t.score_sum > 0 THEN (t.fwd_return > t.bench_fwd_return)
                WHEN t.score_sum < 0 THEN (t.fwd_return < t.bench_fwd_return) END AS hit,
           -- Same defect this view had as v_signal_efficacy: a hit_rate with a
           -- `reliable` badge and nothing to compare it against. A bull bucket
           -- is graded on outperformance and a bear bucket on
           -- underperformance, so they cannot share one baseline number --
           -- resolved per row from that row's own sign, NULL exactly when
           -- `hit` is NULL so both averages span the same rows.
           CASE WHEN t.bench_fwd_return IS NULL THEN NULL
                WHEN t.score_sum > 0 THEN u.p_over
                WHEN t.score_sum < 0 THEN u.p_under END AS null_hit,
           t.composite_date AS composite_date,
           t.entry_date AS entry_date, t.exit_date AS exit_date
    FROM ticker_outcomes t
    LEFT JOIN v_universe_baseline u ON u.horizon = t.horizon
    WHERE t.matured_at IS NOT NULL
),
d AS (
    SELECT bucket, horizon, composite_date,
           MIN(CASE WHEN hit IS NOT NULL THEN entry_date END) AS entry_date,
           MAX(CASE WHEN hit IS NOT NULL THEN exit_date END) AS exit_date
    FROM m GROUP BY bucket, horizon, composite_date
    HAVING COUNT(hit) > 0
),
chain AS (
    SELECT d.bucket, d.horizon, d.composite_date, d.exit_date
    FROM d
    WHERE d.composite_date = (SELECT MIN(d2.composite_date) FROM d d2
                              WHERE d2.bucket = d.bucket AND d2.horizon = d.horizon)
    UNION ALL
    -- composite_date > c.composite_date: cycle guard, see v_signal_blocks
    SELECT nx.bucket, nx.horizon, nx.composite_date, nx.exit_date
    FROM chain c JOIN d nx
      ON nx.bucket = c.bucket AND nx.horizon = c.horizon
     AND nx.entry_date >= c.exit_date
     AND nx.composite_date > c.composite_date
    WHERE nx.composite_date = (SELECT MIN(d2.composite_date) FROM d d2
                               WHERE d2.bucket = c.bucket AND d2.horizon = c.horizon
                                 AND d2.entry_date >= c.exit_date
                                 AND d2.composite_date > c.composite_date)
),
b AS (SELECT bucket, horizon, COUNT(*) AS n_blocks FROM chain GROUP BY bucket, horizon),
g AS (
    SELECT bucket, horizon, COUNT(*) AS n_matured,
           AVG(fwd_return) AS avg_fwd_return,
           AVG(excess) AS avg_excess,
           COUNT(hit) AS n_bench,
           COUNT(DISTINCT CASE WHEN hit IS NOT NULL THEN composite_date END) AS n_dates
    FROM m GROUP BY bucket, horizon
),
-- Date-grain graded statistics — see v_signal_efficacy's dg note (same
-- cluster-mean rationale: one date, one weight).
dg AS (
    SELECT bucket, horizon,
           AVG(d_hit) AS hit_rate,
           AVG(d_null) AS null_rate
    FROM (SELECT bucket, horizon, composite_date,
                 AVG(hit) AS d_hit, AVG(null_hit) AS d_null
          FROM m WHERE hit IS NOT NULL
          GROUP BY bucket, horizon, composite_date)
    GROUP BY bucket, horizon
)
SELECT g.bucket, g.horizon, g.n_matured, g.avg_fwd_return, g.avg_excess,
       dg.hit_rate, dg.null_rate,
       dg.hit_rate - dg.null_rate AS edge, g.n_bench, g.n_dates,
       COALESCE(b.n_blocks, 0) AS n_blocks,
       {_wilson("-", n="COALESCE(b.n_blocks, 0)", p="dg.hit_rate")} AS hit_ci_lo,
       {_wilson("+", n="COALESCE(b.n_blocks, 0)", p="dg.hit_rate")} AS hit_ci_hi,
       (g.n_bench >= {RELIABLE_MIN_N} AND g.n_dates >= {RELIABLE_MIN_N}
        AND COALESCE(b.n_blocks, 0) >= {RELIABLE_MIN_BLOCKS}) AS reliable
FROM g
LEFT JOIN dg ON dg.bucket = g.bucket AND dg.horizon = g.horizon
LEFT JOIN b ON b.bucket = g.bucket AND b.horizon = g.horizon;

-- Per-signal grade, direction-adjusted: excess * sign(score). Crosswalked
-- evidence is split out so mapped scores are graded separately. Guardrails:
-- n_bench is the binomial n (rows with a gradable benchmark; hit_rate,
-- avg_directional_excess and the CI only see those); n_matured - n_bench
-- is the unbenchmarked count, which avg_directional_return (raw, no
-- benchmark) still covers. reliable gates on n_bench AND n_dates (distinct
-- benchmarked composite dates), never n_matured — see the RELIABLE_MIN_N
-- note for why row count alone is one episode wearing a badge.
-- THE NULL both graded views are read against. Equities do not coin-flip
-- against a benchmark, and this universe least of all: every composite name is
-- a microcap and the index rallied through the whole graded window, so a
-- randomly chosen scored ticker beat SPY only 40.3% of the time at 10 days
-- (measured live). A hit_rate read against 0.5 was wrong in BOTH
-- directions at once -- see the note on v_signal_recommendation.
--
-- Population is ticker_outcomes (one row per snapshot x symbol), NOT
-- signal_outcomes, which carries one row per SIGNAL: a signal firing on 2,599
-- of 7,351 rows would otherwise supply a third of its own null. p_over is
-- measured rather than derived as 1 - p_under because exact ties exist (8 at
-- 5d, 3 at 10d) and belong in neither numerator.
--
-- One view, joined by both consumers, so the baseline cannot drift between
-- them the way two copies of the same SQL would.
DROP VIEW IF EXISTS v_universe_baseline;
CREATE VIEW v_universe_baseline AS
SELECT horizon,
       1.0 * SUM(fwd_return > bench_fwd_return) / COUNT(*) AS p_over,
       1.0 * SUM(fwd_return < bench_fwd_return) / COUNT(*) AS p_under
FROM ticker_outcomes
WHERE matured_at IS NOT NULL AND fwd_return IS NOT NULL
  AND bench_fwd_return IS NOT NULL
GROUP BY horizon;

-- Per-date drill-down: one row per (signal, crosswalk split, horizon,
-- composite_date). n_rows/n_bench/date_hit_rate are the date's evidence;
-- entry_date/exit_date are the date's forward-window bounds over its
-- BENCHMARKED rows (MIN entry, MAX exit — conservative), which is what
-- v_signal_blocks chains over. Zero-bench dates stay visible with NULL
-- window bounds; the block chain skips them.
DROP VIEW IF EXISTS v_signal_efficacy_by_date;
CREATE VIEW v_signal_efficacy_by_date AS
SELECT signal_id, via_crosswalk, horizon, composite_date,
       COUNT(*) AS n_rows,
       COUNT(hit) AS n_bench,
       AVG(hit) AS date_hit_rate,
       MIN(CASE WHEN hit IS NOT NULL THEN entry_date END) AS entry_date,
       MAX(CASE WHEN hit IS NOT NULL THEN exit_date END) AS exit_date
FROM (SELECT s.signal_id, s.via_crosswalk, s.horizon, s.composite_date,
             s.entry_date, s.exit_date, {_SIGNAL_HIT} AS hit
      FROM signal_outcomes s WHERE s.matured_at IS NOT NULL)
GROUP BY signal_id, via_crosswalk, horizon, composite_date;

-- The audit trail for n_blocks: one row per block ANCHOR date, chained
-- greedily — the earliest benchmarked date opens a block; the next block
-- opens at the first date whose entry_date >= the running block's
-- exit_date (equal is independent: touching windows share a close, not a
-- return interval). See the v_bucket_performance header for why blocks,
-- not rows or dates, are the sample size.
DROP VIEW IF EXISTS v_signal_blocks;
CREATE VIEW v_signal_blocks AS
WITH RECURSIVE chain AS (
    SELECT d.signal_id, d.via_crosswalk, d.horizon, d.composite_date, d.exit_date
    FROM v_signal_efficacy_by_date d
    WHERE d.n_bench > 0
      AND d.composite_date = (
          SELECT MIN(d2.composite_date) FROM v_signal_efficacy_by_date d2
          WHERE d2.signal_id = d.signal_id AND d2.via_crosswalk = d.via_crosswalk
            AND d2.horizon = d.horizon AND d2.n_bench > 0)
    UNION ALL
    -- composite_date > c.composite_date is redundant for well-formed data
    -- (mature() guarantees exit > entry) but is the cycle guard: a
    -- degenerate row with entry >= exit would otherwise re-select itself
    -- forever — UNION ALL has no cycle detection (verified: infinite
    -- recursion without this predicate).
    SELECT nx.signal_id, nx.via_crosswalk, nx.horizon, nx.composite_date, nx.exit_date
    FROM chain c JOIN v_signal_efficacy_by_date nx
      ON nx.signal_id = c.signal_id AND nx.via_crosswalk = c.via_crosswalk
     AND nx.horizon = c.horizon AND nx.n_bench > 0
     AND nx.entry_date >= c.exit_date
     AND nx.composite_date > c.composite_date
    WHERE nx.composite_date = (
        SELECT MIN(d2.composite_date) FROM v_signal_efficacy_by_date d2
        WHERE d2.signal_id = c.signal_id AND d2.via_crosswalk = c.via_crosswalk
          AND d2.horizon = c.horizon AND d2.n_bench > 0
          AND d2.entry_date >= c.exit_date
          AND d2.composite_date > c.composite_date)
)
SELECT signal_id, via_crosswalk, horizon, composite_date, exit_date FROM chain;

DROP VIEW IF EXISTS v_signal_efficacy;
CREATE VIEW v_signal_efficacy AS
WITH m AS (
    SELECT s.signal_id, s.via_crosswalk, s.horizon, s.benchmark,
           (s.fwd_return - s.bench_fwd_return)
               * (CASE WHEN s.score > 0 THEN 1 ELSE -1 END) AS dir_excess,
           s.fwd_return * (CASE WHEN s.score > 0 THEN 1 ELSE -1 END) AS dir_return,
           {_SIGNAL_HIT} AS hit,
           -- Resolved per ROW from that row's own direction, so a
           -- bidirectional signal (stocks_rsi votes both ways) gets a blended
           -- baseline instead of one wrong number. NULL exactly when `hit` is
           -- NULL, so both averages span the same rows; NULL when the universe
           -- is empty rather than silently reinstating 0.5.
           CASE WHEN s.bench_fwd_return IS NULL THEN NULL
                WHEN s.score > 0 THEN u.p_over ELSE u.p_under END AS null_hit,
           s.composite_date AS composite_date
    FROM signal_outcomes s
    LEFT JOIN v_universe_baseline u ON u.horizon = s.horizon
    WHERE s.matured_at IS NOT NULL
),
g AS (
    SELECT signal_id, via_crosswalk, horizon,
           COUNT(*) AS n_matured,
           AVG(dir_excess) AS avg_directional_excess,
           AVG(dir_return) AS avg_directional_return,
           COUNT(hit) AS n_bench,
           COUNT(DISTINCT CASE WHEN hit IS NOT NULL THEN composite_date END) AS n_dates,
           GROUP_CONCAT(DISTINCT benchmark) AS benchmarks
    FROM m
    GROUP BY signal_id, via_crosswalk, horizon
),
-- Date-grain (cluster-mean) graded statistics: each DATE weighs equally,
-- matching the block count the CI's n uses. Row-pooling let one heavy
-- cross-section drag the center (measured live: si_spike 5d
-- pooled 0.556 vs 0.537 by date — one date carried 26% of the rows), a
-- bias that never shrinks as blocks accumulate. null_rate gets the same
-- weighting so edge and the recommendation comparison stay coherent.
dg AS (
    SELECT signal_id, via_crosswalk, horizon,
           AVG(d_hit) AS hit_rate,
           AVG(d_null) AS null_rate
    FROM (SELECT signal_id, via_crosswalk, horizon, composite_date,
                 AVG(hit) AS d_hit, AVG(null_hit) AS d_null
          FROM m WHERE hit IS NOT NULL
          GROUP BY signal_id, via_crosswalk, horizon, composite_date)
    GROUP BY signal_id, via_crosswalk, horizon
),
b AS (
    SELECT signal_id, via_crosswalk, horizon, COUNT(*) AS n_blocks
    FROM v_signal_blocks GROUP BY signal_id, via_crosswalk, horizon
)
SELECT g.signal_id, g.via_crosswalk, g.horizon, g.n_matured,
       g.avg_directional_excess, dg.hit_rate, dg.null_rate,
       dg.hit_rate - dg.null_rate AS edge,
       g.avg_directional_return, g.n_bench, g.n_dates,
       COALESCE(b.n_blocks, 0) AS n_blocks,
       {_wilson("-", n="COALESCE(b.n_blocks, 0)", p="dg.hit_rate")} AS hit_ci_lo,
       {_wilson("+", n="COALESCE(b.n_blocks, 0)", p="dg.hit_rate")} AS hit_ci_hi,
       (g.n_bench >= {RELIABLE_MIN_N} AND g.n_dates >= {RELIABLE_MIN_N}
        AND COALESCE(b.n_blocks, 0) >= {RELIABLE_MIN_BLOCKS}) AS reliable,
       g.benchmarks
FROM g
LEFT JOIN dg ON dg.signal_id = g.signal_id
   AND dg.via_crosswalk = g.via_crosswalk AND dg.horizon = g.horizon
LEFT JOIN b ON b.signal_id = g.signal_id
   AND b.via_crosswalk = g.via_crosswalk AND b.horizon = g.horizon;

-- Decision-support verdict per signal (roadmap: signal-efficacy reweighting
-- report). Pure passthrough of v_signal_efficacy plus one derived label a
-- human reads before hand-editing composite/catalog.py — it NEVER feeds back
-- into composite scoring (re-weighting stays a human decision, CLAUDE.md
-- invariant). The four states are mutually exclusive and checked in order:
--   reliable = 0 (n_bench/n_dates < RELIABLE_MIN_N or n_blocks <
--     RELIABLE_MIN_BLOCKS) -> 'insufficient evidence'
--   else hit_ci_hi < null_rate (whole 95% CI below the BASE RATE) -> 'anti-signal'
--   else hit_ci_lo > null_rate (whole 95% CI above the BASE RATE)  -> 'keep'
--   else (CI straddles the base rate, directionally unproven)      -> 'watch'
-- The comparison is against v_signal_efficacy.null_rate, NOT 0.5. Graded
-- against a coin flip this view was wrong in both directions at once: it
-- labelled si_spike `keep` on a +1.5pp edge and si_days_to_cover
-- `anti-signal` on a +1.1pp one (measured live). A NULL null_rate
-- (empty ticker_outcomes) makes both comparisons NULL, so the row falls
-- through to 'watch' rather than being judged against a guess.
-- reliable is re-derived from n_bench, n_dates and n_blocks here rather
-- than trusting the flag, so a future loosening of the efficacy view's gate
-- can't silently promote a thin signal to a verdict. via_crosswalk stays
-- split (never merged): direct and crosswalk evidence are distinct rows,
-- same as v_signal_efficacy.
DROP VIEW IF EXISTS v_signal_recommendation;
CREATE VIEW v_signal_recommendation AS
SELECT signal_id, via_crosswalk, horizon,
       n_matured, n_bench, n_dates, n_blocks, avg_directional_excess,
       hit_rate, null_rate, edge, hit_ci_lo, hit_ci_hi, reliable,
       CASE
           WHEN n_bench < {RELIABLE_MIN_N}
             OR n_dates < {RELIABLE_MIN_N}
             OR n_blocks < {RELIABLE_MIN_BLOCKS} THEN 'insufficient evidence'
           WHEN hit_ci_hi < null_rate THEN 'anti-signal'
           WHEN hit_ci_lo > null_rate THEN 'keep'
           ELSE 'watch'
       END AS recommendation
FROM v_signal_efficacy;

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
-- Option rows (contract_ref NOT NULL) grade SELECTION only: their
-- entry_slippage and realized_return are forced NULL — fill_price is a
-- premium, entry_close a stock close, and option P&L lives in
-- v_option_pnl, on premium terms. aligned survives (side is the
-- directional intent derived at parse time), and the flag's own paper
-- legs stay visible.
DROP VIEW IF EXISTS v_decision_outcomes;
CREATE VIEW v_decision_outcomes AS
SELECT d.id AS decision_id, d.symbol, d.side, d.source, d.placed_agent,
       d.contract_ref, d.strategy_ref, d.position_effect, d.expiration,
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
       CASE WHEN d.contract_ref IS NOT NULL THEN NULL
            WHEN t.entry_close IS NULL THEN NULL
            WHEN d.side = 'sell' THEN 1 - d.fill_price / t.entry_close
            ELSE d.fill_price / t.entry_close - 1 END AS entry_slippage,
       CASE WHEN d.contract_ref IS NOT NULL THEN NULL
            WHEN d.exit_fill_price IS NULL THEN NULL
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
-- MIN over the label is the precedence trick: 'acted' < 'acted_option' <
-- 'passed' < 'passed_inferred' alphabetically, so an equity act beats an
-- option act beats a pass. acted_option is its own bucket: the flag's
-- dir_excess still grades the SELECTION (did the flagged name move?), but
-- must never be read as the option position's P&L. dir_excess is excess
-- return in the flag's direction.
DROP VIEW IF EXISTS v_flag_response;
CREATE VIEW v_flag_response AS
SELECT t.composite_snapshot_id, t.composite_date, t.symbol,
       t.score_sum, t.total, t.horizon,
       t.fwd_return, t.bench_fwd_return,
       CASE WHEN t.bench_fwd_return IS NULL THEN NULL
            WHEN t.score_sum > 0 THEN t.fwd_return - t.bench_fwd_return
            ELSE t.bench_fwd_return - t.fwd_return END AS dir_excess,
       COALESCE(
           (SELECT MIN(CASE WHEN d.action = 'passed' THEN 'passed'
                            WHEN d.contract_ref IS NULL THEN 'acted'
                            ELSE 'acted_option' END)
            FROM decisions d
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
SELECT id AS decision_id, symbol, side, contract_ref, fill_date, fill_price,
       quantity, exit_fill_date, exit_fill_price,
       CASE WHEN contract_ref IS NOT NULL THEN NULL
            WHEN exit_fill_price IS NULL THEN NULL
            WHEN side = 'sell' THEN 1 - exit_fill_price / fill_price
            ELSE exit_fill_price / fill_price - 1 END AS realized_return,
       note, placed_agent, source, recorded_at
FROM decisions WHERE action = 'acted' AND composite_snapshot_id IS NULL;

-- Option P&L, one row per option decision, from premium_flows only.
-- direction is the open flow's sign; pnl_dollars is realized-to-date on
-- open positions; premium_return only once fully closed (long = return on
-- premium paid, short = fraction of collected premium kept; a short gone
-- wrong reads < -1.0). Equity grading views never read these numbers.
DROP VIEW IF EXISTS v_option_pnl;
CREATE VIEW v_option_pnl AS
SELECT d.id AS decision_id, d.symbol, d.side, d.contract_ref, d.expiration,
       d.composite_snapshot_id, d.composite_date, d.fill_date,
       CASE WHEN o.cash < 0 THEN 'long' ELSE 'short' END AS direction,
       o.contracts AS contracts_opened,
       COALESCE(c.contracts_closed, 0) AS contracts_closed,
       o.contracts - COALESCE(c.contracts_closed, 0) AS contracts_outstanding,
       (o.contracts - COALESCE(c.contracts_closed, 0) = 0) AS closed,
       o.cash + COALESCE(c.cash, 0) AS pnl_dollars,
       CASE WHEN o.contracts - COALESCE(c.contracts_closed, 0) = 0
             AND o.cash != 0
            THEN (o.cash + COALESCE(c.cash, 0)) / ABS(o.cash)
       END AS premium_return
FROM decisions d
JOIN premium_flows o ON o.decision_id = d.id AND o.kind = 'open'
LEFT JOIN (SELECT decision_id, SUM(contracts) AS contracts_closed,
                  SUM(cash) AS cash
           FROM premium_flows WHERE kind != 'open'
           GROUP BY decision_id) c ON c.decision_id = d.id;

-- The options actor: plain averages + n (v_human_filter posture; Wilson
-- once samples justify). hit is pnl > 0.
DROP VIEW IF EXISTS v_option_actor;
CREATE VIEW v_option_actor AS
SELECT direction, COUNT(*) AS n_closed,
       AVG(pnl_dollars > 0) AS hit_rate,
       SUM(pnl_dollars) AS total_pnl,
       AVG(premium_return) AS avg_premium_return
FROM v_option_pnl WHERE closed GROUP BY direction;

-- Research-verdict grading (the research-ticker skill as its own actor,
-- distinct from the human's decisions). ONE ROW PER HORIZON: filter or
-- group by horizon before aggregating, or every verdict counts
-- len(HORIZONS) times. excess = fwd - bench. verdict_correct: a buy is
-- right when the ticker beat the benchmark; a pass is right when it did
-- NOT (avoidance, never a short call — the theses say so explicitly).
-- NULL until matured, and NULL when the bench leg is ungradeable. An
-- uncovered ticker (no outcome rows) appears with NULL legs via the LEFT
-- JOIN — visible, not lost.
DROP VIEW IF EXISTS v_research_verdict_outcomes;
CREATE VIEW v_research_verdict_outcomes AS
SELECT rv.id AS verdict_id, rv.symbol, rv.verdict, rv.verdict_date,
       rv.doc, rv.note,
       vo.horizon, vo.entry_date, vo.entry_close,
       vo.fwd_return, vo.bench_fwd_return, vo.matured_at,
       vo.fwd_return - vo.bench_fwd_return AS excess,
       CASE WHEN vo.matured_at IS NULL OR vo.bench_fwd_return IS NULL THEN NULL
            WHEN rv.verdict = 'buy'
                 THEN (vo.fwd_return > vo.bench_fwd_return)
            ELSE (vo.fwd_return <= vo.bench_fwd_return) END AS verdict_correct
FROM research_verdicts rv
LEFT JOIN verdict_outcomes vo ON vo.verdict_id = rv.id;

-- The headline, mirroring v_human_filter: is the skill's filter any good?
-- Plain averages + n day one; the Wilson helpers can grade this once
-- samples justify it. Read with the multiple-comparisons caveat that
-- applies to every efficacy view here. Never feeds back into weights.
-- avg_excess/avg_fwd_return are RAW (fwd - bench), NOT direction-adjusted
-- like v_signal_efficacy's dir_excess -- for 'pass' rows they read
-- INVERSELY: a positive avg_excess among passes means the avoided names
-- beat the benchmark, i.e. the passes were WRONG. hit_rate (via
-- verdict_correct, which already flips polarity per verdict) is the
-- polarity-safe headline; read avg_excess/avg_fwd_return as raw color only.
DROP VIEW IF EXISTS v_research_filter;
CREATE VIEW v_research_filter AS
SELECT verdict, horizon, COUNT(*) AS n,
       AVG(verdict_correct) AS hit_rate,
       AVG(excess) AS avg_excess,
       AVG(fwd_return) AS avg_fwd_return
FROM v_research_verdict_outcomes
WHERE matured_at IS NOT NULL
GROUP BY verdict, horizon;

-- Candidate list-entry episodes with their forward legs. Every candidate is
-- an implicit "attractive", so beat_benchmark has one polarity (fwd > bench)
-- — no verdict flip. Unmatured and uncovered rows appear with NULL legs via
-- the LEFT JOIN: visible, not lost.
DROP VIEW IF EXISTS v_candidate_outcomes;
CREATE VIEW v_candidate_outcomes AS
SELECT ca.id AS appearance_id, ca.symbol, ca.screen_date, ca.screen_version,
       CASE WHEN ca.via_rsi AND ca.via_drawdown THEN 'both'
            WHEN ca.via_drawdown THEN 'drawdown' ELSE 'rsi' END AS branch,
       co.horizon, co.entry_date, co.entry_close,
       co.fwd_return, co.bench_fwd_return, co.matured_at,
       co.fwd_return - co.bench_fwd_return AS excess,
       CASE WHEN co.matured_at IS NULL OR co.bench_fwd_return IS NULL THEN NULL
            ELSE (co.fwd_return > co.bench_fwd_return) END AS beat_benchmark
FROM candidate_appearances ca
LEFT JOIN candidate_outcomes co ON co.appearance_id = ca.id;

-- The screen's report card: does entering the candidates list carry timing
-- edge over SPY, and through WHICH dislocation door (rsi / drawdown / both)?
-- Grades TIMING at the configured horizons, never the multi-year quality
-- thesis. Plain averages + n; every n here is entry-episodes (already
-- deduplicated), read with the usual multiple-comparisons caveat. Human
-- reading only — nothing feeds back into the screen's gates.
DROP VIEW IF EXISTS v_candidate_efficacy;
CREATE VIEW v_candidate_efficacy AS
SELECT screen_version, branch, horizon, COUNT(*) AS n,
       AVG(beat_benchmark) AS hit_rate,
       AVG(excess) AS avg_excess,
       AVG(fwd_return) AS avg_fwd_return
FROM v_candidate_outcomes
WHERE matured_at IS NOT NULL
GROUP BY screen_version, branch, horizon;

-- The current on-list episode per symbol, entry sighting vs latest. An
-- episode breaks on the same calendar gap register_candidates uses, so the
-- entry here is the sighting that was (or will be) graded. Trend WHILE on
-- the list only — stocks.db keeps ~3 weeks, so no longer history exists.
DROP VIEW IF EXISTS v_candidate_quality_trend;
CREATE VIEW v_candidate_quality_trend AS
WITH ordered AS (
    SELECT *, LAG(screen_date) OVER (PARTITION BY symbol ORDER BY screen_date) AS prev_date
    FROM candidate_appearances
),
marked AS (
    SELECT *, CASE WHEN prev_date IS NULL
                     OR julianday(screen_date) - julianday(prev_date)
                        > {catalog.CANDIDATE_ENTRY_GAP_DAYS}
                   THEN 1 ELSE 0 END AS is_entry
    FROM ordered
),
episodes AS (
    SELECT *, SUM(is_entry) OVER (PARTITION BY symbol ORDER BY screen_date) AS episode
    FROM marked
),
current AS (
    SELECT symbol, MAX(episode) AS episode FROM episodes GROUP BY symbol
)
SELECT e.symbol,
       MIN(e.screen_date) AS entry_date,
       MAX(e.screen_date) AS latest_date,
       CAST(julianday(MAX(e.screen_date)) - julianday(MIN(e.screen_date)) AS INTEGER)
           AS days_on_list,
       COUNT(*) AS n_sightings,
       MIN(CASE WHEN e.is_entry THEN e.fscore END) AS fscore_entry,
       MIN(CASE WHEN e.is_entry THEN e.roic END) AS roic_entry,
       MIN(CASE WHEN e.is_entry THEN e.fcf_yield END) AS fcf_yield_entry,
       MIN(CASE WHEN e.is_entry THEN e.accruals_pct_assets END) AS accruals_entry,
       (SELECT fscore FROM episodes l WHERE l.symbol = e.symbol AND l.episode = e.episode
         ORDER BY l.screen_date DESC LIMIT 1) AS fscore_now,
       (SELECT roic FROM episodes l WHERE l.symbol = e.symbol AND l.episode = e.episode
         ORDER BY l.screen_date DESC LIMIT 1) AS roic_now,
       (SELECT fcf_yield FROM episodes l WHERE l.symbol = e.symbol AND l.episode = e.episode
         ORDER BY l.screen_date DESC LIMIT 1) AS fcf_yield_now,
       (SELECT accruals_pct_assets FROM episodes l
         WHERE l.symbol = e.symbol AND l.episode = e.episode
         ORDER BY l.screen_date DESC LIMIT 1) AS accruals_now
FROM episodes e JOIN current c ON c.symbol = e.symbol AND c.episode = e.episode
GROUP BY e.symbol, e.episode;

DROP VIEW IF EXISTS v_equity_curve;
-- Daily time-weighted-return legs over LEDGER dates. flow is the date's
-- summed external transfers; port_return = (E_t − flow_t)/E_{{t−1}} − 1, the
-- standard TWR convention that neutralizes deposit timing. Ledger gaps
-- simply widen one leg — harmless UNLESS a transfer hides inside the gap,
-- which is why the scorecard refuses to chain past an orphan transfer.
-- spy_close rides along where a same-date SPY row exists (weekend ledger
-- rows carry NULL); readers compute SPY's cumulative leg from window
-- ENDPOINT closes, never per-day here.
CREATE VIEW v_equity_curve AS
SELECT e.obs_date,
       e.equity,
       COALESCE(t.flow, 0.0) AS flow,
       LAG(e.equity) OVER (ORDER BY e.obs_date) AS prev_equity,
       (e.equity - COALESCE(t.flow, 0.0))
           / NULLIF(LAG(e.equity) OVER (ORDER BY e.obs_date), 0) - 1
           AS port_return,
       p.close AS spy_close
FROM equity_ledger e
LEFT JOIN (
    SELECT obs_date, SUM(amount) AS flow FROM transfers GROUP BY obs_date
) t ON t.obs_date = e.obs_date
LEFT JOIN prices p ON p.symbol = 'SPY' AND p.price_date = e.obs_date;
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
    decisions.placed_agent. The third migration, journal_runs.verdicts_recorded,
    has no view referencing it -- it sits in this block for consistency with
    the other two migrations, not because ordering matters for it."""
    conn.executescript(_TABLES)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(signal_outcomes)")}
    if "benchmark" not in cols:
        conn.execute("ALTER TABLE signal_outcomes ADD COLUMN benchmark TEXT")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(decisions)")}
    if "placed_agent" not in cols:
        conn.execute("ALTER TABLE decisions ADD COLUMN placed_agent TEXT")
    for ddl in (
        "contract_ref TEXT",
        "strategy_ref TEXT",
        "position_effect TEXT CHECK (position_effect IN ('open', 'close'))",
        "expiration TEXT",
    ):
        if ddl.split()[0] not in cols:
            conn.execute(f"ALTER TABLE decisions ADD COLUMN {ddl}")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(journal_runs)")}
    if "verdicts_recorded" not in cols:
        conn.execute(
            "ALTER TABLE journal_runs ADD COLUMN verdicts_recorded INTEGER NOT NULL DEFAULT 0"
        )
    if "expired_closed" not in cols:
        conn.execute(
            "ALTER TABLE journal_runs ADD COLUMN expired_closed INTEGER NOT NULL DEFAULT 0"
        )
    if "option_flows" not in cols:
        conn.execute("ALTER TABLE journal_runs ADD COLUMN option_flows INTEGER NOT NULL DEFAULT 0")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(candidate_appearances)")}
    for col in _APPEARANCE_QUALITY_COLS:
        if col not in cols:
            conn.execute(f"ALTER TABLE candidate_appearances ADD COLUMN {col} REAL")
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


def upsert_equity(conn, rows) -> int:
    """equity_ledger writer: one row per Phoenix date, LAST WRITE WINS —
    unlike insert_prices' INSERT OR IGNORE, because a re-harvest that found
    a better in-window snapshot must be able to replace a fallback row."""
    n = 0
    for obs_date, equity, cash, captured_at in rows:
        if obs_date is None or equity is None:
            continue
        conn.execute(
            "INSERT INTO equity_ledger (obs_date, equity, cash, captured_at)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT(obs_date) DO UPDATE SET equity=excluded.equity,"
            " cash=excluded.cash, captured_at=excluded.captured_at",
            (obs_date, equity, cash, captured_at),
        )
        n += 1
    return n


def record_transfer(conn, obs_date, amount, note, now_iso) -> int:
    """External cash flow (signed: + deposit, − withdrawal), dated on the
    Phoenix calendar date it landed. Permanent — never pruned. The scorecard
    subtracts the date's summed flow before chaining, so an unrecorded
    transfer reads as (fake) performance."""
    cur = conn.execute(
        "INSERT INTO transfers (obs_date, amount, note, recorded_at) VALUES (?, ?, ?, ?)",
        (obs_date, amount, note, now_iso),
    )
    conn.commit()
    return cur.lastrowid


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


def register_verdicts(conn, horizons, benchmark, max_age_days) -> int:
    """Outcome rows for research verdicts that have none yet. Entries reuse
    entry_for: first ledger close STRICTLY AFTER verdict_date (a verdict
    formed intraday cannot claim that day's close — same no-look-ahead rule
    as snapshots), within the forward guard. Uncovered symbols register
    nothing and are retried nightly; coverage arriving beyond the guard
    window never registers (historically exact entry or nothing). All
    horizons for all pending verdicts commit atomically."""
    registered = 0
    pending = conn.execute(
        "SELECT rv.id, rv.symbol, rv.verdict_date FROM research_verdicts rv"
        " WHERE NOT EXISTS (SELECT 1 FROM verdict_outcomes vo"
        "                   WHERE vo.verdict_id = rv.id)"
    ).fetchall()
    with conn:
        for vid, symbol, vdate in pending:
            entry = entry_for(conn, symbol, vdate, max_age_days)
            if entry is None:
                continue
            bench = _bench_close(conn, benchmark, entry[0])
            for h in horizons:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO verdict_outcomes"
                    " (verdict_id, symbol, horizon, entry_date, entry_close,"
                    "  bench_entry_close) VALUES (?, ?, ?, ?, ?, ?)",
                    (vid, symbol, h, entry[0], entry[1], bench),
                )
                registered += cur.rowcount
    return registered


def record_appearances(conn, rows, screen_date, screen_version, now_iso) -> int:
    """One appearance row per (symbol, screen_date) the candidate screen
    surfaced. OR IGNORE makes a weekend run re-seeing Friday's stocks.db
    snapshot free. Caller commits (run.py's skip-and-continue owns the
    transaction boundary)."""
    n = 0
    for r in rows:
        cur = conn.execute(
            "INSERT OR IGNORE INTO candidate_appearances"
            " (symbol, screen_date, screen_version, fcf_yield, rsi, high52ch,"
            "  fscore, via_rsi, via_drawdown, roic, roic5y, rev_growth_3y,"
            "  net_debt_ebitda, shares_yoy, accruals_pct_assets, recorded_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r["symbol"],
                screen_date,
                screen_version,
                r.get("fcf_yield"),
                r.get("rsi"),
                r.get("high52ch"),
                r.get("fscore"),
                r.get("via_rsi", 0),
                r.get("via_drawdown", 0),
                r.get("roic"),
                r.get("roic5y"),
                r.get("rev_growth_3y"),
                r.get("net_debt_ebitda"),
                r.get("shares_yoy"),
                r.get("accruals_pct_assets"),
                now_iso,
            ),
        )
        n += cur.rowcount
    return n


def register_candidates(conn, horizons, benchmark, max_age_days, gap_days) -> int:
    """Outcome rows for list-ENTRY appearances that have none yet. An entry
    is an appearance with no prior appearance for the same symbol within
    gap_days calendar days — continuation sightings of the same episode
    never grade, or one call would be counted N times (the
    overlapping-sample trap v_signal_efficacy documents). The entry/
    continuation split is recomputed from the appearance ledger every night,
    so an uncovered entry retries until the forward guard closes, exactly
    like verdicts. Entries reuse entry_for: first ledger close STRICTLY
    AFTER screen_date (the screen reads that day's settled close — claiming
    it would pocket the overnight gap)."""
    registered = 0
    pending = conn.execute(
        "SELECT ca.id, ca.symbol, ca.screen_date FROM candidate_appearances ca"
        " WHERE NOT EXISTS (SELECT 1 FROM candidate_outcomes co"
        "                   WHERE co.appearance_id = ca.id)"
        "   AND NOT EXISTS (SELECT 1 FROM candidate_appearances prior"
        "                   WHERE prior.symbol = ca.symbol"
        "                     AND prior.screen_date < ca.screen_date"
        "                     AND prior.screen_date >= date(ca.screen_date, ?))",
        (f"-{int(gap_days)} days",),
    ).fetchall()
    with conn:
        for aid, symbol, sdate in pending:
            entry = entry_for(conn, symbol, sdate, max_age_days)
            if entry is None:
                continue
            bench = _bench_close(conn, benchmark, entry[0])
            for h in horizons:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO candidate_outcomes"
                    " (appearance_id, symbol, horizon, entry_date, entry_close,"
                    "  bench_entry_close) VALUES (?, ?, ?, ?, ?, ?)",
                    (aid, symbol, h, entry[0], entry[1], bench),
                )
                registered += cur.rowcount
    return registered


# Maturation: the Nth distinct ledger date after entry, per symbol.
# NOTE: SQLite rejects a correlated OFFSET ("LIMIT 1 OFFSET t.horizon - 1"
# fails with "no such column"), so the Nth date is selected via a
# COUNT-correlated WHERE instead.
# The julianday bound refuses to mature across a ledger gap wider
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
        ("verdict_outcomes", "symbol", ":bench"),
        ("candidate_outcomes", "symbol", ":bench"),
    ):
        cur = conn.execute(_MATURE_SYMBOL.format(table=table, sym=sym, bench=bench), params)
        n += cur.rowcount
    n += conn.execute(_MATURE_REGIME, params).rowcount
    conn.commit()
    return n


_OUTCOME_TABLES = (
    "signal_outcomes",
    "ticker_outcomes",
    "regime_outcomes",
    "verdict_outcomes",
    "candidate_outcomes",
)


def matured_counts(conn) -> dict:
    """table -> count of rows whose forward return has already been computed."""
    return {
        t: conn.execute(f"SELECT COUNT(*) FROM {t} WHERE matured_at IS NOT NULL").fetchone()[0]
        for t in _OUTCOME_TABLES
    }


def rebuild_prices(conn) -> tuple[int, int, int]:
    """Destructive one-shot repair for the off-by-one-session price ledger.

    Background: harvest_prices used to read stockanalysis's "close" column,
    which is the PREVIOUS session's close, so every ledger row carried a real
    close stamped with the NEXT trading day's date. Because insert_prices is
    INSERT OR IGNORE, a corrected harvester cannot overwrite those rows — they
    must be deleted first. Unmatured outcome rows hold entry_close values read
    from the bad ledger, so they are deleted too and re-register on the next
    run; their registered_snapshots gate rows go with them (registered_ids()
    would otherwise skip re-registration forever).

    REFUSES to run when any outcome row has matured: that row's forward return
    was computed from mislabeled closes and cannot be silently repaired.

    Returns (prices_deleted, outcomes_deleted, registrations_deleted)."""
    matured = matured_counts(conn)
    if any(matured.values()):
        raise RuntimeError(
            "refusing to rebuild: matured outcome rows exist "
            f"({', '.join(f'{t}={n}' for t, n in matured.items() if n)}). "
            "Their forward returns came from mislabeled closes; repair them "
            "deliberately before rebuilding."
        )

    prices = conn.execute("DELETE FROM prices").rowcount
    outcomes = 0
    for t in _OUTCOME_TABLES:
        outcomes += conn.execute(f"DELETE FROM {t} WHERE matured_at IS NULL").rowcount
    # The guard above proved every outcome row is unmatured, and the loop just
    # deleted all of them — so no registration can still be backing one. Clear
    # them unconditionally rather than keep an unreachable "survivor" filter.
    regs = conn.execute("DELETE FROM registered_snapshots").rowcount
    conn.commit()
    return prices, outcomes, regs


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Run headers only. The prices ledger and the outcome tables are both
    permanent — outcomes ARE the experiment, and the ledger is the backtest
    evidence (a few hundred MB/year; pruning it would discard history no
    source can re-serve). equity_ledger and transfers are permanent for the
    same reason: they are the only record of account equity once
    portfolio.db's snapshot cascade has run."""
    header_cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    n = conn.execute("DELETE FROM snapshots WHERE captured_at < ?", (header_cutoff,)).rowcount
    conn.commit()
    return n
