# Layer-1 Source Tree Restructure — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Scope:** Pure file/package reorganization. No behavior, schema, signal, or CLI
dispatcher-name change. `main.py fred --db fred.db` etc. keep working identically
after this lands.

## Goal

All 20 screeners and monitors currently live as flat top-level directories,
sharing the root with `registry.py`, `screener_common.py`, `monitor_common.py`,
`http_client.py`, `docs/`, and `tests/`. Before starting on the signal→candidate
pipeline described in `docs/research/2026-07-03-signal-to-candidate-pipeline.md`
("layer 2"), nest the existing layer-1 packages under one `sources/` root so:

- the repo root stays uncluttered when layer 2's package(s) are added later
  (its name is intentionally undecided — this restructure doesn't reserve or
  guess it)
- the already-real architectural line between screeners (`screener_common`
  consumers, 16 packages) and monitors (`monitor_common` consumers, 4 packages)
  becomes visible in the file tree, not just in `docs/ROADMAP.md` prose

This is a mechanical rename/move, not a design change to any screener/monitor's
internals — the payoff is entirely organizational.

## Final tree

```
agentic-trading-bot/
├── main.py
├── registry.py                     # stays at root — CLI dispatch table, not source-specific
├── sources/
│   ├── __init__.py
│   ├── common/
│   │   ├── __init__.py
│   │   ├── screener_common.py      # was repo-root
│   │   ├── monitor_common.py       # was repo-root
│   │   └── http_client.py          # was repo-root
│   ├── screeners/                  # screener_common consumers (16)
│   │   ├── __init__.py
│   │   ├── cftc_screener/
│   │   ├── edgar_screener/
│   │   ├── fred_screener/
│   │   ├── ftd_screener/
│   │   ├── finra_short_volume/
│   │   ├── finra_short_interest/
│   │   ├── finra_ats/
│   │   ├── cboe_options/
│   │   ├── cboe_stats/
│   │   ├── sec_fundamentals/
│   │   ├── treasury_screener/
│   │   ├── nyfed_screener/
│   │   ├── eia_screener/
│   │   ├── usda_screener/
│   │   ├── reddit_screener/
│   │   └── stock_analysis_screener/
│   └── monitors/                   # monitor_common consumers (4)
│       ├── __init__.py
│       ├── econ_calendar/
│       ├── market_calendar/
│       ├── fomc_calendar/
│       └── earnings_calendar/
├── docs/
└── tests/                          # unchanged — stays flat, see below
```

Each screener/monitor package keeps its existing internal four-file shape
(`fetch.py` / `db.py` / `run.py` / `catalog.py`) untouched — only its parent
directory and its import path change.

## Import mechanism: true dotted imports (no path shims)

`cftc_screener` becomes importable as `sources.screeners.cftc_screener`;
`screener_common` becomes `sources.common.screener_common`; etc. This is the
only approach used — no `sys.path` injection, no pytest-only `pythonpath` trick
that would let physical location and import path diverge. The alternative
(inject `sources/screeners`, `sources/monitors`, `sources/common` onto
`sys.path` so old unqualified imports keep working) was considered and
rejected: it would need to work identically under `pytest` and under
`uv run python main.py`, which are different runtimes, and it would introduce
exactly the kind of implicit magic this stdlib-only, explicit-by-design repo
otherwise avoids. Dotted imports mean the directory tree *is* the import
graph — no tool needs to be taught otherwise.

Every cross-file reference that names a moved module gets its prefix updated:

- **`registry.py`** — all 20 `from <pkg>.run import main as ...` lines gain
  the `sources.screeners.` or `sources.monitors.` prefix.
- **Every screener's `db.py`** (16 files) — `from screener_common import ...`
  → `from sources.common.screener_common import ...`.
- **Every monitor's `db.py`/`run.py`** (4 packages) — `from monitor_common
  import ...` → `from sources.common.monitor_common import ...`.
- **Every `fetch.py` that uses the shared HTTP client** — `from http_client
  import ...` → `from sources.common.http_client import ...`. This includes
  the process-wide `SEC_RATE_LIMITER` singleton keyed on `SEC_HOST_KEY` —
  moving the module doesn't change its singleton semantics, only its import
  path, so the shared per-IP SEC throttle across `edgar`/`ftd`/`fundamentals`
  is unaffected.
- **The two existing cross-screener imports** (the only ones in the repo):
  `sources/screeners/sec_fundamentals/fetch.py` importing
  `sources.screeners.edgar_screener.fetch`, and
  `sources/monitors/earnings_calendar/fetch.py` importing
  `sources.screeners.edgar_screener.fetch` and
  `sources.screeners.stock_analysis_screener.probe`.
- **Within-package self-imports** (e.g. `cftc_screener/run.py` doing `from
  cftc_screener import catalog, db, fetch`) — these already use the
  already-existing absolute style, not relative dots, so they simply gain the
  new prefix (`from sources.screeners.cftc_screener import catalog, db,
  fetch`); no change in *style*, only in the dotted path itself.
- **Every test file** that imports a moved module (~all of the ~118 files
  under `tests/`, since every test targets one screener/monitor's
  `catalog`/`fetch`/`db`/`run`, or one of the three common modules).

`sources/__init__.py`, `sources/common/__init__.py`,
`sources/screeners/__init__.py`, and `sources/monitors/__init__.py` are added
(empty) so these are ordinary packages, matching the existing convention (every
screener/monitor package already has its own `__init__.py`).

`pyproject.toml`'s `pythonpath = ["."]` and `testpaths = ["tests"]` need no
change — root stays on the path, and dotted imports resolve from root exactly
like the current flat ones do.

## Tests: directory stays flat, only import lines change

`tests/` keeps its existing flat layout and naming convention
(`tests/test_<name>_<layer>.py`, documented in `CLAUDE.md`). Mirroring
`sources/screeners/`/`sources/monitors/` into `tests/` was considered and
rejected — it would touch the same ~118 files for no benefit beyond cosmetics,
and it would contradict the convention `CLAUDE.md` already documents. Only the
import statements *inside* each test file change (gaining the
`sources.screeners.`/`sources.monitors.`/`sources.common.` prefix); file names
and locations are untouched.

## Docs that need updating as part of this move

- **`CLAUDE.md`** — the "Architecture: one shape, ~20 slices" and "Shared
  spine (repo root)" sections currently describe `registry.py`,
  `screener_common.py`, `monitor_common.py`, `http_client.py`, and every
  screener/monitor package as living at repo root. Update these to reflect
  `sources/screeners/`, `sources/monitors/`, `sources/common/`, and
  `registry.py` remaining at root.
- **`docs/FOLLOWUPS.md`** — one stale path mention, `usda_screener/wasde.py`,
  becomes `sources/screeners/usda_screener/wasde.py`.
- **`docs/ROADMAP.md`** — no change needed; it only names modules in prose
  (`registry.py dispatches all 20: stocks, reddit, ...`) and links to
  `docs/superpowers/specs/...`/`docs/superpowers/plans/...`, none of which
  move.

## What does NOT change

- **CLI dispatcher names** (`fred`, `cftc`, `econ_calendar`, etc.) — these are
  the string keys in `REGISTRY`, unrelated to Python import paths.
  `uv run python main.py fred --db fred.db` behaves identically before and
  after.
- **Database files, schemas, views** — nothing in `db.py` schema/view SQL
  changes; only its module's import path.
- **Any screener/monitor's fetch/parse/signal logic** — zero logic changes.
  This is enforced by the verification plan below (a green test suite is the
  proof nothing behavioral moved).
- **`.env`/`.env.example`, API keys** — unaffected.
- **Layer 2's location or name** — deliberately left undecided. This
  restructure's job is only to make room; naming and structuring the pipeline
  package is a separate future spec.

## Verification plan

1. **Full offline suite green:** `uv run pytest` (currently ~600 tests, <1s,
   no network) after every import is updated. This is the primary safety net —
   the suite is comprehensive enough that a green run is strong evidence the
   rename introduced no behavioral drift.
2. **Runtime smoke test outside pytest:** `uv run python main.py --list`
   (confirms `registry.py`'s 20 imports resolve at runtime, not just under
   pytest's `pythonpath`), plus one real dispatch of a key-free, pure-computed
   monitor — `uv run python main.py market_calendar --db /tmp/mc.db` — to
   confirm the full `main.py → registry → sources.monitors.market_calendar`
   chain executes end-to-end post-move.
3. **Grep sweep for stragglers:** after the move, `grep -rn
   "^from screener_common\|^from monitor_common\|^from http_client\|^from
   [a-z_]*_screener\|^from [a-z_]*_calendar" --include="*.py" .` (excluding
   `sources/` internals that correctly self-reference) should return nothing —
   any hit is a missed import update.

## Non-goals (YAGNI)

- **Grouping by upstream vendor** (e.g. an `sec/` dir bundling `edgar`, `ftd`,
  `fundamentals`). Considered and explicitly rejected in favor of the
  screener/monitor split, which the code already enforces structurally
  (`screener_common` vs `monitor_common`); a vendor grouping would be a second,
  overlapping taxonomy the code doesn't otherwise encode.
- **Deciding layer 2's package name or location now.** Out of scope — this
  spec only clears root-level space for it.
- **Changing any screener/monitor's internal four-file shape.** Untouched.
- **A `sources/__init__.py` that re-exports or aggregates anything.** Stays
  empty — it only exists to make `sources` an importable package.
