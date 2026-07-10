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

Call `coverage(index, ipo_date)` and print it *before* any hit list. Read `ipo_date`
with a plain, read-only query — the skill never writes to `data/*.db`:

```
sqlite3 data/stocks.db "SELECT ipoDate FROM v_latest WHERE symbol='VZ';"
-- 2000-07-03
```

`ipoDate` is NULL for roughly 45% of the 5,601-row universe — **including AT&T, this
section's own headline example** — because stockanalysis itself returns `ipoDate: None`
for those tickers. It is not a gap in this repo's screener:

```
sqlite3 data/stocks.db "SELECT ipoDate FROM v_latest WHERE symbol='T';"
-- (empty)
```

Treat a ticker missing from `v_latest` entirely the same way. Either case, pass
`ipo_date=None`; `coverage()` then returns `uncovered_years=None` instead of a number.
When that happens, report the corpus span (`n_calls`, `first`, `last`) and say plainly
that the pre-corpus history is unquantified. Never imply the corpus is complete, and
never write "management never said X" — that is the binding rule above, applied to the
missing-`ipoDate` case.

The index interleaves earnings calls with conference presentations. An earnings call
is many-to-one — many analysts, one management team — so management dominates the
turn count. A conference presentation is one-to-one: the host bank's moderator asks,
one executive answers, so the bank ties or beats management on turn count within that
single call. Elect the issuer once, from every fetched call pooled together, never
from one call — `rows[0]` is the most recent event, and for a name that does a lot of
conferences that is often a bank's, not the company's.

**Non-US listing?** Swap `/stocks/{TICKER}/` for `/quote/{exchange}/{TICKER}/`
in *both* `page_data` calls below (find the `@exchange/TICKER` slug via
`/symbol-lookup/?q=`). `/stocks/CSU/…` raises rather than 404s cleanly, so this
is silent breakage, not an obvious error. Pass `ipo_date=None` — `stocks.db` has
no row for a non-US name — and set `ISSUER_NAME` yourself, since there is then no
local name to elect from.

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
ISSUER_NAME = None   # set this yourself only if you already know the legal name —
                      # data/stocks.db has no company-name column, so there is no
                      # local source of truth to read it from

index = page_data(f"/stocks/{TICKER}/transcripts/")
if not isinstance(index, dict) or "transcripts" not in index:
    raise SystemExit(f"{TICKER}: no transcript corpus exists")   # BABA, TSM, SAP, SONY, pre-IPO SPACs
rows = index["transcripts"]

print(coverage(rows, ipo_date="2000-07-03"))   # PRINT THIS FIRST. From the sqlite3 SELECT
                                                # above; pass None if the row is NULL or absent

calls = []
for row in rows:
    try:
        body = page_data(f"/stocks/{TICKER}/transcripts/{row['detailSlug']}/")
        turns = body["transcriptQuarter"]["transcriptTurns"]   # KeyError on {info} — intended
    except Exception as exc:                         # noqa: BLE001
        print(f"skip {row['eventDate']}: {type(exc).__name__}")   # never str(exc) — it carries the URL
        continue
    calls.append((row["eventDate"], turns))
    time.sleep(0.7)                                  # unofficial endpoint; be a polite client

# Elect the issuer ONCE, after every call is fetched, from turns POOLED across all of
# them — never inside the loop above, and never from a single call.
# issuer_from_turns is the PRIMARY source: pooled across every fetched call it is
# live-verified correct, and the print below lets you eyeball it. Set ISSUER_NAME
# above only when you already know the legal name; never derive it from
# transcriptMeta.title — XOM's reads "ExxonMobil Holdings Corporation", and the
# company has no "Holdings", so matching on it would silently exclude its own turns.
pooled_turns = [t for _, turns in calls for t in turns]
issuer = ISSUER_NAME or issuer_from_turns(pooled_turns)

print("issuer:", issuer, "| pooled mode:", issuer_from_turns(pooled_turns))
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

**Check the printed `issuer` and the `outside firms` list before you trust any count —
every time, not just when something looks off.** A bank's name printed as `issuer`
means the election went wrong: `classify_side` will then label every real disclosure
`outside` and every analyst question `management`, and every `df` below it is
worthless. A division of the company ("Verizon Consumer Group") showing up inside
`outside firms` is the same failure from the other side — the issuer string doesn't
match the corpus's own spelling, so real management turns are being counted as
outside ones. Either sighting means stop and re-derive `issuer` before reading
anything scan_concepts prints.

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
