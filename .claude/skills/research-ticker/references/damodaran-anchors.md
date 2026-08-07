# Damodaran anchors — the hurdle and the sanity clamps

External reference numbers for Phase 4's hurdle read, from Aswath Damodaran's
NYU Stern data library (`pages.stern.nyu.edu/~adamodar/`). His stated terms
are an explicit free-use grant ("no strings attached"); attribution is
appreciated, not required. Everything below is plain static HTML/xls — no
key, no blocking, fetchable with `curl`.

**Fetch live, cite as-of.** Never quote a number from this file in a
write-up — the figures below are examples pinned to their as-of dates so you
know what shape to expect. The ERP updates monthly; the industry datasets
update each January.

## The run-time fetches

**Risk-free + implied ERP** (monthly, first of the month) — both sit in the
first screen of his home page:

```bash
curl -s https://pages.stern.nyu.edu/~adamodar/New_Home_Page/home.htm \
  | grep -o -E '(Implied ERP on [A-Za-z]+ [0-9]+, [0-9]{4}[^<]*|T\.Bond rate = [0-9.]+%)' | head -5
```

Shape (as of Aug 1, 2026): implied ERP **4.28%** (trailing 12-month, adjusted
payout), risk-free (10Y T-bond) **4.74%**. Use the headline trailing-12-month
ERP, not the alternates he lists beside it.

**Beta** — already on the stockanalysis statistics page Phase 4 probes
(`valuation` block). No extra fetch.

**Country ERPs** (conditional): the headline ERP above is a US premium. When
the filing's geographic segment note shows material non-US revenue or
production, the hurdle ERP is the **operations-weighted** country ERP —
never the country of incorporation's, never the flat US number:

```bash
curl -s https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html
```

This is the one country dataset that parses with stdlib — a static HTML
table (country | Moody's rating | default spread | country risk premium |
**total ERP** | …), unlike the Excel-only regional files noted below. Cite
the page's own "Last updated" stamp: it lags his July country-risk paper
(checked 2026-08-06: page still on the January 5, 2026 vintage).

`ERP_company = Σ wᵢ × total-ERPᵢ` over the segment note's countries.
Weights: revenues for consumer businesses, production for resource
extraction, a stated mix for manufacturers. Slot the result into the same
`rf + beta × ERP` hurdle (pass as `--erp`). Take **every** country's ERP
from this one table — its US row included when there is a US weight — never
mixing in the monthly headline number: one vintage per calculation. Shape
(as of Jan 5, 2026): Germany/Australia (Aaa) **4.23%**, US (Aa1) **4.46%**,
South Africa (Ba2) **8.13%**, Ghana (Caa1) **13.94%**. A US-only name stays
on the headline monthly ERP — no fetch, nothing changes.

## The clamps (annual, refreshed each January — re-check the year)

- **Cost-of-capital distribution** (Data Update 5, 2026): US median **7.79%**;
  80% of US firms fall between **5.26% and 9.88%**. An implied return below
  the 10th percentile is a strong pass regardless of story; a hurdle claim
  outside the band needs an argument.
- **Excess-return base rate** (EVA dataset,
  `New_Home_Page/datafile/EVA.html`): only **~29%** of firms earn above their
  cost of capital. The default terminal assumption is excess returns fading,
  not persisting.
- **Industry margins** (`New_Home_Page/datafile/margin.html`): steady-state
  operating-margin anchors for the margin-expansion path (also carries
  SBC/Sales by industry).
- **Sales-to-capital by industry** (`New_Home_Page/datafile/capex.html`):
  the reinvestment denominator when modelling bookings × margin —
  reinvestment ≈ Δrevenue / sales-to-capital.

The `datafile/*.html` pages are US-only mirrors of the xls files and parse
with stdlib; the regional variants are Excel-only (legacy BIFF — not
stdlib-readable, don't bother).

## Deeper mining index (site fully indexed 2026-08-06; fetch on demand)

The site is far larger than the anchors above — a full section index found
these directly practice-relevant resources not yet mined (all under
`pages.stern.nyu.edu/~adamodar/`, static, robots-clean):

- `New_Home_Page/glossary.htm` — his ~310-term valuation glossary, one
  page; the canonical vocabulary source for skill prose and `docs/GLOSSARY.md`.
- `New_Home_Page/valquestions/valquestions.htm` — "25 Questions on DCF
  Valuation (and my opinionated answers)": FCFF definition, growth, terminal
  value — the judgment calls Phase 4 makes, in checklist form.
- `pdfiles/eqnotes/webcasts/TermValueCheck/termvaluecheck.xls` — his own
  terminal-value consistency checker; the reference implementation behind
  this repo's g/reinvestment discipline.
- `New_Home_Page/definitions.html` — ~100 ratios with per-measure *misuse*
  commentary; attack material for condition checks.
- `pdfiles/eqnotes/valpacket1-3spr26.pdf` — the complete current valuation
  course (supersedes older note PDFs); free-online twin with worked 10-K
  exercises at `New_Home_Page/webcastvalonline.htm`.
- Unread practice papers (method, not numbers — many pre-date ASC 842 /
  current tax rates): `pdfiles/papers/{multiples,returnmeasures,
  cashvaluation,growthorigins,HighGrow,riskfreerate,ERPfull}.pdf`.
- `pc/blog/AlldataMarch2026.xlsx` — every current industry dataset in one
  workbook (filename rotates; scrape home.htm for the current link).
- `New_Home_Page/dataaddon.html` / `databreakdown.html` — dataset changelog
  and variable definitions; check before reading a YoY jump in an anchor as
  a market move rather than a provider/definition switch.
- `New_Home_Page/covals.htm` — 37 worked valuations by company type (banks,
  distress, cyclicals, index DCF) — templates for cases the simple levered
  path handles poorly.

## Rules

- The hurdle (`rf + beta × ERP`) is a **cost of equity**: it reads against
  the levered-FCF ↔ market-cap pairing only. `reverse_dcf` refuses the
  combination with `--net-debt` for this reason — an EV-paired run needs a
  WACC, by hand.
- These are anchors for reading the output, never inputs that tune a screen
  or signal — nothing here feeds `composite`, `candidates`, or `advisor`.
- Source tier: label as reference data (his own computed aggregates), below
  primary filings; it never substitutes for a company-specific disclosure.
