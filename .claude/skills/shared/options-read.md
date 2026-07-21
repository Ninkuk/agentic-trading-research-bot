# Reading an option chain

This answers **"what move is the market pricing in,"** never **"what should I
buy."** It turns quotes, IV, and history into one printed table so a thesis can
be checked against it — nothing here sizes a position or recommends a trade.

## 1. Source selection

Two paths, checked in order. Which one applies is a fact about the ticker and
the DB's history, not a judgment call.

1. **Ticker in the CBOE catalog AND `data/options.db` has usable history** →
   read `v_iv_rank` (`iv30`, `iv_rank`, `iv_percentile`, `n_days`) and
   `v_latest_sentiment` (put/call volume and OI ratios). Own-history
   percentile is the preferred baseline — it answers "is IV high *for this
   name*" without picking a realized-vol window at all.
2. **Otherwise** → Robinhood MCP, with the implied-vs-realized method below.

The 24-symbol CBOE catalog: AAPL AMD AMZN AVGO BABA BAC COIN DIS GOOGL IWM JPM
META MSFT MSTR NFLX NVDA PLTR QQQ SMCI SPX SPY TSLA VIX XOM. Anything else is
path 2 unconditionally — there is no history to check.

**The DB is `data/options.db`, not `data/cboe_options.db`.** It is named for
the registry key (`options`), not the source package (`cboe_options`); a grep
for "cboe" in the schedule finds the wrong jobs and misses it. Confirm a
screener's real DB path from its own registration or its log line, never from
the package name.

**Depth gate.** `v_iv_rank`'s own docstring warns it is meaningless until
history accumulates: require `n_days >= 60` before quoting a percentile at
all, and label it low-confidence below `n_days >= 252` (roughly one year — the
span needed to cover a full seasonal cycle of the name's own vol). If the
table is absent or `n_days < 60`, fall through to path 2 and **say which path
was used** in the write-up.

**As of 2026-07-21, `n_days` was 13 against the 60-day gate.** The screener
has run hourly since 2026-07-02 and gains one day per trading day, so path 1
is unreachable for every ticker in the catalog — every read, on every symbol,
takes path 2 — until roughly mid-September 2026, and the 252-day confidence
bar not until mid-2027. This is not a bug to route around; it is the correct
behavior of a depth gate on a young table. Check `n_days` yourself before
trusting any path-1 percentile — do not assume the gate has cleared just
because time has passed since this was written.

## 2. The tenor warning

`iv30` is a **30-day constant-maturity** figure, built by CBOE to represent a
fixed 30-day horizon regardless of which contracts actually trade. A path-2
ATM IV is read off **one specific expiry** — whatever date the thesis's
catalyst falls in. These are different measurements of different things, and
they disagree materially even on the same name in the same minute.

On AAPL, 2026-07-21: CBOE `iv30` was **29.61%**, while the 10-calendar-day,
earnings-straddling ATM IV was **37.5211%** — 8 points apart, purely from
tenor, nothing else moving.

**Never compare a path-1 number against a path-2 number, and never carry one
forward as though it were the other.** They are not the same measurement, and
a percentile computed from one has no meaning applied to the other.

## 3. Path 2 procedure

1. **Resolve the chain** — `get_option_chains`. No chain → stop, record "no
   listed options," and continue with the rest of the thesis. Non-US
   `/quote/` listings and small caps routinely have none; silence here must
   never read as "nothing worrying" — it reads as "unchecked."
2. **Resolve the catalyst from the thesis, not from the calendar.** Earnings
   is one catalyst among many — FDA decisions, litigation rulings, contract
   awards, index inclusion. Pick the expiry that brackets *the thesis's own*
   catalyst. **If no listed expiry falls near it, abstain and mark the check
   NOT APPLICABLE.** Substituting the next earnings date for an unrelated
   catalyst measures the wrong event, and can "refute" a correct timing claim
   by testing something the thesis never asserted.
3. **Honor before-open vs after-close.** `earnings.db` stores `event_time` as
   the literal strings **`before open`** / **`after close`** — not am/pm —
   precisely because it changes which session absorbs the move. A BMO report
   on day D reprices during D's own session; an AMC report on day D reprices
   at D+1's open. Anchoring on `event_date` alone picks the wrong expiry for
   every AMC name.
4. **Resolve "today" as a Phoenix date.** These are interactive sessions, not
   launchd jobs, but the invariant is the same one that governs the rest of
   this repo: UTC midnight is 17:00 Phoenix, so a UTC-clocked evening session
   reads tomorrow's date and every days-to-expiry figure comes out one day
   short.
5. **Find ATM and quote both legs.** Spot from `get_equity_quotes`, then
   `get_option_instruments` **always with both `expiration_dates` AND
   `strike_price`**. Unfiltered, that endpoint returns the full ladder per
   (chain, expiration, type) — 88 contracts for one expiry, one side, across
   24 expirations. Nearest-strike-to-spot is a slight approximation to the
   true 50-delta strike (the forward sits above spot); sub-1% at short
   tenors, but footnote it when an ex-dividend date falls inside the window.
6. **Apply the scaled liquidity gate** — see the four constants below.
   Failing it → mark UNRELIABLE; it may not move a verdict.

## 4. The command

```bash
uv run python -m tools.options.implied_move \
  --call-mark <mark> --put-mark <mark> --spot <spot> \
  --iv <atm_iv_decimal> --dte <calendar_days> \
  [--closes <closes.json>] [--required-move <decimal>]
```

**Print this table before writing any interpretation. Do not paraphrase its
numbers; quote them.** A paraphrase is where "expected move" quietly becomes
"maximum move" — the exact error this file exists to prevent.

Real run, AAPL 2026-07-21 (spot 327.70, ATM call mark 8.425, put mark 7.800,
ATM IV 0.375211, 10 calendar days to expiry, thesis requiring a 30% move):

```
$ uv run python -m tools.options.implied_move --call-mark 8.425 --put-mark 7.800 \
    --spot 327.70 --iv 0.375211 --dte 10 --required-move 0.30

spot                                          327.70
dte (calendar days)                           10
ATM IV                                        37.52%
expected absolute move (MEAN, not a ceiling)  4.95%
1-sigma move                                  6.21%
thesis requires                               30.00%
that is                                       4.83 sigma
P(|move| >= required)                         0.000136%
refutes timing claim (> 2 sigma)?             YES
```

The CLI's contract: **exit 0 means it computed and printed the table above;
exit 2 means it refused the input** (bad spot, negative mark, malformed
`--closes` file, non-finite number) and printed nothing but a `refused:`
line to stderr. There is no partial output on a refusal — never carry forward
a half-printed table.

## 5. How to read it

**`straddle / spot` — the "expected absolute move" row — is a MEAN, not a
ceiling.** It approximates `0.798 · σ√T` (Brenner–Subrahmanyam) and sits
roughly 20% *below* the true 1-sigma move (`σ√T`). On the AAPL fixture above,
4.95% versus a true 1-sigma of 6.21%. A move at least that large happens
**roughly 42% of the time** — under two coin flips, not a tail event.

**Never treat the straddle figure as a maximum.** An earlier version of this
design did exactly that, and it would have produced false verdicts: citing a
"±4.95% maximum" to refute a thesis needing a 6% move is wrong in over four
cases out of ten, because 4.95% was never a bound in the first place. Gate any
verdict on the **1-sigma move**, never on the straddle mean.

When realized vol is available (via `--closes`), build the comparison table
before interpreting it, in this shape:

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

**Write "elevated" only when both `IV > RV60?` and `IV > RV20?` read YES.** On
disagreement between the two windows, the disagreement *is* the finding —
report it as such. Do not average the two windows into one number, and do not
pick whichever one supports a prior; either move silently discards the
information that the windows disagree.

## 6. The stopgap label

Path 2 is weakest exactly when it is most used, and that is a structural
property, not a fixable bug. A forward IV that spans a scheduled event (an
earnings date, most often) is being compared against trailing realized-vol
windows that may contain no such event at all — so the comparison will
mechanically read "elevated," and that reading is just the market correctly
pricing a known calendar item, not a discovery about this stock. One 8%
earnings-day return sitting inside a 60-day window moves annualized stdev by
roughly 3.6 vol points on its own.

Robinhood cannot close this gap from the inside: `get_option_historicals`
returns price OHLC only, with no per-bar IV, so an own-history IV percentile
is unobtainable from that source — that is exactly what path 1's `v_iv_rank`
provides and path 2 cannot. Path 1 is the real answer; path 2 is a stopgap.
**Say in the write-up which path was used**, every time — a reader cannot
otherwise tell whether "IV looks elevated" survived a full-history percentile
check or just a two-window trailing comparison during the one window most
likely to fool it.

## 7. The four uncalibrated constants

The liquidity gate (procedure step 6, above) runs on four numbers, and none
of them have been measured against a real chain yet:

- **spread gate** — fail when `spread > max(10% of mark, 2 ticks)`
- **liquidity floor** — fail when same-day `volume < 100` AND
  `open_interest < 25% of the median OI across that expiry's strikes`

10%, 2 ticks, 100, and 25% are **starting values, not measured ones.** This
repo's own history is that thresholds set before real data existed have
misfired repeatedly (composite's `v_flagged` gate needed recalibrating from
4/3 to 3/2 after shipping silent). These four need one calibration pass
against real chains — a liquid mega-cap, a mid-cap, and a thin small-cap —
before any verdict is allowed to lean on them. Until that pass runs, treat a
gate failure as informative but treat a gate *pass* as unverified, not as
confirmation the thresholds are right.
