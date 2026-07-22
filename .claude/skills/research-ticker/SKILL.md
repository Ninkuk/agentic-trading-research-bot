---
name: research-ticker
description: Research a stock end-to-end — business, moat, thesis, reverse-DCF valuation, adversarial review — and write a thesis to research/<TICKER>-<DATE>.md. Use when the user asks to research/analyse/dig into a ticker, wants a thesis on a name, or asks whether a composite-flagged ticker is actually worth owning, or whether the options market is already pricing in the move a thesis needs.
---

# research-ticker

Qualitative research to complement the numeric pipeline. `composite` can tell
you a name scores +6 across nine signals. It cannot tell you what the company
sells, why customers come back, or what stops a competitor from copying it.
That is this skill's job.

**Decision support only.** Never place an order, never recommend a size.
Read `data/*.db` **read-only**; live state enters the system only through the
`portfolio` and `journal` dispatchers.

Entry is **any ticker**. A `composite` flag is one path in, not a requirement —
the best ideas often come from noticing a product you use, not from a screen.

## Phase 0 — Triage, and the fast kill

The goal of this phase is to **kick the stock out quickly**. Most research
should end here.

**Live numbers come from the wire, not the warehouse.** `data/*.db` holds
whatever the last scheduled run captured, which may be days stale. A research
session wants today's figures.

Read **`docs/stockanalysis_data_json_catalog.md`** first — it is the route map,
the decoder, and the field gotchas. Never scrape the rendered HTML page. One
call gets almost everything this skill needs:

```bash
uv run python -m sources.screeners.stock_analysis_screener.probe /stocks/AAPL/statistics/
```

**Resolve the route first — it is not always `/stocks/`.** US equities live
under `/stocks/{T}/`; every non-US listing (a large share of the best
compounders) lives under `/quote/{exchange}/{T}/` and needs the exchange
segment on *every* subsequent call — statistics, financials, transcripts alike.
Look it up before you probe, and carry the prefix through:

```bash
uv run python -m sources.screeners.stock_analysis_screener.probe '/symbol-lookup/?q=CSU'
# results[0].s -> '@tsx/CSU'  =>  use /quote/tsx/CSU/statistics/ , /quote/tsx/CSU/financials/ , ...
```

For a `/quote/` name the point-in-time DBs below are **empty** — `stocks.db`,
`sec_fundamentals.db`, and `composite.db` are US-universe only, and it files on
its home regulator (SEDAR+, etc.), not SEC EDGAR. The live probe is then your
*only* structured source; say so, drop the DB cross-checks, and lean harder on
the latest call (Phase 2).

Then read `data/*.db` read-only, as the **point-in-time record** — what was
known when, not what is true now:

- `data/sec_fundamentals.db` — `v_screener` for `net_margin`, `roe`,
  `debt_to_equity`, revenue and income history; `companies` for ticker→CIK.
- `data/stocks.db` — the last captured price and market-cap metrics.
- `data/earnings.db` — next report date (do not research into an earnings print
  and pretend the timing is irrelevant).
- **Robinhood MCP `get_earnings_results`** — the trailing 8 quarters of
  estimate vs actual EPS. Read the **pattern**, not any single quarter: chronic
  beats-by-a-hair indicate managed guidance; large misses indicate execution
  risk. The **actuals** are cross-checkable against an official source —
  `data/sec_fundamentals.db` `v_screener.eps_diluted` — so cross-check them and
  say if they disagree; only the **estimate** side is genuinely new here.
  **The estimate is also a different thing from the forward `eps_est`** carried
  by `data/earnings.db`'s `v_upcoming_earnings` view, which is a scheduling
  input only — the two happen to share a name but neither substitutes for the
  other. (There is no `earnings_calendar` table: that is the source package's
  name; its dispatcher is `earnings` and its DB is `data/earnings.db`.)
- `data/composite.db` — if the name was flagged, read `ticker_scores` and
  `signal_values` so you know what the machine already thinks and why.

Where the live probe and the DB disagree, the probe wins for *today's* numbers
and the DB tells you *when the machine last looked*. Say which you used.

**Print the operating-leverage trajectory before you triage.** Put revenue and
operating income side by side for every year available and state which direction
operating leverage runs — positive, flat, or negative. A company whose revenue
has multiplied while operating income went sideways or backwards is a different
business from the one its cash flow describes, and the income statement is where
stock compensation is actually charged. State the direction explicitly; "it is
loss-making" is a level, not a direction, and does not substitute for it.

Kill it now if:

- **Persistently loss-making.** Not disqualifying, but it is a genuinely harder
  analysis and a bad place to start. Say so, and ask the user whether to go on.
- **Heavy leverage** relative to its cash generation.

Where the business rests on domain science — biotech efficacy, semiconductor
process physics, a novel chemistry — do not bluff it and do not quit over it.
Say what you cannot evaluate, bound it if you can, and mark it UNKNOWN. A moat
you cannot assess is an unassessed moat, not an absent one; write that down and
let Phase 3 count it among the load-bearing conditions.

## Phase 1 — What is the business?

From first principles. **Do not name SWOT, Porter's Five Forces, or any
framework.** A filled-in template substitutes for thinking: "eBay has a network
effect" ticks the box and gets the answer wrong.

Answer three questions, in this order:

1. **How does it create value?** What does the customer actually get, and why
   do they come here rather than anywhere else? What preferences are being
   satisfied — price, speed, convenience, trust, status? When a customer gets
   more than they pay for, that surplus is usually a good sign.
2. **How does it capture value?** Not "advertising" — *how, specifically*.
   Amazon does not take "a commission": it takes a different commission per
   category, plus logistics fees, plus advertising fees. That is three
   businesses. Unpack until the mechanism is concrete.
3. **How does it protect value?** What stops a competitor doing this tomorrow?
   Ask it as a mechanism, never as a label. **If there is no good answer, that
   silence is itself the answer** — write it down.

## Phase 2 — The frame problem, and pulling threads

You cannot know in advance which facts are relevant. Nobody hands you the list.

- Enumerate the candidate relevant facts you have collected. Say which look
  load-bearing and which look decorative.
- Pick the threads worth pulling: the things that set off an alarm. *"Credit
  card issuance is accelerating into a population with no credit history"* is
  a thread. Go investigate it — check delinquencies, provisioning, underwriting
  commentary, the competitive environment.
- **Record the dead ends.** A thread that led nowhere is evidence the work was
  done, not clutter to delete. Most threads lead nowhere. That is the job
  going well.

Use `references/disclosure-hunt.md` for *where to look*. Its three questions,
in order: does the information exist; can it be triangulated or found
elsewhere; and if not, does its absence kill the thesis?

**One thread is not optional** — use `.claude/skills/shared/options-read.md`
and record its finding (or "no listed options / illiquid / path-2 stopgap")
even when nothing else in Phase 2 flagged it.

**Read the single most recent call before you write the business up.** The
latest earnings call / AGM transcript (`.../transcripts/` → newest
`detailSlug`) is one fetch and the highest-value current-state source there is:
this quarter's organic-vs-total growth split, capital deployed, guidance, and —
most valuable — management's own framing of the exact risk the market is pricing
*right now*. The drawdown or pop that made the name worth a look is usually
explained there. This is a different job from the corpus *search* below (what
management said over the years); do both, and do this one first. **Disclosure
cadence is itself a signal** — a call resumed after years of silence, or a
letter that stopped, is material. Read the change; don't just count the rows.

**The call is not the print.** The quarterly shareholder letter / earnings
press release (the 8-K exhibit) is a separate document from the call
transcript, and it carries what the call omits: the metrics table — every
user/engagement metric, not just the one management headlined — the stated
multi-year targets, and the lead metric's history. Fetch it alongside the
transcript; a run sourced only from the call inherits management's on-call
emphasis.

**Then reconcile it against what happened since.** That call is up to a quarter
stale, and on a fast-moving competitive or regulatory thesis the facts that move
the stock happen *between* calls — do not treat the latest transcript as current
state. Sweep for events dated after it: the ticker's `news` feed, 8-Ks, and
(when the thesis turns on an external race) a dated web search for the *rival*,
not the company. A post-call event that contradicts management's framing is the
thread; silence since the call is itself a reading.

When a thread turns on what management has said over the years, search the
transcript corpus rather than reading it — see *Searching the transcript corpus*
there. Print its coverage before you print a hit, and remember the corpus can
show you that something **was** said, never that it never was.

## Phase 3 — The thesis

Write it in plain language. **It does not need to be clever.** "This is a good
business, it is defensible, the price is fair, and management is unlikely to
destroy the cash flow" is a complete thesis. The elaborate, specific,
impressive-sounding thesis — a bottleneck migrating from GPUs to memory,
therefore margins of 65% — is *more likely to be wrong*, because every added
specific is another thing that has to go right.

Then, explicitly:

- **Enumerate the load-bearing conditions and count them.** Print the count.
- **Name the falsifiers.** What observable evidence would make you sell? A
  thesis with no falsifier is a position, not an argument.
- **Mark every UNKNOWN.** Never fill a hole with a plausible number.

## Phase 4 — What return is already priced in?

Do not guess the "right" multiple. A multiple is shorthand for a DCF. Instead,
hold the assumptions fixed and solve for the return the market already implies.

**Pull the inputs live** from `page_data("/stocks/<TICKER>/statistics/")` — its
`valuation`, `cashFlow`, and `balanceSheet` blocks carry market cap, enterprise
value, `fcf`, `capex`, and `debt` in one request. Read each row's **`hover`**
field, not `value`: `hover` is the exact figure (`'4,644,435,714,320'`), while
`value` is a rounded display string (`'4.64T'`). The market-cap row's id is
`marketcap` — lowercased, unlike the `marketCap` used everywhere else.

**`fcf` on this route is a levered (equity) flow, so pair it with market cap.**
It is computed as `ncfo + capex`, and `ncfo` is post-interest under US GAAP —
the debt has already been served. Pass **market cap** as `--market-cap` and
leave `--net-debt` at zero. Enterprise value sits on the same page and is the
wrong denominator for this flow: it re-counts the debt you just paid.

Unlevered (firm) cash flow is what pairs with enterprise value; only then pass
`--net-debt`. The solver never guesses which flow it was handed, so nothing
downstream will catch a mismatch — it just returns a confident wrong number.

`fcf` is also **not** stockanalysis's own `leveredFCF`. On AAPL TTM all three
disagree: `fcf` 129.17B, `leveredFCF` 97.69B, `unleveredFCF` 119.20B. If you
take a flow from `financials/cash-flow-statement/` instead, pair it by the name
it actually carries, and mind that route's own traps.

**Minority interests break the FCF↔market-cap pairing too.** If the company
consolidates subsidiaries it does not wholly own — a `minorityInterest` line on
`/financials/`, or a known holdco (CSU consolidates Topicus/Lumine; Brookfield,
many Japanese/Korean holdcos) — consolidated `fcf` includes cash belonging to
the minority holders while market cap prices only the parent's share. Paired,
the yield reads too high. Haircut FCF to the owner share before you solve. Mind
the trap: the `minorityInterest` *net-income* line **understates** the cash
claim whenever heavy acquired-intangible amortization depresses subsidiary GAAP
income (exactly the holdco case) — reach for the cash-flow distributions to
minorities, or the company's own owner-earnings metric, not the NCI income line.
On CSU, consolidated FCF is ~15× market cap but owner FCF is ~19× — the
difference between "not expensive" and "fairly priced," and the whole reason a
holdco can look cheaper than it is.

```bash
# Verizon: levered FCF 20.27B against MARKET CAP 176.4B — not EV of 368.4B.
uv run python -m tools.valuation.reverse_dcf \
  --market-cap 176400000000 --base-fcf 20270000000 \
  --growth 0.02 0.02 0.02 --terminal-growth 0.015
# implied_discount_rate: 0.1332  (13.32% per year)
```

Hand that same flow to enterprise value and it prints **7.16%** — a 616bp error
that turns an interesting name into a pass. The distortion scales with net debt,
which is why you must never sanity-check this pairing on a debt-free company: on
AAPL, whose net *cash* is 1.3% of market cap, the identical mistake moves the
answer by 4bps (4.36% → 4.40%) and hides completely.

**If margins are mid-expansion, one FCF growth rate hides the upside.** A flat
`--growth` path can't express a business whose operating margin is well below a
credible steady state and still climbing (a post-profitability platform dialing
back subsidies — Uber, and its kind). The value is in the margin lever the flat
rate fixes. Model bookings × margin — grow the top line and the margin
separately — or front-load `--growth` above the revenue rate for the expansion
years and fade it. Say which you did. A single-rate run understates such a name;
don't quote it as the ceiling.

**An "asset-light" claim is a balance-sheet question, not a vibe.** Before you
trust a low-capex base — management's "capital-light" framing, a sell-side
note's, or your own read of tiny trailing capex — pull the 10-K
commitments-and-contingencies footnote (usually a few pages after the debt
note). A multi-year purchase or capacity obligation there — vehicle buys,
minimum-volume take-or-pay, cloud/chip reservations — is future capex the
trailing capex doesn't show yet, and a headwind to the base FCF you feed
`reverse_dcf`. A business is only as asset-light as its commitments let it be.

**The terminal-growth input must survive the disclosed terminal risk.** Sweep
the 10-K Item 1A risk factors once for the dominant structural risk — the one
that bears on whether cash flows still grow in year 10 and beyond — name it in
the write-up, and say why the chosen `--terminal-growth` survives it, or cut
the rate. A terminal rate that never met the company's own disclosed endgame
risk is arithmetic, not knowledge.

Read the output honestly:

- A **low** implied return on **optimistic** assumptions is a bad bet.
- A **high** implied return on **conservative** assumptions is interesting.
- `no solution` (exit 1) means the price implies a return above 100%/yr. That
  is information, not an error.
- `refused` (exit 2) means the input was a category error — usually a
  loss-making base FCF. Go back to Phase 0.

**Check the precision of the implied return against the vol.** When the path-2
ATM IV (or, on path 1, `iv30` — the tenor rule forbids treating one as the
other, but either crossing the line is enough of a warning) exceeds 50%, quote
the implied discount rate to the nearest whole percent and
say the range is wide; a figure like "13.32%" on a name the options market
prices at 60% vol is arithmetic, not knowledge. Never widen a conclusion's
confidence to match a narrow-looking number.

State the assumptions in the write-up. The number is worthless without them.
If you also quote a forward multiple, do not look out more than ~3 years —
beyond that it is not evidence.

## Phase 5 — Try to destroy it

Invoke the **kill-thesis** skill on what you just wrote. Do not skip this
because the thesis is yours; skip it and the whole document is unearned.

Record the verdict — SOUND / FLAWED / UNPROVEN — in the write-up, along with
the attack that came closest to landing.

## Output

Write `research/<TICKER>-<YYYY-MM-DD>.md` with these sections, then commit it:

1. **Verdict and thesis** — the conclusion first, in two sentences, with the
   kill-thesis verdict and the load-bearing condition count.
2. **Business** — created / captured / protected.
3. **Threads pulled** — including the dead ends, and what they ruled out.
4. **Valuation** — the implied return, and every assumption behind it. Add
   the options-implied move where available: name the path used (path 1 —
   CBOE `iv30` percentile from `data/options.db`; path 2 — the Robinhood
   stopgap) and the DTE, or state explicitly "no listed options."
5. **Falsifiers** — what would make you sell.
6. **UNKNOWNs** — what could not be found, where it would come from, and
   whether its absence kills the thesis.
7. **Sources** — every claim, tiered: primary filings; `stockanalysis.com`
   (this repo's one vetted exception); broker/market microstructure (see the
   data-source policy in `CLAUDE.md` — real-time market state, not a
   researched disclosure, admissible only where no already-integrated
   official source covers this ticker or field); low-confidence colour.

## Log the verdict (mandatory final step)

After writing research/<TICKER>-<DATE>.md and appending verdicts.log, record
the buy/pass call in the graded ledger — this is what v_research_filter
grades (the skill analog of v_human_filter). Build one JSON doc in the
scratchpad:

    {"as_of": "<UTC now isoformat>",
     "fills": [],
     "verdicts": [{"symbol": "<TICKER>",
                   "verdict": "buy" | "pass",
                   "verdict_date": "<Phoenix calendar date of the run, YYYY-MM-DD>",
                   "doc": "<TICKER>-<DATE>.md",
                   "note": "<one line: the load-bearing reason>"}]}

then ingest:

    uv run python main.py journal --db data/scorer.db --input <scratchpad>/verdict.json

Rules: never SQL against scorer.db (dispatcher-only write path, same as
journal-sync). verdict_date is a BARE Phoenix date, not a timestamp.
Re-running the same ticker the same day is a counted duplicate — safe.
Unlike passes, a verdict needs no composite flag to answer; unflagged
research logs the same way. This step is the skill's own record, so it does
not require user dictation.

## Guardrails

- **Never place an order.** Never recommend a position size — that is
  `advisor`'s job, from ATR and book heat, not from prose.
- **Never write to `data/*.db`.**
- **Every factual claim carries a source.** Unsourced becomes an explicit
  UNKNOWN, never a confident sentence.
- **Official primary sources first.** `stockanalysis.com` is the single vetted
  exception and does not generalise to other aggregators. Reddit, YouTube, and
  expert-network material are labelled low-confidence, always.
- **Broker/market microstructure is its own source tier**, below primary
  filings and distinct from `stockanalysis.com` — see the data-source policy
  in `CLAUDE.md` for what it covers. It is real-time account and market
  state, not a researched disclosure — label it as this tier, not as primary
  or as the `stockanalysis.com` exception. It is admissible only where no
  already-integrated official source covers this ticker or field, and refused
  wherever it duplicates one.
- **It is a complete and respectable outcome to say "I don't know how I feel
  about this one."** There are other companies. Go back to the list.
- **Options data informs the equity thesis only.** It answers "is the market
  pricing in this catalyst," never "what should I buy." If asked directly —
  "should I buy the calls?" — reply with one sentence: this skill does not
  size or recommend options positions; that decision and its risk are the
  user's alone. Then stop. Do not follow with a strike or expiry "as
  information" — that is the same violation wearing a hedge.
- **`get_financials` is banned** — use `data/sec_fundamentals.db` or live
  EDGAR. This is a **provenance** rule, not a freshness rule: SEC filings are
  the audited primary source for financials specifically, and this does not
  reverse Phase 0's live-over-stale preference for price and statistics data.
- **ATR comes from `advisor`**, which derives it from stockanalysis-derived
  data for its stop and `cap_shares` math — do not call Robinhood's
  technical-indicator endpoint and create a second, conflicting stop distance
  for the same name.
