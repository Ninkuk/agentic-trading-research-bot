---
name: research-ticker
description: Research a stock end-to-end — business, moat, thesis, reverse-DCF valuation, adversarial review — and write a thesis to research/<TICKER>-<DATE>.md. Use when the user asks to research/analyse/dig into a ticker, wants a thesis on a name, or asks whether a composite-flagged ticker is actually worth owning.
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

Then read `data/*.db` read-only, as the **point-in-time record** — what was
known when, not what is true now:

- `data/sec_fundamentals.db` — `v_screener` for `net_margin`, `roe`,
  `debt_to_equity`, revenue and income history; `companies` for ticker→CIK.
- `data/stocks.db` — the last captured price and market-cap metrics.
- `data/earnings.db` — next report date (do not research into an earnings print
  and pretend the timing is irrelevant).
- `data/composite.db` — if the name was flagged, read `ticker_scores` and
  `signal_values` so you know what the machine already thinks and why.

Where the live probe and the DB disagree, the probe wins for *today's* numbers
and the DB tells you *when the machine last looked*. Say which you used.

Kill it now if:

- **Persistently loss-making.** Not disqualifying, but it is a genuinely harder
  analysis and a bad place to start. Say so, and ask the user whether to go on.
- **Heavy leverage** relative to its cash generation.

**STOP CLAUSE — this one is not optional.** If the business rests on domain
science you have not established — biotech efficacy, semiconductor process
physics, a novel chemistry — **stop and say so**. Do not proceed and do not
bluff. The right next step is to go learn the domain, not to write a thesis
whose foundations are decorative. Tell the user plainly:

> I can't research this responsibly without understanding <domain> first.
> Everything downstream would be confidence without competence.

Then offer to research the domain instead, or a different name.

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
`valuation`, `cashFlow`, and `balanceSheet` blocks carry `marketCap`,
`enterpriseValue`, `fcf`, `capex`, and `debt` in one request. Read each row's
**`hover`** field, not `value`: `hover` is the exact figure
(`'4,644,435,714,320'`), while `value` is a rounded display string (`'4.64T'`).

Pair the flow to the value or the answer is quietly wrong. `enterpriseValue` is
given directly, so you rarely need the `--net-debt` bridge — pass EV as
`--market-cap` and leave `--net-debt` at zero. If you instead take
`leveredFCF`/`unleveredFCF` from the `financials/cash-flow-statement/` route,
mind that route's own traps, which the catalog documents.

Mixing a levered flow with enterprise value (or the reverse) is the classic
silent DCF error, which is why the solver never guesses which flow it was
handed. On AAPL the two pairings differ by ~57bps.

```bash
uv run python -m tools.valuation.reverse_dcf \
  --market-cap <mkt cap> --base-fcf <trailing FCF> \
  --growth 0.08 0.06 0.04 --terminal-growth 0.025
```

Levered (equity) free cash flow pairs with market cap. Unlevered (firm) cash
flow pairs with enterprise value — pass `--net-debt`. Mixing them is the
classic silent DCF error.

Read the output honestly:

- A **low** implied return on **optimistic** assumptions is a bad bet.
- A **high** implied return on **conservative** assumptions is interesting.
- `no solution` (exit 1) means the price implies a return above 100%/yr. That
  is information, not an error.
- `refused` (exit 2) means the input was a category error — usually a
  loss-making base FCF. Go back to Phase 0.

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
4. **Valuation** — the implied return, and every assumption behind it.
5. **Falsifiers** — what would make you sell.
6. **UNKNOWNs** — what could not be found, where it would come from, and
   whether its absence kills the thesis.
7. **Sources** — every claim, tiered: primary filings; `stockanalysis.com`
   (this repo's one vetted exception); low-confidence colour.

## Guardrails

- **Never place an order.** Never recommend a position size — that is
  `advisor`'s job, from ATR and book heat, not from prose.
- **Never write to `data/*.db`.**
- **Every factual claim carries a source.** Unsourced becomes an explicit
  UNKNOWN, never a confident sentence.
- **Official primary sources first.** `stockanalysis.com` is the single vetted
  exception and does not generalise to other aggregators. Reddit, YouTube, and
  expert-network material are labelled low-confidence, always.
- **It is a complete and respectable outcome to say "I don't know how I feel
  about this one."** There are other companies. Go back to the list.
