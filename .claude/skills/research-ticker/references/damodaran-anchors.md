# Damodaran anchors — the hurdle and the sanity clamps

External reference numbers for Phase 4's hurdle read, from Aswath Damodaran's
NYU Stern data library (`pages.stern.nyu.edu/~adamodar/`). His stated terms
are an explicit free-use grant ("no strings attached"). Everything here is
plain static HTML/xls — no key, no blocking, fetchable with `curl`.

Four standing rules govern everything below:

- **Fetch live, cite as-of.** Never quote a number from this file in a
  write-up — the figures here are shape examples pinned to their as-of dates.
  The ERP updates monthly, country risk quarterly, the industry datasets each
  January.
- **The hurdle is a cost of equity.** `rf + beta × ERP` reads against the
  levered-FCF ↔ market-cap pairing only; `reverse_dcf` refuses it alongside
  `--net-debt` for this reason. An EV-paired run needs a WACC, by hand.
- **Anchors read the output, never tune a screen or a signal.** Nothing here
  feeds `composite`, `candidates`, or `advisor`.
- **Source tier: reference data** (his own computed aggregates) — below
  primary filings, never a substitute for a company-specific disclosure.

## The hurdle: risk-free + beta × ERP

**Risk-free and implied ERP** (monthly, first of the month) sit in the first
screen of his home page — one fetch gets both:

```bash
curl -s https://pages.stern.nyu.edu/~adamodar/New_Home_Page/home.htm \
  | grep -o -E '(Implied ERP on [A-Za-z]+ [0-9]+, [0-9]{4}[^<]*|T\.Bond rate = [0-9.]+%)' | head -5
```

Use the headline trailing-12-month ERP, not the alternates listed beside it.
Shape (as of Aug 1, 2026): ERP **4.28%**, risk-free (10Y T-bond) **4.74%**.

**Beta** comes from the stockanalysis statistics page Phase 4 already probes —
no extra fetch — but it enters the hurdle only after two sanity checks:

- **The stable band, 0.8–1.2.** A regression beta far outside it needs a
  reason; in particular, a thin-float or family-controlled name prints an
  artificially low beta that would hand the hurdle read a free pass. Floor
  it into the band and say so.
- **The absolute companion: a mature company's cost of capital ≈ risk-free
  + 4.5%** (his terminal checker's default block). A hurdle far below that
  for a stable name deserves a sentence.

**Country ERP** (conditional): the headline ERP is a US premium. When the
filing's geographic segment note shows material non-US revenue or production,
replace it with the **operations-weighted** country ERP — never the country
of incorporation's, never the flat US number:

```bash
curl -s https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html
```

`ERP_company = Σ wᵢ × total-ERPᵢ` over the segment note's countries — weights
by revenues for consumer businesses, production for resource extraction, a
stated mix for manufacturers. Take **every** country's ERP from this one
table, its US row included when there is a US weight; one vintage per
calculation, never mixed with the monthly headline number. This is the one
country dataset that parses with stdlib (a static HTML table: country |
Moody's rating | default spread | country risk premium | **total ERP**).
Cite the page's own "Last updated" stamp — it lags his country-risk paper
(checked 2026-08-06: still the January 5, 2026 vintage). Shape: Germany/
Australia (Aaa) **4.23%**, US (Aa1) **4.46%**, South Africa (Ba2) **8.13%**,
Ghana (Caa1) **13.94%**. A US-only name stays on the headline monthly ERP —
no fetch, nothing changes.

## Reading the implied return: the distribution clamps

Annual figures, refreshed each January — re-check the year before citing:

- **Cost-of-capital distribution** (Data Update 5, 2026): US median
  **7.79%**; 80% of US firms between **5.26% and 9.88%**. An implied return
  below the 10th percentile is a strong pass regardless of story; a hurdle
  claim outside the band needs an argument.
- **Excess-return base rate** (`New_Home_Page/datafile/EVA.html`): only
  **~29%** of firms earn above their cost of capital — the default terminal
  assumption is excess returns fading, not persisting.

## Modelling inputs: the industry datasets

Same January cadence. The `datafile/*.html` pages are US-only mirrors of the
xls files and parse with stdlib; the regional variants are Excel-only
(legacy BIFF — don't bother).

- **Industry margins** (`New_Home_Page/datafile/margin.html`): steady-state
  operating-margin anchors for the margin-expansion path; also carries
  SBC/Sales by industry.
- **Sales-to-capital** (`New_Home_Page/datafile/capex.html`): the
  reinvestment denominator when modelling bookings × margin —
  reinvestment ≈ Δrevenue / sales-to-capital.

## Beyond the anchors: the rest of the site (indexed 2026-08-06)

The site is far larger than the anchors above. Directly practice-relevant
resources not yet mined, fetch on demand (all under
`pages.stern.nyu.edu/~adamodar/`, static, robots-clean):

- `New_Home_Page/glossary.htm` — his ~310-term valuation glossary, one page;
  the canonical vocabulary source (already cross-checked against
  `docs/GLOSSARY.md` once, 2026-08-06).
- `New_Home_Page/valquestions/valquestions.htm` — "25 Questions on DCF
  Valuation (and my opinionated answers)"; the source of Phase 4's
  base-and-terminal integrity checks, worth re-reading whole when a run
  hits an odd structure.
- `pdfiles/eqnotes/webcasts/TermValueCheck/termvaluecheck.xls` — his
  terminal-value consistency checker; validates this repo's g/reinvestment
  discipline nearly verbatim.
- `New_Home_Page/definitions.html` — ~100 ratios with per-measure *misuse*
  commentary; attack material for condition checks.
- `pdfiles/eqnotes/valpacket1-3spr26.pdf` — the complete current valuation
  course; free-online twin with worked 10-K exercises at
  `New_Home_Page/webcastvalonline.htm`.
- Unread practice papers (method, not numbers — many pre-date ASC 842 and
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
