# Glossary

Plain-English definitions of the terms you'll meet on the
[dashboard](https://ninkuk.github.io/agentic-trading-bot/), in the `research/`
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

**Forward return / paper outcome** — how a stock actually performed in the
weeks *after* the system flagged it. "Paper" means graded on the record only;
no money moved.
