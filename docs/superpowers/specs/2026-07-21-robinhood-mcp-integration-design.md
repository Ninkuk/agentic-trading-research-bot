# Robinhood MCP integration — design

Date: 2026-07-21
Status: design approved, plan not yet written
Scope: skills-only batch. No new source package, no dispatcher, no DB, no
schema change, no launchd slot.

## Problem

Robinhood's MCP server has grown well beyond the account-state reads that
`account-positions` and `journal-sync` use. It now exposes option chains with
per-contract IV/greeks/open interest, Level 2 depth, per-lot tax lots, realized
P&L, a server-side scanner, server-side technical indicators, and 8 quarters of
estimate-vs-actual EPS.

The question is which of that is admissible under the repo's data-source
policy, and how it should reach `research-ticker` and `kill-thesis`.

## Audit result

Verified by loading 28 tool schemas and making live read-only probes. Schema
descriptions understate: `get_option_quotes` documents only "quotes" but
returns `implied_volatility`, `delta`, `gamma`, `theta`, `vega`, `rho`,
`open_interest` and `volume`.

**Genuinely new — no repo source covers it:**

- `get_equity_tax_lots` — per-lot cost basis, acquisition date, long/short-term.
  `portfolio.db` stores only a blended `average_buy_price`.
- `get_realized_pnl`, `get_pnl_trade_history` — realized P&L per closing trade.
- `get_earnings_results` — trailing 8 quarters of estimate vs actual EPS.
  `earnings_calendar` stores only a forward `eps_est` used for scheduling.
- `get_equity_price_book` — Level 2 depth.
- `get_index_quotes` — `NDX`, `RUT`, `DJX`, `XSP` have no other source in the
  repo. (VIX/VIX3M/VIX9D/VVIX are already covered EOD by `cboe_stats`, and
  `VIXCLS` by FRED — Robinhood adds only intraday freshness there.)

**Not new — already covered by an official source:**

- Option IV / greeks / OI / volume. `sources/screeners/cboe_options/` already
  ships `option_snapshots` (iv, full greeks, open_interest, volume,
  vol_oi_ratio), `underlying_daily.iv30`, and views `v_iv_rank`,
  `v_unusual_activity`, `v_latest_sentiment`. CBOE is an enumerated official
  source in CLAUDE.md. Catalog (24 symbols): AAPL AMD AMZN AVGO BABA BAC COIN
  DIS GOOGL IWM JPM META MSFT MSTR NFLX NVDA PLTR QQQ SMCI SPX SPY TSLA VIX XOM.

  **It writes `data/options.db`, not `data/cboe_options.db`** — the DB is named
  for the registry key (`options`), and the launchd jobs are `options-intraday`
  (hourly, 6:30am–1:30pm weekdays) and `options-close` (2:45pm). A grep for
  "cboe" in the schedule finds only `cboe-stats` and misses both. It is fully
  live: ~476MB, 124k option rows per run. Verify a DB's real path from
  `logs/<job>.log`, which prints the exact command, rather than inferring it
  from the package name.

**Rejected:**

- `get_financials` — returns 4 fields (revenue, gross profit, net income, net
  margin). `stocks.db` stores 311 data points per symbol; `sec_fundamentals.db`
  holds the audited primary. Strictly worse; banned.
- All write tools (`place_*_order`, `cancel_*`, scan/watchlist mutation) —
  excluded by the existing "never place an order" guardrail.

## Policy decision

The repo's policy is *official primary sources only, one vetted exception
(stockanalysis.com)*. Robinhood is a broker, not a primary source.

**The admissibility test is coverage, not existence:** Robinhood is admissible
only where no *already-integrated official source covers this ticker or field*.
It is refused wherever it duplicates one.

This is deliberately narrower than "no official source publishes this," which
was the original (incorrect) framing — CBOE already publishes option
microstructure, so that framing would have admitted Robinhood for data the repo
already had. The coverage test does not generalise to other aggregators.

Robinhood data is cited as a new source tier: **broker/market microstructure**,
below primary filings and distinct from stockanalysis.com.

## Design

### Shared reference: `.claude/skills/shared/options-read.md`

A neutral home owned by neither consumer, following the precedent of `tools/`
("code that is neither a source nor a dispatcher"). `research-ticker` and
`kill-thesis` both read it. Placing it under one skill's `references/` would
make the other reach across a sibling's private folder via an undocumented
relative path.

Both skills must state **when** to read it, or it will never be opened.

#### Source selection (checked in order)

1. **Ticker in the CBOE catalog AND `data/options.db` has usable history**
   → read `v_iv_rank` (`iv30`, `iv_rank`, `iv_percentile`, `n_days`) and
   `v_latest_sentiment` (put/call volume and OI ratios). Own-history percentile
   is the preferred baseline: it answers "is IV high *for this name*" without
   any realized-vol window choice.
2. **Otherwise** → Robinhood MCP, with the implied-vs-realized method below.

**Depth gate.** `v_iv_rank`'s own docstring warns it returns meaningful values
only once history accumulates. Check `n_days` before trusting `iv_percentile`:
require `n_days >= 60` to quote a percentile at all, and label it low-confidence
below `n_days >= 252` (roughly one year, the span needed before a percentile
covers a full seasonal cycle of the name's own vol). If the table is absent or
`n_days < 60`, fall through to path 2 and **say which path was used**.

The screener has run hourly since 2026-07-02, so `n_days` was **13** on
2026-07-21 and grows one per trading day — path 1 clears the 60-day gate around
mid-September 2026 and the 252-day confidence bar in mid-2027. Until then every
ticker takes path 2. The gate makes that transition automatic with no code
change; nothing needs switching on.

**Tenor mismatch — never mix the two paths.** `iv30` is a 30-day
constant-maturity figure; a path-2 ATM IV is read off one specific expiry. They
are different measurements and disagree materially. On AAPL 2026-07-21 CBOE
`iv30` was 29.6% while the 10-day earnings-straddling ATM IV was 37.5% — 8
points apart on the same name in the same minute, purely from tenor. Never
compare a path-1 number against a path-2 number, and never carry one forward as
though it were the other.

#### Procedure (path 2)

1. **Resolve the chain** — `get_option_chains`. No chain → stop, record
   "no listed options", and continue. Non-US `/quote/` listings and small caps
   have none; silence here must not read as "nothing worrying."
2. **Resolve the catalyst from the thesis** — not from the calendar. Earnings is
   one catalyst among many (FDA decisions, litigation rulings, contract awards,
   index inclusion). Pick the expiry that brackets *the thesis's own* catalyst.
   **If no listed expiry falls near it, abstain and mark the check
   NOT APPLICABLE.** Substituting the next earnings date for an unrelated
   catalyst measures the wrong event and can refute a correct timing claim.
3. **Honor BMO/AMC** — `earnings_calendar` stores `event_time` precisely because
   it matters. A BMO report on day D reprices during D's session; an AMC report
   on day D reprices at D+1's open. Anchoring on `event_date` alone picks the
   wrong expiry for every AMC name.
4. **Resolve "today" as a Phoenix date.** These are interactive sessions, not
   launchd jobs, but the invariant still applies: UTC midnight is 17:00 Phoenix,
   so a UTC-clocked evening session reads tomorrow's date and every
   days-to-expiry figure comes out one day short.
5. **Find ATM and quote both legs** — spot from `get_equity_quotes`, then
   `get_option_instruments` **always with `expiration_dates` AND `strike_price`**.
   Unfiltered, that endpoint returns the full ladder *per (chain, expiration,
   type)* — 88 contracts for one expiry, one side, across 24 expirations.
   Nearest-strike-to-spot is a slight approximation to the true 50-delta strike
   (the forward sits above spot); sub-1% at short tenors, footnote it when an
   ex-dividend date falls inside the window.
6. **Liquidity gate.** Thresholds must be scaled, not absolute:
   - spread gate — fail when `spread > max(10% of mark, 2 ticks)`. A flat
     percentage alone fails a $0.50 contract on a $0.05 tick at one tick, which
     is a maximally tight quote.
   - liquidity floor — fail when same-day `volume < 100` AND
     `open_interest < 25% of the median OI across that expiry's strikes`.
     Open interest accumulates over a contract's life, so a newly-listed weekly
     (exactly what an earnings-bracketing expiry often is) shows low OI
     regardless of tradability; same-day volume is the flow measure that does
     not have that defect.

   Failing the gate → mark UNRELIABLE; it may not move a verdict.

   **These four constants (10%, 2 ticks, 100, 25%) are starting values, not
   measured ones.** Per the repo's own history, thresholds set before real data
   existed have misfired repeatedly. They must get one calibration pass against
   real chains — across a liquid mega-cap, a mid-cap, and a thin small-cap —
   before any verdict is allowed to rest on them.

#### Reporting the move — corrected

`straddle / spot` is **not** an upper bound. It is the expected *absolute* move,
≈ `0.798 · σ√T` (Brenner–Subrahmanyam). Verified on AAPL 2026-07-21: predicted
4.955% vs observed 4.951%, a 0.08% miss.

The true 1-σ move is `σ√T` = **6.211%**, 1.254× larger, and
`P(|move| > 4.95%) = 42.5%`.

Report both, labelled:

- expected absolute move (mean) — `straddle / spot`
- 1-σ move — `σ√T`

**Never gate a verdict on the straddle figure being a ceiling.** Doing so
refutes a thesis needing a 6% move by citing a "±4.95% maximum" that is exceeded
in over four cases in ten.

#### The realized-vol baseline (path 2 only), and its limit

Close-to-close `stdev(log returns) · √252` over 60 and 20 trading days, from
`get_equity_historicals` (`interval=day`, `adjustment_type=all`).

Close-to-close is the correct estimator here **because earnings gap overnight**;
Parkinson and Garman-Klass use intraday ranges and are blind to exactly the gap
being calibrated. State this so it doesn't read as an oversight.

Print before interpreting — a table, then the reading, never the reverse. The
pattern already exists in `disclosure-hunt.md`: *"print it before any hit list."*

| metric | value |
|---|---|
| spot | |
| expected absolute move | |
| 1-σ move | |
| ATM IV | |
| RV60 | |
| RV20 | |
| IV > RV60? | YES/NO |
| IV > RV20? | YES/NO |

Write "elevated" only when both rows read YES. On disagreement, the
disagreement is the finding — do not average the windows, and do not select the
one that supports a prior.

**Documented limitation.** This comparison is weak, and weakest exactly when it
is most likely to be used. A forward IV spanning a scheduled event is compared
against trailing windows that may contain no such event, so it will mechanically
read "elevated" — that is the market correctly pricing a known calendar item,
not a finding. One 8% earnings day inside a 60-day window moves annualized
stdev by roughly 3.6 vol points on its own. Robinhood cannot fix this:
`get_option_historicals` returns price OHLC only, with no per-bar IV, so an
own-history IV percentile is unobtainable from that source. Path 1 is the real
answer; path 2 is a stopgap and must be labelled as one in the write-up.

### `kill-thesis`

**Conditional options check**, placed beside the statistical checks (step 4),
not the standing checks — it applies only when a chain exists *and* the thesis
makes a dated claim.

**Verdict rule — one-way valve.** Refutation is defined against the 1-σ move
`σ√T`, never against the straddle figure. Refute the timing condition only when
the move the thesis requires exceeds **2·σ√T** over the catalyst horizon — under
a lognormal that is roughly a 5% outcome, which is a real claim about
probability rather than a vague "the market disagrees." State the multiple and
the implied probability in the finding. Between 1σ and 2σ the market is merely
less optimistic than the thesis, which is not a refutation and must not be
written as one. Mark the condition FLAWED only above the 2σ line.

The refutation stops there — it may not spread to undated
conditions, because a thesis can be right about the destination and wrong about
the calendar. An implied move that matches or exceeds what the thesis requires
is **not evidence for anything**: options pricing reflects the market's current
uncertainty, not a verdict. Crediting it is the same error step 3 already
forbids — a search that returns support was a search for support. Self-check: if
you write "the options market agrees" without immediately following it with
"which is not evidence for the thesis," delete the sentence.

**Coverage disclosure.** When the check cannot run — no chain, illiquid, no
aligned expiry — say so in the verdict. The check only fires on liquid names, so
silently omitting it makes a thesis on an illiquid name look more thoroughly
vetted than it was.

**Tax lots** on the existing "before adding to a losing position" path: per-lot
basis and holding period, which a blended average hides. Carries the standard
secret-hygiene and Agentic-account-pin rules verbatim from the sibling skills.

### `research-ticker`

- **Phase 0** — `get_earnings_results` for 8 quarters of estimate vs actual.
  Read the *pattern*: chronic beats-by-a-penny is managed guidance, large misses
  are execution risk. Distinguish this trailing surprise series from
  `earnings_calendar`'s forward `eps_est`, which is a scheduling input and
  shares the name.
- **Phase 2** — a one-line non-optional pointer to `options-read.md`, with the
  finding (or "no listed options / illiquid") recorded even when nothing else
  flagged it. Mechanics stay in the reference file.
- **Phase 4** — false-precision check: a tight implied return on a high-IV name
  is arithmetic, not knowledge. Needs a numeric trigger and a rounding rule, not
  prose alone.
- **Output §4** — an implied-move line in the Valuation section.

### `journal-sync`

Reconciliation **read**: compare journaled fills against broker realized P&L for
the window. Read-only, reported, never auto-written — the dispatcher write
boundary is untouched.

Needs an explicit tolerance model or it will cry wolf and be ignored:

- *Expected* divergence — T+1 trade-vs-settlement drift; drip/recurring fills
  that land in `v_freelance` by design; `scorer.realized_return` is a single-lot
  FIFO-shaped model derived from journaled fill prices, while the broker
  computes per actual closed tax lot under a possibly different lot-selection
  method.
- *Unexplained* divergence — investigate.

**Gradeability tag.** Stamp a short tag in the existing `decisions.note`
free-text field (already used for pass reasons) when the options check fired at
decision time — e.g. `iv_elevated_at_entry`. No schema change, no new package.
Without it this check can never be graded against `v_decision_outcomes`, which
is what `scorer` exists for.

### `account-positions`

One line: tax lots are available live and are **deliberately not persisted**.
Protects the skill's identity as the dispatcher-persistence path.

### Guardrails added to every touched skill

- **Options data informs the equity thesis only.** It answers "is the market
  pricing in this catalyst," never "what should I buy." If asked directly —
  "should I buy the calls?" — reply with one sentence: this skill does not size
  or recommend options positions; that decision and its risk are the user's
  alone. Then stop. Do not follow with a strike or expiry "as information" —
  that is the same violation wearing a hedge. A bare prohibition negotiates
  away under a direct request; a scripted reply does not.
- **`get_financials` is banned** in favour of `sec_fundamentals.db`. Framed as
  **provenance, not freshness**: SEC filings are the audited primary source for
  financials specifically. This does not reverse Phase 0's live-over-stale
  preference for price and statistics data.
- **ATR comes from `advisor`**, which computes it from stockanalysis-derived
  data for its `STOP_ATR_MULTIPLE` and `cap_shares` math. Do not call
  Robinhood's indicator endpoint and create a second stop distance for the same
  name on the same evening.
- **New source tier** — broker/market microstructure — added to the existing
  citation ladder.
- Secret hygiene and the Agentic-account pin restated in every new
  account-scoped section rather than assumed inherited.

## Non-goals

- No order placement, no position sizing, no options-trade recommendation.
- No new source package, dispatcher, DB, schema change, or launchd slot.
- Robinhood's scanner, watchlists, `get_equity_price_book`, and index quotes are
  audited but not integrated in this batch.
- `get_financials` is not used anywhere.

## Open risks

1. **The asymmetric-check ratchet.** `kill-thesis` accumulates checks that can
   only subtract — "never credit an uncertain condition," the statistical
   checks, and now this one. Each is defensible alone, but their sum makes SOUND
   monotonically harder to reach regardless of thesis quality, and nothing adds
   a counterweight. The skill already accepts an inaction bias deliberately; the
   risk is that it compounds silently. Flagged, not resolved — worth a cap or a
   reachability requirement before the next one-directional check is added.
2. **Path 1 is gated off by history depth, not by anything broken.** The
   screener runs hourly and `data/options.db` is healthy; `n_days` was 13 on
   2026-07-21 against a 60-day gate. Every ticker therefore takes path 2 —
   the labelled stopgap — until roughly mid-September 2026. Nothing to fix,
   but the batch ships in its weaker configuration and should be re-read once
   the gate clears.
3. **No test coverage.** This logic lives in skill prose, consistent with how
   `research-ticker` and `kill-thesis` already work, so it is not a new failure
   mode — but the date-boundary and lot-accounting risks above have no
   regression net.
4. **`composite` and `advisor` do not read `data/options.db` at all.**
   Pre-existing gap, noted during review, unaddressed here.
