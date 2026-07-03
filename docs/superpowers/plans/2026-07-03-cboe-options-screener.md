# CBOE Options Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a daily `options` screener that snapshots rich per-contract CBOE options data (IV, greeks, OI, volume) for a curated watchlist into SQLite.

**Architecture:** A new top-level `cboe_options/` package following the repo's `fetch`/`db`/`run` triad (closest template: `finra_short_volume/`). For each catalog symbol it GETs one CBOE delayed-quotes JSON chain, parses every contract, and writes one row per contract per session-date using replace-per-day semantics. Per-symbol rollups and a run-header snapshot are written too. Registered in `registry.py` as `options`.

**Tech Stack:** Python 3.12, stdlib only (`sqlite3`, `urllib`, `json`, `argparse`), pytest. Reuses `http_client.py` (bounded backoff) and `screener_common.connect` (WAL).

## Global Constraints

- **Stdlib only** — no third-party dependencies (`pyproject.toml` has `dependencies = []`).
- **Package layout** — top-level package `cboe_options/`; `__init__.py` MUST be empty (0 bytes). `pyproject.toml` sets `pythonpath = ["."]` so top-level packages import directly.
- **User-Agent** — every request uses `{"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}`.
- **Data source** — `https://cdn.cboe.com/api/global/delayed_quotes/options/{TICKER}.json`; indices use a leading underscore (`_SPX.json`). Retryable statuses: `frozenset({429, 503})`. A 404 means "no chain for this ticker" → return `None` (skip), not an error.
- **Secret/error hygiene** — on any per-symbol failure: `conn.rollback()`, then print `warning: skipping {symbol}: {type(e).__name__}` to `stderr`. NEVER print `str(e)`.
- **Connection** — always via `screener_common.connect` (sets `PRAGMA journal_mode=WAL`). Schema is `CREATE ... IF NOT EXISTS` only; no migrations. `ensure_schema` runs at the top of every `run()`.
- **now_iso** — `run()` accepts an injectable `now_iso` (default `datetime.now(timezone.utc).isoformat()`); used for `captured_at`/`fetched_at` and prune cutoffs. It is a fixed-width UTC isoformat with `+00:00`.
- **Pruning** — `--keep-days` prunes ONLY the `snapshots` run-header table. Historical `option_snapshots`/`underlying_daily` data is NEVER pruned.
- **Commit rule** — do NOT add a Co-Authored-By/co-author trailer to commits (repo owner's global rule).
- **Run/DB semantics mirror `finra_short_volume/`** — study that package before starting.

---

## File Structure

- `cboe_options/__init__.py` — empty.
- `cboe_options/catalog.py` — `Underlying` dataclass, `CATALOG` starter list, `select_symbols`, `index_flag`.
- `cboe_options/fetch.py` — URL builder, OCC parser, `session_date`, `parse_chain`, `fetch_chain`, `_http_get`.
- `cboe_options/db.py` — schema + views + writers (`ensure_schema`, `upsert_underlying`, `replace_day`, `upsert_underlying_daily`, `record_day`, `write_snapshot`, `stored_symbols`, `prune`).
- `cboe_options/run.py` — `run(...)` orchestrator + `main(argv)` CLI.
- `registry.py` — MODIFY: import + `REGISTRY["options"]`.
- `tests/test_options_catalog.py`, `tests/test_options_fetch.py`, `tests/test_options_db_schema.py`, `tests/test_options_db_write.py`, `tests/test_options_run.py` — new.
- `tests/test_registry.py` — MODIFY: add `test_dispatch_lists_options`.

---

## Task 1: Catalog

**Files:**
- Create: `cboe_options/__init__.py` (empty)
- Create: `cboe_options/catalog.py`
- Test: `tests/test_options_catalog.py`

**Interfaces:**
- Produces:
  - `Underlying(symbol: str, is_index: bool)` — frozen dataclass.
  - `CATALOG: list[Underlying]`.
  - `select_symbols(all_symbols: Iterable[str], only, exclude, add=None) -> list[str]` — ordered, de-duped resolution.
  - `index_flag(symbol: str) -> bool` — True if `symbol` is a catalog index; default False.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_options_catalog.py
from cboe_options import catalog


def test_catalog_has_starter_symbols():
    syms = {u.symbol for u in catalog.CATALOG}
    assert {"AAPL", "SPY", "SPX", "VIX"} <= syms


def test_indices_are_flagged():
    by = {u.symbol: u.is_index for u in catalog.CATALOG}
    assert by["SPX"] is True and by["VIX"] is True
    assert by["AAPL"] is False and by["SPY"] is False


def test_index_flag_defaults_false_for_unknown():
    assert catalog.index_flag("SPX") is True
    assert catalog.index_flag("AAPL") is False
    assert catalog.index_flag("ZZZZ") is False


def test_select_symbols_only_exclude_add():
    all_syms = ["AAPL", "MSFT", "NVDA"]
    assert catalog.select_symbols(all_syms, None, None) == ["AAPL", "MSFT", "NVDA"]
    assert catalog.select_symbols(all_syms, ["AAPL", "NVDA"], None) == ["AAPL", "NVDA"]
    assert catalog.select_symbols(all_syms, None, ["MSFT"]) == ["AAPL", "NVDA"]
    assert catalog.select_symbols(all_syms, None, None, ["TSLA"]) == [
        "AAPL", "MSFT", "NVDA", "TSLA"]


def test_select_symbols_dedupes_and_strips():
    assert catalog.select_symbols(["AAPL"], None, None, [" AAPL ", "MSFT"]) == [
        "AAPL", "MSFT"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_options_catalog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cboe_options'`

- [ ] **Step 3: Create the empty package init**

```bash
touch cboe_options/__init__.py
```

- [ ] **Step 4: Write minimal implementation**

```python
# cboe_options/catalog.py
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Underlying:
    symbol: str      # catalog key WITHOUT the index underscore (e.g. "SPX")
    is_index: bool   # True -> chain_url adds the leading "_" the CBOE API needs


# Starter watchlist (editable). Equities/ETFs use the plain ticker; indices are
# flagged is_index=True and fetched via the "_"-prefixed CBOE path.
CATALOG: list[Underlying] = [
    # mega-cap tech
    Underlying("AAPL", False), Underlying("MSFT", False), Underlying("NVDA", False),
    Underlying("AMZN", False), Underlying("GOOGL", False), Underlying("META", False),
    Underlying("TSLA", False),
    # high-volume single names
    Underlying("AMD", False), Underlying("NFLX", False), Underlying("AVGO", False),
    Underlying("PLTR", False), Underlying("COIN", False), Underlying("MSTR", False),
    Underlying("SMCI", False),
    # liquid other
    Underlying("JPM", False), Underlying("BAC", False), Underlying("XOM", False),
    Underlying("DIS", False), Underlying("BABA", False),
    # ETFs
    Underlying("SPY", False), Underlying("QQQ", False), Underlying("IWM", False),
    # indices (fetched as _SPX / _VIX)
    Underlying("SPX", True), Underlying("VIX", True),
]

_INDEX = {u.symbol for u in CATALOG if u.is_index}


def index_flag(symbol: str) -> bool:
    """True if `symbol` is a known catalog index; unknown symbols default False
    (treated as equities/ETFs)."""
    return symbol.strip() in _INDEX


def select_symbols(all_symbols: Iterable[str], only, exclude, add=None) -> list[str]:
    """Resolve the ordered, de-duplicated symbols to fetch: ``only`` (or all)
    minus ``exclude``, then any ``add`` appended. Tokens stripped; blanks and
    duplicates dropped."""
    syms = list(only) if only else list(all_symbols)
    ex = {e.strip() for e in (exclude or ())}
    out, seen = [], set()
    for s in list(syms) + list(add or ()):
        s = s.strip()
        if not s or s in ex or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_options_catalog.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add cboe_options/__init__.py cboe_options/catalog.py tests/test_options_catalog.py
git commit -m "feat(cboe_options): add options watchlist catalog"
```

---

## Task 2: Fetch — parse + download

**Files:**
- Create: `cboe_options/fetch.py`
- Test: `tests/test_options_fetch.py`

**Interfaces:**
- Consumes: `http_client.http_get`, `http_client.make_opener`.
- Produces:
  - `chain_url(symbol: str, is_index: bool, base=BASE) -> str`
  - `parse_occ(option: str) -> tuple[str, str, str, float] | None` — `(root, expiration, type, strike)`; `None` if malformed.
  - `session_date(payload: dict) -> str | None` — `YYYY-MM-DD` the data represents.
  - `parse_chain(payload: dict, underlying: str) -> tuple[dict, list[dict]]` — `(daily, contracts)`.
  - `fetch_chain(symbol: str, is_index: bool, get=_http_get) -> dict | None` — parsed JSON payload, or `None` on HTTP 404.
  - `_http_get(url, opener=_urlopen, attempts=_MAX_ATTEMPTS, base_delay=_BASE_DELAY, sleep=time.sleep) -> str`
  - Contract dict keys: `occ_symbol, underlying, expiration, strike, type, bid, ask, mark, last, theo, iv, delta, gamma, theta, vega, rho, open_interest, volume, underlying_price, vol_oi_ratio`.
  - `daily` dict keys: `underlying, underlying_price, close, iv30, total_call_volume, total_put_volume, put_call_volume_ratio, total_call_oi, total_put_oi, put_call_oi_ratio`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_options_fetch.py
import json
import urllib.error

import pytest

from cboe_options import fetch


def _payload():
    """Trimmed CBOE chain: 2 calls + 1 put on one expiration."""
    return {
        "timestamp": "2026-07-03 17:46:09",
        "symbol": "AAPL",
        "data": {
            "symbol": "AAPL", "current_price": 308.45, "close": 308.63,
            "iv30": 27.803, "last_trade_time": "2026-07-02T16:00:00",
            "options": [
                {"option": "AAPL260717C00210000", "bid": 97.8, "ask": 100.35,
                 "iv": 1.02, "delta": 0.97, "gamma": 0.0008, "theta": -0.13,
                 "vega": 0.03, "rho": 0.07, "open_interest": 3131.0,
                 "volume": 40.0, "last_trade_price": 99.0, "theo": 99.08},
                {"option": "AAPL260717C00300000", "bid": 15.0, "ask": 15.5,
                 "iv": 0.30, "delta": 0.55, "gamma": 0.01, "theta": -0.2,
                 "vega": 0.4, "rho": 0.1, "open_interest": 0.0,
                 "volume": 500.0, "last_trade_price": 15.2, "theo": 15.25},
                {"option": "AAPL260717P00300000", "bid": 6.0, "ask": 6.4,
                 "iv": 0.28, "delta": -0.45, "gamma": 0.01, "theta": -0.18,
                 "vega": 0.38, "rho": -0.09, "open_interest": 2000.0,
                 "volume": 300.0, "last_trade_price": 6.2, "theo": 6.2},
            ],
        },
    }


def test_chain_url_equity_and_index():
    assert fetch.chain_url("AAPL", False).endswith("/options/AAPL.json")
    assert fetch.chain_url("SPX", True).endswith("/options/_SPX.json")


def test_parse_occ_call_and_put():
    assert fetch.parse_occ("AAPL260717C00210000") == (
        "AAPL", "2026-07-17", "call", 210.0)
    assert fetch.parse_occ("AAPL260717P00300000") == (
        "AAPL", "2026-07-17", "put", 300.0)


def test_parse_occ_index_and_adjusted_roots():
    # index root with digits, and a fractional strike
    assert fetch.parse_occ("SPXW260320C05000000")[0] == "SPXW"
    assert fetch.parse_occ("AAPL1260717C00007500") == (
        "AAPL1", "2026-07-17", "call", 7.5)


def test_parse_occ_rejects_garbage():
    assert fetch.parse_occ("NOTANOPTION") is None
    assert fetch.parse_occ("") is None


def test_session_date_prefers_last_trade_time():
    assert fetch.session_date(_payload()) == "2026-07-02"
    # falls back to top-level timestamp date when last_trade_time missing
    p = _payload(); p["data"]["last_trade_time"] = None
    assert fetch.session_date(p) == "2026-07-03"
    assert fetch.session_date({"data": {}}) is None


def test_parse_chain_contracts_and_derived():
    daily, contracts = fetch.parse_chain(_payload(), "AAPL")
    assert len(contracts) == 3
    c0 = next(c for c in contracts if c["occ_symbol"] == "AAPL260717C00210000")
    assert c0["underlying"] == "AAPL"
    assert c0["expiration"] == "2026-07-17"
    assert c0["type"] == "call" and c0["strike"] == 210.0
    assert c0["open_interest"] == 3131 and c0["volume"] == 40
    assert c0["mark"] == pytest.approx((97.8 + 100.35) / 2)
    assert c0["vol_oi_ratio"] == pytest.approx(40 / 3131)
    assert c0["underlying_price"] == 308.45
    # zero-OI contract uses max(oi,1) => ratio == volume
    c_zero = next(c for c in contracts if c["occ_symbol"] == "AAPL260717C00300000")
    assert c_zero["vol_oi_ratio"] == pytest.approx(500.0)


def test_parse_chain_daily_rollup():
    daily, _ = fetch.parse_chain(_payload(), "AAPL")
    assert daily["underlying"] == "AAPL"
    assert daily["iv30"] == 27.803
    assert daily["total_call_volume"] == 540   # 40 + 500
    assert daily["total_put_volume"] == 300
    assert daily["put_call_volume_ratio"] == pytest.approx(300 / 540)
    assert daily["total_call_oi"] == 3131       # 3131 + 0
    assert daily["total_put_oi"] == 2000
    assert daily["put_call_oi_ratio"] == pytest.approx(2000 / 3131)


def test_fetch_chain_404_returns_none():
    def get(url, opener=None):
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
    assert fetch.fetch_chain("ZZZZ", False, get=get) is None


def test_fetch_chain_parses_json():
    body = json.dumps(_payload())
    assert fetch.fetch_chain("AAPL", False, get=lambda url, opener=None: body)[
        "symbol"] == "AAPL"


def test_http_get_retries_then_raises_non_retryable():
    calls = {"n": 0}

    def opener(url):
        calls["n"] += 1
        raise urllib.error.HTTPError(url, 503, "busy", None, None)

    slept = []
    with pytest.raises(urllib.error.HTTPError):
        fetch._http_get("u", opener=opener, attempts=3, base_delay=0.1,
                        sleep=slept.append)
    assert calls["n"] == 3 and len(slept) == 2

    def opener403(url):
        raise urllib.error.HTTPError(url, 403, "no", None, None)
    with pytest.raises(urllib.error.HTTPError):
        fetch._http_get("u", opener=opener403, attempts=3, sleep=slept.append)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_options_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cboe_options.fetch'`

- [ ] **Step 3: Write minimal implementation**

```python
# cboe_options/fetch.py
import json
import time
import urllib.error

import http_client

BASE = "https://cdn.cboe.com/api/global/delayed_quotes/options"

_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
# Undocumented CDN behind Cloudflare. Retry only throttling/5xx; 404 means no
# chain for this ticker (fetch_chain maps it to None). Deep-OTM contracts often
# report iv/greeks as 0 — stored as-is; downstream views filter.
_RETRY_STATUS = frozenset({429, 503})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0

_urlopen = http_client.make_opener(_UA)  # opener(url) -> decoded UTF-8 text


def chain_url(symbol: str, is_index: bool, base: str = BASE) -> str:
    """URL of the delayed-quotes chain JSON. Indices take a leading underscore."""
    prefix = "_" if is_index else ""
    return f"{base}/{prefix}{symbol}.json"


def _num(raw, cast):
    """Coerce raw via cast; None/blank/unparseable -> None."""
    if raw is None or raw == "":
        return None
    try:
        return cast(raw)
    except (TypeError, ValueError):
        return None


def _to_int(raw):
    """OI/volume arrive as floats (e.g. 3131.0). None-safe int()."""
    return _num(raw, lambda v: int(float(v)))


def parse_occ(option: str):
    """Parse an OCC symbol ``{ROOT}{YYMMDD}{C|P}{STRIKE*1000:08d}`` by slicing
    from the right (robust to variable/numeric roots). Returns
    (root, 'YYYY-MM-DD', 'call'|'put', strike_float) or None if malformed."""
    s = (option or "").strip()
    if len(s) < 16:
        return None
    strike_raw, cp, ymd, root = s[-8:], s[-9], s[-15:-9], s[:-15]
    if not (root and strike_raw.isdigit() and ymd.isdigit() and cp in ("C", "P")):
        return None
    expiration = f"20{ymd[:2]}-{ymd[2:4]}-{ymd[4:6]}"
    kind = "call" if cp == "C" else "put"
    return root, expiration, kind, int(strike_raw) / 1000.0


def session_date(payload: dict):
    """The 'YYYY-MM-DD' trading date the data represents: the underlying's
    last_trade_time date, else the top-level generation timestamp date, else
    None. Both CBOE formats start with a 10-char ISO date."""
    data = payload.get("data") or {}
    for cand in (data.get("last_trade_time"), payload.get("timestamp")):
        s = (cand or "")[:10]
        if len(s) == 10 and s[4] == "-" and s[7] == "-":
            return s
    return None


def _mark(bid, ask):
    return (bid + ask) / 2 if bid is not None and ask is not None else None


def parse_chain(payload: dict, underlying: str):
    """Split a CBOE chain payload into (daily rollup dict, list of contract
    dicts) for the given catalog `underlying`. Contracts with an unparseable OCC
    symbol are skipped. Pure — no I/O."""
    data = payload.get("data") or {}
    px = _num(data.get("current_price"), float)
    contracts = []
    call_vol = put_vol = call_oi = put_oi = 0
    for o in data.get("options", []):
        parsed = parse_occ(o.get("option"))
        if parsed is None:
            continue
        _root, expiration, kind, strike = parsed
        bid, ask = _num(o.get("bid"), float), _num(o.get("ask"), float)
        oi, vol = _to_int(o.get("open_interest")), _to_int(o.get("volume"))
        contracts.append({
            "occ_symbol": o["option"], "underlying": underlying,
            "expiration": expiration, "strike": strike, "type": kind,
            "bid": bid, "ask": ask, "mark": _mark(bid, ask),
            "last": _num(o.get("last_trade_price"), float),
            "theo": _num(o.get("theo"), float),
            "iv": _num(o.get("iv"), float),
            "delta": _num(o.get("delta"), float),
            "gamma": _num(o.get("gamma"), float),
            "theta": _num(o.get("theta"), float),
            "vega": _num(o.get("vega"), float),
            "rho": _num(o.get("rho"), float),
            "open_interest": oi, "volume": vol,
            "underlying_price": px,
            "vol_oi_ratio": (vol or 0) / max(oi or 0, 1),
        })
        if kind == "call":
            call_vol += vol or 0
            call_oi += oi or 0
        else:
            put_vol += vol or 0
            put_oi += oi or 0
    daily = {
        "underlying": underlying, "underlying_price": px,
        "close": _num(data.get("close"), float),
        "iv30": _num(data.get("iv30"), float),
        "total_call_volume": call_vol, "total_put_volume": put_vol,
        "put_call_volume_ratio": (put_vol / call_vol) if call_vol else None,
        "total_call_oi": call_oi, "total_put_oi": put_oi,
        "put_call_oi_ratio": (put_oi / call_oi) if call_oi else None,
    }
    return daily, contracts


def _http_get(url: str, opener=_urlopen, attempts: int = _MAX_ATTEMPTS,
              base_delay: float = _BASE_DELAY, sleep=time.sleep) -> str:
    """GET chain JSON text with bounded backoff, retrying 429/503 and transient
    network errors. Non-retryable HTTP errors (e.g. 403/404) raise at once, so
    fetch_chain can map 404 -> None."""
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts,
                                base_delay, sleep)


def fetch_chain(symbol: str, is_index: bool, get=_http_get):
    """Download + JSON-decode one ticker's chain. Returns the payload dict, or
    None on HTTP 404 (no chain for this ticker)."""
    try:
        body = get(chain_url(symbol, is_index), opener=_urlopen)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return json.loads(body)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_options_fetch.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add cboe_options/fetch.py tests/test_options_fetch.py
git commit -m "feat(cboe_options): add chain fetch + OCC/chain parsing"
```

---

## Task 3: DB schema + views

**Files:**
- Create: `cboe_options/db.py` (schema portion)
- Test: `tests/test_options_db_schema.py`

**Interfaces:**
- Consumes: `screener_common.connect`.
- Produces: `connect` (re-export), `ensure_schema(conn) -> None`. Tables: `underlyings`, `option_snapshots`, `underlying_daily`, `days`, `snapshots`. Views: `v_unusual_activity`, `v_iv_rank`, `v_latest_sentiment`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_options_db_schema.py
from cboe_options import db


def test_ensure_schema_is_idempotent_and_creates_objects():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)  # second call must not raise
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    assert {"underlyings", "option_snapshots", "underlying_daily",
            "days", "snapshots"} <= names
    assert {"v_unusual_activity", "v_iv_rank", "v_latest_sentiment"} <= names


def test_option_snapshots_primary_key():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(option_snapshots)")]
    assert {"snapshot_date", "occ_symbol", "source", "iv", "delta",
            "open_interest", "volume", "vol_oi_ratio"} <= set(cols)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_options_db_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cboe_options.db'`

- [ ] **Step 3: Write minimal implementation**

```python
# cboe_options/db.py
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_underlying", "replace_day",
           "upsert_underlying_daily", "record_day", "write_snapshot",
           "stored_symbols", "prune"]

_CONTRACT_COLS = [
    "snapshot_date", "occ_symbol", "source", "underlying", "expiration",
    "strike", "type", "bid", "ask", "mark", "last", "theo", "iv", "delta",
    "gamma", "theta", "vega", "rho", "open_interest", "volume",
    "underlying_price", "vol_oi_ratio", "fetched_at",
]

_DAILY_COLS = [
    "snapshot_date", "underlying", "underlying_price", "close", "iv30",
    "total_call_volume", "total_put_volume", "put_call_volume_ratio",
    "total_call_oi", "total_put_oi", "put_call_oi_ratio",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS underlyings (
    symbol     TEXT PRIMARY KEY,
    is_index   INTEGER NOT NULL DEFAULT 0,
    first_seen TEXT,
    last_seen  TEXT
);
CREATE TABLE IF NOT EXISTS option_snapshots (
    snapshot_date    TEXT NOT NULL,
    occ_symbol       TEXT NOT NULL,
    source           TEXT NOT NULL DEFAULT 'cboe',
    underlying       TEXT NOT NULL REFERENCES underlyings(symbol),
    expiration       TEXT,
    strike           REAL,
    type             TEXT,
    bid              REAL,
    ask              REAL,
    mark             REAL,
    last             REAL,
    theo             REAL,
    iv               REAL,
    delta            REAL,
    gamma            REAL,
    theta            REAL,
    vega             REAL,
    rho              REAL,
    open_interest    INTEGER,
    volume           INTEGER,
    underlying_price REAL,
    vol_oi_ratio     REAL,
    fetched_at       TEXT,
    PRIMARY KEY (snapshot_date, occ_symbol, source)
);
CREATE INDEX IF NOT EXISTS ix_os_underlying_date
    ON option_snapshots(underlying, snapshot_date);
CREATE INDEX IF NOT EXISTS ix_os_date ON option_snapshots(snapshot_date);
CREATE TABLE IF NOT EXISTS underlying_daily (
    snapshot_date         TEXT NOT NULL,
    underlying            TEXT NOT NULL REFERENCES underlyings(symbol),
    underlying_price      REAL,
    close                 REAL,
    iv30                  REAL,
    total_call_volume     INTEGER,
    total_put_volume      INTEGER,
    put_call_volume_ratio REAL,
    total_call_oi         INTEGER,
    total_put_oi          INTEGER,
    put_call_oi_ratio     REAL,
    PRIMARY KEY (snapshot_date, underlying)
);
CREATE TABLE IF NOT EXISTS days (
    snapshot_date TEXT NOT NULL,
    underlying    TEXT NOT NULL,
    fetched_at    TEXT NOT NULL,
    row_count     INTEGER NOT NULL,
    PRIMARY KEY (snapshot_date, underlying)
);
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,
    symbol_count INTEGER NOT NULL,
    row_count    INTEGER NOT NULL
);
"""

_VIEWS = """
-- (1) unusual activity on the latest snapshot: contracts where today's volume
-- dwarfs standing open interest. Works from day one.
CREATE VIEW IF NOT EXISTS v_unusual_activity AS
SELECT underlying, occ_symbol, expiration, strike, type,
       volume, open_interest, vol_oi_ratio, iv, snapshot_date
FROM option_snapshots
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM option_snapshots)
  AND source = 'cboe'
  AND volume >= 100
  AND vol_oi_ratio >= 1.0
ORDER BY vol_oi_ratio DESC;

-- (2) IV Rank/percentile of each underlying's latest iv30 within its full
-- stored history (min-max rank + fraction-of-days-below percentile). Returns
-- meaningful values only once history accumulates (needs many days).
CREATE VIEW IF NOT EXISTS v_iv_rank AS
WITH bounds AS (
  SELECT underlying, MIN(iv30) AS iv_min, MAX(iv30) AS iv_max, COUNT(*) AS n_days
  FROM underlying_daily WHERE iv30 IS NOT NULL GROUP BY underlying),
today AS (
  SELECT underlying, snapshot_date, iv30 FROM underlying_daily
  WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM underlying_daily)
    AND iv30 IS NOT NULL)
SELECT t.underlying, t.snapshot_date, t.iv30, b.iv_min, b.iv_max, b.n_days,
       CASE WHEN b.iv_max > b.iv_min
            THEN 100.0 * (t.iv30 - b.iv_min) / (b.iv_max - b.iv_min) END AS iv_rank,
       (SELECT 100.0 * COUNT(*) / b.n_days FROM underlying_daily h
         WHERE h.underlying = t.underlying AND h.iv30 < t.iv30) AS iv_percentile
FROM today t JOIN bounds b USING (underlying);

-- (3) latest-day sentiment snapshot per underlying.
CREATE VIEW IF NOT EXISTS v_latest_sentiment AS
SELECT underlying, snapshot_date, underlying_price, iv30,
       put_call_volume_ratio, put_call_oi_ratio,
       total_call_volume, total_put_volume
FROM underlying_daily
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM underlying_daily);
"""


def ensure_schema(conn) -> None:
    """Create tables, indexes, and screener views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.executescript(_VIEWS)
    conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_options_db_schema.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add cboe_options/db.py tests/test_options_db_schema.py
git commit -m "feat(cboe_options): add sqlite schema + screener views"
```

---

## Task 4: DB writers

**Files:**
- Modify: `cboe_options/db.py` (append writer functions)
- Test: `tests/test_options_db_write.py`

**Interfaces:**
- Consumes: `_CONTRACT_COLS`, `_DAILY_COLS`, `ensure_schema` (from Task 3).
- Produces:
  - `upsert_underlying(conn, symbol, is_index, date) -> None`
  - `replace_day(conn, snapshot_date, underlying, rows, fetched_at, source="cboe") -> int`
  - `upsert_underlying_daily(conn, snapshot_date, daily) -> None`
  - `record_day(conn, snapshot_date, underlying, fetched_at, row_count) -> None`
  - `write_snapshot(conn, captured_at, symbol_count, row_count) -> int`
  - `stored_symbols(conn) -> list[str]`
  - `prune(conn, keep_days, now_iso) -> int` (snapshots-only)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_options_db_write.py
from cboe_options import db

FA = "2026-07-03T00:00:00+00:00"


def _rows(underlying="AAPL"):
    return [
        {"occ_symbol": f"{underlying}260717C00210000", "underlying": underlying,
         "expiration": "2026-07-17", "strike": 210.0, "type": "call",
         "bid": 1.0, "ask": 1.2, "mark": 1.1, "last": 1.1, "theo": 1.1,
         "iv": 0.3, "delta": 0.5, "gamma": 0.01, "theta": -0.1, "vega": 0.2,
         "rho": 0.05, "open_interest": 100, "volume": 250,
         "underlying_price": 308.45, "vol_oi_ratio": 2.5},
    ]


def _daily(underlying="AAPL"):
    return {"underlying": underlying, "underlying_price": 308.45, "close": 308.6,
            "iv30": 27.8, "total_call_volume": 250, "total_put_volume": 100,
            "put_call_volume_ratio": 0.4, "total_call_oi": 100,
            "total_put_oi": 80, "put_call_oi_ratio": 0.8}


def _seed(conn, underlying="AAPL"):
    db.upsert_underlying(conn, underlying, False, "2026-07-02")


def test_upsert_underlying_extends_first_last_seen():
    conn = db.connect(":memory:"); db.ensure_schema(conn)
    db.upsert_underlying(conn, "AAPL", False, "2026-07-02")
    db.upsert_underlying(conn, "AAPL", False, "2026-07-01")
    db.upsert_underlying(conn, "AAPL", False, "2026-07-03")
    row = conn.execute(
        "SELECT first_seen, last_seen, is_index FROM underlyings").fetchone()
    assert row == ("2026-07-01", "2026-07-03", 0)


def test_replace_day_overwrites_in_place():
    conn = db.connect(":memory:"); db.ensure_schema(conn); _seed(conn)
    assert db.replace_day(conn, "2026-07-02", "AAPL", _rows(), FA) == 1
    # rerun with a shrunk set (empty) leaves no orphan for that day+underlying
    assert db.replace_day(conn, "2026-07-02", "AAPL", [], FA) == 0
    n = conn.execute(
        "SELECT COUNT(*) FROM option_snapshots WHERE snapshot_date='2026-07-02'"
    ).fetchone()[0]
    assert n == 0


def test_replace_day_writes_columns_and_source():
    conn = db.connect(":memory:"); db.ensure_schema(conn); _seed(conn)
    db.replace_day(conn, "2026-07-02", "AAPL", _rows(), FA)
    r = conn.execute(
        "SELECT source, fetched_at, iv, open_interest, vol_oi_ratio "
        "FROM option_snapshots").fetchone()
    assert r == ("cboe", FA, 0.3, 100, 2.5)


def test_replace_day_isolated_per_underlying():
    conn = db.connect(":memory:"); db.ensure_schema(conn)
    _seed(conn, "AAPL"); _seed(conn, "MSFT")
    db.replace_day(conn, "2026-07-02", "AAPL", _rows("AAPL"), FA)
    db.replace_day(conn, "2026-07-02", "MSFT", _rows("MSFT"), FA)
    # replacing AAPL must not delete MSFT's rows for the same day
    db.replace_day(conn, "2026-07-02", "AAPL", _rows("AAPL"), FA)
    n = conn.execute(
        "SELECT COUNT(*) FROM option_snapshots WHERE underlying='MSFT'"
    ).fetchone()[0]
    assert n == 1


def test_upsert_underlying_daily_upserts():
    conn = db.connect(":memory:"); db.ensure_schema(conn); _seed(conn)
    db.upsert_underlying_daily(conn, "2026-07-02", _daily())
    d = dict(_daily()); d["iv30"] = 30.0
    db.upsert_underlying_daily(conn, "2026-07-02", d)
    rows = conn.execute(
        "SELECT iv30 FROM underlying_daily WHERE snapshot_date='2026-07-02'"
    ).fetchall()
    assert rows == [(30.0,)]


def test_record_day_and_stored_symbols():
    conn = db.connect(":memory:"); db.ensure_schema(conn); _seed(conn)
    db.record_day(conn, "2026-07-02", "AAPL", FA, 1)
    db.record_day(conn, "2026-07-02", "AAPL", FA, 2)  # upsert
    assert conn.execute("SELECT row_count FROM days").fetchone()[0] == 2
    assert db.stored_symbols(conn) == ["AAPL"]


def test_write_snapshot_and_prune_only_headers():
    conn = db.connect(":memory:"); db.ensure_schema(conn); _seed(conn)
    db.replace_day(conn, "2026-07-02", "AAPL", _rows(), FA)
    db.write_snapshot(conn, "2000-01-01T00:00:00+00:00", 1, 1)  # old
    db.write_snapshot(conn, FA, 1, 1)                            # recent
    removed = db.prune(conn, 30, FA)
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    # option history is untouched by prune
    assert conn.execute("SELECT COUNT(*) FROM option_snapshots").fetchone()[0] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_options_db_write.py -v`
Expected: FAIL — `AttributeError: module 'cboe_options.db' has no attribute 'upsert_underlying'`

- [ ] **Step 3: Append the writer implementations to `cboe_options/db.py`**

```python
def upsert_underlying(conn, symbol: str, is_index: bool, date: str) -> None:
    """Upsert the underlying dimension: extend first_seen/last_seen to the
    min/max date ever seen, and keep is_index current."""
    conn.execute(
        """INSERT INTO underlyings (symbol, is_index, first_seen, last_seen)
           VALUES (:s, :i, :d, :d)
           ON CONFLICT(symbol) DO UPDATE SET
             is_index   = excluded.is_index,
             first_seen = MIN(underlyings.first_seen, excluded.first_seen),
             last_seen  = MAX(underlyings.last_seen,  excluded.last_seen)""",
        {"s": symbol, "i": 1 if is_index else 0, "d": date})
    conn.commit()


def replace_day(conn, snapshot_date: str, underlying: str, rows: list,
                fetched_at: str, source: str = "cboe") -> int:
    """Delete this (snapshot_date, underlying, source)'s contract rows, then
    bulk-insert `rows`. Replace (not upsert) so a shrunk chain leaves no orphan.
    Dedupes the batch by occ_symbol. snapshot_date/source/fetched_at are stamped
    from params onto every row. Returns rows written."""
    by_key = {r["occ_symbol"]: r for r in rows}
    conn.execute(
        "DELETE FROM option_snapshots "
        "WHERE snapshot_date = ? AND underlying = ? AND source = ?",
        (snapshot_date, underlying, source))
    placeholders = ", ".join(":" + c for c in _CONTRACT_COLS)
    stamp = {"snapshot_date": snapshot_date, "source": source,
             "fetched_at": fetched_at}
    params = [{**{c: r.get(c) for c in _CONTRACT_COLS}, **stamp}
              for r in by_key.values()]
    conn.executemany(
        f"INSERT INTO option_snapshots ({', '.join(_CONTRACT_COLS)}) "
        f"VALUES ({placeholders})", params)
    conn.commit()
    return len(by_key)


def upsert_underlying_daily(conn, snapshot_date: str, daily: dict) -> None:
    """Upsert one (snapshot_date, underlying) rollup row."""
    row = {**{c: daily.get(c) for c in _DAILY_COLS}, "snapshot_date": snapshot_date}
    assignments = ", ".join(
        f"{c}=excluded.{c}" for c in _DAILY_COLS
        if c not in ("snapshot_date", "underlying"))
    placeholders = ", ".join(":" + c for c in _DAILY_COLS)
    conn.execute(
        f"INSERT INTO underlying_daily ({', '.join(_DAILY_COLS)}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT(snapshot_date, underlying) DO UPDATE SET {assignments}",
        row)
    conn.commit()


def record_day(conn, snapshot_date: str, underlying: str, fetched_at: str,
               row_count: int) -> None:
    """Upsert one (snapshot_date, underlying) provenance row."""
    conn.execute(
        """INSERT INTO days (snapshot_date, underlying, fetched_at, row_count)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(snapshot_date, underlying) DO UPDATE SET
             fetched_at=excluded.fetched_at, row_count=excluded.row_count""",
        (snapshot_date, underlying, fetched_at, row_count))
    conn.commit()


def write_snapshot(conn, captured_at: str, symbol_count: int,
                   row_count: int) -> int:
    """Insert one fetch-run header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, symbol_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, symbol_count, row_count))
    conn.commit()
    return cur.lastrowid


def stored_symbols(conn) -> list:
    """Distinct underlyings that have at least one ingested day, sorted."""
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT underlying FROM days ORDER BY underlying")]


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.
    Options history is NOT snapshot-scoped, so this is a single-table delete of
    snapshot headers only — it must NOT cascade into option_snapshots."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_options_db_write.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add cboe_options/db.py tests/test_options_db_write.py
git commit -m "feat(cboe_options): add sqlite writers (replace-day, rollup, prune)"
```

---

## Task 5: Run orchestrator + CLI

**Files:**
- Create: `cboe_options/run.py`
- Test: `tests/test_options_run.py`

**Interfaces:**
- Consumes: `catalog` (Task 1), `fetch.parse_chain` / `fetch.session_date` / `fetch.fetch_chain` (Task 2), `db` writers (Tasks 3-4).
- Produces:
  - `run(db_path, symbols=None, keep_days=None, now_iso=None, fetch_chain=fetch.fetch_chain) -> tuple[int, int, int]` returning `(snapshot_id, symbol_count, row_count)`.
  - `main(argv=None)` — argparse CLI (`--db`, `--only`, `--exclude`, `--add`, `--keep-days`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_options_run.py
from cboe_options import db, run as run_mod

NOW = "2026-07-03T00:00:00+00:00"


def _payload(underlying, iv30=27.8):
    return {
        "timestamp": "2026-07-03 17:46:09", "symbol": underlying,
        "data": {"symbol": underlying, "current_price": 100.0, "close": 100.5,
                 "iv30": iv30, "last_trade_time": "2026-07-02T16:00:00",
                 "options": [
                     {"option": f"{underlying}260717C00100000", "bid": 1.0,
                      "ask": 1.2, "iv": 0.3, "delta": 0.5, "gamma": 0.01,
                      "theta": -0.1, "vega": 0.2, "rho": 0.05,
                      "open_interest": 100.0, "volume": 250.0,
                      "last_trade_price": 1.1, "theo": 1.1}]}}


def test_run_ingests_symbols(tmp_path):
    dbp = str(tmp_path / "opt.db")
    sid, sc, rc = run_mod.run(
        dbp, symbols=["AAPL", "MSFT"], now_iso=NOW,
        fetch_chain=lambda sym, is_index: _payload(sym))
    assert (sc, rc) == (2, 2)
    conn = db.connect(dbp)
    assert conn.execute("SELECT COUNT(*) FROM option_snapshots").fetchone()[0] == 2
    # session_date came from the payload, not the wall clock
    assert conn.execute(
        "SELECT DISTINCT snapshot_date FROM option_snapshots").fetchone()[0] == "2026-07-02"
    assert conn.execute("SELECT COUNT(*) FROM underlying_daily").fetchone()[0] == 2


def test_run_skips_none_payload(tmp_path):
    dbp = str(tmp_path / "opt.db")

    def fc(sym, is_index):
        return None if sym == "ZZZZ" else _payload(sym)

    _, sc, rc = run_mod.run(dbp, symbols=["AAPL", "ZZZZ"], now_iso=NOW,
                            fetch_chain=fc)
    assert (sc, rc) == (1, 1)


def test_run_skips_failing_symbol_and_hides_message(tmp_path, capsys):
    dbp = str(tmp_path / "opt.db")

    def fc(sym, is_index):
        if sym == "BAD":
            raise RuntimeError("secret-token-leak")
        return _payload(sym)

    _, sc, _ = run_mod.run(dbp, symbols=["BAD", "AAPL"], now_iso=NOW,
                           fetch_chain=fc)
    assert sc == 1
    err = capsys.readouterr().err
    assert "BAD" in err and "RuntimeError" in err
    assert "secret-token-leak" not in err


def test_run_all_fail_writes_zero_snapshot(tmp_path):
    dbp = str(tmp_path / "opt.db")
    _, sc, rc = run_mod.run(dbp, symbols=["A"], now_iso=NOW,
                            fetch_chain=lambda sym, is_index: None)
    assert (sc, rc) == (0, 0)
    conn = db.connect(dbp)
    assert tuple(conn.execute(
        "SELECT symbol_count, row_count FROM snapshots").fetchone()) == (0, 0)


def test_run_default_symbols_from_catalog(tmp_path):
    dbp = str(tmp_path / "opt.db")
    seen = []

    def fc(sym, is_index):
        seen.append(sym)
        return None

    run_mod.run(dbp, now_iso=NOW, fetch_chain=fc)
    assert "AAPL" in seen and "SPX" in seen and len(seen) >= 20


def test_run_keep_days_prunes_headers(tmp_path):
    dbp = str(tmp_path / "opt.db")
    run_mod.run(dbp, symbols=["A"], now_iso=NOW,
                fetch_chain=lambda sym, is_index: None)
    conn = db.connect(dbp)
    db.write_snapshot(conn, "2000-01-01T00:00:00+00:00", 0, 0)
    conn.close()
    run_mod.run(dbp, symbols=["A"], now_iso=NOW, keep_days=30,
                fetch_chain=lambda sym, is_index: None)
    conn = db.connect(dbp)
    old = conn.execute(
        "SELECT COUNT(*) FROM snapshots WHERE captured_at < '2020-01-01'"
    ).fetchone()[0]
    assert old == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_options_run.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cboe_options.run'`

- [ ] **Step 3: Write minimal implementation**

```python
# cboe_options/run.py
import argparse
import sys
from datetime import datetime, timezone

from cboe_options import catalog, db, fetch


def _split(arg):
    """'A,B , C' -> ['A','B','C']; None/'' -> None."""
    if not arg:
        return None
    return [t.strip() for t in arg.split(",") if t.strip()]


def run(db_path, symbols=None, keep_days=None, now_iso=None,
        fetch_chain=fetch.fetch_chain) -> tuple[int, int, int]:
    """Snapshot each symbol's CBOE option chain into SQLite. For each symbol:
    fetch the chain (None -> skip), parse contracts + daily rollup, and
    replace-write them under the payload's session date. Any per-symbol failure
    rolls back and continues (logging only the exception class). Always writes a
    run-header snapshot. Returns (snapshot_id, symbol_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    if symbols is None:
        symbols = [u.symbol for u in catalog.CATALOG]

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        ok_count = 0
        total_rows = 0
        for symbol in symbols:
            try:
                is_index = catalog.index_flag(symbol)
                payload = fetch_chain(symbol, is_index)
                if payload is None:               # no chain for this ticker
                    continue
                daily, contracts = fetch.parse_chain(payload, symbol)
                snapshot_date = fetch.session_date(payload) or now_iso[:10]
                db.upsert_underlying(conn, symbol, is_index, snapshot_date)
                written = db.replace_day(conn, snapshot_date, symbol,
                                         contracts, now_iso)
                db.upsert_underlying_daily(conn, snapshot_date, daily)
                db.record_day(conn, snapshot_date, symbol, now_iso, written)
                total_rows += written
                ok_count += 1
            except Exception as e:  # skip-and-continue on any per-symbol failure
                conn.rollback()
                print(f"warning: skipping {symbol}: {type(e).__name__}",
                      file=sys.stderr)
                continue

        snapshot_id = db.write_snapshot(conn, now_iso, ok_count, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, ok_count, total_rows


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="options",
        description="Pull CBOE delayed-quote option chains into SQLite")
    p.add_argument("--db", default="cboe_options.db")
    p.add_argument("--only", default=None,
                   help="comma-separated symbols to fetch (default: catalog)")
    p.add_argument("--exclude", default=None,
                   help="comma-separated symbols to skip")
    p.add_argument("--add", default=None,
                   help="comma-separated extra symbols to append")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days "
                        "(never touches option history)")
    a = p.parse_args(argv)
    all_syms = [u.symbol for u in catalog.CATALOG]
    symbols = catalog.select_symbols(all_syms, _split(a.only), _split(a.exclude),
                                     _split(a.add))
    _, sc, rc = run(a.db, symbols=symbols, keep_days=a.keep_days)
    print(f"stored {rc} option rows across {sc} symbols into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_options_run.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add cboe_options/run.py tests/test_options_run.py
git commit -m "feat(cboe_options): add run orchestrator + options CLI"
```

---

## Task 6: Register in dispatcher

**Files:**
- Modify: `registry.py`
- Test: `tests/test_registry.py` (append one test)

**Interfaces:**
- Consumes: `cboe_options.run.main` (Task 5).
- Produces: `REGISTRY["options"]` routes to the options screener.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_registry.py`:

```python
def test_dispatch_lists_options():
    import registry
    assert "options" in registry.REGISTRY
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_registry.py::test_dispatch_lists_options -v`
Expected: FAIL — `KeyError`/`assert 'options' in {...}`

- [ ] **Step 3: Wire it into `registry.py`**

Add the import alongside the others (after the `finra_short_volume` import line):

```python
from cboe_options.run import main as options_main
```

Add the entry to the `REGISTRY` dict (after `"short_volume": short_volume_main,`):

```python
    "options": options_main,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_registry.py -v`
Expected: PASS (all, including `test_dispatch_lists_options`)

- [ ] **Step 5: Full suite + a real smoke run**

Run: `uv run pytest -q`
Expected: PASS (entire suite green)

Run a real end-to-end fetch against the live CBOE endpoint (network required):
`uv run python main.py options --only AAPL --db /tmp/opt_smoke.db`
Expected: prints `stored <N> option rows across 1 symbols into /tmp/opt_smoke.db` with N in the thousands.

Spot-check the data and a view:
`uv run python -c "import sqlite3; c=sqlite3.connect('/tmp/opt_smoke.db'); print(c.execute('SELECT COUNT(*), MAX(vol_oi_ratio) FROM option_snapshots').fetchone()); print(c.execute('SELECT underlying, snapshot_date, iv30 FROM v_latest_sentiment').fetchall())"`
Expected: a non-zero count and one AAPL sentiment row.

- [ ] **Step 6: Commit**

```bash
git add registry.py tests/test_registry.py
git commit -m "feat(cboe_options): register options screener in dispatcher"
```

---

## Self-Review Notes (author)

- **Spec coverage:** source & URL scheme (Task 2), catalog/starter set (Task 1), all schema tables + views incl. IV-rank/unusual-activity (Task 3), replace-per-day + rollups + snapshots-only prune (Task 4), run loop with session-date + skip-and-continue + secret hygiene (Task 5), dispatcher registration (Task 6). `source='cboe'` default column present for future Robinhood layering (Task 3). v1 non-goals (Robinhood/skew/alerting) intentionally absent.
- **session_date:** primary = `data.last_trade_time` date, fallback = top-level `timestamp` date, final fallback in `run()` = `now_iso[:10]`. Honors the spec's "derive from payload, not wall clock" intent (weekend re-run keys to the real session).
- **Type consistency:** `fetch.parse_chain` produces exactly the keys `db._CONTRACT_COLS`/`_DAILY_COLS` consume (plus the run-stamped `snapshot_date`/`source`/`fetched_at`). `fetch_chain(symbol, is_index, get=...)` signature matches the `run()` injection and the test doubles.
- **`uv` note:** commands use `uv run`; if the repo is used with a bare `python`/`pytest`, drop the `uv run` prefix. Verify against how the other screeners are run in this environment before Task 1.
```
