# research/ideas/

Output of the `kill-video-concepts` skill: concepts mined from one video at a
time and run through its seven-gate kill gauntlet.

- `ledger.log` — **append-only and tracked**. One line per concept as the video
  stated it, survivor or corpse, in the format its header states. Most lines are
  corpses; that is the design. It exists so a sibling video cannot re-propose an
  idea this repo already killed, and so the kill distribution across gates is
  measurable. The gate-budget freeze in
  `.claude/skills/kill-video-concepts/SKILL.md` is revisited when it holds
  twenty concepts.
- `<YYYY-MM-DD>-<slug>.md` — one file per surviving concept: landing zone, the
  table or view shape it would take, and a measurement plan.

These are **proposals, not decisions**, and not a data source. Nothing in
`sources/` reads this directory. Git supplies the history and the diffs.
