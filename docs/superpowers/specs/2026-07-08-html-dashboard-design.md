# Design: zero-dependency nightly HTML dashboard

Status: design only. No code ships in this plan; see "Deferred" at the end.

## 1. Goal & non-goal

**Goal**: a single self-contained static HTML file, regenerated nightly, that
summarizes the pipeline's accumulated state — regime, ticker scorecard,
signal efficacy, bucket performance, book heat/caps/disagreements, and the
human-filter tally — for a human to review before the weekly reweighting
decision. It opens locally (double-click, `file://`), no server involved.

**Non-goals** (explicitly out of scope, forever unless a future plan revisits
this decision):

- No interactivity beyond native HTML (`<details>`/`<summary>` disclosure is
  fine; no client-side JS state, no filtering/sorting widgets).
- No server, no live queries — the page is a snapshot of "as of last night's
  runs," not a dashboard app.
- No auth — the file lives on the always-on Mac mini's local filesystem,
  same trust boundary as the SQLite DBs themselves.
- No JS framework, no charting library, no CSS framework, no CDN reference of
  any kind. This is the hard constraint from CLAUDE.md ("Zero runtime
  third-party dependencies — everything is stdlib") extended to the
  dashboard's own output: the generator is Python stdlib, and the HTML it
  emits references nothing external either.

## 2. Architecture

Pure-stdlib generation, mirroring `daily_summary.py`'s already-proven pattern:

- **Read**: `sqlite3.connect("file:data/<db>?mode=ro", uri=True)` per source
  DB (`composite.db`, `scorer.db`, `advisor.db`). Strictly read-only — the
  generator never writes to any source DB. Each DB's block is wrapped in its
  own `try/except Exception`, exactly like `signals_digest()` /
  `advisor_digest()`: a failure becomes a visible "unavailable" note in that
  section, never a crash that aborts the whole page.
- **Render**: plain f-string / `string.Template` HTML assembly. No template
  engine. A handful of small pure functions, one per section
  (`_regime_section(conn) -> str`, `_scorecard_section(conn) -> str`, …),
  each returning an HTML fragment string; `main()` concatenates them into the
  page skeleton. This mirrors the existing `_book_line`/`_disagree_lines`/
  `_caps_lines` decomposition in `daily_summary.py` — small pure formatters,
  easy to unit test without a DB.
- **Write**: `pathlib.Path(output_path).write_text(html, encoding="utf-8")`.
  Atomic-enough for a single local reader: write to a temp path in the same
  directory then `os.replace` into place, so a reader who opens the file
  mid-write never sees a truncated page.

**Where it lives**: `deploy/launchd/dashboard.py`, alongside
`daily_summary.py`. Rationale over a `main.py`-dispatched combiner: the
dashboard is not a data source and produces no queryable rows of its own —
it is a pure *rendering* pass over combiner output, same category as
`daily_summary.py` (which also isn't in `registry.py`). Keeping it beside
`daily_summary.py` keeps "things that read `data/*.db` read-only and produce
a human-facing artifact" in one place.

**Output path**: `reports/dashboard.html` (new top-level dir, sibling to
`data/` and `logs/`; add to `.gitignore` alongside `data/` since it's
generated, not source). A fixed filename (not timestamped) so "open the
dashboard" is always the same path — history lives in the DBs, not in a pile
of old HTML files.

## 3. Section catalog

Each section is independently try/excepted. Query source: Step 1 below (all
validated against live data in this session).

| # | Heading | DB | Query | Render |
|---|---|---|---|---|
| 1 | Regime | composite | `v_latest_regime` header | Stat tile row: regime label (colored badge: risk_on=green, risk_off=red, mixed=amber), VIX, inputs coverage `N/M` |
| 2 | Regime timeline | composite | `v_score_history` — actually regime needs its own longitudinal query (see appendix Q1b: `SELECT s.captured_at, m.regime, m.vix FROM market_regime m JOIN snapshots s ON s.id=m.snapshot_id ORDER BY s.captured_at DESC LIMIT 30`) | Inline-SVG sparkline of VIX over the trailing N snapshots, one dot per night colored by that night's regime; no axes chrome, just a readable trend line (stdlib `<svg><polyline>` string, coordinates computed in Python) |
| 3 | Ticker scorecard + flagged | composite | `v_latest_scorecard` (top movers by `ABS(score_sum)`), `v_flagged` | Table: symbol, score_sum, bullish/bearish/total, coverage, in_portfolio flag. Flagged rows get a highlighted row class |
| 4 | Signal efficacy | scorer | `v_signal_efficacy` | Table: signal_id, via_crosswalk, horizon, n_matured, avg_directional_excess, hit_rate (as %), CI lo/hi, reliable (badge — dim if `reliable=0`, since n_bench < 30 is not yet trustworthy) |
| 5 | Bucket performance | scorer | `v_bucket_performance` | Table: bucket × horizon, n_matured, avg_fwd_return, avg_excess, hit_rate, reliable badge |
| 6 | Human-filter tally | scorer | `v_human_filter` | Small stat table: response (acted/passed/passed_inferred) × horizon → n, avg_dir_excess, avg_fwd_return. This is the headline "does the human filter add value" number |
| 7 | Advisor book heat | advisor | `v_book_heat` | Stat tile row: positions, heat_pct, heat_coverage, equity, sources_failed (flag if >0) |
| 8 | Advisor group heat | advisor | `v_group_heat` | Table: bet (group or symbol), members, symbols, heat_dollars, heat_pct — shows crosswalk groups collapsed to one bet, as the view already does |
| 9 | Disagreements | advisor | `v_disagreements` | Table: symbol, score_sum, group_name, strong badge (red if `strong=1`) |
| 10 | Size caps | advisor | `v_latest_caps` | Table: symbol, direction, score_sum, cap_shares, cap_dollars, group_heat_pct, exceeds_buying_power flag |
| 11 | *(placeholder)* Plan-001 signal-efficacy report | — | — | Reserve a `<section id="plan-001-report">` with a "not yet available" note. Becomes real once plan 001 ships a report artifact/view to render |
| 12 | *(placeholder)* Plan-004 trader scorecard | — | — | Reserve a `<section id="plan-004-scorecard">` with a "not yet available" note. Becomes real once plan 004 lands |

No section uses a chart library. The only "chart" (regime VIX sparkline,
§2) is inline SVG built by hand: a `<polyline points="x1,y1 x2,y2 ...">`
where x/y are computed in Python from the fetched rows — zero JS, zero
external assets, degrades gracefully to "no data" text if the query returns
< 2 points.

## 4. Self-containment & theming

- All CSS lives in one `<style>` block in the `<head>` — no external
  stylesheet, no Google Fonts, no CDN link tag of any kind.
- Font stack: system fonts only (`-apple-system, BlinkMacSystemFont,
  "Segoe UI", sans-serif`) plus a monospace stack for numeric columns
  (tabular alignment matters for scanning score_sum / hit_rate columns).
  `font-variant-numeric: tabular-nums` on numeric `<td>`s.
  No `@font-face`.
- No images. No SVG uses `xlink:href` to an external resource — every SVG is
  inline, generated in Python, containing only `<polyline>`/`<circle>`/
  `<line>` with literal coordinates.
- **Theme stance**: single, fixed dark theme (the trading desk convention —
  low eye strain for a 9pm review, and it removes an entire axis of
  maintenance). Not adaptive to `prefers-color-scheme`; this is a private,
  regenerated-nightly file, not a shared artifact — one committed choice is
  fine. If that changes, revisit; it's a CSS-only change (`:root` custom
  properties for the small palette already used) whenever it does.
- The file is fully self-contained: `Ctrl/Cmd+O` → `reports/dashboard.html`
  works with the machine offline.

## 5. Resilience

Direct extension of `daily_summary.py`'s existing discipline — this dashboard
adds no new failure-handling philosophy, it applies the proven one per
section instead of per digest-line:

- Each DB's connect + queries is wrapped in one `try/except Exception`. On
  failure: `print(f"{db}: unreadable ({type(e).__name__})")` to stderr (never
  `str(e)` — `daily_summary.py`'s discipline against leaking a urllib
  `HTTPError`'s embedded URL/api_key applies here too, though these are
  local `mode=ro` sqlite connects so the risk surface is smaller — keep the
  habit anyway for consistency and because a future db could theoretically be
  attached over a URI with embedded auth) and render that section as a single
  `<p class="unavailable">composite.db: unreadable (OperationalError)</p>`
  fragment instead of its table. The rest of the page still renders.
- A missing view inside a reachable DB (schema drift — see STOP conditions in
  the executing plan) raises `sqlite3.OperationalError: no such view`, which
  the same per-section try/except catches — degrades to "unavailable," does
  not abort sibling sections.
- Zero rows is not a failure: every table renders an explicit
  "no rows yet" `<tr>`/`<p>` rather than an empty `<table>` a reader might
  mistake for a rendering bug. This matters especially early in the project's
  life (composite/scorer/advisor are all young — several validated queries in
  §7 returned `[]` tonight, which is correct, not broken).
- The generator itself never raises past `main()`: outer `try/except` around
  page assembly, matching `daily_summary.py main()`'s
  `except Exception as e: summary = f"...failed ({type(e).__name__})"`
  pattern — on total failure, write a minimal HTML page saying so rather than
  leaving last night's stale file in place silently. (Trade-off: a stale
  dashboard from 3 nights ago with no error banner is worse than an
  explicit "generation failed" page — so a full failure still writes
  *something* rather than skipping the write.)

## 6. Cadence & wiring sketch (not implemented here)

- Placement: after `advisor` (9:12pm) and *before* `daily-summary` (9:15pm)
  per `docs/SCHEDULE.md`, so the dashboard reflects tonight's rows before the
  health ntfy fires — sketch only, e.g. a launchd slot at 9:13pm, OR simplest:
  call `dashboard.main()` as an extra step at the end of
  `daily_summary.py:main()`, wrapped in its own `try/except Exception` so a
  dashboard-generation bug can **never** delay or suppress the 9:15pm health
  ntfy (`notify.send(...)` must still fire even if dashboard rendering
  throws). This ordering constraint is the one hard rule from the plan and is
  repeated here for the build-plan author.
- A future build plan decides: separate launchd job vs. piggyback call. Either
  way the dashboard write must be provably non-blocking and non-failing with
  respect to the ntfy alert — that's the one invariant this design commits
  the builder to.
- No historical-charting polish, no plan-001/004 sections until those land
  (placeholders only, §3 rows 11–12).

## 7. Validated SQL appendix

All commands run from the worktree
`/Users/ninkuk/agentic-trading-bot/.claude/worktrees/agent-a25b262a27da161e5`
against the live checkout's databases via the absolute `mode=ro` URI (the
worktree has no `data/` dir of its own — it's gitignored). Every query below
exited 0. An empty `[]` / `None` result is a **pass** (young data), not a
failure — none of these raised an exception.

**Q1 — composite.db: regime header** (section 1)
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/composite.db?mode=ro',uri=True); print(c.execute('SELECT regime, vix, inputs_present, inputs_expected FROM v_latest_regime').fetchone())"
```
Result: `('risk_on', 16.13, 10, 10)` — exit 0.

**Q1b — composite.db: regime timeline** (section 2, sparkline source; not a
named view — `market_regime` joined to `snapshots` for the trailing window)
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/composite.db?mode=ro',uri=True); print(c.execute('SELECT s.captured_at, m.regime, m.vix FROM market_regime m JOIN snapshots s ON s.id=m.snapshot_id ORDER BY s.captured_at DESC LIMIT 30').fetchall())"
```
Re-run standalone in Step 3 (see below) — exit 0.

**Q2 — composite.db: score history (timeline source for section 3)**
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/composite.db?mode=ro',uri=True); print(c.execute('SELECT captured_at, symbol, score_sum FROM v_score_history ORDER BY captured_at DESC LIMIT 20').fetchall())"
```
Result: 20 rows (e.g. `('2026-07-08T04:05:05.336626+00:00', 'AACP', -1), ...`)
— exit 0.

**Q3 — composite.db: scorecard + flagged** (section 3)
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/composite.db?mode=ro',uri=True); print('scorecard sample:', c.execute('SELECT symbol, score_sum, total, coverage, in_portfolio FROM v_latest_scorecard ORDER BY ABS(score_sum) DESC LIMIT 10').fetchall()); print('flagged:', c.execute('SELECT symbol, score_sum, total, bullish, bearish FROM v_flagged').fetchall())"
```
Result: scorecard sample returned 10 rows (top `('CYDY', 3, 2, 0.1667, 0)`
etc.); `flagged: []` (no ticker currently clears the `|score_sum|>=4 AND
total>=3` bar) — exit 0.

**Q4 — scorer.db: signal efficacy** (section 4)
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/scorer.db?mode=ro',uri=True); print(c.execute('SELECT signal_id, via_crosswalk, horizon, n_matured, avg_directional_excess, hit_rate, reliable FROM v_signal_efficacy ORDER BY n_matured DESC LIMIT 10').fetchall())"
```
Result: `[]` (no matured signal outcomes yet) — exit 0.

**Q5 — scorer.db: bucket performance** (section 5)
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/scorer.db?mode=ro',uri=True); print(c.execute('SELECT bucket, horizon, n_matured, avg_fwd_return, avg_excess, hit_rate, reliable FROM v_bucket_performance ORDER BY horizon, bucket').fetchall())"
```
Result: `[]` — exit 0.

**Q6 — scorer.db: human-filter tally** (section 6)
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/scorer.db?mode=ro',uri=True); print(c.execute('SELECT response, horizon, n, avg_dir_excess, avg_fwd_return FROM v_human_filter').fetchall())"
```
Result: `[]` — exit 0.

**Q7 — advisor.db: book heat** (section 7)
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/advisor.db?mode=ro',uri=True); print(c.execute('SELECT positions, heat_pct, heat_coverage, equity, sources_failed FROM v_book_heat').fetchone())"
```
Result: `(2, 0.002129921146238533, 1.0, 200.12, 0)` — exit 0.

**Q8 — advisor.db: group heat** (section 8)
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/advisor.db?mode=ro',uri=True); print(c.execute('SELECT bet, group_name, members, symbols, heat_dollars, heat_pct FROM v_group_heat').fetchall())"
```
Result: `[('DHR', None, 1, 'DHR', 0.3106, 0.00155), ('energy', 'energy', 1,
'XOM', 0.1156, 0.00058)]` — exit 0.

**Q9 — advisor.db: disagreements** (section 9)
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/advisor.db?mode=ro',uri=True); print(c.execute('SELECT symbol, score_sum, group_name, strong FROM v_disagreements').fetchall())"
```
Result: `[('XOM', -1, 'energy', 0)]` — exit 0.

**Q10 — advisor.db: latest caps** (section 10)
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/advisor.db?mode=ro',uri=True); print(c.execute('SELECT symbol, direction, score_sum, cap_shares, cap_dollars, group_name, exceeds_buying_power FROM v_latest_caps').fetchall())"
```
Result: `[]` (no ticker currently clears the flag bar, so no caps to show) —
exit 0.

All queries (Q1–Q10, plus Q1b) resolved every named view, ran `SELECT`-only,
and touched only `mode=ro`-attached connections. `git status --porcelain
sources main.py registry.py deploy` was empty throughout (confirmed in the
executor's report).

## Deferred

- The actual generator module (`deploy/launchd/dashboard.py`).
- Its launchd slot or `daily_summary.py` call-site wiring.
- Any historical-charting polish beyond the single VIX sparkline sketched in
  §3.
- Sections 11–12 (plan-001 report, plan-004 scorecard) become real once those
  plans ship.
