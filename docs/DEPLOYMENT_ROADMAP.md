# Deployment Roadmap (going live on this machine)

Parent tracker for turning the built-but-dormant system **on**: the outer
trigger that drives `main.py schedule --run`, and cleanup of the machinery
it replaces. The scheduler itself ships in `pipeline/scheduler/` — items
here are host-side (macOS today), deliberately outside the stdlib-only
codebase. Same status legend as [PIPELINE_ROADMAP.md](PIPELINE_ROADMAP.md).

## launchd tick — replaces the docstring cron line on macOS ✅

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

Built 2026-07-05: both deliverables shipped (`--db data/schedule.db
--data-dir data` pinned in the tick so every DB lives under `data/`; PATH
extended with `~/.local/bin` for the gate's claude-cli backend) and
verified with two real ticks — the first exposed that `.env` lacked
`PIPELINE_EQUITY`; it now carries `PIPELINE_EQUITY=200.37` +
`PIPELINE_FRACTIONAL=1`, and the retry tick promoted the first non-empty
candidate book (4 fractional positions). **One manual step remains** (a
session cannot self-authorize persistence):

```sh
cp deploy/com.agentic-trading-bot.schedule.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.agentic-trading-bot.schedule.plist
```

(Reverse with `launchctl bootout gui/$(id -u)/com.agentic-trading-bot.schedule`.)

## Retire the `agentic-trades` LaunchAgents ✅

Done 2026-07-05: both predecessor jobs (`com.agentic.screener-pull` —
daily 05:30 pull, still active; `com.agentic.monitors` — hourly, log
silent since 2026-06-26 with ApeWisdom errors) unloaded and their plists
deleted from `~/Library/LaunchAgents/`. Templates remain in the old repo
(`~/Desktop/agentic-trades`) if ever needed.

Resolved 2026-07-05 ✅: the old repo's ApeWisdom history
(`tools/data/reddit_velocity.db` — 79k hourly rows, 2026-06-20→07-05, subs
wallstreetbets/stocks/4chan) **was backfilled** into `data/reddit.db`
(3,790 observations, downsampled to one snapshot per day per sub, ranks
synthesized by mentions) — under its **original sub names as filters**,
NOT `all-stocks`: the old 3-sub counts are scale-incompatible with the live
aggregate series and would bias crowding baselines low (false kills eat the
3× headroom). The `4chan` series merges cleanly with the live `4chan`
filter (same ApeWisdom universe). The crowding gate reads `all-stocks`
only, so it self-arms after ~`crowding_min_n` (5) daily scheduler runs; the
preserved per-sub history stays queryable for Stage 6 calibration. The old
repo is now safe to delete whenever convenient (nothing else was mined
from it).
