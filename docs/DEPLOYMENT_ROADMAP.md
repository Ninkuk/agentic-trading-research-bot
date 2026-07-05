# Deployment Roadmap (going live on this machine)

Parent tracker for turning the built-but-dormant system **on**: the outer
trigger that drives `main.py schedule --run`, and cleanup of the machinery
it replaces. The scheduler itself ships in `pipeline/scheduler/` — items
here are host-side (macOS today), deliberately outside the stdlib-only
codebase. Same status legend as [PIPELINE_ROADMAP.md](PIPELINE_ROADMAP.md).

## launchd tick — replaces the docstring cron line on macOS 💡

Origin: 2026-07-05 session. The cron wrapper documented in
`pipeline/scheduler/run.py`'s docstring depends on `flock`, which macOS
does not ship (verified absent on this machine) — the line is
Linux-deployment-only as written. On macOS the answer is launchd, which
makes the lock unnecessary rather than porting it: launchd never starts a
second instance of a running job label (that IS the single-runner
guarantee), and a `StartInterval` job missed during sleep fires once on
wake — which the scheduler's at-or-after triggers + idempotent trigger
keys absorb correctly.

Deliverables:

- `deploy/schedule-tick.sh` — cd repo, `set -a && . ./.env && set +a`
  (FRED/EIA/NASS keys + `PIPELINE_EQUITY` for promote), then
  `uv run python main.py schedule --run`. Absolute path to `uv`
  (launchd PATH is minimal).
- `deploy/com.agentic-trading-bot.schedule.plist` — `StartInterval` 900,
  `StandardOutPath`/`StandardErrorPath` → `schedule.log` (stderr must be
  captured: the leads legs' skip-and-continue warnings only exist there).
- `run.py` docstring note: Linux → cron+flock line as documented;
  macOS → this plist.

Known limitation (accepted for now): a LaunchAgent runs only while logged
in and awake — the 15:30 ET pre-close gate window needs the lid open.
Long-term answer is an always-on host; revisit once the gate runs live.

## Retire the `agentic-trades` LaunchAgents ✅

Done 2026-07-05: both predecessor jobs (`com.agentic.screener-pull` —
daily 05:30 pull, still active; `com.agentic.monitors` — hourly, log
silent since 2026-06-26 with ApeWisdom errors) unloaded and their plists
deleted from `~/Library/LaunchAgents/`. Templates remain in the old repo
(`~/Desktop/agentic-trades`) if ever needed.

Still open 💡: before deleting the old repo itself, check whether its
accumulated ApeWisdom history has backfill value for the crowding gate's
per-name baselines ([DEFENSES_ROADMAP.md](DEFENSES_ROADMAP.md)) —
attention-history depth is that design's one data hunger.
