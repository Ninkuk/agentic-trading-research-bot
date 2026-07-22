#!/bin/bash
# Nightly autonomous research: select flagged/stale tickers, run
# /research-ticker headlessly per ticker (subscription auth — same headless
# pattern as portfolio_snapshot.sh). Decision support only: the Python
# orchestrator's allowlist is read-only; order tools are never granted.
set -uo pipefail
source "$(dirname "$0")/env.sh"

job_start "research nightly"
uv run python deploy/launchd/research_nightly.py
