---
name: book-vs-spy-intraday
description: Use when the user asks how the portfolio/book/account is doing today against SPY, wants today's (or a past session's) intraday performance line, a "so far today" chart, or a $100-rebased book-vs-benchmark curve. Not for multi-day history (the dashboard's Portfolio-vs-SPY curve covers that).
---

# book-vs-spy-intraday

Today's stock book against SPY, both rebased to $100 at the prior close, as
a dashboard-styled line chart. The broker exposes no intraday portfolio
history, so the book is rebuilt as **today's quantities × each 5-minute
bar's close** — the dashboard's stock-book convention (cash and option legs
excluded). The pure core is `tools/book/intraday_curve.py`; this skill is
the fetch that lives outside it. Nothing here writes to any `data/*.db`.

## Steps

Files go in the session scratchpad (`$S` below); the build runs from the
repo root with absolute paths. `A` = the Robinhood account the repo tracks
(`get_accounts` → the one `agentic_allowed`, nickname "MCP").

1. **Clock.** `date -u`. DATE is the UTC date; a session is 13:30Z–19:55Z,
   78 five-minute bars (42 on a half day). Before 13:35Z there is nothing
   to chart — say so. Between 13:35Z and 20:00Z the page is "so far" and
   draws the untraded remainder dotted; after 20:00Z it is a closed session.
2. **Positions.** `get_equity_positions(A)`. Zero or option-only: stop,
   nothing to mark.
3. **Intraday bars.** `get_equity_historicals` with `interval: "5minute"`,
   `start_time: "<DATE>T13:30:00Z"`, no `end_time`, **at most 10 symbols
   per call, SPY counts as one of them**. Leave `bounds` unset (regular
   hours is the default).
4. **Prior closes.** `get_equity_historicals` with `interval: "day"`,
   `start_time` **five calendar days before DATE**, same batches. The tool
   takes each symbol's last daily bar strictly before DATE, so extra days,
   weekends, holidays and a partial bar for DATE itself are all harmless.
5. **Land every result in a file.** A result over the harness size limit
   is already saved: the error names its path under `tool-results/` — pass
   that path as-is. A result that came back inline is written to `$S` as
   the inner JSON object, verbatim (`cat > $S/bars-c.json <<'EOF' … EOF`),
   positions included. No number is ever re-typed from the chat.
6. **Build** (from the repo root; `-I` would hide `tools` from the module
   path):
   ```bash
   uv run python -m tools.book.intraday_curve --date <DATE> \
     --positions $S/positions.json --out $S/curve.json \
     --html $S/book-vs-spy-<DATE>.html <every historicals file, intraday and daily>
   ```
   `--session-bars` is the FULL session length (78 default, 42 on a half
   day), never bars-so-far — the tool derives `partial` and `bars_done`.
   Exit 2 names a symbol with no bars or no prior close: fetch it, never
   drop it (a missing name marks part of the book at zero). Exit 1 is a
   file that is not the MCP's JSON — re-save it.
7. **Verify** before showing: `close_book` in `curve.json` vs
   `get_portfolio(A).equity_value` (that field is the stock positions only;
   `total_value` adds cash). Within 0.5% passes (last 5-minute print vs live
   quote). Wider means a position or a bar batch is missing.
8. **Publish** the generated HTML as-is with the Artifact tool
   (`icon: "chart"`; no design pass, the page is the dashboard's own
   styling). A new session date is a new artifact; a refresh of the same
   date republishes the same file path. Report book, SPY and excess to two
   decimals, name `holdings[0]` (largest contribution) as the top mover,
   and say "so far, as of <last_label> Phoenix" when `partial`.

## Reading `curve.json`

- `points[0]` is the prior close at $100; `points[i]` is bar i's END on
  the Phoenix clock (`label`), so the first traded point is 6:35 AM and
  `bars_done` counts completed bars.
- `holdings` is sorted by `contrib` (weight × day return, in fractions of
  the $100 line); `thin` lists names that missed more than a tenth of the
  bars so far — their line is a staircase of real prints, never
  interpolated prices.
- `partial` + `bars_done` drive the dotted projection and the "now" rule
  on the page; the projection is the last value held flat, labelled as not
  yet traded, never a forecast.

## Common mistakes

| Mistake | Why it is wrong |
|---|---|
| Marking the book at the first bar's open | "Today" on the broker's own screen is vs the prior close; the gap at the open is part of the day |
| Plotting interpolated bars | They are gap-fill with zero volume; a thin name reads as a smooth line that never traded |
| Rebasing SPY at its open and the book at the prior close | Two different base times make the gap between the lines meaningless |
| Summing in cash or option legs | The dashboard curve is the stock book only; a mixed book is not comparable to its own history |
| Passing bars-so-far as `--session-bars` | The page would call a half-done morning a closed session |
| Re-typing bar closes from the chat | Transcription errors are silent; every number goes through a saved file |
| Treating the last bar as the official close | It is the last 5-minute print; `get_equity_quotes` carries the settled close, which this chart does not use |
