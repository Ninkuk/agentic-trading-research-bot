# SION — Sionna Therapeutics — 2026-08-11

Price $5.10 (official close, 2026-08-11) · market cap $230.6M · shares 45.21M ·
next earnings not recorded in original run

Entry path not recorded in original run. Unattended scheduled run. Judgment
calls made without user confirmation are marked *[call]*.

## 1. Verdict and thesis

**PASS at $5.10 — do not own.** kill-thesis: **SOUND** — conditions=5 listed
(4 genuinely load-bearing), refuted=0, unknown=1.

Sionna is a post-failure clinical-stage CF biotech whose lead asset died on
2026-08-10 and which now trades at roughly its adjusted net cash; the 4–10%
discount is smaller than a single quarter of burn ($0.478/share, 9.4% of
price), and realistic wind-down value ($4.00–4.90/share) sits *below* the
current price.

**Closest attack:** the balance-sheet correction (§4), which widens the
discount from 4.2% to as much as 9.9% — insufficient, because one quarter's
burn equals or exceeds it.

Load-bearing conditions not enumerated in original run; condition tiers not
recorded in original run.

## 2. Business

**Created:** Nothing yet — pre-revenue. The intended product is a CFTR
modulator regimen for cystic fibrosis built on NBD1 stabilisation, a mechanism
distinct from Vertex's correctors. Value to the patient would be improved CFTR
function beyond today's standard of care.

**Captured:** Nothing yet. TTM revenue `n/a`; TTM operating loss −$109.5M
(R&D $72.0M, SG&A $37.4M); TTM net loss −$97.4M; TTM FCF −$76.2M.

**Protected:** Nothing durable. The competitive question is "what stops
Vertex," and the answer is: nothing. Trikafta produces ~−40 mmol/L sweat
chloride and has normalised life expectancy for most F508del patients. Any
Sionna regimen must match that *and* win on a second axis (tolerability,
price, adherence). Patents and the AbbVie in-licence are inputs, not a moat.

**Domain limit (declared):** Whether NBD1 stabilisation is a viable CF
mechanism is protein biophysics I cannot adjudicate. Bounded below by the one
patient readout that exists (§3), and marked UNKNOWN in §6 rather than
guessed.

**Operating leverage (Phase 0): negative.** There is no revenue line to
lever, and operating loss widened from −$87.7M to −$109.5M YoY while SG&A
nearly doubled ($19.8M → $37.4M) on post-IPO public-company cost.

## 3. Threads pulled

- **The event.** 2026-08-10: Phase 2a PreciSION CF of SION-719 as add-on to
  Trikafta missed. Placebo-adjusted sweat chloride **−1.0 mmol/L, p=0.7**,
  against a **10 mmol/L** bar the trial was designed to detect. n=15 adults,
  F508del homozygous, randomised double-blind placebo-controlled crossover.
  Company will not advance SION-719 as an add-on. Stock: Aug 7 close $51.04 →
  Aug 10 open $4.85, close $4.50 on 38.6M shares (vs ~750k normal); Aug 11
  official close $5.10. ≈ −90%.
- **Is p=0.7 uninformative at n=15?** No — this thread mattered most and it
  closed. Two-sided p=0.7 implies |z| ≈ 0.385, so SE ≈ 1.0/0.385 ≈ 2.6 mmol/L
  and the 95% CI is roughly **−6.1 to +4.1 mmol/L** (t₁₃: −6.5 to +4.5). That
  interval **excludes the 10 mmol/L target**. The crossover design bought
  within-patient precision that "n=15" does not suggest. This is "it isn't
  there," not "we couldn't see it." (Company has not published the actual
  SD/CI — see §6.)
- **The DDI confounder — real, and still not value.** CMO Charlotte McKee
  reported a "noticeable and observable decrease in Trikafta levels when
  patients were dosed in 719 period compared to the placebo period," "large
  enough to have impacted the potential treatment effect," and explicitly
  **not** primarily CYP3A4 induction but "some possible other more complex
  interaction." She separately said higher-than-expected sweat chloride
  variability "did not drive the outcome." Cloonan: "we did have patients
  above 10." Granting the confounder fully, it converts *mechanism failed*
  into *mechanism untested* — and it is self-defeating for the backup: if it
  voids the only patient efficacy data NBD1 stabilisation has produced,
  SION-451 enters Phase 2 with zero de-risking. Cloonan conceded the
  "disconnect" between the translational model's 10 mmol/L prediction and the
  −1.0 result. **The model justifying SION-451 is the model that just missed
  10×.**
- **What is left.** SION-451 + SION-2222 (galicaftor, AbbVie-derived).
  Phase 1, 120 healthy volunteers, met **safety, tolerability and PK only —
  no efficacy, no sweat chloride data.** SION-451 BID + SION-2222 QD
  preferred on "totality of data and target coverage." Tolerability signals:
  1 discontinuation (rash), 2 in BID cohorts (elevated liver tests, flu-like
  symptoms). Management frames it as "a very different context" (standalone
  regimen, not add-on). No decision date; "near term."
- **Will the cash come back?** No strategic review, no restructuring, no
  workforce reduction, no capital-return plan announced. CEO: "We are
  currently undertaking actions to preserve capital." CFO Ridloff defers the
  runway update until "we finalize more of the details around the SION-451,
  SION-2222 next steps" — phrasing that presupposes there *are* next steps.
  **Incentives point the same way:** every option/RSU is struck between $18
  and $50, so a dissolution at ~$5.30 pays management nothing while a Hail
  Mary Phase 2 pays enormously. Classic risk-shifting. Base rate: busted
  biotechs above cash almost never dissolve; reverse mergers are commoner and
  typically leave legacy holders 15–35% of a new speculative entity.
- **Two data traps caught.** (a) stockanalysis's overview `changes` block
  holds price **levels**, not percent changes (`price1m: 45.29` = the Jul-6
  weekly close, verified against Robinhood bars); read as percentages it
  would have said "+45% in a month," the exact inverse of the truth. (b) Its
  blended analyst target of **$17.20 (+237%) is stale** — live post-failure
  targets are Stifel $55→$7, Wedbush $53→$5, with BTIG, Raymond James,
  Citizens JMP and Guggenheim all cut to neutral/market-perform.
- **Options read (mandatory):** path 2 only — SION is not in the 24-symbol
  CBOE catalog, so `data/options.db` has no history and path 1 is
  structurally unreachable; see §4's table.
- **Dead ends (checked, ruled nothing out):** (i) AbbVie licence — milestones
  are **late-stage development and commercial**, i.e. contingent, plus an
  equity stake; no near-term fixed claim found. (ii) Debt — none; the $8.069M
  "debt" line is entirely leases. (iii) Recent dilution — none; APIC rose
  only $27.4M YoY, matching SBC, so no follow-on was done. (iv) Insider
  signal — OrbiMed (director Peter Thompson's fund) sold 115,844 shares at
  $45.50 under a **10b5-1** plan pre-failure, so not discretionary and not a
  signal; no post-crash insider buying found.

## 4. Valuation

**A reverse DCF is a category error here and was not used as the valuation.**
Confirmed by execution, not assumed:

```
$ uv run python -m tools.valuation.reverse_dcf --market-cap 230580000 \
    --base-fcf -76207000 --growth 0.0 0.0 0.0 --terminal-growth 0.02
refused: base_fcf must be positive, got -76207000.0     # exit 2
```

*[call]* The Phase-4 hurdle machinery (risk-free + beta × ERP) is therefore
inapplicable — there is no implied return to spread against a cost of equity.
No hurdle computed this run. The governing comparison for a liquidation-value
case is **discount vs. burn rate**, substituted deliberately and stated here.

**Balance sheet (2026-06-30, company-stated $268.3M; independently reconciled
against stockanalysis: $211.031M current cash+ST investments + $57.222M
long-term investments = $268.253M).** Total liabilities $17.474M (AP $0.523M,
accrued $8.882M, leases $8.069M). No debt.

**Burn, cross-checked two ways.** Q1 cash $289.9M → Q2 $268.3M =
**$21.6M/quarter**; and Q2 net loss $29.9M less ~$8M SBC ≈ $22M. Agreement.
Six weeks to 2026-08-11 at $0.237M/day = $9.97M.

| basis | net assets | per share | discount at $5.10 |
|---|---|---|---|
| hard cash less **all** liabilities | $240.8M | **$5.33** | 4.2% |
| full book, burn-adjusted | $255.8M | **$5.66** | 9.9% |

The lower row is conservative but one-sided — it subtracts liabilities while
ignoring $14.996M of non-cash assets (other current $5.099M, PP&E $8.340M,
other LT $1.557M). The upper row credits PP&E at book, which specialised lab
equipment and leasehold improvements will not fetch. **True range 4–10%.**
The naive "Jun-30 cash vs today's market cap" figure of $37.7M / 14%
overstates it by ignoring six weeks of burn and every liability.

**Why the discount is not enough — the decisive arithmetic:**

- Burn = **$0.478/share/quarter = 9.4% of price, per quarter**; $86.4M/yr =
  **36% of net assets per year**. Even if burn halves post-failure, ~18%/yr.
- **One quarter at the pre-failure run rate consumes the entire 4–10%
  discount.** This is a decaying option, not a free one, and there is no
  announced date at which the decay stops.
- Wind-down would cost severance $15–30M, trial close-out $5–15M, lease
  $5–10M, D&O tail with pending litigation $2–6M, legal/dissolution $3–8M,
  plus Delaware's multi-year contingent-claim reserve → **$35–90M
  ($0.77–2.00/share, 15–35% of assets)**, implying a realistic distribution
  of **$4.00–4.90/share, below today's price.** The "trades below cash"
  framing fails once wind-down is priced.
- Runway guidance of "into 2028" (given 2026-08-06, pre-failure) implies
  planned burn of ~$107–179M/yr — well above the $86M/yr run rate, i.e. it
  assumed a Phase 2/3 ramp.

**Options-implied move — path 2 only** (SION is not in the 24-symbol CBOE
catalog, so `data/options.db` has no history and path 1 is structurally
unreachable). 2026-10-16 $5.00 strike, **66 DTE**, mean ATM IV 126.60%:

| metric | value |
|---|---|
| spot | 5.10 |
| expected absolute move (MEAN, not a ceiling) | 41.67% |
| 1-σ move | 53.83% |
| ATM IV | 126.60% |
| RV60 | 503.40% |
| RV20 | 871.10% |
| IV > RV60? | NO |
| IV > RV20? | NO |

**UNRELIABLE — liquidity gate fails both legs** (call OI=1, volume=2, bid
0.70/ask 2.00 around a 1.35 mark; call IV 153.2% vs put IV 100.0%, a 53-point
gap that is illiquidity, not a market view). **The IV-vs-RV comparison is
void this run** *[call]*: both realized windows are dominated by the single
−91% day, so `IV > RV60? NO` does not mean options are cheap. Only the
standalone 1-σ of ±53.8%/66d is usable. A required move of 8.8% (converge to
$5.33) is 0.16σ, P=87.6% — **does not refute**, and per the one-way valve
this is **not evidence for the thesis** either. The thesis also makes no
*dated* claim, so the timing check formally does not apply.

Read as information rather than as support: the market prices ~127% ATM IV on
a company that is ~92% cash. It is pricing a bimodal outcome, not a cash box.

## 5. Falsifiers

What would make this a buy:

1. **Break —** announced dissolution with a quantified distribution above
   ~$5.50/share net of wind-down costs — the pass is over.
2. **Shift —** price below ~$4.00, creating a real margin against liquidation
   value rather than a 4–10% one — the asset didn't change, the price did.
3. **Break —** a credible SION-451 efficacy signal in patients — sweat
   chloride in CF subjects, not healthy-volunteer PK.
4. **Break —** a binding capital-return commitment or activist board control
   forcing one.
5. **Shift —** burn cut to a genuine caretaker level (< ~$25M/yr) with the
   runway update quantifying it.

**Reopen trigger:** none stated.

## 6. UNKNOWNs

1. **Purchase/manufacturing commitments footnote** — not obtained. EDGAR
   returned HTTP 403 on every route attempted (`cgi-bin/browse-edgar`,
   `data.sec.gov/submissions`, `Archives` listing), consistent with this
   repo's known EDGAR fingerprint sensitivity. A $20–40M non-cancellable
   CRO/API commitment would move net cash. **Does not kill the thesis — it
   can only widen the case for passing.** Would come from the Q2 2026 10-Q
   commitments note.
2. **AbbVie termination economics.** Milestones are confirmed late-stage and
   contingent, but abandonment/wind-down obligations are undisclosed. Would
   come from the licence exhibit.
3. **Actual trial SD and confidence interval.** Not published; the CI in §3
   is derived from the reported point estimate and p-value under a two-sided
   normal/t assumption.
4. **Whether NBD1 stabilisation works at all in patients.** Structurally
   unknowable today — the only patient readout is confounded, and no efficacy
   data exists for SION-451.
5. **Securities litigation exposure.** Johnson Fistel has announced an
   investigation; the Aug-6 "on track" statement is a timing claim, a weak
   10b-5 hook, but Section 11 exposure on the Feb-2025 IPO registration has
   no scienter requirement. Size unquantifiable now.

## 7. Sources

**Primary:** 2026-08-10 press release "Sionna Therapeutics Reports Topline
Data from Two Development Programs in Cystic Fibrosis and Provides Corporate
Update" (trial results, n, p-value, cash, capital-preservation language).
2026-08-10 "Study result" call transcript, detailSlug `729758-study-result`
(McKee on Trikafta exposure and variability; Cloonan on read-through and the
translational disconnect; Ridloff on runway; full analyst Q&A). 2026-08-06
Q2 2026 results release (net loss $29.9M, G&A $10.6M, $268.3M cash, "into
2028", "on track"). 2024-07-16 AbbVie licence announcement. Form 4, OrbiMed
Private Investments VIII LP. CIK 0002036042. *Note: SEC EDGAR direct
retrieval failed (403) throughout this run; filings are cited via company
distribution and search indexes, not fetched from EDGAR.*

**stockanalysis.com (vetted exception):** (via
`sources.screeners.stock_analysis_screener.probe`) — `/stocks/SION/statistics/`,
`/financials/income-statement/`, `/financials/balance-sheet/`,
`/stocks/SION/`, `/stocks/SION/transcripts/`. Supplied the balance sheet, TTM
income statement, share count, and the transcript index. Its `$17.20` analyst
target and `changes` block are flagged unreliable in §3.

**Broker/market microstructure:** (Robinhood MCP — real-time market state,
admissible where no integrated official source covers it; below primary
filings and distinct from stockanalysis.com): `get_equity_quotes` (official
2026-08-11 close $5.10), `get_equity_historicals` (daily/weekly bars
establishing the −90% gap and the closes array), `get_option_chains` /
`get_option_instruments` / `get_option_quotes` (the §4 chain).
**`get_financials` was not used** — banned by the skill; financials came from
stockanalysis and company releases.

**Reference data:** none used.

**Point-in-time repo DBs:** `tools/valuation/reverse_dcf` (exit-2 refusal,
§4) and `tools/options/implied_move` (§4 table) were executed this run. No
`data/*.db` was written. Point-in-time DBs (`stocks.db`, `composite.db`,
`sec_fundamentals.db`, `earnings.db`) could not be read this run — `sqlite3`
was not permitted in this unattended session — so every figure here is
live-wire, not warehouse; noted as a deviation from the Phase 0 procedure
*[call]*.

**Low-confidence:** analyst rating and price-target changes (Stifel, Wedbush,
BTIG, Raymond James, Citizens JMP, Guggenheim, RBC) via secondary
aggregators; the Johnson Fistel investigation notice. None load-bearing.

## Kill-thesis record

Ledger line restated: **SOUND** — conditions=5 listed (4 genuinely
load-bearing), refuted=0, unknown=1; ownership PASS at $5.10.

Per-condition adjudication not recorded in original run.
Standing/statistical/options-timing checks: the statistical and options-timing
detail is recorded in §4 — the IV-vs-RV comparison declared void this run, the
required 8.8% move at 0.16σ (P=87.6%) does not refute and per the one-way
valve is not evidence for the thesis either, and the thesis makes no dated
claim so the timing check formally does not apply.

**Closest attack:** the balance-sheet correction (§4), which widens the
discount from 4.2% to as much as 9.9% — insufficient, because one quarter's
burn equals or exceeds it.

**Flip evidence:** not recorded in original run beyond the §5 falsifiers.
