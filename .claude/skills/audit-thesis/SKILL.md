---
name: audit-thesis
description: Use when an outside writeup, video, interview, or letter covers a ticker that already has a thesis in research/ and the question is whether research-ticker missed something it says — "did we miss anything", "check the thesis against this video", "here's what a fund manager says about X". The benchmark may be pasted text, a file path, or a YouTube link. Not for producing research (research-ticker), stress-testing a thesis (kill-thesis), or mining a video for repo ideas (kill-video-concepts).
---

# audit-thesis

Read an outsider's claims against the thesis the repo already holds, and report
what the thesis lacks. The outsider is a **claim source, not a benchmark and not
an oracle**: every claim gets a tag, only a confirmed material miss reaches the
ledger, and the human decides where each finding goes.

**Decision support only.** Read `data/*.db` read-only. Never place an order or
name a size.

## Inputs

- **Thesis:** the latest `research/<TICKER>-<DATE>.md`. If none exists there is
  nothing to audit — say so and stop; `research-ticker` comes first.
- **Benchmark:** pasted text, a file path, or a YouTube URL. One benchmark per
  invocation. A multi-topic source (a weekly roundup, a portfolio review) is
  audited for every claim about the ticker, wherever it falls; the report names
  the timestamp or section ranges it used.

### A YouTube link

Fetch into the **scratchpad, never the repo**:

```bash
uvx yt-dlp --skip-download --write-subs --write-auto-subs \
  --sub-langs 'en-orig,en' --sub-format json3 --write-info-json \
  -o '<scratch>/bench.%(ext)s' '<URL>'
uv run python -m tools.research.youtube_captions <scratch>/bench.en.json3
```

`uvx`, not a bare `yt-dlp` — YouTube breaks old releases routinely. `json3`,
never `vtt` — vtt doubles every line of a rolling caption window. Prefer
`bench.en.json3` (human-authored) over `bench.en-orig.json3` (machine) when
both exist. Exit 2 means no cues: stop, there is no benchmark. If the fetch
fails (429, age gate, captions off), walk the user to **"Show transcript"**
under the video's description on youtube.com; the watch page itself carries
no captions. Read `upload_date` from `bench.info.json` — the dating rule
below depends on it.

Auto-captions carry no speaker labels and mishear numbers fluently (a control
video rendered "never gonna let you down" as "going to let you down"). A
figure or a negation heard in a caption is a lead to check, never evidence.

## Procedure

1. **Read the thesis** and list its date, load-bearing conditions, falsifiers,
   valuation inputs (FCF base, growth path, terminal, hurdle), and §7 sources.
2. **Inventory the benchmark:** every factual assertion, number, risk, and
   thesis pillar, each with its timestamp or location. Opinions count too —
   they become JUDGMENT rows, and they are where the disagreement lives. A
   claim made from a third-party chart or index may be restated in the
   company's own disclosed terms; the restatement is its own row, tagged on
   its own evidence, and the original keeps its tag.
3. **Tag every claim** with exactly one of:
   - `COVERED` — the thesis has it.
   - `JUDGMENT` — a different read of a genuine unknowable (terminal margin,
     a legal outcome). Not a gap.
   - `POST-THESIS` — dated after the thesis. Not a miss the thesis could have
     made; it is reopen evidence. Date from `upload_date` or the source's own
     dating, never from "last week" alone.
   - `EXPERT-WRONG` — conflicts with a primary source confirmed in step 4,
     whether the thesis cites it or this run fetched it.
   - `MISS` — a verifiable fact, available before the thesis date, that the
     thesis lacks.
   - `UNCONFIRMED` — would be MISS or EXPERT-WRONG but step 4 could not settle
     it.
4. **Verify before booking.** A `MISS` or `EXPERT-WRONG` stands only after the
   fact is confirmed at its primary source — the filing, the IR document, the
   press release — fetched during this run. Source tiers follow
   `research-ticker`'s data policy: primary filings first, then the
   already-integrated official sources, stockanalysis.com, and the broker tier
   only where nothing integrated covers the field. Cannot confirm →
   `UNCONFIRMED`, and the report says what document would settle it.
5. **Materiality** on each `MISS` and `POST-THESIS`: `material` if it touches
   a load-bearing condition, a falsifier, a valuation input, or the verdict;
   otherwise `minor`. Name the condition or input it touches.
6. **Cause** on each material `MISS`:
   - `source-acquisition` — the document is absent from §7 or was read only
     through a summarising fetch, never raw.
   - `in-hand` — the document is cited in §7; the fact sits in it unread.
   - `drift` — `research-ticker` already instructs the check that would have
     found it; the run did not perform it.
   The cause decides the fix form (below). Ask it before proposing anything.

## Report — fixed shape

```
audit-thesis <TICKER> · thesis <thesis-date> · benchmark <title or file>, <date>, <range used>

| # | Claim (short) | Where | Tag | Material | Cause | Evidence |
|---|---------------|-------|-----|----------|-------|----------|
one row per inventoried claim; Material/Cause blank where the tag makes them moot

Material misses: <n>   Post-thesis events: <n>   Unconfirmed: <n>
Ledger: <the lines appended to research/gaps.log, verbatim — or "none">

## Routing (proposed — nothing below is done until the human says so)
Thesis:      <kill-thesis re-run with the named attacks, or "none">
Corrections: <thesis-side factual errors found on the way, for that run — or "none">
Skill:       <a fix, only if the recurrence rule fires; else "no recurrence — none">
```

Then stop. The ledger append is the skill's own record and needs no approval;
everything under Routing waits for the human.

## Routing rules

**Thesis level.** A material `MISS` or `POST-THESIS` is handed to `kill-thesis`
as a named attack on that thesis; kill-thesis appends its own record to the
document and to `research/verdicts.log`, and a fired event is what the reopen
machinery in `research-sweep` reads. Never edit the thesis prose to close a
gap — the correction enters through kill-thesis or a reopen run, where it is
graded, or not at all.

**Ledger.** Append one line per confirmed material `MISS` to `research/gaps.log`
(create if absent) before reporting. It is append-only and public: no account
state, no prices.

```
<audit-date> <TICKER> thesis=<thesis-date> <cause> <slug> doc=<document-class> bench=<yt:<id> | file:<name> | paste>
```

`doc=` names the *kind* of document the fact lived in, from this list, because
recurrence groups on the exact string: `earnings-letter` (prepared remarks,
shareholder letter, IR financial update), `8-k-exhibit` (press release, Ex.
99), `call-transcript`, `10-k-<section>` / `10-q-<section>` (`mdna`,
`balance-sheet`, `segment-note`, `commitments-note`, `risk-factors`), `proxy`,
`13f`, `ir-site`. Add a class only when none fits, and say so in the report.
When a skill fix for a class lands, append `<date> FIX <cause> doc=<class>
commit=<sha>`; recurrence counts only the entries after the last FIX line for
that class, so a fixed class has to fail again before it is reopened.

**Skill level.** Propose a `research-ticker` / `kill-thesis` / `tools/` fix
only when `gaps.log` shows the same `<cause> … doc=<class>` on **two or more
distinct tickers**. One instance is an anecdote; the ledger exists so the
class can be seen. Form follows cause:

| Cause | Fix form | Verified by |
|---|---|---|
| `source-acquisition` | a **route** to the document (where it lives, how to fetch it raw) in `research-ticker` or `references/disclosure-hunt.md` | a fresh full `research-ticker` run on an affected ticker whose scratch dir holds the raw document |
| `in-hand`, `drift` | a **required output slot** in `references/thesis-template.md` | a fresh full run whose thesis fills the slot |

Neither class is visible to a micro-test: a 5-rep packet that hands the agent
the document cannot reproduce a fetch that never happened, and a reinforcing
clause for a check the skill already names has shown no delta at that scale.
Full-scale re-run or it did not happen. Editing the skills is still gated by
`writing-skills`.

## Guardrails

- Read-only against `data/*.db`; no orders, no sizing, no MCP payloads pasted
  into the conversation (exception type name only on error).
- Nothing in `research/` changes except the appended `gaps.log` lines, and
  those only after step 4 confirmed the fact.
- One benchmark, one report, then stop.
