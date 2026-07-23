---
name: setup
description: Get a fresh clone of this repo running — environment, keyless demo, API keys, optional nightly schedule. Use when the user says "set this up", "get this running", asks where to start after cloning, or hits a first-run failure.
---

# setup

Wrap `./setup.sh` — the script is the single source of truth for the
mechanical steps. This skill's job is to run it, watch it, diagnose failures
conversationally, and handle the parts a script can't: key signups and the
schedule decision.

## Guardrails

- Never overwrite an existing `.env`.
- Never install the launchd schedule without the user's explicit yes.
- No sudo, ever. Nothing in setup needs it.

## Procedure

1. Run `./setup.sh` from the repo root and watch the output. It is
   idempotent — safe to re-run after fixing anything.
2. When it prompts (uv install, schedule install), relay the question to the
   user rather than answering it yourself.
3. Diagnose instead of dumping:
   - `uv` missing and user declines the installer → point at
     https://docs.astral.sh/uv/getting-started/installation/ for the manual
     methods (brew, pipx), then re-run.
   - treasury/CBOE fetch failures → likely offline or blocked network. Note
     that `market_calendar` output still proves the pipeline works (it is
     computed locally, no network), and the fetches can be re-run later.
   - Hook wiring issues → `git config core.hooksPath .githooks` is the only
     thing being set; check it with `git config core.hooksPath`.
4. Offer the API-key walkthrough: for each of FRED / EIA / USDA NASS, give
   the signup URL from `.env.example`, wait for the user to paste the key,
   put it in `.env` (never in a committed file), then prove it works by
   running that one source, e.g.
   `uv run python main.py fred --db data/fred.db --keep-days 90`.
   After this first-run setup, ongoing tuning happens via
   `uv run python config_ui.py` (a local, loopback-only web UI) — prefer
   pointing the user there over hand-editing `.env`.
5. If the user is unsure about the schedule prompt: it installs per-job
   launchd agents (macOS only) that run the collectors and the nightly
   summary automatically; the undo is
   `uv run python deploy/launchd/install.py --uninstall`. `--dry-run` shows
   what would be installed without touching launchctl.
6. Finish by pointing at the dashboard the nightly jobs produce
   (https://ninkuk.github.io/agentic-trading-research-bot/ is the author's;
   theirs is `reports/dashboard.html`) and `uv run python main.py --list`.
