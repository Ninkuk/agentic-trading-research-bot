#!/bin/bash
# Health check for the com.tradingbot.* schedule: per-job launchd state
# (last exit code), last log activity, and per-database freshness.
source "$(dirname "$0")/env.sh"

echo "== launchd state (PID / last exit code / label) =="
launchctl list | grep com.tradingbot | sort -k3

echo
echo "== last log line per job =="
for f in logs/*.log; do
    [ -e "$f" ] || continue
    printf "%-24s %s\n" "$(basename "$f" .log)" "$(tail -1 "$f")"
done

echo
echo "== database freshness (latest snapshot per DB) =="
for db in data/*.db; do
    latest=$(sqlite3 "$db" \
        "SELECT MAX(captured_at) FROM snapshots;" 2>/dev/null) || continue
    printf "%-28s %s\n" "$(basename "$db")" "${latest:-<no snapshots>}"
done
