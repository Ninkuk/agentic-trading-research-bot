"""Generate the dashboard's data.json: the same accumulated pipeline state as
the legacy HTML generator (dashboard_lib/sections.py), exported as plain data
for a React frontend instead of server-rendered markup.

Mirrors dashboard_lib/sections.py's resilience contract: reads each source DB
with `sqlite3.connect("file:data/<db>?mode=ro", uri=True)`, strictly
read-only, and wraps every section in its own try/except so a missing DB, a
dropped view, or zero rows degrades to an `"error"` key on that section's
export rather than crashing the whole document. Nothing derived from the
exception ever leaves this module beyond `type(e).__name__` — never
`str(e)`/`repr(e)`, which can embed a DB path or (for a urllib error
upstream) a URL. A section registered here whose exporter fn doesn't exist
yet is simply absent from `SECTION_EXPORTERS` until its task lands; the
document as a whole always exports successfully — a total failure is the
caller's job to catch (mirrors dashboard.py's "generation failed" page: an
absent data.json would be worse than an honest error banner).
"""

import sqlite3
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from dashboard_lib import narrative  # noqa: E402
from dashboard_lib.glossary import load_glossary  # noqa: E402
from sources.common.clock import phx_date  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[3]

MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def _streak_nights(conn: sqlite3.Connection) -> int:
    """Leading run of consecutive nightly snapshots (newest-first) whose
    regime equals the latest snapshot's regime. Snapshot-grain (one
    market_regime row per snapshot by construction) — a regime change resets
    the run, and a `mixed` streak counts like any other regime. NEW SQL: no
    section in sections.py computes a streak (review-verified)."""
    rows = conn.execute(
        "SELECT m.regime FROM market_regime m"
        " JOIN snapshots s ON s.id = m.snapshot_id"
        " ORDER BY s.captured_at DESC"
    ).fetchall()
    if not rows:
        return 0
    latest = rows[0]["regime"]
    streak = 0
    for row in rows:
        if row["regime"] != latest:
            break
        streak += 1
    return streak


# _classify_regime (sources/combiners/composite/db.py) decides the regime
# from exactly three inputs — VIX level, VIX term-structure backwardation,
# and the high-yield spread (matching this section's own `note` prose
# below); the other eight tracked inputs never move the label. These
# thresholds mirror that function's own numbers so a driver row's "lean"
# reads consistently with the regime it explains; they are duplicated
# (not imported) because `_classify_regime`'s constants are module-private.
_VIX_RISK_ON_MAX = 20.0
_VIX_RISK_OFF_MIN = 25.0
_HY_SPREAD_WIDE = 4.0


def _lean_vix(vix: float | None) -> str:
    if vix is None:
        return "mid"
    if vix >= _VIX_RISK_OFF_MIN:
        return "off"
    if vix < _VIX_RISK_ON_MAX:
        return "on"
    return "mid"


def _lean_backwardation(back: int | None) -> str:
    if back is None:
        return "mid"
    return "off" if back else "on"


def _lean_hy_spread(hy: float | None) -> str:
    if hy is None:
        return "mid"
    return "on" if hy < _HY_SPREAD_WIDE else "off"


_REGIME_DRIVER_COLUMNS: list[dict[str, Any]] = [
    {"key": "input", "label": "Input", "numeric": False, "direction": None, "term": None},
    {"key": "value", "label": "Value", "numeric": True, "direction": None, "term": None},
    {"key": "lean", "label": "Lean", "numeric": False, "direction": None, "term": None},
]


def _regime(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    r = conn.execute(
        "SELECT regime, vix, inputs_present, inputs_expected,"
        " t10y2y, curve_inverted, hy_spread, vix_backwardation,"
        " equity_pcr_pctile, in_fomc_blackout, imminent_high_impact,"
        " days_to_opex, rrp_change, tga_change FROM v_latest_regime"
    ).fetchone()
    if r is None:
        return {
            "verdict": None,
            "tiles": [],
            "columns": _REGIME_DRIVER_COLUMNS,
            "rows": [],
            "empty": "no composite snapshot yet — fills after the first nightly run",
        }
    verdict = narrative.regime_verdict(r["regime"], _streak_nights(conn))
    tone = verdict["tone"] if verdict is not None else "mid"
    vix_band = None if r["vix"] is None else narrative.qualitative_band("vix", r["vix"])
    tiles = [
        {"label": "regime", "value": r["regime"], "band": None, "tone": tone},
        {"label": "VIX", "value": r["vix"], "band": vix_band, "tone": None},
        {
            "label": "inputs",
            "value": f"{r['inputs_present']}/{r['inputs_expected']}",
            "band": None,
            "tone": None,
        },
    ]
    rows = [
        {"input": "VIX level", "value": r["vix"], "lean": _lean_vix(r["vix"])},
        {"input": "10y–2y spread", "value": r["t10y2y"], "lean": "mid"},
        {"input": "yield curve inverted", "value": r["curve_inverted"], "lean": "mid"},
        {
            "input": "high-yield spread",
            "value": r["hy_spread"],
            "lean": _lean_hy_spread(r["hy_spread"]),
        },
        {
            "input": "VIX backwardation",
            "value": r["vix_backwardation"],
            "lean": _lean_backwardation(r["vix_backwardation"]),
        },
        {"input": "put / call percentile", "value": r["equity_pcr_pctile"], "lean": "mid"},
        {"input": "FOMC blackout", "value": r["in_fomc_blackout"], "lean": "mid"},
        {
            "input": "imminent high-impact event",
            "value": r["imminent_high_impact"],
            "lean": "mid",
        },
        {"input": "days to options expiry", "value": r["days_to_opex"], "lean": "mid"},
        {"input": "Fed RRP change", "value": r["rrp_change"], "lean": "mid"},
        {"input": "Treasury TGA change", "value": r["tga_change"], "lean": "mid"},
    ]
    return {"verdict": verdict, "tiles": tiles, "columns": _REGIME_DRIVER_COLUMNS, "rows": rows}


def _regime_timeline(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT s.captured_at, m.regime, m.vix FROM market_regime m"
        " JOIN snapshots s ON s.id = m.snapshot_id"
        " ORDER BY s.captured_at ASC"
    ).fetchall()
    if not rows:
        return {
            "rows": [],
            "empty": "no composite snapshots yet — fills after the first nightly run",
        }
    return {
        "rows": [
            {"date": phx_date(r["captured_at"]), "regime": r["regime"], "vix": r["vix"]}
            for r in rows
        ]
    }


# (series_id, tile label, qualitative_band metric) — the regime's three
# deciding inputs, same trio as _regime's `note` prose.
_FRED_DRIVER_SERIES = [
    ("T10Y2Y", "10y–2y spread", "t10y2y"),
    ("BAMLH0A0HYM2", "high-yield spread", "hy_spread"),
    ("VIXCLS", "VIX", "vix"),
]


def _macro_drivers(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    tiles: list[dict[str, Any]] = []
    for sid, label, metric in _FRED_DRIVER_SERIES:
        rows = conn.execute(
            "SELECT date, value FROM observations WHERE series_id = ?"
            " AND value IS NOT NULL ORDER BY date DESC LIMIT 90",
            (sid,),
        ).fetchall()
        values = list(reversed(rows))  # oldest-first
        if not values:
            tiles.append(
                {
                    "label": label,
                    "series_id": sid,
                    "value": None,
                    "delta": None,
                    "band": None,
                    "history": [],
                }
            )
            continue
        latest = values[-1]["value"]
        delta = latest - values[-2]["value"] if len(values) > 1 else None
        tiles.append(
            {
                "label": label,
                "series_id": sid,
                "value": latest,
                "delta": delta,
                "band": narrative.qualitative_band(metric, latest),
                "history": [{"date": row["date"], "value": row["value"]} for row in values],
            }
        )
    return {"tiles": tiles}


# (sid, title, db_name, fn, kicker, note) — same ids/titles/kickers/notes as
# sections.py's SECTIONS; prose copied verbatim from sections.py:907-940.
# Grows through Tasks 5-8 as the remaining sections register.
SECTION_EXPORTERS: list[tuple[str, str, str, Callable[..., dict[str, Any]], str, str]] = [
    (
        "regime",
        "Regime",
        "composite.db",
        _regime,
        "Macro",
        "The market's mood. The label is decided by three inputs — the VIX, its term structure, and high-yield spreads; the other seven are tracked and shown but do not move it. “Risk-on” means"
        " money is flowing toward risk; the VIX is a fear gauge — lower is"
        " calmer. Open the drivers to see which inputs argued which way.",
    ),
    (
        "regime-timeline",
        "Regime timeline",
        "composite.db",
        _regime_timeline,
        "Macro",
        "The colored strip is the regime verdict itself, one cell per day —"
        " green risk-on, red risk-off, gray mixed. How the market mood and"
        " the VIX fear gauge have moved across recent nightly snapshots."
        " Each dot is one snapshot; higher = more fear; color = that"
        " night's regime.",
    ),
    (
        "macro-drivers",
        "Macro drivers",
        "fred.db",
        _macro_drivers,
        "Macro",
        "The regime's three deciding inputs with their recent history: the"
        " 10y–2y Treasury spread, the high-yield credit spread, and the VIX."
        " Each tile is today's value, the one-day change, and the last 90"
        " observations' trend.",
    ),
]


def _ro(data_dir: str, db_name: str) -> sqlite3.Connection:
    """Read-only connection to `<data_dir>/<db_name>` — never write access."""
    conn = sqlite3.connect(f"file:{Path(data_dir) / db_name}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _snapshot_number(data_dir: str) -> int | None:
    """The composite.db snapshot id for the masthead. Guarded on its own: a
    missing DB, no rows, or a NULL MAX(id) all mean "omit the snapshot
    number" — never fabricate or coerce a placeholder value."""
    try:
        conn = _ro(data_dir, "composite.db")
        try:
            row = conn.execute("SELECT MAX(id) FROM snapshots").fetchone()
        finally:
            conn.close()
    except Exception:
        return None
    if row is None or row[0] is None:
        return None
    return int(row[0])


def _edition_date(now_iso: str) -> str:
    """'July 8, 2026' — the Phoenix calendar date, not the UTC one (the
    9:13pm render slot is already tomorrow in UTC). Unlike the legacy
    `_edition_date` in sections.py (hair-space HTML entities meant for the
    masthead's styling), this is plain text bound for JSON — an explicit
    MONTHS table, no locale-dependent `%B`, no platform-dependent `%-d`. An
    unparseable now_iso degrades to the raw input rather than raising — the
    export must always produce something."""
    try:
        y, m, d = phx_date(now_iso).split("-")
        return f"{MONTHS[int(m) - 1]} {int(d)}, {y}"
    except Exception:
        return now_iso


def export_data(data_dir: str, now_iso: str, repo_root: str | None = None) -> dict[str, Any]:
    """The full data.json document. `repo_root` (default: this repo's real
    root) is where docs/GLOSSARY.md and research/ are resolved from — kept
    as an explicit parameter, not a hardcoded relative path, so tests can
    point it at a tmp_path sandbox instead of the live repo."""
    root = Path(repo_root) if repo_root is not None else _REPO_ROOT

    sections: dict[str, Any] = {}
    for sid, title, db_name, fn, kicker, note in SECTION_EXPORTERS:
        header = {"title": title, "kicker": kicker, "note": note}
        try:
            if db_name.endswith(".db"):
                conn = _ro(data_dir, db_name)
                try:
                    body = fn(conn, now_iso)
                finally:
                    conn.close()
            else:
                # File-backed section (e.g. research/verdicts.log): fn
                # resolves its own path from repo_root, under the same
                # degrade contract as a DB-backed section.
                body = fn(str(root), now_iso)
        except Exception as e:  # missing DB, dropped view — degrade, never crash
            body = {"error": f"unavailable ({db_name}: {type(e).__name__})"}
        sections[sid] = {**header, **body}

    return {
        "schema_version": 1,
        "generated_at": now_iso,
        "edition_date": _edition_date(now_iso),
        "snapshot_number": _snapshot_number(data_dir),
        "hero": {"bullets": []},
        "sections": sections,
        "tickers": {},
        "glossary": load_glossary(root / "docs" / "GLOSSARY.md"),
    }
