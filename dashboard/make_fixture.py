"""Refresh src/fixtures/data.json with every section the Python exporter ships.

    uv run python dashboard/make_fixture.py

Builds the same synthetic DBs the Python tests use (tests/conftest.py's
builders, plus a schema-only DB for every other source) — never data/ —
exports the document, merges any section id the fixture lacks, and syncs
every existing section's `kicker` and list position to the exporter's.
Bodies and the hero/ticker/glossary blocks are left as they are, so the
hand-tuned rows the component tests rely on survive.
`tests/test_dashboard_sections.py::test_fixture_carries_every_section`
fails until this has been run for a newly added section.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "deploy" / "launchd"))

from dashboard_lib import coverage, data  # noqa: E402

from tests import conftest  # noqa: E402

FIXTURE = REPO / "dashboard" / "src" / "fixtures" / "data.json"
NOW = "2026-07-29T04:13:00+00:00"


def build_synthetic_dir(root: Path) -> str:
    d = root / "data"
    d.mkdir()
    conftest._build_composite_db(d / "composite.db")
    conftest._build_scorer_db(d / "scorer.db")
    conftest._build_advisor_db(d / "advisor.db")
    conftest._build_stocks_db(d / "stocks.db")
    conftest._make_fred_db(d / "fred.db")
    for name, ensure in coverage.DB_SCHEMAS.items():
        if (d / name).exists():
            continue
        conn = sqlite3.connect(d / name)
        ensure(conn)
        conn.commit()
        conn.close()
    research = root / "research"
    research.mkdir()
    (research / "verdicts.log").write_text("")
    return str(d)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        doc = data.export_data(build_synthetic_dir(Path(tmp)), NOW)
    fixture = json.loads(FIXTURE.read_text())
    added = []
    for sid, sec in doc["sections"].items():
        if sid not in fixture["sections"]:
            fixture["sections"][sid] = sec
            added.append(sid)
        else:
            fixture["sections"][sid]["kicker"] = sec["kicker"]
    order = {sid: i for i, sid in enumerate(doc["sections"])}
    fixture["sections"] = dict(
        sorted(fixture["sections"].items(), key=lambda kv: order.get(kv[0], len(order)))
    )
    FIXTURE.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")
    print(f"added {len(added)} section(s): {', '.join(added) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
