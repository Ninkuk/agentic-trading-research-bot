# Layer-1 Source Tree Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nest the 20 existing screener/monitor packages and the 3 shared "common" modules
under `sources/{screeners,monitors,common}/`, using true dotted imports, per
`docs/superpowers/specs/2026-07-03-source-tree-restructure-design.md`. Zero behavior change —
this is a pure mechanical rename verified by the existing offline test suite.

**Architecture:** Move files with `git mv` (preserves history), then rewrite every import
line that references a moved module via targeted `sed` passes (never hand-edit each of the
~140 touched files individually), then verify with the full test suite plus a runtime smoke
test outside pytest. Each task leaves the whole repo green before moving to the next.

**Tech Stack:** Python 3.12, `uv`, `pytest`, macOS (BSD) `sed`, `git mv`.

## Global Constraints

- **Zero behavior change.** No screener/monitor's `fetch.py`/`db.py`/`run.py`/`catalog.py`
  logic changes — only import lines and file locations. CLI dispatcher names (`fred`, `cftc`,
  `econ_calendar`, …) are unaffected.
- **Every task ends with `uv run pytest` reporting `626 passed`** (the current baseline,
  confirmed before this plan was written) — a regression in count or a failure means something
  beyond an import path broke, and must be fixed before moving to the next task.
- **Use `git mv` for every relocation**, never delete-and-recreate — this preserves file
  history.
- **macOS BSD `sed`**, not GNU: use `sed -i '' -E '...'` (note the empty string after `-i`).
  BSD `sed` does not support `\b` word-boundary — every substitution below matches on an
  explicit trailing space-or-dot instead (`[ .]`), which is safe here because none of the 20
  package names is a prefix of another (verified during design).
- **No new runtime dependencies, no schema changes, no `.env`/`.env.example` changes.**

---

### Task 1: Relocate the 3 shared common modules to `sources/common/`

**Files:**
- Move: `screener_common.py` → `sources/common/screener_common.py`
- Move: `monitor_common.py` → `sources/common/monitor_common.py`
- Move: `http_client.py` → `sources/common/http_client.py`
- Create: `sources/__init__.py` (empty), `sources/common/__init__.py` (empty)
- Modify (import-line rewrite only): every one of the 20 screener/monitor packages' `db.py`
  and/or `fetch.py`/`run.py` that imports `screener_common`, `monitor_common`, or
  `http_client`, plus the 10 test files that reference them directly (`test_screener_common.py`,
  `test_monitor_common_schema.py`, `test_monitor_common_views.py`, `test_monitor_common_write.py`,
  `test_http_client.py`, `test_ftd_fetch.py`, `test_econ_calendar_db_write.py`,
  `test_market_calendar_db_write.py`, `test_earnings_db_views.py`, `test_fomc_db_views.py`) —
  exact set is discovered by the grep commands below, not hand-enumerated, so nothing is missed.

**Interfaces:**
- Produces: `sources.common.screener_common`, `sources.common.monitor_common`,
  `sources.common.http_client` as the new import paths every later task's packages depend on.

- [ ] **Step 1: Confirm starting baseline is green**

Run: `uv run pytest -q`
Expected: `626 passed` (if this doesn't match, stop and investigate before proceeding — this
plan assumes a clean, fully-green starting point).

- [ ] **Step 2: Scaffold `sources/common/` and move the 3 files**

```bash
mkdir -p sources/common
git mv screener_common.py sources/common/screener_common.py
git mv monitor_common.py sources/common/monitor_common.py
git mv http_client.py sources/common/http_client.py
touch sources/__init__.py sources/common/__init__.py
git add sources/__init__.py sources/common/__init__.py
```

- [ ] **Step 3: Rewrite every `from screener_common import ...` line**

```bash
grep -rl "^from screener_common import" --include="*.py" . | grep -v __pycache__ \
  | xargs sed -i '' -E 's/^from screener_common import/from sources.common.screener_common import/'
```

- [ ] **Step 4: Rewrite every `from monitor_common import ...` line**

```bash
grep -rl "^from monitor_common import" --include="*.py" . | grep -v __pycache__ \
  | xargs sed -i '' -E 's/^from monitor_common import/from sources.common.monitor_common import/'
```

- [ ] **Step 5: Rewrite every `from http_client import ...` line**

```bash
grep -rl "^from http_client import" --include="*.py" . | grep -v __pycache__ \
  | xargs sed -i '' -E 's/^from http_client import/from sources.common.http_client import/'
```

- [ ] **Step 6: Rewrite the bare `import http_client` / `import monitor_common` forms**

These are bare-module imports (call sites use `http_client.foo(...)` /
`monitor_common.foo(...)`), so alias on import to avoid touching every call site:

```bash
grep -rl "^import http_client$" --include="*.py" . | grep -v __pycache__ \
  | xargs sed -i '' -E 's/^import http_client$/import sources.common.http_client as http_client/'
grep -rl "^import monitor_common$" --include="*.py" . | grep -v __pycache__ \
  | xargs sed -i '' -E 's/^import monitor_common$/import sources.common.monitor_common as monitor_common/'
```

- [ ] **Step 7: Verify no unrewritten references remain**

```bash
grep -rn "^from screener_common\|^from monitor_common\|^from http_client import\|^import http_client$\|^import monitor_common$" \
  --include="*.py" . | grep -v __pycache__
```

Expected: no output (empty).

- [ ] **Step 8: Run the full test suite**

Run: `uv run pytest -q`
Expected: `626 passed`

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "refactor: relocate screener_common/monitor_common/http_client to sources/common/"
```

---

### Task 2: Relocate the 16 screener packages to `sources/screeners/`

**Files:**
- Move: `cftc_screener/`, `edgar_screener/`, `fred_screener/`, `ftd_screener/`,
  `finra_short_volume/`, `finra_short_interest/`, `finra_ats/`, `cboe_options/`, `cboe_stats/`,
  `sec_fundamentals/`, `treasury_screener/`, `nyfed_screener/`, `eia_screener/`,
  `usda_screener/`, `reddit_screener/`, `stock_analysis_screener/` → each under
  `sources/screeners/<name>/`
- Create: `sources/screeners/__init__.py` (empty)
- Modify: `registry.py` (16 of its 20 import lines gain the `sources.screeners.` prefix), plus
  every package's own self-imports (e.g. `cftc_screener/run.py`'s
  `from cftc_screener import catalog, db, fetch`), the 2 known cross-package references
  (`sec_fundamentals/fetch.py` → `edgar_screener.fetch`; `earnings_calendar/fetch.py` →
  `edgar_screener.fetch` and `stock_analysis_screener.probe` — `earnings_calendar` itself
  doesn't move until Task 3, but its import *lines* pointing at these two screeners must be
  fixed now, since that's when the referenced modules move), and every test file that imports
  any of these 16 packages' modules.

**Interfaces:**
- Consumes: `sources.common.screener_common`, `sources.common.http_client` (from Task 1) —
  already correctly referenced inside each package from Task 1's rewrite, unaffected by this
  task's directory move.
- Produces: `sources.screeners.<name>` as the new import path for all 16 screener packages,
  which Task 3's monitor packages (specifically `earnings_calendar`) depend on.

- [ ] **Step 1: Move the 16 screener directories**

```bash
mkdir -p sources/screeners
for d in cftc_screener edgar_screener fred_screener ftd_screener finra_short_volume \
         finra_short_interest finra_ats cboe_options cboe_stats sec_fundamentals \
         treasury_screener nyfed_screener eia_screener usda_screener reddit_screener \
         stock_analysis_screener; do
  git mv "$d" "sources/screeners/$d"
done
touch sources/screeners/__init__.py
git add sources/screeners/__init__.py
```

- [ ] **Step 2: Rewrite every import of each of the 16 screener package names**

This single loop handles `registry.py`'s 16 lines, every package's own self-imports, the 2
known cross-screener references, and every test file's imports — all in one pass, since it
operates on file *content* regardless of where a file currently lives:

```bash
for pkg in cftc_screener edgar_screener fred_screener ftd_screener finra_short_volume \
           finra_short_interest finra_ats cboe_options cboe_stats sec_fundamentals \
           treasury_screener nyfed_screener eia_screener usda_screener reddit_screener \
           stock_analysis_screener; do
  grep -rl "^from ${pkg}[ .]" --include="*.py" . | grep -v __pycache__ \
    | xargs sed -i '' -E "s/^from ${pkg}([ .])/from sources.screeners.${pkg}\\1/"
done
```

- [ ] **Step 3: Verify no unrewritten references remain for these 16 names**

```bash
grep -rn "^from cftc_screener[ .]\|^from edgar_screener[ .]\|^from fred_screener[ .]\|^from ftd_screener[ .]\|^from finra_short_volume[ .]\|^from finra_short_interest[ .]\|^from finra_ats[ .]\|^from cboe_options[ .]\|^from cboe_stats[ .]\|^from sec_fundamentals[ .]\|^from treasury_screener[ .]\|^from nyfed_screener[ .]\|^from eia_screener[ .]\|^from usda_screener[ .]\|^from reddit_screener[ .]\|^from stock_analysis_screener[ .]" \
  --include="*.py" . | grep -v __pycache__
```

Expected: no output (empty).

- [ ] **Step 4: Run the full test suite**

Run: `uv run pytest -q`
Expected: `626 passed`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: relocate the 16 screener packages to sources/screeners/"
```

---

### Task 3: Relocate the 4 monitor packages to `sources/monitors/`

**Files:**
- Move: `econ_calendar/`, `market_calendar/`, `fomc_calendar/`, `earnings_calendar/` → each
  under `sources/monitors/<name>/`
- Create: `sources/monitors/__init__.py` (empty)
- Modify: `registry.py` (its remaining 4 import lines), each monitor's own self-imports (e.g.
  `earnings_calendar/run.py`'s `from earnings_calendar import db, fetch`), and every test file
  that imports any of these 4 packages' modules.

**Interfaces:**
- Consumes: `sources.common.monitor_common` (Task 1), `sources.screeners.edgar_screener`,
  `sources.screeners.stock_analysis_screener` (Task 2, already correctly referenced inside
  `earnings_calendar/fetch.py` from Task 2's rewrite — unaffected by this task's move).
- Produces: `sources.monitors.<name>` as the new import path for all 4 monitor packages.

- [ ] **Step 1: Move the 4 monitor directories**

```bash
mkdir -p sources/monitors
for d in econ_calendar market_calendar fomc_calendar earnings_calendar; do
  git mv "$d" "sources/monitors/$d"
done
touch sources/monitors/__init__.py
git add sources/monitors/__init__.py
```

- [ ] **Step 2: Rewrite every import of each of the 4 monitor package names**

```bash
for pkg in econ_calendar market_calendar fomc_calendar earnings_calendar; do
  grep -rl "^from ${pkg}[ .]" --include="*.py" . | grep -v __pycache__ \
    | xargs sed -i '' -E "s/^from ${pkg}([ .])/from sources.monitors.${pkg}\\1/"
done
```

- [ ] **Step 3: Verify no unrewritten references remain for these 4 names**

```bash
grep -rn "^from econ_calendar[ .]\|^from market_calendar[ .]\|^from fomc_calendar[ .]\|^from earnings_calendar[ .]" \
  --include="*.py" . | grep -v __pycache__
```

Expected: no output (empty).

- [ ] **Step 4: Run the full test suite**

Run: `uv run pytest -q`
Expected: `626 passed`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: relocate the 4 monitor packages to sources/monitors/"
```

---

### Task 4: Runtime smoke test, final sweep, and docs update

**Files:**
- Modify: `CLAUDE.md:37-71` (Architecture / Shared spine sections — update paths)
- Modify: `docs/FOLLOWUPS.md:40` (one stale `usda_screener/wasde.py` path mention)

**Interfaces:** none — this task only verifies and documents the completed move.

- [ ] **Step 1: Runtime smoke test outside pytest — dispatcher listing**

Run: `uv run python main.py --list`
Expected: all 20 names printed (`stocks`, `reddit`, `edgar`, `fred`, `cftc`, `ftd`,
`short_volume`, `short_interest`, `options`, `fundamentals`, `econ_calendar`,
`market_calendar`, `fomc`, `earnings`, `treasury`, `ats`, `nyfed`, `cboe_stats`, `eia`,
`usda`), confirming `registry.py`'s imports resolve at runtime (not just under pytest).

- [ ] **Step 2: Runtime smoke test — one real dispatch**

Run: `uv run python main.py market_calendar --db /tmp/mc_smoke.db`
Expected: exits 0, no traceback (`market_calendar` is key-free and pure-computed, so this
proves the full `main.py → registry → sources.monitors.market_calendar.run.main` chain
executes end-to-end post-move). Clean up: `rm -f /tmp/mc_smoke.db`

- [ ] **Step 3: Full-repo grep sweep for any straggler flat imports**

```bash
grep -rn "^from screener_common\|^from monitor_common\|^from http_client import\|^import http_client$\|^import monitor_common$\|^from cftc_screener[ .]\|^from edgar_screener[ .]\|^from fred_screener[ .]\|^from ftd_screener[ .]\|^from finra_short_volume[ .]\|^from finra_short_interest[ .]\|^from finra_ats[ .]\|^from cboe_options[ .]\|^from cboe_stats[ .]\|^from sec_fundamentals[ .]\|^from treasury_screener[ .]\|^from nyfed_screener[ .]\|^from eia_screener[ .]\|^from usda_screener[ .]\|^from reddit_screener[ .]\|^from stock_analysis_screener[ .]\|^from econ_calendar[ .]\|^from market_calendar[ .]\|^from fomc_calendar[ .]\|^from earnings_calendar[ .]" \
  --include="*.py" . | grep -v __pycache__
```

Expected: no output (empty). If anything shows up, fix it and re-run `uv run pytest -q`
before continuing.

- [ ] **Step 4: Update `CLAUDE.md`'s Architecture section**

In `CLAUDE.md`, find this exact block (currently lines 51-71):

```markdown
Exceptions to the four-file rule: `market_calendar/compute.py` (pure OPEX/holiday math),
`stock_analysis_screener/probe.py` + `typing.py` (SvelteKit `__data.json` "devalue" decoder),
`usda_screener/wasde.py`.

### Shared spine (repo root)

- **`registry.py`** — `REGISTRY` dict maps name → each screener's `main`; `dispatch()` routes
  `main.py <name> [args...]`. **A screener "ships" only once registered here** (this is the
  source of truth for `docs/ROADMAP.md`).
- **`screener_common.py`** — `connect()` (opens SQLite in **WAL** mode) and a generic snapshot
  cascade `prune()`.
- **`monitor_common.py`** — the event-date **monitor framework**: a forward `events` table keyed
  `(event_type, event_date, subtype)`, `upsert_events` (dates firm up in place: tentative →
  confirmed), `replace_forward_window` (cancellation-aware; **never touches past events**),
  `v_upcoming`/`v_imminent` views, and a snapshot-only prune. Monitors (`econ_calendar`, `fomc`,
  `market_calendar`, `earnings`, and Treasury's `v_upcoming_auctions`) build on this.
- **`http_client.py`** — bounded exponential-backoff `http_get` (honors `Retry-After`),
  `make_opener(headers)`, and a `RateLimiter` token bucket. Note the process-wide
  `SEC_RATE_LIMITER` (9 req/s) keyed on `SEC_HOST_KEY="sec.gov"` — **all** SEC fetchers
  (`edgar`, `ftd`, `fundamentals`) must acquire under that one key so the per-IP cap is shared,
  not doubled across `www.` / `data.` hosts.
```

Replace it with:

````markdown
Exceptions to the four-file rule: `sources/monitors/market_calendar/compute.py` (pure
OPEX/holiday math), `sources/screeners/stock_analysis_screener/probe.py` + `typing.py`
(SvelteKit `__data.json` "devalue" decoder), `sources/screeners/usda_screener/wasde.py`.

### File tree

Every screener/monitor package lives under `sources/`, nested by kind:

```
sources/
├── common/       # screener_common.py, monitor_common.py, http_client.py
├── screeners/    # 16 point-in-time data readers (import screener_common)
└── monitors/     # 4 event-date calendars (import monitor_common)
```

`registry.py` and `main.py` stay at repo root — `registry.py` is the CLI dispatch table, not a
source itself. Import a screener/monitor's internals as `sources.screeners.<name>.<module>` /
`sources.monitors.<name>.<module>`.

### Shared spine

- **`registry.py`** (repo root) — `REGISTRY` dict maps name → each screener's `main`;
  `dispatch()` routes `main.py <name> [args...]`. **A screener "ships" only once registered
  here** (this is the source of truth for `docs/ROADMAP.md`).
- **`sources/common/screener_common.py`** — `connect()` (opens SQLite in **WAL** mode) and a
  generic snapshot cascade `prune()`.
- **`sources/common/monitor_common.py`** — the event-date **monitor framework**: a forward
  `events` table keyed `(event_type, event_date, subtype)`, `upsert_events` (dates firm up in
  place: tentative → confirmed), `replace_forward_window` (cancellation-aware; **never touches
  past events**), `v_upcoming`/`v_imminent` views, and a snapshot-only prune. Monitors
  (`econ_calendar`, `fomc`, `market_calendar`, `earnings`, and Treasury's
  `v_upcoming_auctions`) build on this.
- **`sources/common/http_client.py`** — bounded exponential-backoff `http_get` (honors
  `Retry-After`), `make_opener(headers)`, and a `RateLimiter` token bucket. Note the
  process-wide `SEC_RATE_LIMITER` (9 req/s) keyed on `SEC_HOST_KEY="sec.gov"` — **all** SEC
  fetchers (`edgar`, `ftd`, `fundamentals`) must acquire under that one key so the per-IP cap
  is shared, not doubled across `www.` / `data.` hosts.
````

- [ ] **Step 5: Update the stale path mention in `docs/FOLLOWUPS.md`**

Change (line 40):
```
`usda_screener/wasde.py` (tolerant, fail-loud tidy-CSV parser) + `wasde_obs`
```
to:
```
`sources/screeners/usda_screener/wasde.py` (tolerant, fail-loud tidy-CSV parser) + `wasde_obs`
```

- [ ] **Step 6: Final full test suite run**

Run: `uv run pytest -q`
Expected: `626 passed`

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "docs: update CLAUDE.md and FOLLOWUPS.md for sources/ restructure"
```
