#!/usr/bin/env bash
# One-command setup: toolchain, deps, git hook, .env, a keyless demo run,
# and (macOS, opt-in) the nightly launchd schedule. Idempotent — safe to
# re-run. Never uses sudo; never overwrites an existing .env.
set -euo pipefail
cd "$(dirname "$0")"

say() { printf '\n== %s\n' "$*"; }

# ---- 1. toolchain ----------------------------------------------------------
if ! command -v uv >/dev/null 2>&1; then
  echo "This project is run with uv (https://docs.astral.sh/uv/), which is not installed."
  read -r -p "Install uv now via its official installer? [y/N] " ans || ans=""
  if [[ "${ans:-}" =~ ^[Yy]$ ]]; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
  else
    echo "Install uv manually, then re-run ./setup.sh"
    exit 1
  fi
fi

say "Installing dependencies (uv reads .python-version -> Python 3.12)"
uv sync

say "Wiring the pre-commit hook (lint + format + types + tests, ~2s)"
git config core.hooksPath .githooks

if [[ -f .env ]]; then
  say "Keeping your existing .env (never overwritten)"
else
  say "Creating .env from .env.example (signup URLs for the free keys are inside)"
  cp .env.example .env
fi

# ---- 2. demo: three keyless sources ---------------------------------------
say "Demo: fetching three sources that need no API key"
uv run python main.py market_calendar --db data/market_calendar.db
uv run python main.py treasury --db data/treasury.db \
  || echo "   (treasury fetch failed — offline? The demo continues.)"
uv run python main.py cboe_stats --db data/cboe_stats.db \
  || echo "   (CBOE fetch failed — offline? The demo continues.)"

say "What your machine just produced:"
uv run python - <<'PY'
import pathlib
import sqlite3


def q(db, sql, label):
    p = pathlib.Path("data") / db
    if not p.exists():
        return
    rows = sqlite3.connect(f"file:{p}?mode=ro", uri=True).execute(sql).fetchall()
    if rows:
        print(f"\n{label}")
        for r in rows:
            print("   ", " · ".join(str(c) for c in r))


q("market_calendar.db",
  "SELECT event_date, title FROM v_next_opex",
  "Next option expiration:")
q("market_calendar.db",
  "SELECT event_date, title FROM v_upcoming_closures LIMIT 3",
  "Next market closures:")
q("treasury.db",
  "SELECT auction_date, security_type, security_term FROM v_upcoming_auctions LIMIT 3",
  "Upcoming Treasury auctions:")
q("cboe_stats.db",
  "SELECT vix_date, vix_close, total_pcr FROM v_latest_sentiment",
  "Latest VIX close / total put-call ratio:")
PY

# ---- 3. nightly schedule (macOS only, opt-in) ------------------------------
if [[ "$(uname)" == "Darwin" ]]; then
  echo
  read -r -p "Install the nightly launchd schedule so this runs itself? [y/N] " ans || ans=""
  if [[ "${ans:-}" =~ ^[Yy]$ ]]; then
    uv run python deploy/launchd/install.py
    echo "Installed. Undo anytime: uv run python deploy/launchd/install.py --uninstall"
  else
    echo "Skipped. Later: uv run python deploy/launchd/install.py   (cadence: docs/SCHEDULE.md)"
  fi
else
  echo "Scheduling here is macOS/launchd; docs/SCHEDULE.md documents the cadence to replicate with cron."
fi

say "Done. Next steps"
cat <<'EOF'
   * Free API keys unlock more sources (FRED, EIA, USDA) — signup URLs are in .env.example.
   * Change settings anytime: uv run python config_ui.py  (local browser page; keys shown masked)
   * Everything you can run:   uv run python main.py --list
   * Tests (offline, ~2s):     uv run pytest
   * Read next: README.md · docs/DEVELOPMENT.md · docs/GLOSSARY.md
EOF
