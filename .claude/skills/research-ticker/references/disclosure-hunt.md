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
- **Earnings-call transcripts.** For a deep look, read many years. The point
  is not the quarter; it is learning what management has and has not ever said.

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
