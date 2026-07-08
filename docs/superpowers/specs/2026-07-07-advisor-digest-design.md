# Advisor digest — design

**Date:** 2026-07-07
**Status:** design approved, ready for implementation plan
**Roadmap item:** #8 "Advisor enrichment" residual — *fold advisor output into the
9:15pm daily-summary digest*.

## Problem

The 9:15pm ntfy digest (`deploy/launchd/daily_summary.py`) is a **health**
report: run counts, FAILED/STALE lines, non-zero exit codes, stale DBs. It
already appends a best-effort `— signals —` block (composite regime + scorer
stats) via `signals_digest()`. It does **not** surface the `advisor` combiner's
output, so the one thing pushed to the phone each night says nothing about the
book: total risk, holdings the model disagrees with, or size caps. The human has
to open a SQL client (or ask Claude) to read advice the advisor already
computed at 9:12pm.

## Goal

Add a sibling `— advisor —` block to the nightly digest that presents, in clean
plain text, the advisor's per-night book view: total heat, disagreements
against real holdings, size caps, and a staleness note when the holdings
snapshot isn't from tonight. Decision-support only — no new analysis, no
automation; strictly a presentation layer over existing `advisor.db` views.

## Constraints & context

- **ntfy limits are the only real limits.** Message body up to 4096 bytes
  before ntfy converts it to a file attachment — the digest is a few hundred
  bytes, so length is not a constraint. **Markdown renders only in the ntfy web
  app**, not on mobile push, and does not support tables; therefore the block is
  **clean structured plain text, no markdown** — reads well everywhere and never
  degrades to raw syntax. (Matches the existing `— signals —` convention.)
- **Best-effort, never alarm.** The advisor block *informs*; the health layers
  above *alert*. Any read failure degrades to a single note line; the digest
  still sends. Same contract as `signals_digest()`.
- **Read-only.** Open `data/advisor.db` with `mode=ro`. The 9:15 slot runs after
  advisor (9:12), so tonight's rows are normally present.
- **Offline tests.** No network, no real DB required in tests — matches the
  suite. The pure formatter is tested with hand-built rows.
- **Do not duplicate regime.** `signals_digest()` already prints the regime
  line; the advisor block is strictly *your book*.

## Architecture

One new function pair in `deploy/launchd/daily_summary.py`, mirroring
`signals_digest()` but split so the formatting is unit-testable:

- **`format_advisor_lines(book, disagreements, caps, header) -> list[str]`** —
  **pure**. Takes already-fetched rows (tuples/`sqlite3.Row`/None), returns the
  display lines. No DB, no I/O. This is where all formatting logic and empty-case
  wording lives, and it is the unit-under-test.
- **`advisor_digest() -> list[str]`** — thin reader. Opens
  `data/advisor.db?mode=ro`, reads the four sources, calls the formatter. Wrapped
  in `try/except sqlite3.Error` → returns a single
  `advisor: unreadable (ErrType)` line; never raises.
- **`build_summary(...)`** — gains one addition: after the `— signals —` block,
  append `["", "— advisor —", *advisor_digest()]` when non-empty.

No new modules. No changes to the `advisor` combiner or `notify.py` — every input
already exists as an advisor view.

## Data flow

| Source (`advisor.db`, read-only)                                             | Feeds                                                        |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------- |
| `v_book_heat` (one-row aggregate: `positions`, `heat_pct`, `heat_coverage`, `equity`) | the **book** line                                    |
| `v_disagreements` (0+ rows: `symbol`, `score_sum`, `total`, `group_name`, `strong`)   | one **disagree** line per holding                    |
| `v_latest_caps` (0+ rows)                                                    | **cap** line(s), or "none tonight"                          |
| `snapshots` header (`portfolio_captured_at`, `captured_at`, `sources_failed`) | the **staleness note** and a source-failure note           |

`v_book_heat` is already a per-snapshot aggregate keyed to `v_latest_snapshot`,
so no summing is needed. `heat_pct` is a **fraction** (e.g. `0.0021` = 0.21%).

## Output format

Rendered from real data for 2026-07-07:

```
— advisor —
book: 0.21% risk · 2 positions · cov 1.0 · equity $200
disagree: XOM -1 weak (energy)
caps: none tonight
(sized vs portfolio from Jul 06 — 2d old)
```

Formatting rules (enforced by `format_advisor_lines`, all unit-tested):

- **book line**: `book: {heat_pct:.2%} risk · {positions} position(s) · cov
  {heat_coverage:.1f} · equity ${equity:.0f}`.
  - `heat_pct` is a fraction → format with Python `{:.2%}` (e.g. `0.0021` →
    `0.21%`, `0` → `0.00%`, `0.00008` → `0.01%`). The two decimal places guard
    both the "fraction printed as whole percent" bug and the collapse of small
    non-zero risk to `0.0%`.
  - `cov` from `heat_coverage` (fraction of book with ATR data), `{:.1f}`.
    `heat_coverage` may be NULL (no positions / zero market value) → render
    `cov n/a`.
  - `equity` rounded to whole dollars with `${:.0f}`. NULL equity → `equity ?`.
  - `positions` pluralized (`1 position`, `2 positions`).
- **disagree line(s)**: one per `v_disagreements` row —
  `disagree: {SYM} {±score_sum} {weak|STRONG} ({group_name})`.
  - `strong = 1` → uppercase `STRONG`; else `weak`.
  - `group_name` omitted (with its parens) when NULL.
  - multiple rows → multiple lines in a stable order (by `score_sum` ascending,
    then symbol).
  - none → single line `disagree: none`.
- **caps line(s)**: when `v_latest_caps` non-empty, one per row —
  `cap: {SYM} ≤ {cap_shares:.2f}sh` (cap_shares is a fractional REAL), ordered
  by symbol; when empty → `caps: none tonight`.
- **staleness note**: compare `portfolio_captured_at` date to `captured_at`
  (run) date. When they differ → append `(sized vs portfolio from {Mon DD} —
  {N}d old)`. Same calendar day → omit the note entirely.
- **source-failure note**: when `sources_failed > 0` → extra line
  `advisor: {N} sources failed`.
- **no snapshot header at all** → the block is the single line
  `advisor: no snapshot`.

## Error handling

- `advisor_digest()` wraps all reads in `try/except sqlite3.Error`; on failure
  returns `["advisor: unreadable (ErrType)"]`. The digest still assembles and
  sends. Mirrors `signals_digest()` exactly.
- `format_advisor_lines` is total: it accepts `None`/empty for any input and
  produces sensible lines (`no snapshot`, `disagree: none`, `caps: none
  tonight`) rather than raising.

## Testing

New `tests/test_daily_summary_advisor.py`, exercising the pure
`format_advisor_lines` with hand-built rows (no DB, no network), plus one
reader-level failure test. `deploy/launchd/` is imported by path the same way
the module already inserts the repo root on `sys.path`.

1. **Nominal** — tonight's data → exact 4-line block (book, disagree, caps,
   staleness).
2. **Risk-% formatting** — `heat_pct=0.0021` → `0.21%`; `0.00008` → `0.01%`
   (non-zero); `heat_pct=0` → `0.00%`.
2b. **NULL book fields** — NULL `heat_coverage` → `cov n/a`; NULL `equity` →
   `equity ?`; both present render normally.
3. **Disagreement labeling** — `strong=1` → `STRONG`; `strong=0` → `weak`;
   NULL `group_name` → no parens.
4. **Multiple disagreements** — 3 rows → 3 lines in stable (`score_sum` asc,
   then symbol) order.
5. **Empty disagreements** — `disagree: none`.
6. **Caps present** — rows → `cap:` lines; **caps empty** → `caps: none
   tonight`.
7. **Staleness** — same-day `portfolio_captured_at` → no note; 2-days-prior →
   note with `2d old` and correct `Mon DD`.
8. **Source failures** — `sources_failed=2` → `advisor: 2 sources failed`;
   **no snapshot** (`header=None`) → single `advisor: no snapshot` line.
9. **Reader resilience** — a simulated `sqlite3.Error` from the reader yields
   `advisor: unreadable (OperationalError)` and does not raise.

## Out of scope (YAGNI)

- No ntfy `Click`/`Actions`/`Icon` features (no web dashboard to link to yet).
- No markdown (renders only in the web app; degrades to raw syntax on mobile).
- No changes to the advisor combiner, its views, or its schedule.
- No new alerting/priority behavior — the advisor block never changes the
  healthy/unhealthy verdict or the notification priority.
```
