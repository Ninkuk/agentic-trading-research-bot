# Thesis document template

The fixed layout for `research/<TICKER>-<YYYY-MM-DD>.md`. It standardizes
presentation only — every element below is something the skill's phases
already produce; nothing here adds an analysis step. Machine consumers read
only the filename, `verdicts.log`, and the journal JSON — the body is for the
human reader, so the value of this template is that 100+ documents stay
skimmable in the same places.

## Filename and title

- File: `research/<TICKER>-<YYYY-MM-DD>.md` (Phoenix date). A second run on
  the same ticker and date appends a short suffix (e.g. `-postprint`) — the
  suffixed file is deliberately invisible to `tools/research/worklist.py`.
- Title: `# <TICKER> — <Company Name> — <YYYY-MM-DD>`. Reopen runs append
  ` (reopen of <YYYY-MM-DD>, trigger: <slug>)`.
- Under the title, one metadata line, middot-separated:
  `Price $X (<basis: official close / after-hours / live quote, date>) ·
  market cap $X · next earnings <date + BMO/AMC, or "none scheduled">`.
  Add EV/net debt only when §4 uses them.
- Then one provenance line: entry path (`candidates` screen row, composite
  flag, user-directed, reopen) and, on a scheduled run, the sentence
  "Unattended scheduled run." Reopen runs replace this line with a short bold
  block: prior file, prior verdict + ownership call, and the reopen question.

## Section skeleton

All headings are `##`, numbered, exactly these names, in this order. Never
add `###` levels; never reorder; a section that cannot run is still present
and says why (a stated refusal is a finding, an omitted section is a hole).

```
## 0. The reopen question, answered first      (reopen runs only)
## 1. Verdict and thesis
## 2. Business
## 3. Threads pulled
## 4. Valuation
## 5. Falsifiers
## 6. UNKNOWNs
## 7. Sources
## Kill-thesis record                          (unnumbered, always last)
```

Prose is hard-wrapped at ~80 columns like the rest of the repo. No
horizontal rules between sections. Bold lead-ins, not `###`, structure the
inside of a section.

## §0 — reopen runs only

Answer the reopen question before anything else. Include a three-column
table sweeping the prior thesis's falsifiers:

| prior falsifier | actual | status |
|---|---|---|

Status vocabulary: `NOT TRIGGERED` / `GRAZED` / `HALF-TRIGGERED` / `FIRED`.

## §1 Verdict and thesis

First line, bold, always this shape (research-sweep and the journal read the
ownership call from here):

> **BUY at $X.** kill-thesis: **SOUND** — conditions=5 (4 probable,
> 1 plausible), refuted=0, unknown=1.

- Ownership call first (`BUY` / `PASS`, caps, with the price and its basis),
  kill-thesis label second. The ledger mirrors `verdicts.log` vocabulary:
  `conditions= refuted= unknown=` — write `unknown`, not "unverifiable".
  A scope parenthetical is allowed ("SOUND (on this pass)").
- Then the thesis in plain language, 2–5 sentences.
- Then `**Closest attack:**` — the attack that came nearest to landing.
- Then the load-bearing conditions, numbered, each tagged by evidence tier
  in italics (*probable* / *plausible* / *possible*) with one line of the
  evidence behind the tag. This list is mandatory — a count whose conditions
  are never enumerated is unauditable, and reopen runs need the list to
  sweep against.
- Then the factor line, always present, this exact lead-in (overlap reads
  grep it):
  `**Dominant shared risk factor:** <factor> — shared by N of M held names
  (<tickers>) · K unlabelled`. `<factor>` is factor grain, never a sector
  label; `idiosyncratic` stands alone with no overlap clause. When holdings
  cannot be read, the overlap clause is replaced by "holdings unavailable in
  this session".

## §2 Business

Three bold lead-ins: `**Created:**` / `**Captured:**` / `**Protected:**` —
capture unpacked into its distinct mechanisms, protection as a mechanism or
an honest "no moat". End with the Phase 0 print, always here (not §1/§3/§4):
`**Operating leverage (Phase 0): positive | flat | negative.**` plus the
revenue/op-income figures behind it (table or sentence).
Reopen runs may write "Unchanged from `<prior file>` §2" plus deltas.

## §3 Threads pulled

Bold-lead bullets, one per thread, findings inline with sources. Two bullets
are mandatory: `**Options read (mandatory):**` naming the paths used (path 1
/ path 2 / no listed options) and pointing at §4's table; and a final
`**Dead ends:**` bullet recording what was checked and ruled nothing out.
Data-coverage gaps (no `sec_fundamentals.db` row, EDGAR 403) are recorded
here as findings.

## §4 Valuation

In order:

1. Inputs paragraph: exact figures (statistics-probe `hover` values), the
   flow↔denominator pairing stated ("levered TTM FCF $X against market cap
   $Y; net debt 0 by the pairing rule"), SBC/minority-interest haircuts.
2. Hurdle line: `rf X% + beta Y × ERP Z% = H%` with the Damodaran as-of date
   and any beta clamp to the 0.8–1.2 band, stated.
3. Scenario table, these columns:

   | scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
   |---|---|---|---|---|---|

   Spreads in bp. Precision follows the IV rule: ATM IV > 50% → whole
   percents only.
4. Integrity bullets: the reinvestment/terminal-ROE warning answered, the
   market-share sentence, terminal growth vs the Item 1A terminal risk,
   distribution clamp.
5. Options-implied move: the metric table from
   `.claude/skills/shared/options-read.md` §5, rendered as a markdown table
   (never a code block), introduced by path + expiry + DTE + what it
   brackets, followed by the liquidity-gate verdict (`FAILED → UNRELIABLE`
   where it fails) and the timing-check applicability line.

6. Equity as option (levered names only — the Phase 4 leverage gate): the
   `equity_option` table as a markdown table, the vol source named, and one
   sentence saying which frame (DCF or option) governed §1's ownership
   call. Omit the item entirely at normal leverage.

When `reverse_dcf` refuses (exit 2), quote the refusal line and substitute
the honest arithmetic (required-FCF inversion, capital structure, moneyness)
— the section is never dropped. No listed options → say so; the table is
replaced by that sentence.

## §5 Falsifiers

Every item starts with its class tag: `**Break —**` (story over: sell /
never enter) or `**Shift —**` (input moved: revalue). On a PASS, split the
list: "For the pass (flip toward buy)" then "For an owner (sell)". Close the
section with one line, always present:

`**Reopen trigger:** 2026-11-04: <slug>` — or `event:<slug>`, or
`none stated`. This is the same trigger the `verdicts.log` line carries;
the thesis file (here) holds the actual condition.

## §6 UNKNOWNs

Numbered. Each entry: what is missing, where it would have to come from,
and whether its absence kills the thesis.

## §7 Sources

Fixed tier names, fixed order, bold lead-ins; a tier with nothing in it says
"none used" rather than disappearing:

- `**Primary:**` — SEC/regulator filings, company disclosures (transcripts
  via stockanalysis are primary-transcribed; say so).
- `**stockanalysis.com (vetted exception):**`
- `**Broker/market microstructure:**` — Robinhood MCP, with the
  admissibility note (no integrated official source covers the field).
- `**Reference data:**` — Damodaran rf/ERP/base rates, with as-of dates.
- `**Point-in-time repo DBs:**` — what `data/*.db` said, read-only.
- `**Low-confidence:**` — web colour, labelled.

## Kill-thesis record

Written by the Phase 5 kill-thesis pass; the one place its detail lives (not
§1, not an appendix, not a footer). Contents: the ledger line restated;
per-condition adjudication (`SURVIVED` / `REFUTED` / `UNKNOWN`) with the
attack each faced; the standing/statistical/options-timing checks that ran
(or why one was N/A); `**Closest attack:**`; `**Flip evidence:**` in both
directions (what makes it SOUND, what makes it FLAWED).
