---
name: kill-thesis
description: Adversarially attack an investment thesis and return a SOUND / FLAWED / UNPROVEN verdict. Use when the user wants a thesis stress-tested, asks "what am I missing", shares a thesis from Substack/Twitter, or after research-ticker drafts one. Also use before adding to a losing position.
---

# kill-thesis

Come at this from the position that you want to **destroy the investment**.
A thesis that survives an honest attempt to kill it is worth something. A
thesis that was never attacked is worth nothing, however well written.

You are not the author's ally here. Do not soften. The author asked for this.

## Inputs

A thesis: a `research/*.md` file, a pasted argument, a Substack post, or a
position the user already holds. If the user gives you only a ticker and a
direction ("I'm long X"), ask them to state the thesis in two sentences first
— you cannot attack a claim nobody has made.

**Before adding to a losing position**, pull the real cost basis before you
attack anything else. The blended `average_buy_price` in `portfolio.db` hides
which lots are actually underwater and by how much — averaging down changes
the answer per lot, not per position.

- Fetch `get_equity_tax_lots` via the Robinhood MCP (read-only) for the
  position's per-lot cost basis and holding period.
- **Account pin**: use the **"Agentic" account (number ending 1936)**; if
  `get_accounts` returns more than one account, select it by name/last-4, and
  if no account matches, stop and report — never fall back to a different
  account.
- **Never paste raw MCP payloads into the conversation** (they can carry
  account identifiers) — summarize per-lot basis, quantity, and acquisition
  date instead.
- **Secret hygiene**: on any MCP error, report the exception type name only —
  never message bodies, URLs, or payload fragments.

## Procedure

1. **Enumerate the load-bearing conditions.** Restate the thesis as a numbered
   list of claims that must *each* be true for it to pay off. If the author
   did not enumerate them, do it for them, and show the list before attacking
   — a thesis often dies right here, when its author sees it has six legs.

   Count them. **More conditions means more surface area to be wrong.** A
   thesis resting on one condition ("this is a good business at a fair price")
   is far more likely to be right than one resting on five, even when every
   step of the five sounds clever. Say the count out loud in the verdict.

2. **Attack each condition independently.** For each, spend real effort trying
   to make it false. Under genuine uncertainty, **never credit the condition** —
   uncertainty withholds SOUND, it never earns it.

   Then say *which kind* of uncertainty you hit, because they route to
   different verdicts and are constantly confused:

   - **You attacked it, and the evidence stands against it.** The condition is
     *refuted*. → FLAWED.
   - **You could not attack it, because the evidence needed does not exist in
     any disclosure.** The condition is *unverifiable*. Mark it UNKNOWN and
     go to step 7. → UNPROVEN.

   A condition you merely find *uncomfortable* is neither. Go and check it.
   (Known bias: refusing to credit an unproven condition pushes toward
   inaction. Accepted deliberately — a false SOUND costs money, a false
   UNPROVEN costs an opportunity.)

3. **Run the standing checks.** Every thesis gets all of these:

   - **Base rate.** What normally happens to companies in this position?
     Rapidly extended credit to borrowers with no history usually ends badly.
     Turnarounds usually don't. Say the base rate before crediting the story.
   - **The short case.** What does someone short this stock see? Not a
     strawman — the strongest version. If you cannot construct one, you do
     not understand the business well enough to be long it.
   - **Management incentives.** What is management compensated on, and does
     the thesis quietly assume they will act against that incentive?
   - **Disconfirming search.** Go looking for evidence *against*, not for.
     A search that only returns support was a search for support.
   - **Is the moat a checkbox or a mechanism?** "It has a network effect" is
     a label. *What specifically stops a competitor tomorrow?* eBay passes the
     network-effect checkbox and fails the question.

4. **Run the statistical checks** whenever a claim rests on data — a backtest,
   a hit rate, a screen, a signal from this repo:

   - **Base rate is not 0.5.** Equities drift up. "It rose 60% of the time"
     may be worse than doing nothing. Compare against the benchmark, never
     against a coin.
   - **Overlapping windows.** Forward returns sampled daily over 20-day
     windows are ~20x less independent than they look.
   - **Multiple comparisons.** Testing 48 signals uncorrected guarantees
     "significant" ones.
   - **Effective n.** Not the row count.
   - **Mechanism claims are not inference claims.** "The API returns column
     X" is verifiable. "X predicts returns" is an inference and needs a null.

5. **Run the options-market timing check — but only when it applies.** This
   step is conditional, unlike the standing checks above: run it only when the
   thesis makes a **dated** claim (earnings, an FDA decision, a contract
   award, index inclusion — a specific date, not "eventually") **and** the
   ticker has a listed options chain. If either is missing, skip it outright
   and record why — skipping is not a failure and must not be treated as one.

   Use `.claude/skills/shared/options-read.md` for the options procedure.

   **Options evidence has a one-way valve: it can only cut, never confirm.**
   Refutation is measured against the 1-sigma move, never the straddle figure.
   Refute the timing condition only when the thesis needs a move beyond
   **2 sigma** — roughly a 5% outcome — and state the sigma multiple and the
   implied probability in the finding (the CLI prints this threshold in its
   verdict row — quote that row, don't restate the number; `REFUTE_SIGMAS` in
   `tools/options/implied_move.py` owns it and this prose can drift from it).
   Between 1 and 2 sigma the market is
   merely less optimistic than the thesis; that is not a refutation and must
   not be written as one. Mark the condition FLAWED only above the 2-sigma
   line, and the refutation stops there — it may not spread to undated
   conditions, because a thesis can be right about the destination and wrong
   about the calendar. An implied move that matches or exceeds what the thesis
   requires is NOT evidence for anything. If you catch yourself writing "the
   options market agrees" without immediately following it with "which is not
   evidence for the thesis," delete the sentence.

   **Disclose coverage in the verdict.** When the check could not run — no
   chain, illiquid, no aligned expiry, or the path-2 stopgap was used — say so
   explicitly. The check only fires on liquid names with a clean expiry
   match; silent omission makes a thesis look more thoroughly vetted than it
   was.

6. **Ask what would change the author's mind**, and whether it is observable.
   A thesis with no falsifier is not a thesis. If the author cannot name the
   evidence that would make them sell, they have a position, not an argument.

7. **Missing information is a finding.** When a load-bearing number does not
   exist in any disclosure, do not assume a value. State it as UNKNOWN and
   answer: *does its absence kill the thesis?* Sometimes the honest verdict is
   "I can't know this," and that is a complete and useful answer.

## Verdict

Close with exactly one, matching the vocabulary this repo's plan reviewers use:

- **SOUND** — every load-bearing condition survived a real attack. Say which
  attack came closest to landing.
- **FLAWED** — you attacked at least one load-bearing condition and the
  evidence stands against it. Name it, show the evidence, and say whether the
  thesis is repairable or dead.
- **UNPROVEN** — nothing was refuted, but at least one load-bearing condition
  could not be attacked at all: the evidence needed does not exist. Name what
  is missing and where it would have to come from. This is a real verdict, not
  a failure to reach one.

Then state, in one sentence, what evidence would flip your verdict.

## Guardrails

- **Never place an order** and never recommend a position size. Decision
  support only.
- **Never write to `data/*.db`.** Read-only, always.
- **Cite every factual claim.** A claim without a source becomes an explicit
  UNKNOWN, never a confident sentence.
- **Label source tiers.** SEC filings and company disclosures are primary.
  `stockanalysis.com` is this repo's one vetted exception and does not
  generalise. Reddit, YouTube, and expert-network colour are labelled
  low-confidence and never launder into fact.
- **Do not be agreeable.** If the thesis is good, the verdict is SOUND — but
  arrive there by failing to kill it, not by declining to swing.
- **Options data informs the equity thesis only.** It answers "is the market
  pricing in this catalyst," never "what should I buy." If asked directly —
  "should I buy the calls?" — reply with one sentence: this skill does not
  size or recommend options positions; that decision and its risk are the
  user's alone. Then stop. Do not follow with a strike or expiry "as
  information" — that is the same violation wearing a hedge.
- **Broker/market microstructure is its own source tier**, below primary
  filings and distinct from `stockanalysis.com`. Robinhood MCP quotes, option
  chains, and tax lots are real-time account and market state, not a
  researched disclosure — label them as this tier, not as primary or as the
  `stockanalysis.com` exception.
