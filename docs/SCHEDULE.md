# Data-collection schedule

Every screener/monitor/combiner runs on a launchd schedule (35 `com.tradingbot.*`
LaunchAgents). **Source of truth is the `JOBS` dict in
`deploy/launchd/install.py`** — this doc is the human-readable view; if they
disagree, trust install.py and fix this file.

All times are **Phoenix wall-clock** (America/Phoenix, MST year-round — no
DST). Data publishers are US-East, so ET releases drift against a fixed
Phoenix clock: ET is 3h ahead in summer (EDT), 2h in winter (EST). Slots for
post-release jobs were placed using the winter offset (ET−2h), which is
at-or-after the release in both seasons; pre-open jobs anchor to the earlier
summer open (6:30am Phoenix).

## Intraday — weekdays, market hours

| Job | When | Notes |
|---|---|---|
| `options-intraday` | hourly :30, 6:30am–1:30pm | CBOE chains; IV/flow intraday shape. `--keep-days 90` |
| `reddit-intraday` | hourly :35, 6:35am–1:35pm | ApeWisdom sentiment. `--keep-days 90` |

## Daily — weekdays

| Job | When | Notes |
|---|---|---|
| `preopen` | 4:00am | ONE serialized process: earnings → stocks → etfs → reddit baseline. Earnings watchlist = portfolio.db holdings ∪ cboe_options catalog equities (required — without `--only`, 8-K confirmation is skipped). stocks/etfs run `--keep-days 30`: their metrics rows are snapshot-scoped and only `v_latest` is read, so unpruned they grow by a full universe/day |
| `nyfed` | 11:30am | After RRP results (~1:15pm ET) |
| `portfolio` | 2:30pm | Headless `claude -p "/account-positions"` → Robinhood MCP; verifies a fresh snapshot landed (no fresh snapshot = loud failure). Runs on **sonnet**: haiku improvises tools outside `--allowedTools` and then misreports the denial as unauthenticated MCP. Skill passes `--keep-days 365` (positions are snapshot-scoped) |
| `journal` | 2:40pm | Headless `claude -p "/journal-sync"` → Robinhood MCP order history → `main.py journal`. Ten minutes after portfolio so a headless failure shows up twice. Also **sonnet**, same reason. Empty-fill days still write a run header (that's what the freshness check reads). Journal matching reads composite.db; decisions land in scorer.db (never pruned) |
| `options-close` | 2:45pm | Settled end-of-day chains (post-close both seasons) |
| `treasury` | 4:30pm | FiscalData + yield-curve XML |
| `fred` | 4:40pm | Daily rate series finalized ~4:15pm ET. Observations only (no `--vintages`); vintages run weekly (see `fred-vintages` below) |
| `cboe-stats` | 6:00pm | VIX term-structure CSVs + daily put/call ratios (SSR stats page) |
| `short-volume` | 6:15pm | FINRA Reg SHO daily file |
| `short-interest` | 6:30pm | Daily probe; FINRA disseminates twice-monthly on varying days, 404s are free |
| `edgar` | 8:30pm (+retry 15min) | **Must stay in the evening**: the daily-index walk-back starts at *today* and stops at the first non-empty index, so a morning run (after EDGAR's 6am-ET filing window opens) stores a partial current-day sliver and permanently skips the prior day. Evening = same-day complete index. `--keep-days 90` — filings are snapshot-scoped and this bound IS `v_activity_history`'s lookback depth |

## Weekly

| Job | When | Notes |
|---|---|---|
| `fred-vintages` | Sat 7:00am | `fred --vintages`: full ALFRED revision history into `observation_vintages` (the backtest combiner's point-in-time store + `fred.v_asof`). Windowed+paginated fetch (~80 FRED calls, ~1.7M rows re-upserted, seconds). Weekly not nightly — vintages grow one date/day, backtesting reads them occasionally, so a nightly full re-pull would be wasteful. FRED endpoint, no SEC rate-limit interaction with Sat 6am `fundamentals` |
| `backtest` | Sat 7:30am | 4th combiner: replays **nine** of composite's signals point-in-time into `data/backtest.db` (`v_replay_efficacy`) — two FRED regime signals via ALFRED vintages, five market-grain signals, and two `eia_*` asset-class signals graded vs XLE (the rest vs SP500). 30min after `fred-vintages`. Reads `fred.db`/`cboe_stats.db`/`nyfed.db`/`treasury.db`/`eia.db` and `scorer.db`'s price ledger read-only; `--keep-days 365` bounds snapshot headers only. **Read `excess`, not `hit_rate`**: the latter is scored against 0.5 while SP500 drifts up ~68% of 21-day windows. `reliable` is a sample-size floor, never a verdict; `beats_baseline` is a nominal, uncorrected 95% flag across ~48 rows (≈2 expected by chance). Class-proxy spines (XLE/GLD/DBA/TLT) come from the one-shot `main.py pricehistory` backfill — never scheduled |
| `econ-calendar` | Mon 5:00am | FRED release dates |
| `fomc` | Mon 5:10am | Fed calendar page |
| `ats` | Mon 6:45pm | FINRA ATS weekly aggregates (published Mondays, 2–4wk lag) |
| `eia` | Wed/Thu/Fri 10:15am | WPSR Wed, NG storage Thu; the Friday run covers holiday-shifted releases |
| `cftc` | Fri 2:15pm | COT (Fri 3:30pm ET); all three families sequentially |
| `fundamentals` | Sat 6:00am | XBRL frames → `data/sec_fundamentals.db` |
| `ftd` | Sun 7:00am | Weekly probe; SEC publication dates drift |

## Monthly

| Job | When | Notes |
|---|---|---|
| `market-calendar` | 1st 5:00am | Seeded holidays/OPEX (network-free, can't break) |
| `market-calendar-refresh` | 1st 5:30am | Merges live NYSE/SIFMA holiday pages over the seed (which ends 2027-12). **Must stay monthly, after the seed run**: every run `replace_forward_window`s, so the seed-only run wipes refresh-added events and this re-adds them. Raises on page drift *before* touching the DB — a failed month just runs on seed data, loudly |
| `usda-nass` | 2nd 10:15am | NASS Quick Stats (corn/soy/wheat production + ending stocks; needs `NASS_API_KEY`). Feeds `v_latest_balance`/`v_stocks_to_use` — NASS reports are quarterly/annual, monthly probe is ample |
| `ftd-full` | 15th 8:00am | `--full` re-ingests all 24 months of FTD half-months; the weekly probe only re-fetches ~1 month back, so SEC reposts older than that land only here |
| `short-interest-full` | 15th 7:00pm | `--full` re-ingests ~12 months of settlements; the daily probe only re-fetches ~1 month back, FINRA corrections older than that land only here |
| `usda-wasde` | 12th & 16th 10:15am | WASDE lands ~9th–12th, occasionally later — the 16th probe catches stragglers |
| `composite` | every day 9:05pm | Combines all source DBs into `data/composite.db` (read-only attaches; regime + ticker scorecard). Must stay after every collector's last daily slot INCLUDING edgar's 15-min failure retry (~8:45pm+) and before daily-summary at 9:15pm |
| `scorer` | every day 9:10pm | Grades composite opinions: harvests closes into data/scorer.db, registers pending outcomes, matures forward returns. Must stay after composite 9:05pm. Outcome tables AND the close-price ledger are permanent (never pruned; the ledger is the future backtest store, growing a few hundred MB/year). Entries are next-day closes (no look-ahead), so a snapshot registers the night after its entry close is harvested — the newest snapshot printing `defer` is steady-state, not a failure |
| `advisor` | every day 9:12pm | Sizing/risk advice into `data/advisor.db`: joins the composite scorecard against portfolio holdings + stocks/etfs ATR + scorer efficacy (all attached read-only). Book heat (`v_book_heat`/`v_group_heat`, crosswalk groups = one bet), holdings composite disagrees with (`v_disagreements`), and 1%-risk-budget size caps (`v_latest_caps`). Must stay after scorer 9:10pm, before daily-summary 9:15pm. Weekend runs size against Friday's 2:30pm portfolio snapshot — `portfolio_captured_at` in the header makes that auditable |
| `dashboard` | every day 9:13pm | Renders `composite`/`scorer`/`advisor` rows read-only into `reports/dashboard.html` (a self-contained static file; see `deploy/launchd/dashboard.py`). After advisor 9:12pm so it reflects tonight's rows; a separate process from daily-summary, so a render bug can never delay or suppress the 9:15pm ntfy. Each section is independently try/excepted — a missing DB/view degrades to an "unavailable" note, never a crash |
| `daily-summary` | every day 9:15pm | ntfy digest (see below) |
| `publish-dashboard` | every day 9:20pm | Force-pushes `reports/dashboard.html` to the `gh-pages` branch behind GitHub Pages (https://ninkuk.github.io/agentic-trading-bot/). **After** the 9:15pm ntfy by design — a hung push must not delay or suppress the health alert. Refuses to publish unless the file's mtime is tonight's *Phoenix* date, so a failed 9:13pm dashboard run fails loudly here instead of silently republishing yesterday's page. Single-commit orphan branch, force-pushed from a temp dir; the live worktree is never touched. Git calls are now bounded — push at 300s, other git calls at 120s — so the job cannot exceed roughly 13 minutes worst case. The page carries live account positions, so it ships `<meta name="robots" content="noindex,nofollow">` — the only crawler control that works here. It also publishes a `robots.txt`, but that lands at the project-page path `.../agentic-trading-bot/robots.txt`, which no crawler ever consults (robots.txt is per-origin, fetched only from `ninkuk.github.io/robots.txt`) — it is inert here, not a second layer of protection |

## Quarterly

| Job | When | Notes |
|---|---|---|
| `fundamentals-bulk` | Feb/May/Aug/Nov 20th 9:00am | DERA zip for the latest completed quarter (~6wk after quarter end); carries amendments/restatements *filed* that quarter, which the weekly frames job never re-reads |

## Constraints (preserve when editing the schedule)

- **SEC jobs never share an hour.** The 9 req/s rate limiter in
  `http_client.py` is per-process; concurrent launchd jobs (`edgar`, `ftd`,
  `ftd-full`, `fundamentals`, `fundamentals-bulk`, earnings-in-preopen)
  would double-dip SEC's per-IP cap. The monthly/quarterly slots stay
  distinct even on collision days (15th=Sunday: ftd 7am vs ftd-full 8am;
  20th=Saturday: fundamentals 6am vs fundamentals-bulk 9am).
- **`stocks`/`etfs` stay serialized** (same batch) and `stocks` stays daily —
  stockanalysis.com is an unofficial endpoint; don't hammer it.
- Missed runs self-heal via revision lookbacks (CFTC 10wk, Treasury/NY Fed 7d,
  FINRA/FTD reprobe, plus the monthly `--full` re-absorbs) — **except
  `edgar`**: a skipped day is a permanent hole; backfill with
  `uv run python main.py edgar --db data/edgar.db --date YYYY-MM-DD`.

## Operations

- **Change the schedule**: edit `deploy/launchd/install.py`, then
  `uv run python deploy/launchd/install.py` (regenerates + reloads plists).
  `--uninstall` removes every job; `--dry-run` writes plists without loading.
- **Health check**: `deploy/launchd/status.sh` — launchd exit codes, last log
  line per job, per-DB snapshot freshness.
- **Logs**: `logs/<job>.log` (gitignored), timestamped start/stored/FAILED lines.
- **Nightly push**: `daily_summary.py` sends an ntfy digest at 9:15pm — run
  counts, FAILED/STALE lines, non-zero exit codes, stale DBs vs expected
  cadence. Healthy = ✅ default priority; problems = ⚠️ high priority. No
  9:15pm ping at all ⇒ the machine (or login session) is down — the summary
  can't report its own absence. If `HEALTHCHECK_URL` is set (see
  `.env.example`), a successful run also pings an external dead-man's switch
  (e.g. healthchecks.io); configure that service to alarm when the ping is
  absent by a deadline, closing exactly this gap.
- **Backtest replay** (manual, unscheduled by design):
  `uv run python main.py backtest --db data/backtest.db` — copies FRED
  vintages + SP500 closes out of `data/fred.db` (read-only) and prints
  point-in-time hit rates for the FRED regime signals. See
  `docs/superpowers/specs/2026-07-07-backtesting-foundation-design.md`.
- **Restarts**: plists live in `~/Library/LaunchAgents` and survive reboots,
  but jobs only run once a login session exists (they need the Keychain and
  `.env`) — keep auto-login enabled on the always-on Mac mini. Runs missed
  while powered off are skipped, not made up.
