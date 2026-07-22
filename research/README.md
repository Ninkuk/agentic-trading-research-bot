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
