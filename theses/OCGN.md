# OCGN — Ocugen, Inc. — 2026-09-10

Price $1.025 (official close, 2026-09-10) · market cap $347.6M · next earnings
2026-11-05 BMO (tentative; `stocks.db` carries 2026-11-04 — the disagreement is
noted, neither is confirmed) · EV ~$349M · net debt −$12.1M (net *cash*)

Entry path: `composite` flag (2026-09-10 Phoenix, score_sum +3 on coverage 0.18).
Unattended scheduled run.

## 1. Verdict and thesis

**PASS at $1.025.** kill-thesis: **FLAWED** — conditions=5 (0 probable,
2 plausible), refuted=3, unknown=0, pending=2, not_obtained=0.

**p(beat SPY, 63 td): 0.33** · kill-thesis: 0.33

**Disputed expectation:** The market prices Ocugen's $348M equity as a rational
call option on a firm that has never sold a product — the `equity_option` lens
returns $373M against $348M traded (1.07×), with a risk-neutral 46.7% chance the
firm covers its debt at maturity. There is no discount to a distressed-equity
model to collect. What revises this is the OCU400 Phase 3 topline in Q1 2027 and
the full 8-month OCU410ST dataset in Q2 2027; nothing between now and then
changes the business, only the financing.

Ocugen is a pre-commercial gene-therapy company with three retinal programs in
registrational trials and no product ever approved in the United States. Its
entire $4.58M of TTM "revenue" is **non-cash** — the accounting value of
manufacturing services received from CanSinoBIO, not cash from a customer. It
burns roughly $77M a year against $100.1M of cash, carries negative book equity,
and filed explicit going-concern language in its Q2 10-Q six weeks ago. The bull
case is entirely a bet on three binary clinical readouts, the first of which is
five months away; the equity is priced approximately where option arithmetic says
it should be, so there is no valuation edge to pair with the clinical bet. Two of
the three programs share one transgene, and that transgene's only human 8-month
efficacy readout just came back directionally negative.

**Closest attack:** The FY2025 10-K states plainly that "OCU410 and OCU410ST
utilize an AAV delivery platform for the retinal delivery of the RORA gene." They
are the same construct in different indications. Ocugen dosed the first patient in
OCU410's registrational Phase 3 on 2026-09-01; on 2026-09-03 the OCU410ST DMC
reported that "one could consider futility based on the negative direction of
treatment effect." That is not one program disappointing — it is the platform's
only efficacy signal pointing the wrong way, and it spans conditions 3 and 5 at
once.

Load-bearing conditions of the bull case (5):

1. *plausible* — Stockholders approve the +250M authorized-share increase
   (390M → 640M) at the 2026-09-21 special meeting, establishing the Reserved
   Share Effective Date. Settled by the Item 5.07 8-K due within four business
   days of 2026-09-21. Proposal 1 needs a majority of **outstanding** shares — a
   high bar on a 98%-float retail name — but the proxy states brokers have
   discretion ("we do not expect there to be broker non-votes"), and Proposal 2
   permits adjournment to grind out a quorum.
2. *plausible* — OCU400 Phase 3 topline (Q1 2027) is positive and supports the
   rolling BLA, with PDUFA targeted Q4 2027. Settled by the topline release, due
   by 2027-03-31 per company guidance.
3. *refuted* — OCU410ST's full 8-month dataset overcomes the DMC's interim
   finding, preserving the priority review voucher management values at
   $100–200M.
4. *refuted* — Ocugen reaches first product revenue without dilution that
   swamps the return.
5. *refuted* — OCU410 (geographic atrophy, ~2–3M patients) reaches BLA in 2028.

**Dominant shared risk factor:** binary clinical/regulatory readout on
unapproved single-platform biotech assets — holdings unavailable in this session.

## 2. Business

**Created:** Nothing yet, for any patient, commercially. Ocugen has never had a
product approved for sale in the United States (FY2025 10-K, Item 1A). The
prospective value is real: OCU400 targets retinitis pigmentosa across >30 causal
mutations (~300,000 patients in the US and Europe), OCU410ST targets Stargardt
disease (~100,000 globally, no approved therapy), OCU410 targets geographic
atrophy secondary to dry AMD (~2–3M in the US and Europe). The distinctive claim
is **modifier gene therapy** — instead of replacing one broken gene, deliver a
nuclear hormone receptor gene (NR2E3 for OCU400; RORA for OCU410 and OCU410ST)
that regulates whole networks, so one product could serve a mutation-agnostic
population. If it works, the patient gets a one-time subretinal injection instead
of nothing.

**Captured:** Today, not at all in cash. The $4.581M TTM revenue line is
collaborative-arrangement revenue from CanSinoBIO, and the 10-Q is explicit that
it is recognized as **non-cash consideration** — the measured value of CMC
development and clinical-supply manufacturing services CanSinoBIO performs. In
exchange CanSinoBIO holds exclusive rights in China, Hong Kong, Macau and Taiwan,
and Ocugen receives low- to mid-single-digit royalties on net sales in each
territory. So the one revenue line on the income statement is a barter entry that
cost Ocugen a quarter of the world's largest patient pool. Future capture, if
approvals arrive, would be one-time per-patient therapy pricing plus a
potential priority review voucher sale ($100–200M per management) — note a PRV is
a one-time asset, not a business.

**Protected:** There is no moat today, and the honest answer is to write that
down rather than reach for the orphan-designation checkbox. Orphan exclusivity
and RMAT are regulatory protections that **attach on approval**; Ocugen has none,
because it has no approvals. What remains is patent estate and the platform claim
itself — and the platform claim is precisely what the OCU410ST interim
undercut. A competitor is not stopped tomorrow by anything Ocugen owns; it is
stopped, if at all, by the same clinical difficulty that is currently stopping
Ocugen.

**Control:** One class of common stock, no controlling holder, no dual-class
structure. Insiders hold 1.69% and institutions 42.9%; float is 333.4M of
339.1M shares (98.3%). Nothing is foreclosed — this company is fully exposed to
an unsolicited approach or an activist, and the practical constraint on both is
that there is no cash flow to redirect. The null answer, written explicitly.

**Operating leverage (Phase 0): negative.** Revenue went from approximately zero
to $4.6M while the operating loss widened by roughly $49M (SEC XBRL,
`OperatingIncomeLoss`, annual):

| FY | operating income |
|---|---|
| 2019 | −$14.163M |
| 2020 | −$21.285M |
| 2021 | −$58.028M |
| 2022 | −$84.868M |
| 2023 | −$65.531M |
| 2024 | −$54.757M |
| 2025 | −$62.916M |

This is the direction, not merely the level. Q2 2026's loss of $(24.877)M against
Q2 2025's $(14.739)M says the widening is still current, and share-based
compensation alone ($9.208M TTM) runs at 201% of revenue.

## 3. Threads pulled

**The going-concern language versus what management said on the call.** The Q2
10-Q filed 2026-08-06 states the company "has concluded that there is substantial
doubt about the Company's ability to continue as a going concern within one year
after the date these condensed consolidated financial statements are issued." On
the earnings call **the same day**, CFO Rita Johnson-Greene described "our cash
runway into 2028" and the going-concern disclosure was not raised. Both can be
literally true — the going-concern trigger is the financing structure, not purely
the burn — but the emphasis gap is the finding, and it repeats below.

**Why a 2034 note sits in current liabilities.** The $130.0M of 6.75% convertible
senior notes mature 2034-07-15, yet carry at $82.359M as a **current** liability,
alongside a $33.708M derivative liability for the embedded conversion option. The
10-Q explains it: "unless and until the Reserved Share Effective Date occurs the
Company is required to settle conversions solely in cash. As a result, the
Convertible Notes … will remain classified as current liabilities." That single
accounting fact drives the working-capital deficit ($106.721M current assets vs
$133.080M current liabilities) and the negative book equity of $(16.556)M.

**What actually happens if the September 21 vote fails — the author's own framing
was wrong and is corrected here.** I expected a default trigger. There is none.
The proxy's only stated consequence of missing the September 30 deadline is that
the company is "obligated to use our best efforts to obtain such approval as soon
as possible" — no event of default, no penalty interest, no redemption right, no
repurchase obligation. The notes also cannot be converted before the earlier of
2027-05-15 and the Reserved Share Effective Date, so there is no near-term cash
call either way. The condition remains load-bearing, but for an inverted reason:
from 2027-05-15, conversions must be settled **in cash** absent the reserved
shares, and conversion only becomes attractive above the ~$2.68 conversion price.
**The bull case's own success is what triggers the cash drain.** A positive OCU400
readout that triples the stock, with the vote unpassed, obliges Ocugen to pay cash
it does not have. Separately, Nasdaq Rule 5635(d) caps physical settlement at
67.6M shares absent approval, with the excess settled in cash.

**The DMC language — I went to the 8-K body rather than the deck, and it was
worse.** The investor presentation (EX-99.1) says only that the DMC "recommended
continuing the study according to the protocol except with a modification to
obtain 8 months of follow-up on lesion size in the entire study population." The
8-K body, Item 8.01, says: "The DMC noted that **one could consider futility based
on the negative direction of treatment effect** on the interim sample and other
interim results, but the DMC recommended the modification to obtain the entire
dataset at 8 months in order to observe the results without the baseline lesion
size imbalance that existed between the treatment and control arms in the small
interim analysis population and that does not exist in the entire dataset at 8
months." Interim n=26 (16 treated, 10 control) of 63 enrolled. Ocugen's
baseline-imbalance defence is legitimate — baseline characteristics are known at
randomization, so the company can assert the full dataset is balanced — but an
explanation for a negative result is not a positive result. The disclosure-
emphasis gap between the body and the deck is itself the thread.

**Same transgene, two programs.** The FY2025 10-K: "OCU410 and OCU410ST utilize
an AAV delivery platform for the retinal delivery of the RORA gene," both
"utilizing the RORA (RAR Related Orphan Receptor A) gene for the treatment of GA
secondary to dAMD and ST, respectively." OCU400 is a different transgene (NR2E3,
AAV5), so the read-through to OCU400 is conceptual — the modifier-gene thesis —
not construct-level. To OCU410 it is direct. OCU410's Phase 3 began 2026-09-01,
two days before the DMC delivered its read on the same construct; that is
sequencing, not concealment, but it means a registrational trial in a 2–3M-patient
indication is now running on a construct whose only human 8-month efficacy signal
points the wrong way.

**The CEO filed to sell into the crash.** Chairman/CEO and co-founder Shankar
Musunuri filed a Form 144 on 2026-09-09 — the day the stock fell 19.9% — proposing
to sell 525,991 shares for approximately $589,741 through Merrill Lynch,
individually and through KVM Holdings. **Whether this sits under a pre-existing
Rule 10b5-1 plan was not determined this run** (see §6); a 144 is a notice of
proposed sale, not a completed sale, and routine 10b5-1 selling would drain most
of the signal from it. Recorded because the timing is conspicuous, not because it
is established as discretionary.

**Runway arithmetic against management's "into 2028."** H1 2026 operating cash use
was $(33.992)M, an annualized ~$68M, and the trailing figure understates the
forward number because three Phase 3 trials are now running simultaneously and
OCU410's only started this month. Add the convertible coupon — 6.75% × $130M =
$8.775M/yr cash, of which H1 contains under two months — and the forward need is
roughly $77M/yr against $100.051M of cash (plus $0.320M restricted). That is
about 15–16 months from 2026-06-30, reaching roughly Q4 2027. Management's
"into 2028" therefore requires burn to flatten while trial activity scales. The
BLA dates it must fund to are mid-2027 (OCU410ST), Q4 2027 (OCU400 PDUFA) and
2028 (OCU410).

**The non-dilutive levers, checked.** Named on the Q2 call: a priority review
voucher worth $100–200M, ex-US business development, and $15M from Janus Henderson
warrants expiring August 2027. The PRV is the largest and it is **conditional on
OCU410ST approval** — the program whose interim just read negative. So the
principal non-dilutive lever and the refuted condition are the same event. Against
that, the special meeting asks for 250M new authorized shares, which at $1.025 is
roughly $256M of issuance capacity; the CFO described this as the ability "to
raise additional equity if we decide to do so."

**Options read (mandatory):** Path 2 only — OCGN is not among the 24 symbols in
the CBOE catalog, so path 1 is structurally unreachable and no own-history IV
percentile exists. The 2026-10-16 $1.00 straddle brackets the September 21 vote
but **fails the liquidity gate** (put bid $0.00 against a $0.30 ask — a spread of
200% of mark), so its table is UNRELIABLE. The expiry bracketing the decisive
catalyst, OCU400 topline in Q1 2027, is 2027-04-16, and both its $1.00 legs are
zero-bid with the call returning null IV and no greeks (OI 20 and 7, zero volume)
— so the timing check on the thesis's real catalyst is **NOT APPLICABLE**, not
passed. Table and full caveats in §4.

**Dead ends.** (a) I looked for an at-the-market equity program that would let
Ocugen dilute continuously without a discrete raise; the Q2 10-Q discloses none.
(b) I looked for a coupon step-up, special redemption, or fundamental-change put
tied to the September 30 approval deadline; the proxy and the 8-K carry none, and
this is what corrected my framing above. (c) I checked whether the Avenue Capital
loan still encumbered the company — it was fully repaid and terminated 2026-05-07
with a $2.383M extinguishment loss, leaving only a $1.5M EB-5 loan at 4%
(carrying $1.749M) secured by substantially all assets except IP. So the balance
sheet is genuinely simpler than the negative book equity suggests, and net debt is
actually *negative* (−$12.1M). (d) The composite flag that produced this run
carries coverage of 0.18 — two of eleven ticker signals had data — and both were
mechanical consequences of the 2026-09-09 crash rather than independent evidence
(see §4's integrity bullets).

## 4. Valuation

**`reverse_dcf` refused, exit 2:** `refused: base_fcf must be positive, got
-61022000.0`. No discounted-cash-flow solve is available — TTM levered FCF is
−$61.022M, operating income −$68.902M, net income −$81.811M. The section is not
dropped; the honest arithmetic is substituted below.

**Inputs and pairing.** Market cap $347.588M (339,110,401 shares × $1.025 official
close, 2026-09-10). Cash $100.051M, restricted $0.320M; total debt $87.986M
carrying ($82.359M convertible + $1.749M EB-5, plus a $33.708M derivative
liability carried separately); net debt −$12.065M. Because the flow is negative
there is no flow-to-denominator pairing to state; the SBC haircut that would apply
($9.208M TTM, 201% of revenue) only makes a negative base more negative, and there
is no minority interest.

**Hurdle: rf 4.83% (DGS10, 2026-09-09) + beta 2.20823 × ERP 4.14% (Damodaran
implied ERP, as of 2026-09-01, solved against his T-bond rate of 4.75%) =
13.97%.** Beta was **not** clamped to the 0.8–1.2 band: insiders hold 1.69%
(far below the one-fifth threshold) and float is 98.3% of shares out (far above
four-fifths), so there is no thin-float distortion — the 2.21 beta is real
information about a genuinely high-volatility equity, not an artifact.

**Terminal-growth ceiling: 2.40% (T10YIE 10-year breakeven, 2026-09-10.)** Moot
for a solve that cannot run, and see the integrity bullet below on why it is the
wrong *shape* for this business regardless.

**Required-FCF inversion** (substituting for the refused solve). To justify
$347.588M at the 13.97% hurdle with 2.40% terminal growth, the company must
produce a perpetual free cash flow of `347.588 × (0.1397 − 0.0240)` = **$40.2M a
year, starting today**. It produces −$61.0M. If first product cash flow instead
begins in 2028, that required figure compounds to roughly **$52.2M a year in
perpetuity from 2028**. At a 25% FCF margin — generous for a launch-stage
single-product biotech — that is about $209M of annual revenue by 2028; at a 40%
margin, about $130M.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| any | −$61.0M | n/a | n/a | **refused (exit 2)** | not computable |
| required-FCF inversion, flow from today | +$40.2M needed | n/a | 2.40% | 13.97% by construction | 0 bp by construction |
| required-FCF inversion, flow from 2028 | +$52.2M needed | n/a | 2.40% | 13.97% by construction | 0 bp by construction |

**Integrity checks.**

- *The reinvestment / terminal-ROE warning is not reachable* — the tool refused
  before computing it. Recorded as unanswerable rather than silently skipped.
- *Market-share sentence.* $209M of 2028 revenue at a 25% FCF margin, against the
  ~300,000 US-and-Europe retinitis pigmentosa population the company cites for
  OCU400, is a few hundred patients a year at gene-therapy pricing. That is not a
  bigger-than-the-market forecast — the arithmetic is achievable **if** a product
  is approved. The constraint here is binary approval, not addressable market,
  which is exactly why the valuation section cannot do the work on this name.
- *Terminal growth is the wrong shape, not merely the wrong number.* A one-time
  curative therapy exhausts its prevalent patient pool and then falls back to the
  incidence rate. Assuming +2.40% perpetual growth on such a product is
  structurally wrong in the optimistic direction; the defensible terminal rate for
  a single curative asset is negative after the prevalence bolus. This makes the
  required near-term FCF above an **understatement**.
- *Terminal risk from Item 1A.* The dominant structural risk is stated by the
  company itself: "We have never been profitable and expect to incur substantial
  losses for the foreseeable future," "We will require substantial additional
  capital to fund our operations," and "We depend substantially on the success of
  our product candidates, particularly OCU400, OCU410." There is no terminal rate
  that survives this, because there is no established cash flow for a terminal
  rate to grow.
- *Distribution clamp.* The US median cost of capital is ~7.8% with roughly 80% of
  firms between 5% and 10%. OCGN's 13.97% hurdle sits far above that band, which
  is the correct read for a pre-revenue name with a 2.21 beta — but it means any
  bull case must clear a very high bar, not that the stock is cheap.
- *Base rate.* Only ~29% of firms earn above their cost of capital (Damodaran's
  EVA dataset), and Ocugen has produced zero product revenue across seven years
  and more than $400M of cumulative operating losses.
- *The flag that generated this run is not evidence.* Composite scored OCGN +3 on
  **coverage 0.18** — two of eleven ticker signals had data, `si_days_to_cover`
  at 23.89 and `stocks_rsi` at 29.08. Both are mechanical consequences of the
  2026-09-09 crash, not independent observations about the business; effective n
  is one episode on one day. This is the documented behaviour of composite's
  ticker layer as a microcap dislocation scanner.

**Options-implied move.** Path 2 (Robinhood stopgap) only; path 1 structurally
unavailable. Expiry 2026-10-16, $1.00 strike, **36 DTE**, bracketing the
2026-09-21 special meeting. Call mark $0.20 (bid $0.15 / ask $0.25, IV 146.40%,
OI 419, volume 15); put mark $0.15 (bid $0.00 / ask $0.30, IV 17.99%, OI 5,066,
volume 31); ATM IV taken as the mean of the two legs per procedure, 82.19%.

| metric | value |
|---|---|
| spot | 1.02 |
| expected absolute move (MEAN, not a ceiling) | 34.15% |
| 1-σ move | 25.81% |
| ATM IV | 82.19% |
| RV60 | 75.37% |
| RV20 | 94.17% |
| IV > RV60? | YES |
| IV > RV20? | NO |

**Liquidity gate: FAILED → UNRELIABLE.** The put's bid is $0.00 against a $0.30
ask — a spread of 200% of mark, far outside the `max(10% of mark, 2 ticks)` gate.
The damage is visible inside the table itself: the expected absolute move (34.15%)
exceeds the 1-σ move (25.81%), inverting the Brenner–Subrahmanyam relationship
where the straddle mean should sit roughly 20% *below* 1-σ. That inversion is a
direct symptom of the broken put quote, and it is why no verdict here leans on
these numbers. The two realized-vol windows also **disagree** (IV above RV60, below
RV20), so "elevated" is not writable — the disagreement is the finding.

**Timing check applicability: NOT APPLICABLE.** The thesis's decisive catalyst is
the OCU400 Phase 3 topline in Q1 2027. The only expiry bracketing it is
2027-04-16, where both $1.00 legs are zero-bid, the call returns null implied
volatility and no greeks at all, and open interest is 20 puts and 7 calls on zero
volume. There is no measurable ATM IV at that tenor, so the 2-sigma refutation
could not be run against the claim that actually matters. This is disclosed rather
than passed over.

**Equity as an option (leverage gate fired).** The gate fires on negative book
equity, $(16.556)M, and on the 10-Q's going-concern language — though note net
debt is *negative*, so the usual net-debt-to-EV trigger does not apply. Firm value
$465.41M (market cap $347.59M + market value of debt ~$117.82M, taking the
convertible's carrying value plus its bifurcated derivative as a proxy for market
value); debt face including cumulated expected coupons $200.8M ($131.5M principal
plus 6.75% × $130M over 7.77 years); duration 7.77 years to the 2034-07-15
maturity; rf 4.83%; equity-vol 0.7537 (RV60, from the closes series above);
debt-vol 0.20 **assumed** — a 144A convertible has no public price series, so this
leg is unobservable; debt-weight 0.2532; correlation 0.5 (the tool's Eurotunnel
default).

| | value |
|---|---|
| firm value | $465,410,000 |
| debt face (incl. cumulated coupons) | $200,800,000 |
| duration (years) | 7.77 |
| riskless rate (continuous) | 4.83% |
| firm volatility | 58.98% |
| equity value (call on firm) | $373,413,570 |
| debt value (firm − equity) | $91,996,430 |
| implied debt yield | 10.57% |
| risk-neutral P(firm covers debt at maturity) | 46.71% |
| market equity | $347,588,161 |
| option/market ratio | **1.07×** |

The assumed debt-vol is **not load-bearing**: sweeping it from 0.05 to 0.50 moves
the ratio only from 1.07× to 1.09×. Equity-vol matters more — at 1.10 the ratio
reaches 1.18× — but no setting produces the large discount that would make this an
option-theoretic bargain. Read with the two inversions stated: volatility here is a
shareholder **asset** and a creditor cost (raising equity-vol to 1.10 lifts equity
value to $409.7M while cutting P(cover) from 46.7% to 25.2%), and a maturity
extension would be equity value. The 2034 maturity is genuinely far away, and that
time premium is why a company with negative book equity and going-concern doubt
still carries a $348M equity value rationally.

**Which frame governed §1:** the **option** frame, because the DCF refused. Its
verdict is that the equity is priced approximately right — 1.07× — so the
ownership call turns on the clinical conditions in §1, not on a valuation gap. A
PASS here is not "the stock is expensive"; it is "there is no discount to
compensate for three binary readouts, two of which the evidence already argues
against."

## 5. Falsifiers

**For the pass (flip toward buy)**

- **Break —** The full 8-month OCU410ST dataset (guided Q2 2027) shows a positive
  treatment effect on atrophic lesion growth with balanced baselines across all 63
  subjects. This directly reverses the refutation of condition 3 and restores the
  PRV lever.
- **Break —** OCU400 Phase 3 topline (Q1 2027) is positive on its primary
  endpoint. The single largest revision available; it would move condition 2 from
  plausible to settled and convert a pre-revenue story into a pre-approval one.
- **Shift —** A non-dilutive financing of $100M or more — an ex-US partnership or a
  PRV sale — closes the funding gap without issuing equity at ~$1. This repairs
  condition 4 without touching the clinical conditions.
- **Shift —** OCU410's Phase 3 in geographic atrophy reports a positive interim on
  the RORA construct, severing the read-through from OCU410ST.

**For an owner (sell)**

- **Break —** The September 21 vote fails and is not rescued by adjournment. The
  going-concern classification persists and a successful OCU400 readout would then
  create a cash conversion obligation the company cannot fund.
- **Break —** OCU400 misses its primary endpoint in Q1 2027. With OCU410ST already
  directionally negative and OCU410 on the same construct as OCU410ST, a miss on
  the one differentiated transgene leaves nothing carrying the platform.
- **Shift —** An equity raise before the OCU400 readout. Issuing into a $348M
  market cap at ~$1 to cover a $77M/yr burn is the dilution condition 4 already
  fails on; doing it before the data prices the risk at its widest.
- **Shift —** A sustained close below $1.00 putting the Nasdaq minimum-bid rule in
  play. The 2026-09-10 close was $1.025 and the 52-week low is $1.01; a compliance
  deficiency would raise the reverse-split path the indenture already contemplates
  as an alternative to the share increase.

**Reopen trigger:** 2027-03-31: ocu400-phase3-topline-positive-on-primary-endpoint-
or-ocu410st-8mo-full-dataset-positive-with-balanced-baselines-or-non-dilutive-
financing-at-or-above-100m. *(Judgment call, noted per the unattended-run brief:
the earliest pending date is 2026-09-21, but that vote is a procedural step whose
passage is near-certain and which changes no fact about the business. The reopen
is set to the date the flip evidence actually arrives. If the vote fails, the
falsifier above is the route back, not this trigger.)*

## 6. UNKNOWNs

1. **NOT OBTAINED — whether the CEO's Form 144 sits under a Rule 10b5-1 plan.**
   The document exists: the Form 144 filed 2026-09-09 (accession
   0001628280-26-061150) carries a 10b5-1 adoption-date field, and this run read
   the filing's seller, size and broker but did not resolve that field. Does not
   kill the thesis — it is colour on an insider-sale thread, not a load-bearing
   condition, and it is why §3 records the timing without asserting intent.
   *(Not counted in the ledger's `not_obtained=`, which counts load-bearing
   conditions only.)*
2. **PENDING 2026-09-21 — the special-meeting result.** Settled by the Item 5.07
   8-K due within four business days. Absence does not kill the thesis; it is
   condition 1.
3. **PENDING 2027-03-31 — the OCU400 Phase 3 topline.** Settled by the company's
   guided Q1 2027 release. This is condition 2 and the single largest unresolved
   input in the document.
4. **UNKNOWN — the strike price of the $15M Janus Henderson warrants expiring
   August 2027.** Named by the CFO on the Q2 2026 call as a non-dilutive lever;
   the 10-Q does not carry the strike, and whether the $15M is realizable depends
   entirely on where it sits against a $1.025 stock. Does not kill the thesis —
   $15M is under three months of burn either way — but it means one of the three
   stated non-dilutive levers cannot be evaluated at all.
5. **UNKNOWN — the conditional power or pre-specified futility boundary behind the
   OCU410ST interim.** The 8-K discloses the DMC's qualitative observation and the
   n (26 of 63; 16 treated, 10 control) but no test statistic, boundary, or
   conditional-power figure, and DMC charters are not public documents. No filing
   past or future is obliged to carry it. Its absence does not kill the thesis —
   the disclosed direction of effect is enough to refute condition 3 — but it does
   bound how confidently anyone outside the DMC can size the damage.

*Option value, unnumbered (possible tier, not conditions):* a priority review
voucher sale at the upper end of management's $100–200M range would be worth
roughly a third of the current market cap on its own; and a competitor or partner
acquiring the RP asset after positive OCU400 data is a real path that no condition
above requires.

## 7. Sources

**Primary:** Q2 2026 10-Q filed 2026-08-06 (accession 0001628280-26-054057) —
going-concern paragraph, balance sheet, convertible-note and derivative
accounting, CanSinoBIO collaborative-arrangement terms and non-cash recognition,
EB-5 and Avenue Capital loan facts, share count. 8-K filed 2026-09-08 (accession
0001104659-26-105968) Item 8.01 — verbatim DMC language, OCU410 Phase 3 first
patient dosed, RMAT designation; and its EX-99.1 investor presentation, for the
contrast in §3. 8-K filed 2026-05-14 (accession 0001104659-26-061230) Items 2.03
and 3.02 — convertible note terms. DEF 14A filed 2026-07-30 (accession
0001140361-26-030258) — special meeting date, Proposal 1 and 2, authorized-share
counts, vote standard, broker-discretion statement, absence of any default or
penalty consequence. Form 144 filed 2026-09-09 (accession 0001628280-26-061150).
FY2025 10-K filed 2026-03-04 (accession 0001628280-26-014435) — Item 1 transgene
and vector descriptions (NR2E3/AAV5 for OCU400; RORA for OCU410 and OCU410ST),
Item 1A risk-factor headings. SEC XBRL `companyconcept` API for the annual
`OperatingIncomeLoss` series. 8-K filed 2026-08-06 EX-99.1 — Q2 earnings release,
pipeline milestones and timelines.

**stockanalysis.com (vetted exception):** Q2 2026 earnings call transcript of
2026-08-06 (primary-transcribed — management's words, carried by this vendor),
for the CFO's "cash runway into 2028," the special-meeting framing, and the
non-dilutive levers. TTM income-statement, cash-flow and balance-sheet metrics
via `stocks.db`.

**Broker/market microstructure:** Robinhood MCP for the live quote and official
2026-09-10 close, the trailing-8-quarter earnings estimate-vs-actual series, the
option chain, ATM contract quotes and greeks, and 90 daily closes for the
realized-vol series. Admissible here because no already-integrated official
source covers real-time option quotes or intraday market state for this ticker;
the EPS **actuals** were cross-checked against `sec_fundamentals.db`
(`eps_diluted` −0.07 matches the Q2 2026 actual) and agree.

**Reference data:** Damodaran implied ERP 4.14% as of 2026-09-01 (against his
T-bond rate of 4.75%); Damodaran EVA dataset for the ~29% above-cost-of-capital
base rate; US cost-of-capital distribution (median ~7.8%, 80% within 5–10%).

**Point-in-time repo DBs (read-only):** `data/stocks.db` `v_latest` — price
$1.065 at 2026-09-09, beta 2.20823, short float 30.53%, short ratio 22.65, Altman
Z −5.17, Piotroski fScore 2, SBC $9.208M / 201% of revenue, float and ownership
percentages. `data/sec_fundamentals.db` `v_screener` — CIK 1372299, Q2 2026
pivoted XBRL facts. `data/composite.db` — the flag that produced this run
(score_sum +3, coverage 0.18, `si_days_to_cover` 23.89, `stocks_rsi` 29.08).
`data/fred.db` — DGS10 4.83% (2026-09-09), T10YIE 2.40% (2026-09-10).
`data/earnings.db` — no upcoming-earnings row for OCGN.

**Low-confidence:** Sell-side consensus of "Strong Buy" with a $12.17 price
target on an analyst count of 5 (via `stocks.db`), recorded as small-cap
sell-side colour and used for nothing.

## Kill-thesis record

`2026-09-10 OCGN FLAWED conditions=5 refuted=3 unknown=0 pending=2
not_obtained=0`

**Per-condition adjudication.**

1. **PENDING 2026-09-21** — the authorized-share increase. Attacked on the vote
   standard: Proposal 1 requires a majority of **outstanding** shares, a genuinely
   high bar for a 98%-float, retail-heavy register. The attack fails because the
   proxy states brokers hold discretion on this proposal ("we do not expect there
   to be broker non-votes"), which is what usually rescues charter amendments, and
   Proposal 2 authorizes adjournment to keep soliciting. Separately attacked the
   *framing*: the author claimed this condition removes a default risk. It does
   not — there is no default, penalty interest, or redemption right anywhere in
   the proxy or the 8-K, and the notes cannot convert before 2027-05-15 regardless.
   The condition survives as load-bearing only under the inverted reading now in
   §3: without reserved shares, a *successful* readout above ~$2.68 forces cash
   settlement. Not refuted; dated; PENDING.
2. **PENDING 2027-03-31** — OCU400 topline. Attacked with the modifier-gene base
   rate and with read-through from OCU410ST. The read-through is real but
   **conceptual only** — OCU400 is NR2E3/AAV5 and OCU410ST is RORA, per the FY2025
   10-K, so a RORA failure does not falsify an NR2E3 construct. Attacked also on
   the mutation-agnostic claim across >30 mutations, which is a far stronger
   assertion than approved gene-replacement precedent (Luxturna, RPE65-specific);
   this is a reason for a low prior, not evidence standing against the condition.
   Honestly PENDING, not refuted.
3. **REFUTED** — OCU410ST overcomes the interim. The evidence that exists today
   stands against the condition, which is the stated route from PENDING to
   REFUTED. The DMC's own words are "one could consider futility based on the
   negative direction of treatment effect on the interim sample and other interim
   results." The company's baseline-lesion-size-imbalance defence is an
   explanation for a negative result, not a positive one, and uncertainty never
   credits a condition. Repairable by the full 8-month dataset, not by argument.
4. **REFUTED** — funding to revenue without dilution that swamps the return.
   Refuted on arithmetic rather than opinion: ~$77M/yr forward cash need
   ($68M annualized H1 operating burn plus $8.775M of convertible coupon) against
   $100.051M of cash gives roughly 15–16 months from 2026-06-30, reaching about
   Q4 2027 — short of the 2028 BLA the plan funds to. Closing a $150–200M gap at a
   $347.6M market cap is 43–58% dilution. The largest named non-dilutive lever,
   the $100–200M PRV, is conditional on OCU410ST approval, i.e. on condition 3,
   already refuted; a second lever ($15M Janus Henderson warrants) has an
   unknown strike (§6.4).
5. **REFUTED** — OCU410 BLA in 2028. Two independent lines. First, construct
   identity: the FY2025 10-K states "OCU410 and OCU410ST utilize an AAV delivery
   platform for the retinal delivery of the RORA gene," so the only human 8-month
   efficacy readout on this exact construct is directionally negative. Second,
   schedule: first patient was dosed 2026-09-01, and a geographic-atrophy Phase 3
   on anatomic endpoints needs 12–24 months of follow-up before BLA preparation
   even begins. The program is not refuted; the 2028 date is.

**Standing checks.** *Base rate* — ~29% of firms earn above their cost of capital
(Damodaran EVA); Ocugen has produced zero product revenue and >$400M of cumulative
operating losses over seven years, and has never had a US approval. *Short case
(strongest form)* — a company with no cash revenue at all (the $4.6M line is
non-cash CanSinoBIO services), negative book equity, a going-concern
qualification, ~$77M/yr of cash need against $100M, three simultaneous Phase 3s it
cannot fund, a lead construct that just printed a negative treatment effect, a
proxy requesting 250M new shares explicitly to enable equity raises, and a $1.025
share price one cent above its 52-week low with Nasdaq's $1.00 minimum-bid rule in
view; the short's exit is dilution, not bankruptcy. *Management incentives* —
pre-commercial biotech compensation is milestone- and equity-linked, so management
is paid to keep three Phase 3s alive rather than to cut burn; the thesis assumes
management minimizes dilution (the CFO's stated "primary goal") while the same
management asks for 250M new shares. Two disclosure choices point the same way:
the investor deck omits the futility sentence the 8-K body carries, and the
August 6 call did not mention the going-concern language filed that day.
*Disconfirming search* — run deliberately: I went to the 8-K body rather than the
EX-99.1 deck precisely to find the harsher wording, and found it. *Moat —
checkbox or mechanism?* Checkbox. Orphan exclusivity and RMAT attach on approval
and Ocugen has none; the platform claim that would be the mechanism is the exact
claim the OCU410ST interim undercut.

**Statistical checks.** The composite flag that generated this run is not
evidence: coverage 0.18 (two of eleven ticker signals), both signals
(`si_days_to_cover` 23.89, `stocks_rsi` 29.08) mechanical consequences of the
2026-09-09 crash, effective n of one episode on one day. Benchmark is SPY, not a
coin — equities drift up, so a bare "it could bounce" is not a claim. The $12.17
consensus target rests on an analyst count of 5 and is treated as colour.

**Options-market timing check: ran, and could not conclude.** Both dated claims
were tested and neither yielded a usable measurement. The 2026-10-16 expiry
brackets the September 21 vote but fails the liquidity gate (put bid $0.00,
spread 200% of mark), and its output is internally inconsistent (expected move
34.15% above the 1-σ move 25.81%, inverting Brenner–Subrahmanyam) — UNRELIABLE, so
it may not move a verdict. The 2027-04-16 expiry brackets the decisive OCU400
topline but has zero-bid legs, null IV and no greeks — NOT APPLICABLE. Path 1 was
structurally unavailable (OCGN is not in the 24-symbol CBOE catalog). **No
condition was refuted on timing grounds**, and the three refutations above rest
entirely on filings and arithmetic.

**Was the short interest the real call?** Tested, and no. Short interest is 30.53%
of float with 22.65 days to cover, which is genuine two-sided squeeze risk and is
the main reason the probability below is not lower. But a squeeze is a statement
about positioning, not about the business, and all three refutations are
independent of it: the DMC's negative direction of effect, the runway arithmetic,
and the construct identity would each read the same at zero short interest. The
PASS is a business call; the short interest is why it is a PASS rather than a
conviction short.

**Closest attack:** condition 5 via construct identity — the 10-K's own sentence
that OCU410 and OCU410ST both deliver the RORA gene converts a single-program
interim disappointment into a platform-level problem spanning two of the five
conditions, and it did so two days after OCU410's registrational Phase 3 dosed its
first patient.

**Flip evidence — toward SOUND:** the full 8-month OCU410ST dataset showing a
positive treatment effect with balanced baselines across all 63 subjects, which
would repair condition 3 and restore the PRV that repairs condition 4; a positive
OCU400 topline would settle condition 2 on top of that. **Toward more FLAWED:** a
failed September 21 vote, an equity raise before the OCU400 readout, or a
sustained sub-$1.00 close putting Nasdaq minimum-bid compliance in play.

**p(beat SPY, 63 td): 0.33.** Within this horizon (ending approximately
2026-12-11) there is no clinical readout — OCU400 is Q1 2027 — so the period
contains only the near-certain September 21 vote, continued burn, live financing
overhang, and minimum-bid pressure at $1.025. Against that, a 30.53% short
interest at 22.65 days to cover makes a violent squeeze a real tail. Net: below
even, but not deeply, because the downside catalysts in this window are financing
events rather than data.
