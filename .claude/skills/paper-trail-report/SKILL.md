---
name: paper-trail-report
description: Humanify the pipeline's error logs and decision ledgers into a plain-English digest — which gate killed what and why, gate alerts (clamps, agent errors, discarded vetoes), scheduler failures, and log warnings. Use when the user asks what the pipeline did, why something was rejected, or for a paper-trail/pipeline report.
---

# paper-trail-report

Read every failure surface and produce a digest a human can act on, instead
of raw rows. **Read-only by design**: open every DB with SQLite URI
read-only mode so zero writes are structurally possible —

```bash
sqlite3 "file:data/<name>.db?mode=ro" "<query>"
```

A missing DB or log file means that surface has no history yet (e.g. the
scheduler hasn't gone live) — say so in one line; it is not an error.

## Surfaces and queries

1. **Funnel kills** — `data/candidates.db`:
   ```sql
   SELECT id, captured_at, candidate_count, rejection_count, equity,
          regime_scalar, fractional FROM snapshots
   ORDER BY captured_at DESC LIMIT 5;
   SELECT gate, COUNT(*) AS n FROM rejections
   WHERE snapshot_id = (SELECT id FROM snapshots
                        ORDER BY captured_at DESC, id DESC LIMIT 1)
   GROUP BY gate;                                   -- = v_rejection_summary
   SELECT instrument, gate, reason FROM rejections
   WHERE snapshot_id = (SELECT id FROM snapshots
                        ORDER BY captured_at DESC, id DESC LIMIT 1);
   ```
2. **Gate ledger** — `data/gate.db`:
   ```sql
   SELECT * FROM v_gate_alerts;        -- clamps, agent errors, denies,
                                       -- DISCARDED vetoes (veto yet shares>0)
   SELECT * FROM v_delta_history ORDER BY run_id DESC LIMIT 10;
   SELECT * FROM v_decision_makers ORDER BY run_id DESC LIMIT 10;
   SELECT id, captured_at, window, decision_count, model_version
   FROM gate_runs ORDER BY captured_at DESC LIMIT 5;
   ```
3. **Scheduler** — `data/schedule.db` (may not exist until launchd is live):
   ```sql
   SELECT * FROM v_failures;           -- jobs whose last attempt errored
   SELECT * FROM v_recent_runs LIMIT 20;
   ```
4. **Skip-and-continue warnings** — `tail -200 schedule.log`, keep lines
   containing `warning:` (e.g. a leads leg that silently sat out a run, a
   missing reddit.db).

## Digest shape (follow this, plain English, no raw dumps)

> Yesterday's pre-close run promoted 4 of 19 leads; 14 died at the direction
> gate (shorts, expected), 1 at liquidity (UNG fell under the $10M floor).
> The gate vetoed nothing, but one veto was discarded below τ — third time
> this week, consider reviewing τ. The scheduler's fred job failed twice on
> Thursday (HTTPError) and recovered Friday. schedule.log shows the leads
> quality leg skipped Monday's run (fundamentals.db was mid-refresh).

- Lead with the most recent promote snapshot: X of Y leads promoted, kills
  grouped by gate with reasons translated (e.g. `direction / allow_short=False`
  → "shorts, expected on a cash account").
- Gate section: approvals/cuts/vetoes, every `v_gate_alerts` row explained;
  call out streaks in `v_delta_history` (rising `discarded_vetoes` or
  `clamps` = the agent is getting noisier → τ review).
- Scheduler section: only failures and anything still stuck (attempts
  exhausted).
- End with a short "worth a look" list — at most 3 bullets, each one action.

## Rules

- Never mutate any DB (mode=ro enforces this — do not open writable).
- Secret hygiene: `error` columns and log lines already carry type names
  only; never speculate secrets back in.
- If every surface is empty/absent, say exactly that: nothing has run yet.
