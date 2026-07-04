"""USDA OCE WASDE balance-sheet CSV client (1e).

Reads the machine-readable `oce-wasde-report-data-{YYYY}-{MM}.csv` (a tidy long
table: one row per Commodity/Region/Attribute/MarketYear with a Value+Unit),
which carries the full ending-stocks/use balance sheet that NASS Quick Stats
cannot supply (see the usda catalog note). No API key required.

Pure parser + a bytes-free text fetch, network-free-testable. The column matcher
is case/spacing-tolerant and raises WasdeSchemaError on a missing required column
so a header change fails loudly instead of silently dropping data."""
import csv
import io
import time
import urllib.error
import urllib.parse

import http_client

CSV_BASE = "https://www.usda.gov/sites/default/files/documents"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 4
_BASE_DELAY = 1.0
# The USDA file host is slow for these ~1MB CSVs; give it room.
_urlopen = http_client.make_opener(_UA, timeout=180)

__all__ = ["WasdeSchemaError", "parse_wasde_csv", "wasde_csv_url", "fetch_wasde",
           "BALANCE_METRICS"]

# Balance-sheet Attribute -> canonical metric. Keys are the Attribute string
# normalized by _norm_attr (lowercased, commas/periods dropped). Non-balance
# attributes (yield, area, price, sub-components) are intentionally absent and
# skipped. "Domestic, Total"/"Domestic Total"/"Domestic Use" all -> domestic_use.
_METRIC_MAP = {
    "beginning stocks": "beginning_stocks",
    "production": "production",
    "imports": "imports",
    "supply total": "total_supply",
    "domestic total": "domestic_use",
    "domestic use": "domestic_use",
    "exports": "exports",
    "use total": "total_use",
    "ending stocks": "ending_stocks",
}
BALANCE_METRICS = tuple(dict.fromkeys(_METRIC_MAP.values()))

# Candidate header names per logical field (matched case/space-insensitively).
_FIELDS = {
    "attribute": ("attribute",),
    "commodity": ("commodity",),
    "region": ("region",),
    "market_year": ("marketyear", "market year"),
    "value": ("value",),
    "unit": ("unit",),
    "report_date": ("releasedate", "release date"),
}
_REQUIRED = ("attribute", "commodity", "region", "market_year", "value")


class WasdeSchemaError(Exception):
    """The CSV header lacks a required column (a schema change) — raised so the
    mismatch is visible rather than silently yielding zero/partial rows."""


def _http_get(url, opener=_urlopen, attempts=_MAX_ATTEMPTS, base_delay=_BASE_DELAY,
              sleep=time.sleep):
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay,
                                sleep)


def _num(v):
    v = ("" if v is None else str(v)).strip().replace(",", "")
    if not v or v.startswith("("):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _norm_attr(a):
    return " ".join((a or "").lower().replace(",", "").replace(".", "").split())


def _resolve_columns(fieldnames):
    """Map each logical field to the real header key (case/space-insensitive).
    Raise WasdeSchemaError if any REQUIRED field is absent."""
    norm = {"".join((c or "").lower().split()): c for c in (fieldnames or [])}
    resolved = {}
    for field, candidates in _FIELDS.items():
        for cand in candidates:
            key = "".join(cand.lower().split())
            if key in norm:
                resolved[field] = norm[key]
                break
    missing = [f for f in _REQUIRED if f not in resolved]
    if missing:
        raise WasdeSchemaError(
            f"WASDE CSV missing required column(s) {missing}; "
            f"header was {list(fieldnames or [])}")
    return resolved


def parse_wasde_csv(text) -> list:
    """Parse the tidy WASDE CSV into balance-sheet fact rows. Keeps only rows
    whose Attribute maps to a balance metric; each row is
    {commodity, region, metric, market_year, value, unit, report_date,
    projection}. Rows missing commodity/region/market_year are skipped. The
    (commodity, region, metric, market_year, unit) tuple is unique — unit
    distinguishes the U.S.-domestic (bushels) and world-table (metric-tons)
    copies of the same U.S. line."""
    reader = csv.DictReader(io.StringIO(text))
    col = _resolve_columns(reader.fieldnames)
    out = []
    for r in reader:
        metric = _METRIC_MAP.get(_norm_attr(r.get(col["attribute"])))
        if metric is None:
            continue
        commodity = (r.get(col["commodity"]) or "").strip()
        region = (r.get(col["region"]) or "").strip()
        my = (r.get(col["market_year"]) or "").strip()
        if not commodity or not region or not my:
            continue
        out.append({
            "commodity": commodity, "region": region, "metric": metric,
            "market_year": my, "value": _num(r.get(col["value"])),
            "unit": (r.get(col.get("unit", "")) or "").strip() or None,
            "report_date": (r.get(col.get("report_date", "")) or "").strip()[:10]
                           or None,
        })
    return out


def wasde_csv_url(year: int, month: int, base: str = CSV_BASE) -> str:
    """URL of the machine-readable CSV for a release, e.g. .../oce-wasde-report-
    data-2025-12.csv."""
    return f"{base}/oce-wasde-report-data-{year:04d}-{month:02d}.csv"


def fetch_wasde(year: int, month: int, get=_http_get):
    """Download + parse one release's CSV. Returns fact rows, or None on HTTP
    404 (a release not yet published for that month)."""
    try:
        text = get(wasde_csv_url(year, month))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return parse_wasde_csv(text)
