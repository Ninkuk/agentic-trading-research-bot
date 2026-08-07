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

## The two run-time fetches

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

## Rules

- The hurdle (`rf + beta × ERP`) is a **cost of equity**: it reads against
  the levered-FCF ↔ market-cap pairing only. `reverse_dcf` refuses the
  combination with `--net-debt` for this reason — an EV-paired run needs a
  WACC, by hand.
- These are anchors for reading the output, never inputs that tune a screen
  or signal — nothing here feeds `composite`, `candidates`, or `advisor`.
- Source tier: label as reference data (his own computed aggregates), below
  primary filings; it never substitutes for a company-specific disclosure.
