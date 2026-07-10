# Finding the number

Three questions, in order. Do not skip to the third.

## 1. Does this information exist?

Skim the 10-K **before** reading it closely. The first pass is not for
understanding the business — it is for learning what the company discloses at
all: segments, geographies, the shape of the revenue split. You cannot know
what is missing until you know what is there.

Then, in order:

- **SEC EDGAR** (`https://www.sec.gov/cgi-bin/browse-edgar`) — 10-K, 10-Q, 8-K,
  DEF 14A (compensation, and therefore incentives), S-1 for recent listings.
  This repo's `sec_fundamentals.db` `companies` table maps ticker to CIK.
  Respect the shared 9 req/s SEC rate limit; a descriptive User-Agent is
  mandatory or you get a 403.
- **The investor-relations site.** Critically, IR and EDGAR **disclose
  different things**. Earnings *presentations* and *press releases* routinely
  carry segment numbers, unit economics, and cohort charts that appear in no
  10-K. Check all of them; assume neither is a superset.
- **Investor days**, when they exist. The single best document for how
  management frames the business — the transcript and the deck both.
- **Earnings-call transcripts.** For a deep look, search many years — do not read
  them; the corpus is ~650k tokens. See *Searching the transcript corpus* below.
  The point is not the quarter. But read the coverage warning there before you
  conclude anything from silence.
- **stockanalysis.com** — this project's single vetted non-primary source, and
  the fastest way to a company's aggregated financial history. Never scrape the
  HTML page. **`docs/stockanalysis_data_json_catalog.md`** is the route map, the
  decoder, and the field gotchas; read it rather than rediscovering the site.
  It is an aggregator, not a filer — when a number matters to the thesis,
  confirm it against the filing.

## 2. If it isn't disclosed, can it be triangulated or found elsewhere?

- **Triangulate.** A number disclosed once, long ago, can be tied to a number
  disclosed regularly. Copart named its market share exactly twice, in 2003 and
  2004, and never again — but cross-tied to a still-reported disclosure, it
  bounds the answer today. Old disclosures do not expire.
- **Segment redefinitions** let you carve out what a number is *not*. When a
  company merges or splits segments, the overlap year prints both.
- **Search in the local language** for a foreign issuer. Korean sources on a
  Korean retailer say things the English ones don't.
- **The Wayback Machine** for pages, guidance, and pricing that were quietly
  removed.
- **Low-confidence, clearly labelled:** Reddit, YouTube reviews, LinkedIn,
  X/Substack write-ups, expert networks. Google does not index the walled
  gardens; search them directly. **None of this ever becomes a fact.** It is
  colour that tells you where to look next, and it is labelled as such in
  the write-up, every time.

## 3. If it cannot be found — does its absence kill the thesis?

This is the question that matters, and the one most often skipped.

Bound it. "Adobe's enterprise revenue is somewhere between 20% and 50%" is a
real finding, and if the thesis needs it to be above 45%, the thesis is
UNPROVEN and you should say so.

Never fill the hole with a plausible number. Write **UNKNOWN**, state what
would resolve it, and say plainly whether you can proceed without it.
Sometimes the right answer is: *I don't know how I feel about this one.*
There are other companies. Go back to the list.

## Searching the transcript corpus

`/stocks/{T}/transcripts/` indexes a company's earnings calls and conference
presentations; `/stocks/{T}/transcripts/{detailSlug}/` returns one in full. A big
corpus is ~76 calls, ~2.6M characters, ~650k tokens. **You cannot read it.** Search
it, and read only what matches.

### First, the coverage warning — this is not optional

Transcript depth tracks the data provider's onboarding date, **not the company's
history**, and nothing in the payload says so. There is no `fullCount`, no coverage
marker, and `?page=2` silently returns the `{info}` gate rather than more rows.

| Ticker | Calls | Earliest |
|---|---|---|
| NVDA | 148 | 2010 |
| AAPL | 74 | 2011 |
| VZ | 76 | 2019 |
| IBM | 40 | 2021 |
| T | **12** | **2021** |
| BABA · TSM · SAP · SONY | **0** | no corpus exists |

So:

- **The corpus proves presence.** "Management said X on 2024-10-22" is citable.
- **The corpus never proves absence.** Zero hits means *"not found in the N calls
  covering `first`–`last`, which excludes this company's first M years as a filer."*
  Write that sentence, with the numbers. **Never** write "management has never
  discussed X." That is a confident falsehood wearing the authority of a search.
- **Rarity only means something when coverage ≈ company history.** Copart naming its
  market share twice in twenty years is a finding. The same silence across AT&T's
  twelve calls since 2021 is nothing at all.

Call `coverage(index, ipo_date)` and print it *before* any hit list. Take `ipo_date`
from `data/stocks.db`; the helper is pure and will not fetch it.

### The loop

```python
import time
from collections import Counter
from sources.screeners.stock_analysis_screener.probe import page_data
from tools.research.transcripts import (
    LEXICON, MANAGEMENT, OUTSIDE, classify_side, coverage, flatten_turn,
    issuer_from_turns, scan_concepts,
)

TICKER = "VZ"

index = page_data(f"/stocks/{TICKER}/transcripts/")
if not isinstance(index, dict) or "transcripts" not in index:
    raise SystemExit(f"{TICKER}: no transcript corpus exists")   # BABA, TSM, SAP, SONY, pre-IPO SPACs
rows = index["transcripts"]

print(coverage(rows, ipo_date="2000-07-03"))   # PRINT THIS FIRST. ipo_date from data/stocks.db

calls, issuer = [], None
for row in rows:
    try:
        body = page_data(f"/stocks/{TICKER}/transcripts/{row['detailSlug']}/")
        turns = body["transcriptQuarter"]["transcriptTurns"]   # KeyError on {info} — intended
    except Exception as exc:                         # noqa: BLE001
        print(f"skip {row['eventDate']}: {type(exc).__name__}")   # never str(exc) — it carries the URL
        continue
    calls.append((row["eventDate"], turns))
    issuer = issuer or issuer_from_turns(turns)      # the corpus names itself; do not guess
    time.sleep(0.7)                                  # unofficial endpoint; be a polite client

print("issuer:", issuer)                             # sanity-check this before trusting a count
sides = Counter(classify_side(t, issuer) for _, turns in calls for t in turns)
print(sides)
print("outside firms:", sorted({t["company"] for _, ts in calls for t in ts
                                if classify_side(t, issuer) == OUTSIDE}))

docs = [
    (date, " ".join(flatten_turn(t) for t in turns
                    if classify_side(t, issuer) == MANAGEMENT))   # analysts ask; management discloses
    for date, turns in calls
]
for stat in scan_concepts(docs, LEXICON):
    print(stat)
```

~78 seconds for a 76-call corpus. Write the JSONL to your scratchpad if you want to
re-search without re-fetching; never to `data/` and never to `research/`.

**Check the `issuer` and the `outside firms` list before you trust any count.** If a
division of the company ("Verizon Consumer Group") shows up under *outside firms*, the
issuer string is wrong and every `df` below it is understated.

### Reading the result

- **`classify_side` is the correctness property.** A hit for "market share" is a
  *disclosure* if the CFO said it and a *question* if Goldman asked it. Filter to
  `MANAGEMENT` before you count anything, or you will cite an analyst's premise as
  the company's own claim.
- **Report `df` and seasons, never hit counts.** Management reads the same script
  every quarter. Verizon's corpus has 82 raw mentions of "market share" and 39
  documents across 8 years; the first number is not evidence of anything.
- **`LEXICON` is fixed before you see the ticker.** That is deliberate — it cannot be
  anchored by what you already noticed. Add ticker-specific probes *after* running
  it, as a supplement, never as a replacement. You cannot generate the question you
  do not know to ask; the fixed list is what covers for that, imperfectly.

### Quartr, not EDGAR

These are *transcriptions*, produced by a third party. The words are management's;
the text is not.

- Qualitative framing, tone, and emphasis are usable, cited as **primary, transcribed**.
- **Any number** that is load-bearing for the thesis must be corroborated against the
  printed filing — the earnings release, the slides, the 10-Q — before it counts as a
  fact. A misheard "15%" for "50%" is silent, and it does not look like colour. It
  looks like a quote.
- `summaryShort` and `summaryLongHtml` are AI-generated. Low-confidence, always.
