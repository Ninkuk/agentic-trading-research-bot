# IREN — IREN Limited — 2026-09-01

Price $37.12 (official close 2026-08-31; pre-market $36.51 at 08:09Z) ·
market cap $14.63B · EV $16.57B / net debt ~$1.9B (gross principal $7.71B +
$0.27B finance leases vs $5.90B cash, $1.67B of it restricted) · next
earnings 2026-11-05 AMC (Robinhood, unverified; `earnings.db` carries no
upcoming row as of its 2026-08-31 calendar).

User-directed (`/research-ticker IREN`). Not a `candidates` row, not a
composite flag (composite 2026-08-28: bullish 1 / bearish 0 / neutral 2, no
flag). FY26 10-K filed 2026-08-27, the same day as the Q4 print and call.

## 1. Verdict and thesis

> **PASS at $37.12.** kill-thesis: **FLAWED** — conditions=5 (2 probable,
> 2 plausible, 1 possible), refuted=1, unknown=2.

IREN is a former bitcoin miner that has spent FY26 turning ~2.9 GW of owned
grid connections into an AI-cloud landlord-plus-operator: it owns the power,
the buildings, the GPUs and (via Mirantis) an orchestration layer, and rents
GPU-hours on 3–5 year contracts to Microsoft ($9.7B TCV), NVIDIA ($3.4B TCV)
and a widening list of AI developers. The claim is real and the demand is
documented by customer prepayments (deferred revenue jumped $1.72B in one
quarter). The problem is arithmetic, not story: at $14.6B the equity is
priced for roughly $1.15B of perpetual owner free cash flow (at a
band-clamped 9.9% hurdle) or $3.1B (at the stock's own 4.3 beta), while the
company's disclosed unit economics — >$20M/MW/yr on 3-year contracts, ~2-year
GPU payback, GPUs ≈ two-thirds of all-in capex — mean a contract returns
roughly 1.0× the all-in capital over its term. The equity value is therefore
the residual: what a 3-year-old GPU fleet re-contracts for in years 4–5 and
beyond, which is exactly the obsolescence risk the 10-K names as structural.
Add a $25–30B FY27 capex guide against $14B of secured funding, a share count
up 41.6% YoY, 27% of the float sold short, and an 87% ATM implied vol, and
this is a levered call on GPU rental pricing holding through 2029, not a
business a reverse DCF can price today.

**Closest attack:** the residual-value condition (5) is *possible*-tier and
load-bearing at the same time. A possible-tier condition may not carry a
base case; strip it out and the contracted cash flows alone return the
capital, not a return on it. That leaves the buy case UNPROVEN on its own
terms; the FLAWED label comes from condition 3, refuted on the company's
own funding record — equity has been issued in every fiscal year since the
IPO ($6.39B cumulative, $4.75B of it in FY26) and the FY27 plan names
"corporate sources" for the $3–8B the debt and prepayments do not cover.

Load-bearing conditions (for the buy case a reader would need):

1. *probable* — Horizons 2–4 (150 MW IT) are delivered to and accepted by
   Microsoft in the December 2026 quarter. Evidence: Horizon 1 accepted
   August 2026; H2 commissioning, H3–4 "late-stage construction" (10-K,
   call); grace periods run mid-Q4 2026 to early Q2 2027, so a slip is a
   shift, not a break.
2. *probable* — AI Cloud segment gross margin holds ≥80% as the fleet
   scales. Evidence: FY26 AI Cloud revenue $128.8M vs cost of revenue
   $16.9M (87%); Q4 $70.5M vs $9.2M (87%) — press release tables.
3. *plausible* — the FY27 funding gap (guided capex $25–30B vs $14B cash +
   committed GPU financing + prepayments) closes on GPU/data-center debt and
   prepayments, not a dilutive equity raise. Evidence for: $6.5B of GPU
   financing in three months, 6% (IG, Microsoft) and 9% (Blue Owl/PIMCO,
   non-IG). Evidence against: $2.5B drawn on the $6B ATM by 2026-08-14,
   $4.75B of shares issued in FY26, 100% of data centers still unencumbered
   because the DC-financing market "hasn't started" (co-CEO, Q&A).
4. *plausible* — contract pricing of $20–25M/MW (IT) holds for the 2027 and
   2028 capacity now being negotiated. Evidence: management's own statement
   that 3-year pricing is +125% since November 2025; no third-party
   corroboration, and public H100 on-demand rates run $1.49–$6.98/hr across
   providers (low-confidence colour, §7) — a market that is tight at the
   frontier and soft on prior generations at the same time.
5. *possible* — a GB200/GB300 fleet re-contracts in years 4–5 at enough of
   its initial rate that the owner earns a return *on* capital, not just
   *of* it. No evidence either way exists; the 10-K's own Item 1A says the
   opposite may happen ("pricing for services delivered on older
   generations of hardware may decline"). This is the equity.

**Dominant shared risk factor:** AI-compute capex pace (hyperscaler and
frontier-lab spend on rented GPU capacity continuing to grow through 2028) —
shared by 0 of 17 held names (INTU's factor, generative-AI substitution of
paid software, fails in the opposite scenario; CAH, KTB, ZTO fail on
unrelated factors) · 13 unlabelled (BR CI EEFT G HIG LOPE MORN ORI PAGS PRI
SAP WRB YOU).

## 2. Business

**Created:** a customer — Microsoft, NVIDIA, Cohere, Perplexity, Figure AI,
Together AI, an unnamed frontier lab — gets a commissioned, liquid- or
air-cooled NVIDIA cluster (GB200/GB300 NVL72, Blackwell Ultra) on a
dedicated, powered site months or years sooner than it could permit, connect
and build one itself. The scarce input is the energized megawatt, not the
GPU: IREN locked ~2.9 GW of grid connections (Childress and Sweetwater in
ERCOT West, three BC hydro sites, Kiowa OK, Bundey SA, Badajoz ES via
Nostrum) as a bitcoin miner between 2019 and 2024, and is converting them.
Buyers reveal the surplus by prepaying 45–55% of GPU capex up front.

**Captured:** three distinct mechanisms, not one. (a) Bare-metal GPU rental
on 3–5 year take-or-pay contracts, priced per GPU-hour, quoted by management
at >$20M/MW-IT/yr on recent 3-year deals ($4B "contracted ARR" for the
2026 fleet; $1B operating today after Horizon 1). (b) Customer prepayments
and 90%-LTV GPU financing that shift the working-capital burden to the
customer and the lender — the deferred-revenue balance went from $46M to
$1.84B during FY26, and the co-CEO's own framing is that customers are
"starting to finance our build-out for us". (c) A managed-services and
orchestration layer (Mirantis, acquired FY26; NVIDIA-certified hypervisor)
sold above bare metal to smaller AI developers — the stated path to
on-demand pricing and to "monetize higher on the stack". Bitcoin mining
($578M of FY26's $707M revenue) is being decommissioned by December 2026
and is the source of the $639M FY26 impairments; it is a run-off, not a
segment to value.

**Protected:** the moat, such as it is, is an energized-site portfolio with
multi-year interconnect lead times, a delivered reference design (Horizon
1, NVIDIA Exemplar Cloud status), and a growing customer base with MSAs.
That protects the *2026–2028 capacity*; it does not protect the *price*.
Every layer IREN owns is also rented by CoreWeave, Nebius, Crusoe, Lambda,
Nscale, and the hyperscalers themselves (10-K competition paragraph), the
GPUs are the same NVIDIA parts on the same lead times, and there is no
disclosed switching cost beyond the contract term. Texas's new
interconnection scrutiny (Governor Abbott's directive, Q&A) raises rivals'
cost of *new* power; it does nothing to raise the price of a GPU-hour in
2029. Honest answer: the site portfolio is a real, time-limited advantage;
the GPU fleet is a commodity that depreciates.

**Control:** one class of Ordinary shares, 394,058,648 outstanding at
2026-08-14, plus one B Class share each held by co-founders/co-CEOs Daniel
and William Roberts carrying 15 votes per Ordinary share they hold until
the earlier of retirement from the board or 2033-11-17. The 10-K says
their aggregate vote is "less than 50%" but "a substantial proportion",
and the board granted each of them 9,099,328 RSUs in July 2026 (18.2M
total, 4.6% of shares) that will push it up. Practically: an unsolicited
takeover or an activist path requires the founders' consent, and the
founder options struck at $75 (2.4M each, 12-year term) tell you what
price they are paid to reach. The FY26 proxy (due by late October) is
where the exact vote share will appear — UNKNOWN 3.

**Operating leverage (Phase 0): negative.** Revenue has grown 12× over four
fiscal years while operating income went from roughly breakeven to a
$379M loss (ex-impairment; $1,047M reported):

| FY (June) | revenue | op. income (SA basis) | reported op. income | SBC |
|---|---|---|---|---|
| 2022 | $59.0M | +$0.5M | — | $13.9M |
| 2023 | $75.5M | −$40.5M | — | $14.4M |
| 2024 | $187.2M | −$27.3M | — | $23.6M |
| 2025 | $501.0M | +$20.6M | +$17.3M | $42.6M |
| 2026 | $707.0M | −$378.8M | −$1,046.7M | $205.0M |

The FY26 quarters run the same direction: revenue $240M → $185M → $145M →
$137M as miners are switched off ahead of GPUs, opex $220M → $204M → $198M →
$245M as headcount triples ahead of revenue. Management guides Q1 FY27 cash
SG&A up another $40–50M sequentially. Stock compensation is charged on the
income statement ($205M, 29% of revenue) and added back in the cash flow.

## 3. Threads pulled

- **Why is revenue falling in a company that just contracted $4B of ARR?**
  Because ARR is an operating metric on *commissioned GPUs under contract*,
  and the press release's own footnote says "recognized revenue may be
  materially lower". Q4 AI Cloud revenue was $70.5M ($282M annualized)
  against "$1B operating ARR today"; the gap is Horizon 1, accepted in
  August, i.e. after the quarter. Meanwhile mining revenue fell $44M QoQ
  as sites were converted. The CFO says the December-quarter capacity
  lands "late in the quarter", so the reported-revenue step-up is a March
  2027 quarter event. Finding: the P&L will lag the ARR headline by two
  quarters, and the company knows it.
- **The −$684M quarter.** Non-cash: $450.4M impairment (decommissioned
  miners), $102.1M fair-value write-down of miners held for sale, $25.1M
  loss on disposal. Cash SG&A and D&A were $128M and $112M against $137M of
  revenue. Adjusted EBITDA fell to $19.2M (14% margin) from $59.5M. FY26's
  net loss of $703M would have been ~$1.26B without a $558.5M unrealized
  *gain* on the capped-call derivatives that hedge the converts — a
  mark-to-market on IREN's own stock volatility, not an operating item.
- **The balance sheet moved more than the P&L.** Debt principal $7.71B at
  June 2026 vs $0.99B a year earlier: $6.75B of converts (0%–3.5% coupons,
  2029–2033), $0.94B drawn of the $3.65B non-recourse Microsoft GPU
  facility (SOFR+225 DDTL / 7.05% USPP notes, inside an SPV whose
  creditors have no recourse to the parent except tranche-level guarantees
  that fall away on Microsoft's acceptance). Post-quarter: the $2.4B Blue
  Owl/PIMCO 9% facility for Mackenzie (Note 30, 2026-08-25) and a further
  $0.4B of non-IG equipment financing. Cash $5.90B of which $1.67B is
  restricted for Microsoft GPU capex. Commitments: **$13.81B** of
  contracted capex at June 30 (vs $369M a year earlier), *excluding*
  hardware agreements signed after June 30 — Dell NCNR purchase agreements
  are listed as exhibits. This is the commitments footnote the skill says
  to read before trusting an "asset-light" claim; here nobody claims one.
- **FY27 funding gap.** CFO: capex $25–30B; secured $14B (cash + committed
  GPU financing + prepayments); target a further ~$8B of GPU financing and
  prepayments; "the balance" from data-center financing, operating cash
  flow and "corporate sources". Arithmetic: $25–30B − $14B − $8B = $3–8B
  still to be found, on a data-center asset base that has never been
  financed (100% unencumbered — management calls it an opportunity; a
  lender would call it untested) plus the $3.5B of undrawn ATM. Share
  count: 258M → 381M during FY26 (+47.5%), 394M by August. Thread
  outcome: dilution is the residual funding source and is not optional.
- **Customer concentration and what Microsoft can do.** Microsoft $9.7B
  and NVIDIA $3.4B TCV "together represent a substantial majority of our
  contracted revenue" (10-K). If Microsoft validly terminates a funded
  tranche and no replacement customer is found in the remarketing period,
  the *parent* guarantees the tranche's debt net of GPU sale proceeds. The
  guarantee is released tranche by tranche on acceptance, so Horizon 2–4
  delivery in the December quarter is what retires it. A delay past the
  grace window (early Q2 2027) is a contractual, not merely operational,
  event.
- **Insider and ownership filings since the call.** Seven Form 4s dated
  2026-07-01 are RSU/award grants at $0 (CFO +26,968; director
  +8,369 — checked two; the rest share the filer agent and date). No open-
  market sales found in the recent index. Form D 2026-08-18 and 424B7
  2026-08-04 are, respectively, a private placement notice and a resale
  prospectus consistent with the Blue Owl notes and acquisition-share
  registration — not read in full (UNKNOWN 4). Nothing filed after the
  10-K on 2026-08-27; the post-call event set is the Blue Owl press
  release (2026-08-28) and the stock's −12.5% reaction on the revenue
  print.
- **Pricing claims vs the market.** Management: 3-year pricing +125%
  since November, recent deals >$20M/MW, live talks ~$25M/MW, "consistent
  across live conversations". Public colour (low-confidence): H100
  on-demand rates span $1.49–$6.98/hr across 15+ providers; CoreWeave
  H100 $6.16/hr vs Nebius $3.85/hr; GB300 is contact-sales at CoreWeave and
  publicly priced only at Nebius. A tight frontier-generation market and a
  loose prior-generation one is exactly the shape that makes condition 5
  the thesis. Dead end for corroboration: nothing published prices a
  5-year Blackwell contract per MW.
- **Transcript corpus.** 19 calls, 2022-02-09 → 2026-08-27, 0.23
  uncovered years since the 2021-11-17 IPO — coverage ≈ company history,
  so silence would be meaningful; it was not needed, because the Q4 call
  and the 10-K are the current-state sources and were read in full.
- **Options read (mandatory):** path 2 only (IREN is not in the CBOE
  24-symbol catalog; `data/options.db` has no history for it). 2026-11-20
  expiry, 80 DTE, brackets both the Nov 5 print and most of the
  Horizon 2–4 delivery window. Table in §4. ATM IV 87% → all return figures
  in this document are quoted to the whole percent.
- **Dead ends:** `sec_fundamentals.db` `v_screener` carries one quarter
  (Q3 FY26 revenue $144.8M, net loss $247.8M) — it matches the 10-Q, rules
  nothing out. `stocks.db` is a day stale (price $35.45 vs $37.12 close)
  and agrees on shares and debt. Robinhood's trailing EPS actuals
  (−0.74 Q4, −0.327 Q3, −0.52 Q2, +1.08 Q1 FY26) match the 10-K/10-Q
  diluted EPS to the cent except Q4 (−0.74 vs −1.88 GAAP — Robinhood is
  quoting an adjusted figure; the definition switch this repo has seen
  before). Pattern: four straight misses on the estimate side since the
  transition started, which reads as the sell side under-modelling
  opex growth, not as managed guidance. The `/metrics/` route returned
  `{info}` (no segment breakdown served); `/filings/` returned no page
  data. Neither changes anything above.

## 4. Valuation

Inputs (statistics-probe `hover`, 2026-09-01): market cap $14,625,486,721;
enterprise value $16,569,421,721; TTM `fcf` −$2,232,669,000 (ncfo
+$2,100,418,000 + capex −$4,333,087,000); TTM net income −$702,621,000; SBC
$205.0M; D&A $417.1M; shares 394,058,648; beta 4.30. The ncfo figure is
itself $1.84B of customer prepayments (deferred revenue) — cash the company
must still earn — so the owner cash flow before growth capex is nearer
+$0.26B, and after the $4.33B of capex it is −$2.2B. Levered flow ↔ market
cap pairing; net debt 0 by the pairing rule. No minority interests
(Financing SPV is wholly owned and consolidated).

Hurdle: rf 4.74% + beta × ERP 4.28% (Damodaran, 2026-08-01). At the printed
beta of 4.30 the hurdle is **23.1%**; clamped to the top of the 0.8–1.2
stable band it is **9.88%**. Both are stated because the truth sits between
them: a 4.3 regression beta on a stock that traded like a bitcoin miner for
three of the four years in the window overstates the forward equity risk,
but 1.2 for a company with $7.7B of debt, an 87% implied vol and one
customer for most of its backlog understates it. Country ERP: operations
are US (Aa1, 4.46%) and Canada/Australia (Aaa, 4.23%) per the January 5,
2026 vintage — an operations-weighted premium lands within 0.2 points of the
headline 4.28% either way, so the headline is used.

`reverse_dcf` refuses the input: `refused: base_fcf must be positive, got
-2232669000.0` (exit 2). The honest substitute is the inversion — what
perpetual owner FCF the price already assumes — and the company's own unit
economics laid against it:

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| reverse DCF, TTM FCF | −$2.23B | n/a | n/a | **refused** (exit 2) | n/a |
| inversion, band-clamped hurdle | $1.15B needed, perpetual | 0% | 2% | 10% by construction | 0 bp at 9.88% |
| inversion, printed-beta hurdle | $3.09B needed, perpetual | 0% | 2% | 23% by construction | 0 bp at 23.1% |
| inversion, no growth ever | $1.44B / $3.38B needed | 0% | 0% | 10% / 23% | 0 bp |

What the unit economics say about reaching those numbers: at >$20M/MW-IT
revenue, ~2-year GPU payback (press-release definition: GPU capex ÷
(revenue − direct costs)), and GPUs ≈ two-thirds of all-in capex (co-CEO,
Q&A), a megawatt costs ~$45–50M all-in and throws off ~$15–17M/yr of
contribution — so a **3-year contract returns ~1.0× all-in capital before
financing cost (6–9% on 90% of GPU capex ≈ $2–3M/MW/yr) and before SG&A**.
The 2026 fleet ($4B ARR on ~300 MW IT = $13.3M/MW — below the $20M quoted
for new deals, because the Microsoft pricing was struck in November 2025)
therefore produces the *return of* the ~$14B it cost, spread over
2027–2029, and the *return on* it comes from years 4–5 and re-contracting.
$1.15B of perpetual owner FCF is ~29% of $4B ARR, after D&A on a GPU fleet
the 10-K depreciates against "expected utilization and technological
developments" and after $449M (FY26) of SG&A that is guided higher. It is
reachable only if condition 5 holds, and condition 5 is the disclosed
terminal risk.

Integrity checks:

- **Reinvestment / terminal ROE warning:** not reached — the tool refused.
  The equivalent question is answered above: growth here is entirely
  reinvestment-funded, at $25–30B for one year against $4B of ARR — a
  sales-to-capital ratio well under 1 during the build, which is what the
  refusal is telling you.
- **Market-share sentence:** $4B of ARR from "less than 10%" of a 5 GW
  pipeline (co-CEO) implies management's own end state is >$40B of ARR —
  roughly the size of the entire neocloud segment as it exists today, and
  larger than any single competitor's disclosed contracted backlog. That
  is the "bigger than the market" shape unless the market itself grows
  several-fold, i.e. condition 4 and the dominant risk factor.
- **Terminal growth vs Item 1A:** the disclosed terminal risk is hardware
  obsolescence — "the economic useful life and residual value of our
  deployed equipment may be shorter or lower than we anticipate, pricing
  for services delivered on older generations of hardware may decline".
  A 2% terminal rate survives it only if the *sites* (not the GPUs) are the
  terminal asset and re-fill at each generation; the inversion above uses
  2% and 0% for that reason.
- **Distribution clamp:** the printed-beta hurdle (23%) sits far above the
  US 90th-percentile cost of capital (9.88%, 2026 Data Update 5). Even at
  the band-clamped 9.88% the price needs owner FCF the company has never
  earned in any year (best: FY25, FCF −$1.13B). Strong pass on the clamp
  alone.
- **Base-year cash taxes:** immaterial (FY26 cash taxes $2.7M; NOLs and
  losses mean the base is not flattered — there is no positive base).
- **SBC:** $205M FY26 (29% of revenue) plus 18.2M RSUs granted to the
  co-CEOs in July 2026 and 2.4M founder options each at $75 — any future
  positive FCF should be read net of ≥$200M/yr before pairing with market
  cap.
- **Leverage gate:** net debt ~$1.9–2.1B against EV $16.6B (~12%), book
  equity +$4.19B, no going-concern language (the only "going concern"
  string in the 10-K is boilerplate about bitcoin regulation). The gate
  does not fire, so the `equity_option` lens is not run — but note the
  structure it would model is already in the filing: the Microsoft GPUs sit
  in a non-recourse SPV, $6.75B of converts sit at the parent, and the
  converts' capped calls mark to IREN's own vol. Equity here behaves like
  an option on GPU pricing without needing the Merton frame to say so.

Options-implied move — path 2 (Robinhood stopgap), 2026-11-20 expiry, 80
calendar days from 2026-09-01 (Phoenix), brackets the 2026-11-05 print and
the December-quarter Horizon 2–4 deliveries up to Nov 20. ATM strike $37
(spot $37.115): call mark $6.175 (IV 0.868), put mark $5.80 (IV 0.874), mean
IV 0.8710. Closes: 91 daily bars 2026-04-22 → 2026-08-31 (split-adjusted).

| metric | value |
|---|---|
| spot | 37.12 |
| expected absolute move | 32.26% (MEAN, not a ceiling) |
| 1-σ move | 40.78% |
| ATM IV | 87.10% |
| RV60 | 118.18% |
| RV20 | 89.97% |
| IV > RV60? | NO |
| IV > RV20? | NO |

Liquidity gate: call spread $6.00/$6.35 (5.7% of mark, under the 10% gate),
OI 439, volume 185; put spread $5.60/$6.00 (6.9%), OI 3,752, volume 29 —
the put fails the same-day volume floor (<100) but its OI is far above any
plausible 25%-of-median threshold, so the gate PASSES on OI; treat the pass
as unverified per the shared reference's uncalibrated-constants note.
Timing check: NOT APPLICABLE — this thesis states no required move; the
table is reported because IV below both realized windows is itself the
finding: the market is *not* pricing an event premium into the delivery
window, it is pricing a stock that has realized 118% vol over 60 days. No
`--required-move` was passed; nothing here refutes or supports any dated
condition, and by the one-way-valve rule it could not support one anyway.

## 5. Falsifiers

For the pass (flip toward buy):

- **Shift —** two consecutive quarters of positive owner FCF *after*
  maintenance capex and *before* customer prepayments (i.e. ncfo net of the
  deferred-revenue change, minus GPU-refresh capex) at or above a
  $1.15B/yr run-rate, with the FY27 funding gap closed without ATM
  issuance. That is the inversion's number appearing in GAAP.
- **Shift —** a disclosed re-contracting of a ≥3-year-old GPU cohort (any
  generation) at ≥50% of its initial per-GPU-hour rate — the first tangible
  evidence for condition 5. Would move it from *possible* to *plausible*.
- **Shift —** a data-center-level financing (the unencumbered $6.76B of
  PP&E) at an IG-adjacent rate, which would prove the "third leg" of the
  funding flywheel management describes but has not closed.

For an owner (sell):

- **Break —** Horizon 2, 3 or 4 not accepted by Microsoft by the end of the
  contractual grace window (early Q2 2027), or any Microsoft tranche
  termination triggering the parent guarantee. The backlog and the
  financing are one structure; this breaks both.
- **Break —** a reported quarter in which contracted new-deal pricing
  ($/MW-IT, 3-year) is disclosed below the FY26 level (~$13M/MW, the
  Microsoft-vintage rate) — that is the residual thesis inverting before
  the fleet is even three years old.
- **Shift —** FY27 capex funded more than ~25% by equity (ATM or
  registered direct), or the share count exceeding ~475M by June 2027
  without a corresponding ARR increase — dilution ahead of revenue.
- **Shift —** AI Cloud segment gross margin below 80% for two quarters
  (condition 2), or adjusted EBITDA negative on a full quarter of Horizon
  1–4 revenue (March 2027 quarter).

**Reopen trigger:** 2027-02-04: iren-q2fy27-print-horizon-2-4-acceptance-
and-owner-fcf-net-of-prepayments — the first print that carries a full
quarter of Horizon 1 and the December-quarter deliveries; it settles
conditions 1 and 2 and puts a GAAP number against the ARR headline.

## 6. UNKNOWNs

1. **Terms of the frontier-lab contract** (counterparty, MW, term, price,
   prepayment). Source: the Q1 FY27 10-Q (November) or an 8-K if material.
   Does not kill the pass; it would matter for a buy because it is the only
   non-Microsoft/NVIDIA anchor of size.
2. **Actual $/MW and prepayment on the Microsoft and NVIDIA contracts**
   versus the >$20M/MW quoted for new deals. The $4B-on-300 MW arithmetic
   gives ~$13M/MW blended, but the split is undisclosed. Source: nothing
   public; triangulate from segment revenue once Horizons 1–4 are the
   whole fleet (March 2027 quarter). Bounded: $9.7B ÷ 200 MW ÷ 5 yr ≈
   $9.7M/MW/yr for Microsoft — which is *below* the blended figure, so the
   quoted uplift on new deals is credible in direction. Does not kill the
   pass.
3. **Founders' exact voting share** after the July 2026 RSU grants. Source:
   the FY26 proxy, due by ~2026-10-28. Does not kill anything; it is the
   control line's precision.
4. **Contents of the 2026-08-18 Form D and 2026-08-04 424B7** — assumed to
   be the Blue Owl notes and acquisition-share resale; not read. Source:
   the filings themselves. Low stakes; the 10-K's Note 30 covers the debt.
5. **Residual value of a Blackwell-generation GPU at year 4** — the
   condition-5 number. Source: does not exist yet anywhere; the first
   H100 cohorts (2023 vintage) reach year 4 in 2027 industry-wide, and
   their re-contract rates are the earliest proxy. Its absence is what
   makes the buy case UNPROVEN-at-best and, combined with the price, FLAWED.

## 7. Sources

- **Primary:** IREN FY26 Form 10-K (filed 2026-08-27, accession
  0001878848-26-000052) — debt note (Note 23 table: converts by series,
  DDTL/USPP, $7,705.6M principal), Note 30 subsequent events (Blue Owl/
  PIMCO $2.4B, 2026-08-25), contractual obligations ($13,810.0M
  commitments), Item 1A obsolescence and customer-concentration risk
  factors, B Class share provisions, Financing SPV/VIE note, ATM usage
  (47.2M shares / $2.5B to 2026-08-14), power-cost sensitivity (27% of
  revenue), Microsoft/NVIDIA TCV. 8-K Ex-99.1 "IREN Reports FY26 Results"
  (2026-08-27) — segment revenue/cost tables, adjusted EBITDA
  reconciliation, ARR definitions and footnotes. Forms 4 (2026-07-01,
  CFO and a director — award grants). FY26 Q4 earnings call 2026-08-27
  (primary, transcribed via stockanalysis/Quartr — prepared remarks and
  Q&A read in full).
- **stockanalysis.com (vetted exception):** `/stocks/IREN/statistics/`
  (market cap, EV, fcf, ncfo, capex, debt, cash, shares, beta, short
  interest, analyst count/target), `/financials/income-statement/`,
  `/cash-flow-statement/`, `/balance-sheet/` (annual + quarterly FY22–FY26),
  `/transcripts/` index (19 calls) and the Q4 FY26 detail, `/symbol-lookup/`.
- **Broker/market microstructure:** Robinhood MCP — `get_equity_quotes`
  (close $37.115, pre-market), `get_option_chains` / `get_option_instruments`
  / `get_option_quotes` (Nov-20 $37 straddle, IV, OI, spreads),
  `get_equity_historicals` (91 daily closes for RV), `get_earnings_results`
  (estimate-vs-actual pattern; next date 2026-11-05 unverified),
  `get_equity_news` (post-call headline sweep). Admissible: no integrated
  official source covers live quotes, option chains, or consensus estimates
  for this ticker; `get_financials` not used.
- **Reference data:** Damodaran implied ERP 4.28% and 10Y 4.74% (2026-08-01);
  country ERP table (last updated 2026-01-05: US 4.46%, Canada/Australia
  4.23%, Spain 5.78%); cost-of-capital distribution (2026 Data Update 5,
  median 7.79%, 80% band 5.26–9.88%).
- **Point-in-time repo DBs:** `stocks.db` v_latest (2026-08-28 capture:
  price $35.45, cap $13.97B, EV $15.91B, ipoDate 2021-11-17, next earnings
  2026-08-27 amc), `sec_fundamentals.db` v_screener (Q3 FY26 row only),
  `composite.db` ticker_scores (2026-08-28: 1/0/2, unflagged),
  `earnings.db` calendar_now 2026-08-31 (no upcoming IREN row),
  `options.db` (no IREN history → path 1 unavailable), `portfolio.db`
  v_latest_positions (17 held symbols for the factor overlap).
- **Low-confidence:** web colour on GPU rental pricing (SemiAnalysis
  H100 rental index; Spheron, IntuitionLabs, Thunder Compute, MarkTechPost
  price comparisons, Aug 2026); Blue Owl press release coverage (Yahoo
  Finance / PRNewswire, 2026-08-28); Benzinga/MT Newswires post-print
  headlines. None of it is load-bearing.

## Kill-thesis record

`2026-09-01 IREN FLAWED conditions=5 refuted=1 unknown=2
reopen=2027-02-04:iren-q2fy27-print-horizon-2-4-acceptance-and-owner-fcf-net-of-prepayments
(PASS)`. Five conditions for the buy case were enumerated in §1 and
attacked independently; the ownership call is PASS and the attack ran
against the case a buyer would need, not against the pass.

Per-condition adjudication:

1. Horizon 2–4 accepted in the December quarter — **SURVIVED.** Attack:
   Horizon 1 itself slipped on NVIDIA component shortages (10-K Item 1A
   says so in terms), so the delivery record is one-for-one late, not
   one-for-one on time. It stands because the contract carries a grace
   window to early Q2 2027, H1 is accepted, and H2 is in commissioning;
   a slip inside the window is a shift. Evidence against acceptance
   itself: none found.
2. AI Cloud segment gross margin ≥80% — **SURVIVED**, with the caveat that
   it is the wrong margin. Attack: segment cost of revenue excludes D&A
   (10-K Note 5 / CODM definition), so 87% is a pre-depreciation number
   on a fleet whose useful life is the disclosed terminal risk; power at
   ~$40/MWh on ~1.4 MW gross per MW IT is ~2–3% of $20M/MW revenue, so
   the ex-D&A margin is credible and the condition holds as written.
   Nothing in the buy case may be valued on it.
3. FY27 funding gap closes without a dilutive equity raise — **REFUTED.**
   Attack: the company's own record. Ordinary shares issued for cash in
   every fiscal year since listing — FY22 $215M, FY23 $39M, FY24 $783M,
   FY25 $602M, FY26 $4,749M (stockanalysis cash-flow statement, agreeing
   with the 10-K's $4,742.8M) — $2.5B of the $6B ATM used between March
   and August 2026, and the CFO's funding plan naming "corporate sources"
   for the residual after $14B secured and ~$8B targeted against $25–30B
   of capex. Internal-consistency attack also lands: the thesis pairs
   maximal growth (5 GW pipeline, capex ≈ 6× ARR in one year) with
   equity-light funding, and g = reinvestment × return does not allow
   both when the data-center leg has never been financed. Repairable
   only by restating the buy case per share after an assumed raise —
   which is what §4's inversion already does, and it still fails.
4. $20–25M/MW pricing holds for 2027–2028 capacity — **UNKNOWN.** Attack:
   disconfirming search found only on-demand H100 dispersion
   ($1.49–$6.98/hr, low-confidence) and no published multi-year Blackwell
   per-MW rate from any counterparty; management's +125% claim is
   uncorroborated but also uncontradicted. The evidence needed — a
   third-party contract print — does not exist in any disclosure.
5. Year-4+ re-contracting yields a return *on* capital — **UNKNOWN**, and
   load-bearing, which is the structural kill. Attack: no
   Blackwell-generation fleet is four years old anywhere; the earliest
   proxy (2023 H100 cohorts) reaches year four in 2027. The 10-K's own
   Item 1A states the direction of risk ("pricing for services delivered
   on older generations of hardware may decline"). A *possible*-tier
   condition cannot carry a base case; without it the contracted flows
   return ~1.0× all-in capital and the equity value is undefined.

Standing checks:

- **Base rate.** Only ~29% of firms earn above their cost of capital
  (Damodaran EVA dataset), so "the excess return persists into the
  re-contracting years" starts as a 3-in-10 proposition. Narrower: the
  company's own five-year record is one profitable year (FY25, +$86.9M)
  against four losses summing to −$1.32B, and negative FCF in every year.
  First-wave builders of demanded infrastructure (fibre 1999–2002) were
  right about demand and wrong about equity returns; that is the
  reference class, not "AI wins".
- **The short case** (27.2% of float short, 1.96 days to cover): GAAP
  revenue lags ARR by two-plus quarters while capex runs $6–7B a quarter;
  $11–16B of FY27 funding remains to be found with the ATM as the proven
  residual; $6.75B of converts overhang a 394M share count; Microsoft is
  most of the backlog and the parent guarantees its tranches until
  acceptance; no positive owner FCF has ever been printed; and the price
  needs $1.1–3.1B of perpetual FCF from a fleet whose residual is
  unknown. It is the strongest version, and it is the pass.
- **Management incentives.** Co-CEOs each granted 9.1M RSUs in July 2026
  (vesting terms in the pending proxy — UNKNOWN 3) on top of 2.4M options
  each struck at $75 with a 12-year term; the B Class shares carry 15
  votes each until 2033. The incentive set rewards scale and share price,
  not per-share FCF or issuance discipline. The buy case's condition 3
  assumes discipline the incentives do not pay for. Attack lands.
- **Disconfirming search.** Ran against the rival and the market, not
  the company: neocloud pricing colour (mixed), Blue Owl deal coverage
  (confirms the 10-K), Form 4s (grants, no sales), post-10-K filings
  (none). Nothing found that management's framing suppresses, and
  nothing that corroborates the pricing claim either.
- **Moat: checkbox or mechanism?** The energized-site portfolio is a
  mechanism (interconnect lead times, Texas scrutiny of new projects)
  and it is time-limited to the 2026–2028 build. The GPU layer is a
  checkbox: same NVIDIA parts, same lead times, no switching cost past
  the contract term, and the 10-K lists seven named competitors on every
  layer.

Statistical checks: N/A — no backtest, hit rate or repo signal is claimed;
composite is unflagged on the name.

Options-market timing check: applicable in principle (dated claims —
Horizon 2–4 in the December quarter, print 2026-11-05 — and a listed
chain) and run on **path 2 only** (no `options.db` history; the stopgap).
2026-11-20 expiry, 80 DTE, ATM IV 87.1%, 1-σ move 40.8%. No
`--required-move` was passed because the thesis states no required move,
so the CLI printed no refutation row and none is claimed. Liquidity gate
passed on OI (call OI 439 / put OI 3,752; put same-day volume 29 fails the
volume floor alone) — a pass, but an uncalibrated one. IV below RV60
(118%) and RV20 (90%) is reported as a finding, not as support for
anything.

**Closest attack:** condition 5 — the equity is the residual value of a
GPU fleet after its first contract, the number does not exist, and the
10-K says its direction is down. It did not "land" as a refutation only
because the evidence is absent rather than adverse; that absence is what
makes the buy case unprovable at this price.

**Flip evidence:** to SOUND — a disclosed year-4 re-contract of any GPU
cohort at ≥50% of its initial rate *and* the FY27 build funded with equity
at ≤25% of the raise, both visible by the 2027-02-04 print; or, more
slowly, two quarters of positive owner FCF net of prepayments at a
≥$1.15B run-rate. To dead (from FLAWED) — a Microsoft tranche termination
or a Horizon acceptance missing the early-Q2-2027 grace window, or a
disclosed new-deal rate below the FY26 blended ~$13M/MW.
