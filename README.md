# Agentic Trading Research Bot

[![CI](https://github.com/Ninkuk/agentic-trading-research-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/Ninkuk/agentic-trading-research-bot/actions/workflows/ci.yml)

**A research assistant for the stock market.**

Every day, this project visits about twenty official public sources — mostly
the U.S. government agencies and regulators that publish the country's economic
and market numbers — and files away what it finds. Every evening it re-reads
those files and writes up an opinion: what the market's overall mood looks
like, and which stocks currently stand out. A person reads those notes,
applies their own judgment, and makes every actual decision.

**It never buys or sells anything.** No code in this project can place a
trade. The only thing it does with a brokerage account is _look at it_ — read
which positions exist, so its notes can take them into account. The word "bot"
in the name describes where the project may eventually head; the current,
deliberate stage is proving the research is any good before anything is ever
allowed to act on it.

## See it working

The nightly summary is published as a small website:

**<https://ninkuk.github.io/agentic-trading-research-bot/>**

It regenerates every evening around 9pm Phoenix time. What you're looking at:
a snapshot of the market's overall condition according to the collected data, a
scorecard of stocks the system currently finds notable, and a running record of
how its past opinions actually worked out. Any term you don't recognize is
probably in the [glossary](docs/GLOSSARY.md).

## How it works, in plain words

Three kinds of programs, doing three jobs:

- **Collectors.** About twenty small programs, each responsible for one
  official source: the Federal Reserve's economic statistics, stock-market
  regulators' filings, the weekly report on what professional futures traders
  are betting, Treasury auction results, energy and agriculture statistics, and
  so on. Each fetches its source's latest numbers on a schedule and files them
  away. A few keep calendars instead: when the central bank next meets, when
  companies report earnings, when the market is closed.
- **Opinion-writers.** A second set of programs reads everything the collectors
  filed and writes an opinion: a one-line summary of the market's mood, plus a
  scorecard pointing out stocks whose numbers look unusual. They only read —
  they never fetch anything themselves, and never act on anything.
- **The report card.** The part that makes this more than a pile of opinions: a
  grader goes back and checks how each past opinion actually turned out over
  the following weeks. Signals with a poor track record get exposed by their
  own numbers — and a human, reading that track record, decides whether to
  keep, adjust, or retire them. Nothing tunes itself automatically.

That last part is the point of the whole project: **measure first, trust
later, act last.**

## Where the AI comes in

The "agentic" part: an AI assistant (Anthropic's Claude) operates parts of the
system by following small written playbooks — called _skills_ — that are
version-controlled right here in the repository (`.claude/skills/`). Claude
takes the daily read-only snapshot of the brokerage account, syncs the trade
journal, researches individual stocks into the write-ups in `research/`, and
then plays devil's advocate against its own write-ups before a human acts on
them. The same house rule binds the AI as everything else here: it reads data
and writes notes — it cannot place a trade, and a human makes every decision.

## Questions you might have

**Does it trade?** No. There is no order-placing code in this repository. It
reads public data and one brokerage account's positions; it writes notes.

**Is this financial advice?** No. It's one person's research tooling,
published openly. See the disclaimer below.

**Where does the data come from?** Official public sources — the same
government and regulator websites anyone can visit (the Federal Reserve, SEC,
Treasury, and more), plus one vetted commercial data site.

**Why build this?** Most trading ideas sound convincing and quietly fail. The
premise here is to collect the data, write down every opinion the system
forms, and grade those opinions against what actually happened — _before_
trusting any of it with real decisions.

**Can I run it myself?** Yes, if you're comfortable with a terminal. Two
commands install what's needed, fetch a first round of data, and show you a
real result within a couple of minutes:

```bash
git clone https://github.com/Ninkuk/agentic-trading-research-bot.git
cd agentic-trading-research-bot && ./setup.sh
```

The setup asks before changing anything on your machine, and free API keys
are only needed later, for a few extra data sources.

Prefer not to fiddle with a terminal? If you use
[Claude Code](https://claude.com/claude-code), open the cloned folder and ask
it to _"set this up"_ — one of the playbooks that ships in this repository
walks the AI through the same setup, explains anything that fails, and helps
you sign up for the free keys. Details in the developer guide below.

## For developers

Setup, architecture, and contribution notes live in
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Disclaimer

This is a personal research project — not investment advice, not a product,
and not audited. The write-ups in `research/` are one person's working notes
on specific stocks, published to show what the tooling produces, not as
recommendations. All data comes from public sources under their respective
terms; if you point this code at those sources, respecting their rate limits
and usage policies is your responsibility.
