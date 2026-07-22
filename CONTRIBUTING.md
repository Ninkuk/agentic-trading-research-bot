# Contributing

This is a personal research project, developed in the open. Issues —
questions, bug reports, "this doc confused me" — are genuinely welcome.
PRs are too, with expectations set below so nobody's effort is wasted.

## Ground rules (non-negotiable invariants)

- **Zero runtime dependencies.** Everything runs on a plain Python 3.12
  checkout: `urllib`, `sqlite3`, stdlib only. Dev tools (`pytest`, `ruff`,
  `mypy`) are the only dependency group.
- **Tests are fully offline.** No network, no real API keys, no live
  fixtures. Network sits behind injectable seams; tests inject fakes.
- **Official primary sources only.** New data comes from the issuing
  agency, not an aggregator (one vetted historical exception exists).
  Propose a source in an issue before building a screener around it.
- **Nothing places a trade.** No order-generation code will be merged.

## The mechanics

```bash
./setup.sh                              # or: uv sync
git config core.hooksPath .githooks     # the same four gates CI runs, ~2s
uv run pytest && uv run ruff check && uv run ruff format --check && uv run mypy
```

The pre-commit hook runs all four gates; CI runs the identical set. A PR
that passes locally passes CI.

Architecture, the four-file screener shape, and the deeper invariants
(clock discipline, prune semantics, secret hygiene) are documented in
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) and [CLAUDE.md](CLAUDE.md) —
CLAUDE.md is written for AI-assisted development but is the contributor
reference for humans too.
