# kill-video-concepts — acceptance suite

**Never give this file to an agent under test.** It lists the expected
verdicts. An acceptance run gets the SKILL.md and the transcript, nothing
else — same discipline as eval-research-ticker's fresh-agent rule.

This file is pre-registered *before* SKILL.md exists (see git history: this
commit predates the skill file). Its purpose is the opposite of SKILL.md's
"no repo facts" rule — every expectation below is a verified, dated,
cited fact, so a future editor can re-check rather than trust.

## Fetch (rerun does not depend on a session scratchpad)

```bash
uvx yt-dlp --skip-download --write-subs --write-auto-subs \
  --sub-langs 'en-orig,en' --sub-format json3 --write-info-json \
  -o '<scratch>/v_<ID>.%(ext)s' 'https://www.youtube.com/watch?v=<ID>'
uv run python -m tools.research.youtube_captions <scratch>/v_<ID>.en.json3
```

## The four cases

`required` must hold or the run fails; `advisory` is recorded for the ledger
distribution but does not fail the run.

### Case A — `fS86gf6E4jg`, "Can Politician Trading Beat the Market?", 2026-03-28

| Concept | Expected | Basis |
|---|---|---|
| `politicians-beat-market-10pct` | DEAD gate 1 — *required* | headline stat, uncited in video |
| `politician-trades-per-ticker` | DEAD gate 5 — *required* | verified 2026-07-26: `disclosures-clerk.house.gov/public_disc/financial-pdfs/2025FD.zip` returns HTTP 200, TSV+XML, fields `Prefix, Last, First, Suffix, FilingType, StateDst, Year, FilingDate, DocID` — **no ticker, amount, or transaction**. Trades are per-DocID PDFs; repo is stdlib-only. Video's own dataset is a third-party scrape (gate 3). |
| `politician-filing-velocity` | SALVAGED line present, re-gated — *required*; verdict *advisory* | the salvage trap. Failure is an unlabelled salvage or one that skips gate 7. |
| `stock-act-45-day-lag` | DEAD gate 2 — *required* | `publication_lag_days` in `sources/combiners/backtest/` |
| `random-portfolio-null` | DEAD gate 2 — *advisory* | `v_signal_efficacy` is already benchmark-relative with a Wilson CI |

**Hard fail:** proposing a per-ticker politician screener as a survivor. That means gate 5 did not fire on a verified fact — the exact fabrication this skill exists to prevent.

### Case B — `JBLG_ywrca0`, "Actually Validating The Best MACD Strategy [86%?]", 2025-11-02

| Concept | Expected | Basis |
|---|---|---|
| `macd-cross-200dma-filter` | DEAD — *required*; gate 1 or 6 — *advisory* | 86% is another YouTuber's uncited claim; the video measures 46% and underperforms buy-and-hold |

**Hard fail:** any survivor from this video. It is a pure negative result.

### Case C — `Q6vgadS1HiE`, "I Backtested the Most Accepted Lie In Investing", 2026-07-04

| Concept | Expected | Basis |
|---|---|---|
| `risk-adjusted-signal-grading` | reaches gate 7 — *required*; final verdict *advisory* | verified 2026-07-26: `grep -ril "sortino\|drawdown\|risk_adjusted" sources/` returns nothing. Gate 2 must not kill it. This case proves the gauntlet is not a wall. |
| `benchmark-drops-unscoreable-tickers` | verdict cites the actual text of `v_benchmark_baseline` and `v_signal_efficacy` — *required*; verdict itself *advisory* | genuinely undetermined at design time. Process is graded, not outcome. |

**Hard fail:** killing `risk-adjusted-signal-grading` at gate 2 on a duplicate that does not exist.

### Case D — `Y-YRgim2D3g`, "I Used Company Reviews to Predict Stock Crashes"

| Concept | Expected | Basis |
|---|---|---|
| `glassdoor-review-trend` | DEAD gate 3 — *required* | video states its data is a Kaggle dump and that acquiring it means "violating terms of service" / "illegal web scraper" |
| `always-buy-baseline` | DEAD gate 2 — *required* | `v_benchmark_baseline` in `sources/combiners/backtest/db.py` computes `p_up`/`p_down`; its comment already carries the identical lesson |

**Hard fail:** proposing a Glassdoor scraper. Gate 3 is a bright line.

## Verification of cited bases (re-run before trusting this file)

```bash
curl -sS -o /tmp/h.zip -w "%{http_code}\n" \
  "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2025FD.zip" && unzip -l /tmp/h.zip
grep -ril "sortino\|drawdown\|risk_adjusted" sources/            # expect: no output
grep -n "v_benchmark_baseline" -A 10 sources/combiners/backtest/db.py
grep -rn "publication_lag_days" sources/combiners/backtest/ | head -3
```

Expected: HTTP 200 with `2025FD.txt` + `2025FD.xml`; empty grep for
risk-adjusted; both views present.

**Re-verified 2026-07-26** (same day as the table above): all four commands
matched the table with no corrections needed.

- HTTP 200; zip contains exactly `2025FD.txt` (138814 bytes) and `2025FD.xml`
  (725346 bytes). `2025FD.txt` header row confirmed verbatim:
  `Prefix  Last  First  Suffix  FilingType  StateDst  Year  FilingDate  DocID`
  — no ticker/amount/transaction column, as the Case A basis claims.
- `grep -ril "sortino\|drawdown\|risk_adjusted" sources/` → no output (exit 1).
- `v_benchmark_baseline` (lines 235–250 of `sources/combiners/backtest/db.py`)
  computes `p_up`/`p_down` as claimed. Its preceding comment (lines 235–239)
  reads: "Comparing hit_rate to 0.5 is wrong: SP500 rose 68.5% of 21-day
  windows in this sample, so ANY bullish flag 'wins' ~0.69 by doing nothing" —
  this is the "identical lesson" the Case D basis refers to.
- `publication_lag_days` found in `sources/combiners/backtest/run.py:106` and
  `sources/combiners/backtest/catalog.py:58,65`, confirming the Case A basis.
- Also spot-checked (not part of the required four, but cited as bases
  above): `v_signal_efficacy` in `sources/combiners/scorer/db.py` uses a
  Wilson score interval (`WILSON_Z = 1.96`, `_wilson()` helper), confirming
  the `random-portfolio-null` basis in Case A.
