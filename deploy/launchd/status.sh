#!/bin/bash
# Health check for the com.tradingbot.* schedule: per-job launchd state
# (last exit code), last log activity, and per-database freshness.
source "$(dirname "$0")/env.sh"

# `launchctl list` prints 0 in its exit-status column both for "exited
# cleanly" and for "has never exited", so a job that has never run reads as a
# pass. install.py bootstraps every plist on each run, which resets `runs` to
# 0, so that ambiguity covers the whole table after any schedule edit. Ask
# `launchctl print` instead: it reports `(never exited)` distinctly.
echo "== launchd state (runs since load / last exit / label) =="
uid=$(id -u)
launchctl list | awk '/com\.tradingbot\./ {print $3}' | sort | while read -r lbl; do
    info=$(launchctl print "gui/$uid/$lbl" 2>/dev/null) || {
        printf "%-8s %-16s %s\n" "-" "NOT LOADED" "$lbl"
        continue
    }
    runs=$(printf '%s\n' "$info" | sed -n 's/^[[:space:]]*runs = \(.*\)$/\1/p' | head -1)
    last=$(printf '%s\n' "$info" | sed -n 's/^[[:space:]]*last exit code = \(.*\)$/\1/p' | head -1)
    case "$last" in
        0) state="ok" ;;
        "(never exited)") state="never ran" ;;
        *) state="FAILED exit $last" ;;
    esac
    printf "%-8s %-16s %s\n" "${runs:-?}" "$state" "$lbl"
done

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
