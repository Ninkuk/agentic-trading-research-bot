"""Every view in every source DB reaches the dashboard, or says why not.

The gate that keeps a new `v_*` from being SQL-only: build every DB from its
own ensure_schema (no rows), run the whole export with SQLite's authorizer
recording each view a section reads, and require each view to be (a) read
by a section, (b) named by a combiner's fetch/catalog (it reaches the page
as a regime input, scorecard signal, or advisor number), or (c) listed in
`coverage.UNSURFACED` with a reason. Reads are transitive — the authorizer
also reports the views a shown view is built from, and those are surfaced
by definition — so the allowlist holds only views nothing on the page
touches. Also runs every exporter against an empty schema, so a column
typo fails here rather than at 9:13pm.
"""

import re
import sqlite3
from pathlib import Path

import pytest
from dashboard_lib import coverage, data
from dashboard_lib.common import ro

NOW = "2026-07-09T04:12:00+00:00"
REPO = Path(__file__).resolve().parents[1]
_VIEW_RE = re.compile(r"\bv_[a-z0-9_]+\b")


@pytest.fixture(scope="module")
def schema_dir(tmp_path_factory):
    root = tmp_path_factory.mktemp("repo")
    d = root / "data"
    d.mkdir()
    # research-reopens resolves research/ as data's sibling.
    (root / "research").mkdir()
    (root / "research" / "verdicts.log").write_text("")
    for name, ensure in coverage.DB_SCHEMAS.items():
        conn = sqlite3.connect(d / name)
        ensure(conn)
        conn.commit()
        conn.close()
    return str(d)


def _views(db_path: Path) -> set[str]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'")}
    finally:
        conn.close()


def _combiner_named_views() -> set[str]:
    text = ""
    for p in (REPO / "sources" / "combiners").glob("*/fetch.py"):
        text += p.read_text()
    for p in (REPO / "sources" / "combiners").glob("*/catalog.py"):
        text += p.read_text()
    return set(_VIEW_RE.findall(text))


def _read_views_by_db(schema_dir: str, monkeypatch) -> dict[str, set[str]]:
    """Run the export with every read-only connection instrumented; returns
    {db file: views read}."""
    seen: dict[str, set[str]] = {}
    real_connect = sqlite3.connect
    # Resolved before patching: the spy must not call the patched connect.
    known = {db: _views(Path(schema_dir) / db) for db in coverage.DB_SCHEMAS}

    def spy_connect(database, *a, **kw):
        conn = real_connect(database, *a, **kw)
        db = Path(str(database).removeprefix("file:").split("?")[0]).name
        if db in known:
            views = known[db]

            def auth(action, a1, a2, dbname, src):
                if action == sqlite3.SQLITE_READ and a1 in views:
                    seen.setdefault(db, set()).add(a1)
                return sqlite3.SQLITE_OK

            conn.set_authorizer(auth)
        return conn

    monkeypatch.setattr(sqlite3, "connect", spy_connect)
    doc = data.export_data(schema_dir, NOW)
    monkeypatch.undo()
    errors = {sid: s["error"] for sid, s in doc["sections"].items() if s.get("error")}
    assert not errors, f"sections failed on an empty schema: {errors}"
    return seen


def test_every_view_is_surfaced_or_explained(schema_dir, monkeypatch):
    read = _read_views_by_db(schema_dir, monkeypatch)
    combiner = _combiner_named_views()
    missing = []
    stale = []
    for db in coverage.DB_SCHEMAS:
        for view in sorted(_views(Path(schema_dir) / db)):
            key = (db, view)
            on_page = view in read.get(db, set())
            if on_page and key in coverage.UNSURFACED:
                stale.append(key)
            if not (on_page or view in combiner or key in coverage.UNSURFACED):
                missing.append(key)
    assert not missing, (
        f"views with no dashboard card, no combiner consumer, and no UNSURFACED reason: {missing}"
    )
    assert not stale, (
        "UNSURFACED entries a section now reads (directly or under a shown view)"
        f" — delete them: {stale}"
    )


def test_unsurfaced_names_real_views(schema_dir):
    ghosts = [key for key in coverage.UNSURFACED if key[1] not in _views(Path(schema_dir) / key[0])]
    assert not ghosts, f"UNSURFACED names views that no longer exist: {ghosts}"


def test_every_section_has_about_blocks_and_one_sentence_note():
    """Design Memory: every card carries a one-sentence note and an About
    modal. A section without about blocks renders a card with no info icon."""
    bad = []
    for sid, _title, _db, _fn, kicker, note, about in data.SECTION_EXPORTERS:
        if not about or not all(h and b for h, b in about):
            bad.append((sid, "about"))
        if not note or note.count(". ") > 1:
            bad.append((sid, "note"))
        if kicker not in {
            "Macro",
            "Signals",
            "Research",
            "Track record",
            "Your book",
            "Ops",
            "Sources",
        }:
            bad.append((sid, f"kicker {kicker!r}"))
    assert not bad, bad


def test_section_ids_unique():
    ids = [s[0] for s in data.SECTION_EXPORTERS]
    assert len(ids) == len(set(ids))


def test_exporters_are_read_only(schema_dir):
    """Every exporter runs on a `mode=ro` connection; a write raises."""
    for _sid, _t, db, fn, *_ in data.SECTION_EXPORTERS:
        if not db.endswith(".db"):
            continue
        conn = ro(schema_dir, db)
        try:
            fn(conn, NOW)
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("CREATE TABLE _probe(x)")
        finally:
            conn.close()
