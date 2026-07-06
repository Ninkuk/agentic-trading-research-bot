"""USDA OCE WASDE report client (XML edition).

Reads the monthly report's XML rendering from /oce/commodity/wasde/ — the tidy
`oce-wasde-report-data-*.csv` this module originally used now connection-resets
at the edge for non-browser clients (the whole /sites/default/files/documents/
tree; verified 2026-07), while the XML path serves fine. Only the CURRENT
release is hosted (prior months 404, the next month's pre-staged link 302s to
an apology page) and its filename carries an unpredictable revision suffix
(e.g. wasde0626v2.xml), so the fetch discovers the live link from the report
landing page and falls back across candidates.

The XML mirrors the printed report: one Report element per page whose
sub_report_title names the table and whose matrixN children are the side-by-
side commodity columns — the XML nowhere labels a matrix with its commodity,
so _US_TABLES curates the (title -> commodity/unit per matrix) print layout,
which has been stable for decades. Pure parser + fetch seam,
network-free-testable. Raises WasdeSchemaError when no curated table matches
so a layout change fails loudly instead of silently dropping data."""

import re
import time
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime

import sources.common.http_client as http_client

REPORT_PAGE_URL = (
    "https://www.usda.gov/about-usda/general-information/"
    "staff-offices/office-chief-economist/commodity-markets/"
    "wasde-report"
)
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 4
_BASE_DELAY = 1.0
# The USDA host is slow for the ~2MB report XML; give it room.
_urlopen = http_client.make_opener(_UA, timeout=180)

__all__ = ["WasdeSchemaError", "find_xml_urls", "parse_wasde_xml", "fetch_wasde", "BALANCE_METRICS"]

# Balance-sheet attribute -> canonical metric, keyed by _norm_attr output
# (lowercased, commas/periods/footnote markers dropped). Non-balance rows
# (area, yield, price, sub-components) are intentionally absent and skipped.
# The domestic-use synonyms cover the print tables' per-commodity phrasing:
# "Domestic, Total" (corn), "Total Domestic" (sorghum), "Domestic Use"
# (cotton), "Domestic & Residual" (rice), "Domestic Disappearance" (soybean
# products), "Deliveries" (sugar, whose table has no single use-total line).
_METRIC_MAP = {
    "beginning stocks": "beginning_stocks",
    "production": "production",
    "imports": "imports",
    "supply total": "total_supply",
    "total supply": "total_supply",
    "domestic total": "domestic_use",
    "total domestic": "domestic_use",
    "domestic use": "domestic_use",
    "domestic & residual": "domestic_use",
    "domestic disappearance": "domestic_use",
    "deliveries": "domestic_use",
    "exports": "exports",
    "exports total": "exports",
    "use total": "total_use",
    "ending stocks": "ending_stocks",
}
BALANCE_METRICS = tuple(dict.fromkeys(_METRIC_MAP.values()))

# Print-layout curation: normalized sub_report_title prefix -> (commodity,
# unit) per matrixN in document order. Extra matrices (wheat-by-class, rice
# by grain length, Mexico sugar) are deliberately unmapped and skipped.
# Units are curated because the XML splits them into presentation fragments
# ("Million 480 " + " Pound Bales"); assignments live-verified against the
# June 2026 report's magnitudes.
_US_TABLES = (
    ("u.s. wheat supply and use", (("Wheat", "Million Bushels"),)),
    (
        "u.s. feed grain and corn supply and use",
        (("Feed Grains", "Million Metric Tons"), ("Corn", "Million Bushels")),
    ),
    (
        "u.s. sorghum, barley, and oats supply and use",
        (
            ("Sorghum", "Million Bushels"),
            ("Barley", "Million Bushels"),
            ("Oats", "Million Bushels"),
        ),
    ),
    ("u.s. rice supply and use", (("Rice", "Million Hundredweight"),)),
    (
        "u.s. soybeans and products supply and use",
        (
            ("Soybeans", "Million Bushels"),
            ("Soybean Oil", "Million Pounds"),
            ("Soybean Meal", "Thousand Short Tons"),
        ),
    ),
    ("u.s. sugar supply and use", (("Sugar", "1000 Short Tons, Raw Value"),)),
    ("u.s. cotton supply and use", (("Cotton", "Million 480-Pound Bales"),)),
)
_REGION = "United States"

_XML_LINK = re.compile(
    r'href="((?:https://www\.usda\.gov)?/oce/commodity/wasde/'
    r'wasde(\d{2})(\d{2})(?:v\d+)?\.xml)"'
)


class WasdeSchemaError(Exception):
    """The XML contains none of the curated U.S. tables (a layout change) —
    raised so the mismatch is visible rather than silently yielding zero rows."""


def _http_get(
    url, opener=_urlopen, attempts=_MAX_ATTEMPTS, base_delay=_BASE_DELAY, sleep=time.sleep
):
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay, sleep)


def _num(v):
    v = ("" if v is None else str(v)).strip().replace(",", "")
    if not v or v.startswith("("):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _norm_attr(a):
    """'    Supply, Total  7/' -> 'supply total' (footnote markers dropped)."""
    a = re.sub(r"\b\d+/", "", (a or "").lower().replace(",", "").replace(".", ""))
    return " ".join(a.split())


def _norm_title(t):
    return " ".join((t or "").lower().split())


def find_xml_urls(html) -> list:
    """Report-XML candidates linked from the landing page, absolute, newest
    (year, month) first, de-duplicated. The newest link may be next month's
    pre-staged placeholder — callers fall back across the list."""
    seen, out = set(), []
    for path, mm, yy in _XML_LINK.findall(html or ""):
        url = path if path.startswith("http") else f"https://www.usda.gov{path}"
        if url in seen:
            continue
        seen.add(url)
        out.append((2000 + int(yy), int(mm), url))
    return [u for _, _, u in sorted(out, reverse=True)]


def _attr_value(el, prefix):
    """First non-empty attrib value whose key starts with prefix (the XML
    suffixes keys per matrix: attribute1/attribute2, cell_value1, ...)."""
    return next((v for k, v in el.attrib.items() if k.startswith(prefix) and v and v.strip()), None)


def _matrix_rows(matrix):
    """Yield (metric, market_year, value) from one commodity's matrix: for
    each balance attribute row, per marketing year, the LAST month group's
    cell — the current forecast (e.g. Jun supersedes May for Proj. years)."""
    for holder in matrix.iter():
        metric = _METRIC_MAP.get(_norm_attr(_attr_value(holder, "attribute")))
        if metric is None:
            continue
        for yg in holder.iter():
            my = _attr_value(yg, "market_year")
            if not my:
                continue
            cells = [
                _attr_value(mg, "cell_value")
                or next(
                    (
                        _attr_value(c, "cell_value")
                        for c in mg.iter()
                        if _attr_value(c, "cell_value")
                    ),
                    None,
                )
                for mg in yg.iter()
                if any(k.startswith("forecast_month") for k in mg.attrib)
            ]
            if not cells:
                continue
            # Est./Proj. markers stripped so next month's status flip upserts
            # the same row instead of forking a new market_year key.
            year_key = re.sub(r"\s+(Est|Proj)\.?$", "", my.strip())
            yield metric, year_key, _num(cells[-1])


def _report_date(sub) -> str | None:
    """Report_Month 'June 2026' -> '2026-06-01' (source-derived, no wall clock)."""
    try:
        d = datetime.strptime((sub.get("Report_Month") or "").strip(), "%B %Y")  # noqa: DTZ007 — date-only parse
    except ValueError:
        return None
    return d.date().replace(day=1).isoformat()


def parse_wasde_xml(xml_text) -> list:
    """Parse the report XML into balance-sheet fact rows: one per (commodity,
    metric, market_year) from the curated U.S. tables, each
    {commodity, region, metric, market_year, value, unit, report_date}.

    Hardening: stdlib xml.etree does not resolve external entities (no XXE)
    but is vulnerable to entity-expansion DoS, which needs a DOCTYPE/ENTITY
    block the legitimate feed never has — reject those before parsing
    (treasury_screener.parse_yield_curve's guard)."""
    if xml_text and ("<!DOCTYPE" in xml_text or "<!ENTITY" in xml_text):
        raise ValueError("refusing XML with a DOCTYPE/ENTITY declaration (entity-expansion guard)")
    root = ET.fromstring(xml_text)
    out = []
    for sub in root.iter("Report"):
        title = _norm_title(sub.get("sub_report_title"))
        table = next(
            (commodities for prefix, commodities in _US_TABLES if title.startswith(prefix)), None
        )
        if table is None:
            continue
        report_date = _report_date(sub)
        matrices = [el for el in sub if el.tag.startswith("matrix")]
        for (commodity, unit), matrix in zip(table, matrices, strict=False):
            for metric, market_year, value in _matrix_rows(matrix):
                out.append(
                    {
                        "commodity": commodity,
                        "region": _REGION,
                        "metric": metric,
                        "market_year": market_year,
                        "value": value,
                        "unit": unit,
                        "report_date": report_date,
                    }
                )
    if not out:
        raise WasdeSchemaError("report XML matched none of the curated U.S. supply/use tables")
    return out


def fetch_wasde(get=_http_get):
    """Discover the current report XML from the landing page and parse it.
    Candidates are tried newest-first: the pre-staged next-month link 302s to
    an HTML apology page (parses but matches no table) and a stale link 404s —
    both fall through to the next candidate. Returns fact rows, or None when
    no candidate yields a parseable report (the caller warns; a real layout
    change surfaces there rather than as a raised WasdeSchemaError)."""
    try:
        candidates = find_xml_urls(get(REPORT_PAGE_URL))
    except urllib.error.HTTPError:
        return None
    for url in candidates:
        try:
            return parse_wasde_xml(get(url))
        except (urllib.error.HTTPError, ET.ParseError, WasdeSchemaError):
            continue  # placeholder / gone -> next
    return None
