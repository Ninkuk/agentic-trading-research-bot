# research/

One markdown thesis per ticker per research session, written by the
`research-ticker` skill and reviewed by a human:
`research/<TICKER>-<YYYY-MM-DD>.md`.

These are **decision support, not decisions**, and not a data source. Nothing
in `sources/` reads this directory. Git supplies the history and the diffs.

A `theses` table in `scorer.db` is deliberately deferred until enough
documents exist here to show which fields are actually reached for.

`verdicts.log` is the kill-thesis verdict ledger — one line per verdict, in
the format its header states. It exists so "have verdicts skewed toward
UNPROVEN?" is answerable with data; the one-way-check freeze in
`.claude/skills/kill-thesis/SKILL.md` is revisited when it holds ten lines.

A verdict line may carry the thesis's stated revisit trigger as
`reopen=<YYYY-MM-DD>:<slug>` (dated) or `reopen=event:<slug>` (undated). Both
are listed on the dashboard's research-reopens section; a dated trigger for a
held ticker due within +/-7 days also surfaces in that section's checkpoints
list. A dated trigger that has arrived is also worklist B of the
`research-sweep` skill (`tools/research/worklist.py`), which re-researches
it; `event:` triggers stay grep-only there. The slug is a pointer; the thesis
file holds the actual condition.
Only a ticker's newest verdict line counts: re-researching a name retires
the older thesis's trigger.
