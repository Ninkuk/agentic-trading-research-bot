# SIEGY — Siemens AG (ADR, 2 ADRs = 1 ordinary share) — 2026-08-24

Price $163.30 (Robinhood last trade, 2026-08-24 regular close; official close
$163.30) · market cap $251.46B (stockanalysis `marketcap` hover, Xetra-priced;
~$255B at today's ADR print) · EV $305.0B (gross debt $57.0B incl. Siemens
Financial Services funding; Industrial net debt €9.3B) · next earnings
~2026-11-12 (Q4 FY26; date not yet confirmed by the company — FY25's Q4 came
2025-11-13).

Entry path: user-directed (`/research-ticker SIEGY`). Non-US `/quote/otc/`
listing: `stocks.db`, `sec_fundamentals.db`, `composite.db` and `earnings.db`
carry no row for it; the live stockanalysis probe, Siemens' own earnings
releases and the Q3 FY26 call transcript are the structured sources. No prior
thesis.

## 1. Verdict and thesis

**PASS at $163.30.** kill-thesis: **SOUND (on this pass)** — conditions=4
(3 probable, 1 plausible), refuted=0, unknown=0.

Siemens is a genuinely good industrial: the world's largest factory-automation
and PLM/EDA software franchise, a switchgear and building-electrification
business riding the data-center build-out (9M FY26 data-center orders ~€6B,
revenue +50% to €3.1B), a rail business with a €58B backlog, and a record
€132B group backlog at book-to-bill 1.34. Q3 FY26 was a record on every
line and guidance was raised. But at $163.30 the equity already prices a
7.2–8.8% annual return on FCF paths from 3% to 8% growth, against a cost of
equity of 10.6–11.0% (rf 4.52% + beta 1.2–1.29 × operations-weighted ERP
5.07%) — and still short of Damodaran's mature-company companion (rf + 4.5%
= 9.0%) on every path. A haircut the naive read skips — one-third of
Healthineers' €3.4B TTM FCF belongs to minority holders — is worth ~60bp of
implied return on its own. The base case meets the hurdle only near a $172B
market cap (~$112/ADR), 31% below today. Good business, full price: pass.

**Closest attack:** "The hurdle is wrong, not the price — a 1.29 beta on a
diversified Aaa-domiciled industrial is a regression artefact, and the
operations-weighted ERP (5.07%) double-counts country risk that the beta
already carries. At beta 1.0 on the US ERP the hurdle is 8.8% and the
optimistic path clears it." True at the optimistic path only: base-case
6% growth at beta 1.0 / US ERP 4.28% implies 7.9% vs an 8.8% hurdle, still
−90bp; and the optimistic path needs 8% FCF growth for five years plus
2.5% terminal on a business guiding 6–8% revenue growth with margins
already at the top of their medium-term bands. The attack narrows the
spread; it does not turn it positive on the base case.

Load-bearing conditions for the pass:

1. *probable* — At $163.30 the implied equity return is below the hurdle on
   every FCF path modelled: 7.19% (3% growth), 7.91% (6%), 8.81% (8%/2.5%
   terminal), vs 11.03% at beta 1.285 and 10.60% at beta 1.2. Even the
   un-haircut stockanalysis `fcf` ($13.54B) only reaches 8.52%.
2. *probable* — Consolidated `fcf` overstates the owner's flow: Siemens owns
   ~67% of Healthineers, whose TTM FCF is €3,409M (FY25 €3,315M − 9M FY25
   €2,293M + 9M FY26 €2,387M, Siemens segment tables), so ~€1.1B ($1.3B) of
   the group FCF is the minority's. SBC is a further, unquantified deduction
   (UNKNOWN 1).
3. *probable* — Q3's record 17.3% Industrial Business margin carries
   non-recurring US tariff refunds (SI net +50bp after an e-mobility
   impairment; Healthineers' 18.2% "due primarily to positive effects from
   tariff refunds"); DI margin was flat q/q and is guided 17–19%. The
   run-rate margin is below the headline, so the base FCF is not
   understated.
4. *plausible* — Growth cannot rescue the price: management's own ceiling is
   6–8% group revenue growth (raised only at SI, to 10–11%); DI Q4 orders
   are guided flat on tough EDA comps; data-center orders are explicitly
   "lumpy"; China automation growth (orders +17–20%) is a K-shaped recovery
   the CEO said "slowed a bit in June". An 8% five-year FCF path is already
   the optimistic case, and it fails the hurdle.

**Dominant shared risk factor:** global industrial-capex and AI-infrastructure
build-out pace (data-center electrification, semiconductor fab automation,
China machinery cycle) — shared by 0 of 17 held names (CAH: US brand-drug
pricing; KTB: US lower/middle-income consumer) · 15 unlabelled (BR CI EEFT G
HIG INTU LOPE MORN ORI PAGS PRI SAP WRB YOU ZTO have no factor line).

## 2. Business

**Created:** Siemens sells the hardware and software that lets a factory,
building, grid or railway run automatically and be designed digitally.
Digital Industries (DI, €14.1B 9M revenue) sells PLCs, drives and motion
control (SIMATIC/SINAMICS) plus PLM (Teamcenter, NX), simulation (Altair,
acquired FY25) and EDA (Mentor/Siemens EDA) software; the customer gets one
vendor from chip design to production line, a physics-based digital twin,
and a controller installed base that its engineers already know. Smart
Infrastructure (SI, €17.8B) sells low- and medium-voltage switchgear,
building automation and grid products — for a hyperscaler, the power train
from grid connection to rack (9 of the top 10 data-center providers are
customers, per the call). Mobility (€9.5B) sells trains, signalling and
service on 10–30-year contracts. Healthineers (€16.8B, 67% owned, being
spun) sells imaging, diagnostics and radiotherapy. Siemens Financial
Services finances customer purchases.

**Captured:** four distinct mechanisms. (a) Automation hardware sold through
distributors and OEMs at a premium, with a "value-for-money" China line
growing mid-20s; pricing power shown by a "net positive economic equation"
(price > cost inflation) every quarter of FY26. (b) Software: licence and
SaaS (transition "at the end of the belly of the fish"), 11% organic ARR
growth, DI software orders ~€1.7B in Q3; EDA revenue is the accretive mix.
(c) Project/product electrification: framework agreements with data-center
customers, backlog €23.7B at SI with ~€12B scheduled for FY27. (d) Service
and long-dated rail contracts: Mobility book-to-bill 2.35 in Q3 on a "high
share of attractive service contracts". Group profit Industrial Business
9M FY26 €9.4B at 16.1%; 9M FCF €6.5B, Q3 alone €4.1B (cash conversion 1.61).

**Protected:** the mechanism is the installed base plus the engineering
switching cost. A factory's PLC programs, drive parameterisation and PLM
data model are written against Siemens' toolchain (TIA Portal, Teamcenter);
replacing them means re-engineering and re-validating the line, so the
incumbent wins the retrofit and expansion orders at a premium. The EDA leg
is a three-player oligopoly (Synopsys, Cadence, Siemens) with multi-year
design-flow lock-in. In switchgear the moat is thinner — Schneider, ABB and
Eaton sell the same boxes — and rests on capacity, certification and
delivery reliability during a shortage; management concedes competitors'
data-center orders are "margin diluted by nature" is a live question (JPM,
Q3 call). Where the moat is absent it is stated: Mobility competes on
price against Alstom/CRRC/Stadler at 8–10% margins.

**Control:** one share, one vote; 800M registered shares, ~770M outstanding
after buybacks; no controlling holder. The Siemens family pool holds ~6% and
has a supervisory-board seat; BlackRock and other index holders are the
largest institutions. A €6B, five-year buyback launched July 2026 (€0.4B in
month one). Nothing forecloses a takeover except size (€220B+). The Feb 2027
AGM votes on the Healthineers spin-off.

**Operating leverage (Phase 0): positive.** Revenue FY21 €62.3B → TTM
€81.1B (+30%); operating income €6.4B → €10.0B (+56%); operating margin
10.3% → 12.4% (FY25's 11.5% dip reflects Altair/Dotmatics PPA and
integration costs, reversed in FY26). Net income to common €6.2B → €8.0B
TTM (FY25's €9.6B carried a €2.1B Innomotics disposal gain).

## 3. Threads pulled

- **Why the stock fell 5% on a record quarter (Aug 6, $165.50 → $156.89)
  and recovered to $163.30:** Bloomberg framed it as a "muted outlook
  raise" — investors wanted a bigger data-center read-through. The raise was
  EPS pre-PPA €10.70–11.10 → €11.20–11.50 (+€0.45 midpoint) with group
  revenue growth held at 6–8% "upper half"; DI guidance unchanged, only SI
  raised. Reading: the stock is priced for acceleration the guide did not
  deliver — consistent with §4's negative spread. Source: Q3 FY26 earnings
  release, call transcript; Bloomberg headline (low-confidence colour).
- **Healthineers deconsolidation:** Siemens (67%) will spin 30% of
  Healthineers directly to Siemens shareholders under the Umwandlungsgesetz,
  keep a "significant minority" and reduce it to a financial asset over the
  medium term. Binding tax rulings received (Q3 call); AGM votes of both
  companies Feb 2027; next steps with the Q4 release. For the equity this is
  value-neutral arithmetic (holders receive the SHL shares), but it removes
  ~€3.4B of consolidated FCF and ~€1.0B of segment profit from the
  reported group, and the 30% spun (~€16B at SHL's market cap) is ~6% of
  Siemens' market cap. ADR-holder mechanics — whether Deutsche Bank
  delivers SHL ADRs, ordinary shares or cash — are undisclosed (UNKNOWN 2).
- **Healthineers minority haircut (the §4 pairing):** Healthineers segment
  FCF TTM €3,409M; 33% minority claim ≈ €1,125M ≈ $1.29B at the 1.1425
  USD/EUR the probe embeds ($92.67B / €81.11B). The NCI net-income line
  (€0.93B TTM) is close to this because Healthineers' Varian PPA
  amortisation (€349M/yr, Siemens tables) depresses its GAAP income less
  than the skill's holdco warning anticipates; the cash figure is used.
- **Siemens Energy stake:** cut from 14.96% to 5.54% on 2026-04-02 (voting
  rights notice via TipRanks/MarketScreener; the pension trust no longer
  holds SE shares). `incomeEquity` TTM €0.55B still carries SE's
  contribution; it fades. A one-off, not a recurring FCF source — not in
  the base.
- **Siemens Financial Services:** €33.4B of total assets, EBT €468M 9M FY26
  with a €156M one-off gain from a UK equity sale in Q3; SFS is why gross
  debt is €50–57B while Industrial net debt is only €9.3B (0.6× EBITDA).
  Pairing rule: levered `fcf` ↔ market cap, net debt 0 — EV would double-
  count SFS funding. Not haircut; SFS FCF (9M €544M) is small relative to
  group and its funding is matched to receivables.
- **Margin quality:** Q3 IB margin 17.3% (17.7% ex severance) vs 14.9%;
  CFO put SI's net tariff-refund benefit at 50bp and said Q4's guide has
  "no special effects baked in out of tariff"; Healthineers' 18.2% margin
  is attributed "primarily" to refunds. DI 18.7% includes 70bp of
  Altair/Dotmatics integration cost — a genuine offset. Net: the run-rate
  IB margin is roughly 16.5–17%, and FY26 EPS guidance already embeds it.
- **Supply chain / stocking (Ben Uglow, Oxcap):** CEO sees "certain
  constraints" on electronic components and possible price increases, but
  "no sign" of channel stocking, and lead times nowhere near 2021–22. A
  thread to reopen if DI automation orders (+11% Q3, book-to-bill 1.01)
  keep outrunning revenue.
- **Software monetisation under AI seat compression (BNP):** Siemens is not
  charging per token; licence + SaaS; Eigen Engineering Agent priced as a
  licensed tool with "doubling and tripling" customer counts over weeks
  (unquantified). Seat-count risk acknowledged; management bets on usage.
  Not load-bearing for the pass; noted as a plausible-only growth vector.
- **Post-call sweep (Aug 6 → Aug 24):** no 8-K-equivalent ad-hoc releases,
  no directors' dealings surfaced for Busch/Bienert in August (last found:
  Bienert sold 107 shares 2025-02-04). Two Q4 Deutsche Bahn rail contracts
  were pre-announced on the call. A $185M US contract (fundz.net, 2026-08-07)
  is immaterial. Silence since the call is itself the reading.
- **Options read (mandatory):** `get_option_chains` returns no chain for
  SIEGY — **no listed options** on the ADR; SIEGY is not in the 24-symbol
  CBOE catalog, so path 1 is unavailable too. No implied-move table (§4).
  Robinhood `get_earnings_results` also returns no rows for the ADR, so the
  8-quarter estimate-vs-actual pattern could not be read; Siemens' own
  guidance history (raised twice in FY26) is the substitute.
- **Dead ends:** the `/quote/otc/SIEGY/transcripts/` and `/filings/` routes
  return `{info}` only (unfed for OTC) — the Xetra route `/quote/etr/SIE/`
  carries 48 transcripts and was used instead. `data/stocks.db` `v_latest`
  and `composite.db` have no SIEGY row (US universe only). Statistics-page
  `sharesOut`, `shortInterest` and `fcfps` are `n/a` on the OTC route;
  share count taken from Siemens' own tables (~770M). Search for a Siemens
  annual-report risk section returned Siemens Energy's report instead; the
  Item 1A-equivalent terminal risk was taken from Siemens' own FY25
  release language on tariffs/China (below).

## 4. Valuation

Inputs (stockanalysis `/quote/otc/SIEGY/statistics/` hover values,
2026-08-24): market cap $251,457,856,872; enterprise value $305,007,448,491;
`ncfo` $16,382,954,410; `capex` −$2,845,881,411; `fcf` $13,537,072,999
(= €11.85B, matching Siemens' own TTM group FCF cont.+disc. of €11,848M:
FY25 €10,812M − 9M FY25 €5,505M + 9M FY26 €6,541M); net income
$9,078,030,386; beta 1.285. Pairing: levered TTM FCF against **market cap**,
net debt 0 by the pairing rule (EV would re-count the €50B+ of SFS and
corporate debt already served in NCFO). Haircut: minority share of
Healthineers FCF, $1.29B (§3) → **owner FCF $12.25B**. SBC not deducted
(amount UNKNOWN 1; direction is a further cut to the base). Cash taxes paid
€2.74B TTM vs €3.23B book expense (24.3% rate) — no NOL flattery.

Hurdle: rf 4.52% (Damodaran home page, Aug 1 2026 vintage) + beta 1.285 ×
ERP 5.07% = **11.03%**; at beta clamped to the top of the 0.8–1.2 band,
**10.60%**. The ERP is operations-weighted from Damodaran's country table
(Jan 5 2026 vintage) over Siemens' FY25 revenue split (Q4 FY25 release):
Germany 14.8% × 4.23, rest of Europe/CIS/Africa/ME 32.0% × ~5.2 (Aa3
Europe blended with ME/Africa), US ~25% × 4.46, other Americas ~7.6% × ~7.0,
China 9.1% × 5.14, other Asia/Australia 11.5% × ~5.8 — sub-regional blends
are proxies where the release gives only region totals. A US-only headline
ERP (4.28%) would read 10.02% at beta 1.285. Damodaran's mature-company
companion, rf + 4.5% = 9.02%, is the floor any reading has to beat.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle (β1.285 / β1.2) |
|---|---|---|---|---|---|
| A conservative | $12.25B | 3% | 2.0% | 7.19% | −384bp / −341bp |
| B base | $12.25B | 6% | 2.0% | 7.91% | −313bp / −269bp |
| C optimistic | $12.25B | 8% | 2.5% | 8.81% | −222bp / −179bp |
| E naive (no NCI haircut) | $13.54B | 6% | 2.0% | 8.52% | −252bp / −208bp |
| B at beta 1.0 | $12.25B | 6% | 2.0% | 7.91% | −168bp (hurdle 9.59%) |

Precision: no listed options, so no IV rule applies; two decimals are the
tool's output, not a claim of that precision. Base case meets the β1.2
hurdle at a ~$172–175B market cap (~$112–114/ADR).

Integrity checks:
- **Reinvestment warning answered.** `--base-earnings` $9.08B < base FCF
  $12.25B → the tool prints "growth without reinvestment". Siemens' net
  income is depressed by ~€0.7B/yr of PPA amortisation (IB segment tables:
  €713M in 9M FY26) and FY26 integration costs, and capex (€2.5B) runs
  below D&A (€2.9B) — cash earnings are closer to €9.5–10B, still below
  FCF. The honest response taken: terminal growth held at 2.0% ≈ euro
  inflation (repricing of existing assets), 2.5% only in the optimistic
  case, and the base is not raised. Growth beyond inflation in the explicit
  years is paid for by the buyback/acquisition cash the base ignores.
- **Serial acquirer.** `cashAcquisition` €14.2B FY25 (Altair, Dotmatics),
  €4.4B TTM. The 6% path is treated as organic (guidance 6–8% comparable),
  so acquisition spend is not charged; the 8% path would need M&A that the
  base FCF does not fund — one more reason C is optimistic, not base.
- **Market-share sentence.** 6% for five years takes revenue from €81B to
  ~€109B. Automation + electrification + rail + medtech is a multi-hundred-
  billion-euro market; no "bigger than the market" failure.
- **Terminal growth vs disclosed terminal risk.** Siemens' own FY25 release
  names "volatile tariff developments" and US–EU–China trade conflict as
  the largest risks, with China industrial revenue −9% comparable in FY25.
  A 2% nominal terminal rate survives a permanently fragmented China (the
  local-for-local portfolio grows mid-20s and China is 9% of revenue); a
  broad Western industrial-capex bust is a cyclical, not terminal, hit.
- **Distribution clamp.** US median cost of capital 7.79%, 80% band
  5.26–9.88% (Data Update 5, 2026). Implied 7.2–8.8% sits inside the band
  near the median — an average return priced on an above-average business:
  not a strong pass by the clamp alone, a pass by the hurdle.
- **Terminal ROE / excess returns.** ROIC 6.6%, ROCE 8.2% (statistics page,
  goodwill-laden after €55B of acquisitions); Siemens' own ROCE 14.8% Q3.
  The terminal assumes excess returns fading, consistent with the ~29%
  base rate.
- **Asset-light claim.** Not made; capex ~3% of revenue and management is
  adding switchgear capacity (Frankfurt) — no hidden take-or-pay found, but
  the commitments note was not read (UNKNOWN 3).
- **Leverage gate.** Not triggered: Industrial net debt €9.3B is 0.6×
  EBITDA and 3% of EV; gross debt is SFS-matched. Equity-as-option lens
  omitted.

Options-implied move: **no listed options** on SIEGY (Robinhood chain
lookup empty; not in the CBOE catalog). The timing check is NOT APPLICABLE
and the pass rests on the hurdle, not on options evidence. Realised vol for
reference (95 daily closes 2026-04-15 → 2026-08-21, Robinhood): the ADR moved
+17% over the window with a −5.2% earnings day; no IV to compare it to.

## 5. Falsifiers

For the pass (flip toward buy):
- **Shift —** Market cap near $175B (~$114/ADR at today's FX) with the FY27
  guide intact: base case reaches the β1.2 hurdle. Revalue, do not wait for
  a story.
- **Shift —** FY27 guidance (Q4 release, ~Nov 12) sets group comparable
  growth ≥9% with DI margin ≥19% and SI ≥20% — the 8% FCF path becomes the
  base and the spread narrows to ~−180bp; still a pass unless the price
  also moves, but the condition-4 ceiling is gone.
- **Shift —** Healthineers spin terms make Siemens ex-SHL cheaper than the
  consolidated read (e.g. the retained stake is monetised into the buyback):
  rerun the pairing on the industrial core only.

For an owner (sell):
- **Break —** DI automation orders turn negative y/y with book-to-bill <1
  for two quarters alongside channel-stocking commentary — the 2021–22
  pattern the CEO says is absent.
- **Break —** SI data-center orders fall by half y/y for two quarters and the
  ~€12B FY27 SI backlog conversion slips — the AI-infrastructure factor
  fails.
- **Shift —** Tariff refunds reverse or a new US/EU tariff round lands: the
  Q3 margin's non-recurring 50–100bp becomes a headwind; revalue.
- **Shift —** Buyback pace drops below €1B/yr while M&A resumes at FY25
  scale — capital allocation shifts from per-share to empire.

**Reopen trigger:** 2026-11-12: siegy-q4-print-fy27-guide-and-shl-spin-terms

## 6. UNKNOWNs

1. **Stock-based compensation run-rate.** Not on the stockanalysis
   cash-flow route for this listing (no `sbc` key); Siemens' annual report
   Note on share-based payment would give it. Absence does not kill the
   pass — SBC is a further deduction from the base, so it only widens the
   negative spread.
2. **ADR mechanics of the Healthineers spin.** Whether Deutsche Bank (the
   depositary) delivers SHL ADRs, ordinary shares, or sells and remits cash
   — and the US tax treatment of a German Umwandlungsgesetz spin to ADR
   holders. Source: the depositary notice and the spin-off documentation
   due with the Q4 release / AGM invitation. Does not change the ownership
   call; it changes the friction an ADR holder pays.
3. **Commitments and contingencies.** The FY25 annual report's purchase-
   obligation note was not read; a large switchgear capacity commitment
   would raise capex above the trailing €2.5B. Direction: lowers base FCF.
   Does not kill the pass.
4. **FY26 Q4 date.** Company has not published it; ~Nov 12 assumed from the
   FY25 pattern. Reopen trigger inherits the uncertainty by a day or two.
5. **Trailing estimate-vs-actual EPS pattern.** Robinhood returns no rows
   for the ADR; the guidance-revision history (two raises in FY26) is the
   only proxy. Not load-bearing.

## 7. Sources

- **Primary:** Siemens Q3 FY26 earnings release and press release, 2026-08-06
  (segment tables, outlook, capital structure, Industrial net debt, FCF
  reconciliation, Healthineers/SFS pages); Siemens Q4 FY25 earnings release,
  2025-11-13 (FY25 revenue by region, FY25 group FCF €10,812M, Healthineers
  FY25 segment FCF €3,315M); Siemens press releases "Siemens plans to
  deconsolidate Siemens Healthineers" (2025-11-12) and "Siemens clarifies
  timeline for spin-off" (2026-04-17); Siemens IR ADR page (2 ADRs = 1
  share since 2017-03-13); Q3 FY26 earnings call transcript (Quartr via
  stockanalysis `/quote/etr/SIE/transcripts/553899-q3-2026/` — primary-
  transcribed; Busch/Bienert prepared remarks and Q&A).
- **stockanalysis.com (vetted exception):** `/quote/otc/SIEGY/statistics/`
  (market cap, EV, FCF, beta, margins, ROIC, taxes); `/quote/otc/SIEGY/
  financials/{income-statement,cash-flow-statement,balance-sheet}/` (EUR,
  FY21–TTM); `/symbol-lookup/` route resolution.
- **Broker/market microstructure:** Robinhood MCP `get_equity_quotes`
  (price $163.30), `get_equity_historicals` (95 daily bars), `get_option_
  chains` (empty), `get_earnings_results` (empty) — admissible: no
  integrated official source covers an OTC ADR's quote, chain or bars.
- **Reference data:** Damodaran home page (implied ERP 4.28%, rf 4.52%, Aug 1
  2026); country risk premiums table (Jan 5 2026 vintage: Germany 4.23%,
  US 4.46%, China 5.14%, France/UK 5.01%, India 7.08%, Brazil 7.47%,
  Mexico/Italy 6.69%); cost-of-capital distribution (Data Update 5, 2026).
- **Point-in-time repo DBs:** `earnings.db` (`calendar_now.today`
  2026-08-24; no SIEGY event), `stocks.db`, `sec_fundamentals.db`,
  `composite.db`, `options.db` (no rows — US universe only), `portfolio.db`
  `v_latest_positions` (17 held symbols, for the factor overlap).
- **Low-confidence:** Bloomberg headline "Siemens Disappoints Investors With
  Muted Outlook Raise" (2026-08-06); TipRanks/MarketScreener voting-rights
  notice on the Siemens Energy stake (5.54%, 2026-04-02); fundz.net $185M
  contract note; web summaries of the Siemens family ~6% pool.

## Kill-thesis record

Ledger: `2026-08-24 SIEGY SOUND conditions=4 refuted=0 unknown=0
reopen=2026-11-12:siegy-q4-print-fy27-guide-and-shl-spin-terms`.

Per-condition adjudication:
1. Valuation below hurdle — **SURVIVED.** Attack: lower the hurdle. Beta
   1.0 + US headline ERP gives 8.80%; base case 7.91% is still −90bp;
   only the optimistic 8%/2.5% path clears (8.81%, +1bp). Attack: raise
   the base — use Siemens' "FCF all-in" or add back Altair integration
   cash (~€0.2B): moves the base case by <30bp. Neither turns the spread.
2. Minority haircut — **SURVIVED.** Attack: the haircut is too large because
   Siemens receives Healthineers' dividend (67% of ~€1.1B). Rebuttal: the
   dividend is inside the consolidated FCF already; what leaves is the
   minority's 33% of the whole segment FCF, which is what was deducted.
   Attack: Healthineers' FCF is depressed by Varian PPA — irrelevant to
   cash. Cross-check: NCI income €0.93B TTM ≈ the €1.1B cash deduction.
3. Margin quality — **SURVIVED.** Attack: refunds are small (50bp at SI)
   and DI's 70bp integration cost is a larger, temporary offset in the
   other direction. Accepted in part — the run-rate is ~17%, not lower —
   but the condition only needs the base FCF not to be understated, and
   FY26 guidance (raised to €11.20–11.50 EPS pre-PPA) already embeds the
   Q3 run-rate. Not refuted.
4. Growth ceiling — **SURVIVED (plausible).** Attack: SI's ~€12B FY27
   backlog conversion plus the data-center pipeline "well into FY27 and
   beyond" implies group growth above 8% next year. Possible for FY27 in
   isolation; a five-year 8% FCF path also needs DI software ARR to hold
   11% through an AI seat-compression cycle the CEO conceded is real, and
   management's own "lumpiness" warning. The condition is plausible, not
   probable, and the pass does not depend on it — scenario C already
   assumes it and still fails.

Standing checks: **base rate** — only ~29% of firms sustain returns above
their cost of capital; Siemens' ROIC 6.6% (goodwill-laden) vs ROCE 14.8%
says the operating business does, the acquisitive balance sheet does not;
the terminal fades excess returns. **Short case** — the strongest: a
European industrial at 27.7× trailing / 22× forward earnings with margins
at the top of their bands, a data-center order book that competitors
(Schneider, Eaton, ABB) will price into, China exposure, a spin-off that
removes the highest-margin, least-cyclical segment, and FCF that flatters
because capex < D&A during a capacity build. **Management incentives** —
Managing Board LTI is EPS pre-PPA and relative TSR; the FY26 raise is
exactly the metric they are paid on (annual report; not re-read this run).
**Disconfirming search** — searched for the muted-raise reaction, tariff-
refund dependence, supply-chain constraints and seat-compression risk;
found all four in the call and press. **Moat as mechanism** — installed-
base switching cost in automation/PLM/EDA (mechanism); switchgear moat is
capacity and certification during shortage (weaker, stated).

Statistical checks: no data-driven claim (no composite signal, no
backtest) — N/A. Options-timing check: **not run — no listed options on
SIEGY**; the thesis makes one dated claim (Q4 print ~Nov 12) that the
market cannot be read against; coverage gap disclosed.

**Closest attack:** the hurdle attack (condition 1) — beta 1.0 with the US
headline ERP narrows the base-case spread to −90bp and lets the optimistic
path scrape the line.

**Flip evidence:** to FLAWED (pass was wrong) — the base case reaching the
β1.2 hurdle at today's cap, i.e. owner FCF ~$17B or a demonstrated 9%+
five-year organic FCF path in FY27 guidance; or the market cap near $175B.
To confirm SOUND — the Q4 print holding FY27 group growth at 6–8% with the
Q3 margin run-rate, and the spin terms as announced.
