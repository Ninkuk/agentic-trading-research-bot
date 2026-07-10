# Unit 3 — Research corpus workflow

Design doc · 2026-07-10 (Phoenix) · branch `feat/stock-research-skills`

Resolves the sub-questions that `2026-07-10-stockanalysis-suite-design.md` Unit 3 left open.
That doc's header says "Prose. No module." and its body says the module question is
"deliberately left open" and the doc-only verdict is "unsettled." **The body is correct; the
header is a defect.** This doc supersedes it for Unit 3 only.

## What the adversarial review changed

Four adversaries (empirics, YAGNI, invariants, epistemics) were run against a first design.
They refuted its central premise. What follows is the design that survived.

### The premise, refuted

The handoff and the suite spec both assert exhaustive recall: *"read many years… learn what
management has and has not ever said."* The motivating anecdote is Copart naming its market
share **twice in twenty years**, where the *rarity* was the finding.

**Transcript depth tracks Quartr's onboarding date, not the company's history**, and nothing in
the payload discloses this. There is no `fullCount`, no coverage marker, and `?page=2` silently
degrades to the `{info}` gate rather than paginating. Verified live 2026-07-10:

| Ticker | Calls | Earliest | Reality |
|---|---|---|---|
| NVDA | 148 | 2010-05-13 | ~1.3M tokens — 2× the VZ benchmark |
| GE | 87 | 2010-07-16 | founded 1892 |
| KO | 86 | 2015-04-22 | listed 1919 |
| XOM | 86 | 2015-04-30 | |
| AAPL | 74 | 2011-04-20 | the suite spec says "~18 years"; it is 15 |
| CROX | 75 | 2011-07-27 | |
| VZ | 76 | 2019-04-23 | public since 2000 |
| IBM | 40 | 2021-04-19 | five years of coverage |
| **T** | **12** | **2021-03-12** | twelve calls, for AT&T |
| BABA · TSM · SAP · SONY | **0** | — | `{info}`. No corpus exists. |

Coverage is uncorrelated with market cap or listing venue. It is not a foreign-ADR rule (PDD,
SHOP, SE, MELI have coverage; ASML, BP, RIO do not).

### The consequence

**The corpus establishes presence. It can never establish absence.**

- **Presence is sound.** "Management said X on 2024-10-22 and 2025-01-24" is citable.
- **Absence is not a finding.** Zero hits means *"not found in the N calls Quartr covers
  (`first`–`last`), which excludes this company's first M years as a filer."* That sentence,
  with N and the span, is mandatory. A bare "management has never discussed X" is the
  confident-wrong outcome the skill's UNKNOWN discipline exists to prevent, now wearing the
  authority of an exhaustive search.
- **Rarity is meaningful only when coverage ≈ company history.** True for AAPL and NVDA. False
  for T, IBM, VZ, KO, GE. The Copart structure is not reproducible on most names.

This is a smaller claim than the handoff assumed. It is still worth building. It must not be
oversold in the skill's prose.

## Architecture

Split on **purity**, not on subject. The earlier design put a `corpus.py` beside `probe.py` and
had no legal home: the four-file rule governs screener packages, and `tools/` forbids network.

The functions whose silent wrongness is dangerous — attribution, the concept lexicon, coverage
arithmetic — are **pure functions over already-decoded dicts**. No network, no DB, no clock.
They satisfy `tools/`'s contract exactly, beside `tools/valuation/reverse_dcf.py`.

The network is a 76-iteration loop over `probe.page_data`. It is trivial, it is regenerated
fresh each session, and it breaks loudly. It stays in prose.

```
tools/research/transcripts.py          pure · tested · fixtures pin the traps
    classify_side(turn, issuer) -> "management" | "outside" | "unattributed"
    flatten_turn(turn)          -> str
    coverage(index, ipo_date)   -> Coverage(n, first, last, uncovered_years)
    scan_concepts(docs, LEXICON)-> [ConceptStat(concept, df, n, first, last, seasons)]
    LEXICON                     -> the curated concept -> synonym-regex map

.claude/skills/research-ticker/references/disclosure-hunt.md    prose · judgment
    the ~29-line fetch loop (probe.page_data, 0.7s pacing)
    "absence is never a finding"
    "corroborate every load-bearing number against the filing"
```

Nothing under `sources/`. No `registry.py` entry, no `main.py` dispatch, no launchd slot, no
schema. `research/` output is human-facing; nothing in `sources/` reads it.

## Attribution — the correctness property

A transcript contains management *and* the analysts interrogating them. A hit for "market
share" is a **disclosure** if the CFO said it and a **question** if Goldman asked it.
Inverting this inverts the finding.

**Key on `company`. Never on `role`.** Evidence, all verified live:

- `role` is free text with no controlled vocabulary: `Analyst`, `Managing Director`,
  `MD - Global Investment Research`, `Managing Director and Senior Analyst`, `Operator`, `None`.
- `role` is **provably wrong**: on VZ Q1 2022, CFO Matt Ellis is tagged `role='Analyst'`,
  `company='Verizon'`. The `company` field was right.
- On VZ, `company is None` for 573 turns: 559 with `role is None`, **14 with `role='Operator'`**.
  An earlier draft claimed `role is None ⟺ company is None`. That biconditional is false. Detect
  unattributed turns by `company is None`, never by `role is None`.

Three classes, never two:

| `company` | class | meaning |
|---|---|---|
| contains the issuer name | `management` | a disclosure |
| a different firm | `outside` | an analyst's question — not a fact about the business |
| `None` | `unattributed` | Operator / Moderator / "Speaker 11" |

Matching rules:

- **Substring, not equality.** CROX Q1 2026 tags its CEO `company='Crocs'` and its CFO
  `company='Crocs, Inc.'` in the same call. Test short-form-inside-long-form.
- **Never derive the issuer string from `transcriptMeta.title`.** XOM's reads
  `"ExxonMobil Holdings Corporation"` — a stockanalysis data bug; the company has no "Holdings".
  It would fail to match its own turns, which use `company='ExxonMobil'`. `data/stocks.db` has no
  company-name column — `metrics`/`v_latest` carries `symbol`, not `n` or any name field. Take the
  issuer name from the modal `company` across turns (`issuer_from_turns`), or pass one explicitly
  if you already know it.
- Morgan Stanley is **not** a counterexample. On MS's own call, only Ted Pick and Sharon Yeshaya
  carry `company='Morgan Stanley'`; every outside analyst carries their own firm. Verified.

## Reporting — document frequency, never hit counts

Management repeats talking points quarterly, often verbatim, from the same two or three people.
Grep hits are **not independent observations**. A naive grep of the VZ corpus returns **82 raw
hits** for "market share"; the honest figure is **39 documents across 8 years**. Raw-hit
counting inflates the evidence 2×.

`scan_concepts` reports `df/N`, first date, last date, and distinct years — never a hit count.
This is the repo's `verify-before-claiming` discipline (effective n, independent observations)
applied to text.

### The lexicon, and why open-vocabulary rarity fails

The epistemics adversary proposed a document-frequency scan (`df ≤ 3`) over corpus vocabulary as
the primary source of candidate terms, to defeat anchoring. **Tested and refuted:** on the VZ
management corpus, `df ≤ 3` selects **86% of bigrams (104,880) and 95% of trigrams**. Natural
language is Zipfian; nearly every n-gram is rare. It is not a shortlist.

Rarity is meaningful only against a **curated, ticker-independent concept lexicon** with synonym
sets. Measured on VZ management-side turns (76 calls):

```
CAC                   0/76   -- never --                  ABSENT
unit economics        1/76   2026-04-27                   RARE
backlog               3/76   2020-10-21 .. 2023-05-23     RARE
wallet share          3/76   2020-11-11 .. 2023-04-25     RARE
"we don't disclose"   3/76   2023-04-25 .. 2025-05-28     RARE
take rate             6/76   2020-10-21 .. 2025-09-04
...
market share         39/76   2019-06-18 .. 2026-05-13     a talking point
churn                71/76   2019-04-23 .. 2026-05-18     constant
```

This closes three attacks at once:

1. **Synonym blindness.** Synonyms live inside the concept, so `0 hits` means zero across the
   whole set — not zero for the one word someone guessed. `wallet share` and `market share` are
   separate concepts precisely because a firm may disclose one and not the other.
2. **Anchoring.** The lexicon is fixed and authored before any ticker is seen. It cannot be
   biased by what the agent noticed in Phase 1. Agent-derived, thread-specific terms are a
   *supplement* to the lexicon scan, never a replacement — an agent-proposed shortlist
   manufactures false coverage ("I reviewed the terms") without solving *"I didn't know to ask
   the question."*
3. **Independence.** `df` + seasons is the reporting unit.

The lexicon is the one durable, cross-ticker artifact here, and a wrong synonym set silently
prints *"not disclosed."* That is why it is code with fixtures, not a markdown table.

## Fetch discipline (prose, in `disclosure-hunt.md`)

- **Pace at 0.7s** between body fetches, with an injected `sleep=` seam. Precedent:
  `sources/combiners/scorer/pricehistory.py:24` (`_SLEEP_SECONDS = 0.7  # unofficial endpoint;
  be a polite client`) — the identical shape. Measured latency is 0.33s/call unthrottled (an
  86-call burst on XOM showed no 429s and no slowdown), so a full corpus is ~76 × 1.03s ≈ 78s,
  not the 25s an earlier draft quoted.
- **Descriptive User-Agent**, per `sources/screeners/edgar_screener/fetch.py:84`
  (`agentic-trading-bot ninadk.dev@gmail.com`). `probe.py` and `pricehistory.py` both spoof
  `Mozilla/5.0`; do not extend that wart.
- **`{info}`-only is a normal outcome**, not a crash: BABA, TSM, SAP, SONY, and SPACs
  pre-first-call have no corpus at all. Assert `transcripts` on the index and
  `transcriptQuarter.transcriptTurns` on each body. HTTP 200 proves nothing.
- **Skip-and-continue per body.** On failure of call 43 of 76, print only `type(e).__name__` —
  never `str(e)`, `repr(e)`, or `e.url`. (`probe.main()` prints `str(exc)[:120]`; that is
  excused as a CLI diagnostic and must not be copied into a batch loop.)
- Corpus lands in the **session scratchpad**, one JSONL per call, discarded at session end. Not
  `data/*.db`. Not `research/`. Re-fetched per session by design.

## Traps

- `paragraphs` is `list[list[dict]]` — a list of paragraphs, each a list of *sentences*
  `{text, startSec, endSec}`. Two levels. Verified invariant across 10 tickers / ~590 turns,
  including operator turns and conference presentations.
- The index is **not only earnings calls** — conference presentations are interleaved
  (`eventTitle` "J.P. Morgan 54th Annual…", `quarterLabel` "FY 2026").
- `/stocks/{T}/transcripts/` 404s under `/etf/`. `?page=N` is not pagination.
- **Quartr, not EDGAR.** Transcripts are *transcriptions*. The words are management's; the text
  is a third party's. `summaryShort`/`summaryLongHtml` are AI-generated — low-confidence, always.

### Source tiering

Qualitative framing, tone, and emphasis from a transcript are usable, cited as
*"primary, transcribed."* **Any number quoted from a transcript that is load-bearing for the
thesis must be corroborated against the printed filing** (earnings release, slides, 10-Q) before
it counts as a fact. A misheard "15%" vs "50%" is silent and catastrophic, and does not look like
colour — it looks like a quote.

## Testing

Offline, per the repo invariant. The seam sits at the **caller**, matching the existing pattern:
`parse_catalog(raw: dict)` is pure and unit-tested with a literal fixture; `fetch_catalog()` is a
one-line network wrapper and is never unit-tested, only injected into `run()` as
`fetch_catalog=fake_catalog`.

Everything in `tools/research/transcripts.py` is pure, so it needs no seam at all.
`tests/test_transcripts.py` pins, with literal fixtures drawn from real payloads:

- two-level `paragraphs` flattening, including a single-sentence paragraph
- `('Verizon', 'Analyst')` → `management` (the CFO mislabel)
- `role='Operator', company=None` → `unattributed`
- `role=None, company=None` → `unattributed`
- `company='Crocs'` and `company='Crocs, Inc.'` → both `management` for issuer `Crocs`
- `company='Morgan Stanley'` → `management` for issuer `Morgan Stanley`, `outside` for issuer `Verizon`
- `coverage()` arithmetic: T (12 calls, 2021→2026, IPO 1983) reports the uncovered span
- `scan_concepts` returns `df`/seasons, not hit counts; a term repeated 5× in one document counts once

## Out of scope

- **Phase 0's leverage gate has no threshold** (`"heavy leverage relative to its cash
  generation"`). `debtFcf`, `netDebtEbitda`, and `interestCoverage` are all in the payload Phase 0
  already fetches. Quantifying it decides which companies ever get researched, and the repo's
  `composite-calibration-lesson` warns against thresholds set before real data exists. Separate
  decision.
- Storing the corpus. No cross-name, cross-time comparison exists to make.
- `/filings/` PDFs and `/metrics/{metric}` segment splits: reachable today via `probe.page_data`;
  they need prose in `disclosure-hunt.md`, not code.

## Open questions

1. Does the lexicon ship with ~16 concepts (the tested set) or a broader vocabulary? Broader is
   cheap to add and each entry is a synonym-set judgment call. Start at 16, grow on use.
2. Should `coverage()` fetch `ipoDate` itself, or take it as an argument? Taking it keeps the
   module pure. The skill reads it from `data/stocks.db`. Recommend: argument.
