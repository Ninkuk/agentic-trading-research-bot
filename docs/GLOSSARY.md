# Glossary

Plain-English definitions of the terms you'll meet on the
[dashboard](https://ninkuk.github.io/agentic-trading-research-bot/), in the `research/`
notes, and in the developer guide. Simplified on purpose — each entry is the
gist, not the full story.

**Screener** — one of the small programs here that visits a single official
data source and files away what it finds. There are about seventeen, one per
source.

**Monitor** — like a screener, but instead of measuring today it keeps a
calendar of upcoming events: central-bank meetings, company earnings dates,
market holidays.

**Combiner** — a program that reads what the screeners and monitors collected
and derives something from it: an overall market opinion, a stock scorecard, a
report card on past opinions. Combiners never fetch anything from the internet.

**Market regime** — a one-line summary of the market's overall mood (roughly:
calm, nervous, or stressed), distilled from many indicators at once.

**Z-score** — a way of saying "how unusual is today's number compared with its
own history?" Zero means perfectly typical; +2 or −2 means rare. Used here to
spot readings worth a second look.

**Short interest** — how many of a company's shares investors have borrowed and
sold, betting the price will fall. High short interest means many people are
betting against the stock.

**Fails-to-deliver (FTD)** — trades where the seller didn't hand over the
shares on time. Occasional fails are plumbing noise; persistent ones can hint
at stress or heavy short-selling in a stock.

**Dark pool (ATS)** — a private marketplace where large investors trade shares
away from the public exchanges. The trades are real and eventually reported;
"dark" refers to the order book not being publicly visible.

**Put/call ratio** — compares the volume of bets that prices will fall (puts)
against bets that they'll rise (calls). An unusually high ratio suggests
widespread nervousness.

**VIX** — a widely quoted index of how much turbulence traders expect over the
next month, often called the market's "fear gauge." Low ≈ complacent; high ≈
frightened.

**OPEX** — options-expiration day, when a large batch of options contracts
expires at once (typically the third Friday of the month). Markets can behave
oddly around it, so the calendar here tracks it.

**Yield curve** — the pattern of interest rates on government debt from short
loans to long ones. Normally longer loans pay more; when the curve "inverts"
(short rates above long rates), it has historically preceded recessions.

**COT / positioning** — the Commitments of Traders report, a weekly government
publication showing what large professional traders are betting in futures
markets. Extreme positioning can mark crowded trades.

**Backtest** — replaying the system's rules against past data to see how they
*would* have done — using only the information that was actually available on
each historical day, so the replay can't cheat by peeking at the future.

**Forward return (paper outcome)** — how a stock actually performed in the
weeks *after* the system flagged it. "Paper" means graded on the record only;
no money moved.

**Settings UI** — `uv run python config_ui.py`; a local browser page that
edits `.env` (the file holding your keys and tuning knobs) safely, with API
keys shown masked.

**ATR (average true range)** — a measure of how much a stock typically bounces
around in a single day. Higher ATR means more volatility; used here to size
positions—bigger ATR, smaller bet.

**Book heat / Heat** — a summary of how much money is riding on your current
holdings, adjusted for market swings. High heat means concentrated risk; useful
for knowing whether the portfolio is humming quietly or wearing thin.

**Coverage** — how much of the full picture actually has data behind it. On
the ticker scorecard it's the share of the signals that could have had an
opinion on a stock tonight that actually did — low coverage means the score
rests on just a few inputs, not the whole roster. On the book-heat panel
it's the share of your holdings' value where a real risk read (an ATR) was
available to size it — low coverage means the heat number is missing
pieces of the book.

**Hit rate** — in the backtester's report, the percentage of time the system's
opinion was right (price went the way it was flagged). Always read alongside the
benchmarks—if prices drift up anyway, a bearish flag "wins" by doing nothing.

**Confidence interval (CI)** — a range around a measured result that's probably
correct, expressed as "the true answer is here about 95% of the time." A wide
interval means less certainty; a narrow one means more.

**Piotroski score** — a simple nine-factor check of a company's financial health,
ranging from 0 (weak) to 9 (strong). Looks at profitability, asset quality, and
cash flow—rough, but a useful beginning-of-funnel filter.

**Risk-on / risk-off** — the market's mood in broad strokes. "Risk-on" means
investors are buying stocks and taking chances; "risk-off" means they're
retreating to safe havens like bonds and cash.

**Score (composite score)** — the nightly sum of a ticker's signal votes.
Positive means more bullish signals fired than bearish ones. The size says how
lopsided the vote was, not how far the price will move.

**Base rate** — how often the benchmark moved that way anyway. A hit rate only
means something when it beats this number; otherwise the "wins" were just the
market drifting.

**Edge** — hit rate minus base rate. A positive edge means the signal called
direction better than the market's own drift; zero means it added nothing.

**Excess (excess return)** — how much better or worse a stock did than the
benchmark over the same stretch. Positive excess means it beat the market, not
just that it went up.

**Directional excess** — excess return counted in the direction the signal
called. A bearish flag earns positive directional excess when the stock does
*worse* than the market.

**RSI (relative strength index)** — a 0-to-100 gauge of how hard a stock has
been bought or sold lately. Below about 30 usually reads as oversold; above 70,
overbought.

**ROIC (return on invested capital)** — how much profit a company earns on
each dollar tied up in the business. A steady double-digit ROIC is a mark of
quality.

**FCF yield (free cash flow yield)** — the spare cash a business generates in
a year, divided by the price of the whole company. Higher means each dollar of
cash costs you less to own.

**Market cap (market capitalization)** — the total price tag on all of a
company's shares put together.

**Reverse DCF (implied return)** — instead of guessing what a stock is worth,
hold the cash-flow assumptions fixed and solve for the yearly return today's
price already bakes in. A high implied return on cautious assumptions is
interesting; a low one on rosy assumptions is a warning.

**Hurdle (cost of equity)** — the return an investment has to beat to be worth
the risk: the safe Treasury rate plus a premium scaled by how volatile the
stock is. An implied return only means something next to this number.

**Equity risk premium (ERP)** — the extra yearly return investors demand for
holding stocks instead of Treasuries. Damodaran re-solves it monthly from the
market's own level; it is the market-wide half of the hurdle.

**Terminal value** — the part of a valuation covering everything past the
forecast years, usually most of the total. It leans on a "forever" growth
rate, which is why that one assumption gets policed hardest.

**Terminal growth** — the forever growth rate inside the terminal value.
Capped at the Treasury rate (nothing outgrows the economy forever), and real
growth above inflation has to be paid for with reinvested earnings.

**Data age** — how many days old the freshest input behind a number is. Small
means current; large means the reading is running on stale data.
