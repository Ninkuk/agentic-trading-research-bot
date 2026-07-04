"""data.sec.gov XBRL client + pure parsers. Reuses edgar_screener's SEC
scaffolding (UA, bounded backoff over 403/429/503) verbatim — see the note in
[[edgar-sec-rate-limit-followup]] on SEC fingerprint-blocking bare urllib."""
import csv
import io
import json
import time
import urllib.error
import urllib.request
import zipfile

import sources.common.http_client as http_client
from sources.screeners.edgar_screener.fetch import (  # reuse UA + bounded-backoff scaffolding
    _BASE_DELAY, _MAX_ATTEMPTS, _RETRY_STATUS, _UA, _http_get, fetch_ticker_map)

__all__ = ["cik_str", "fetch_ticker_map", "parse_frame", "fetch_frame",
           "parse_company_facts", "fetch_company_facts", "fetch_submissions",
           "parse_bulk", "bulk_zip_url", "fetch_bulk"]

_FRAMES = "https://data.sec.gov/api/xbrl/frames"
_FACTS = "https://data.sec.gov/api/xbrl/companyfacts"
_SUBS = "https://data.sec.gov/submissions"
# Quarterly Financial Statement Data Sets (DERA) — the --bulk backfill source.
_BULK_BASE = ("https://www.sec.gov/files/dera/data/"
              "financial-statement-data-sets")


def cik_str(cik: int) -> str:
    """10-digit zero-padded CIK path segment, e.g. 320193 -> 'CIK0000320193'."""
    return f"CIK{int(cik):010d}"


def _num(v):
    """Coerce a numeric string/number to float; blanks/None -> None."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _unit_path(unit: str) -> str:
    """Frames URL unit segment: 'USD/shares' -> 'USD-per-shares'."""
    return unit.replace("/", "-per-")


def parse_frame(payload: dict) -> list:
    """Pure: a frames payload's data[] -> fact rows. Frames carry no
    form/fy/fp/filed, so those are None (the run substitutes form='FRAME')."""
    out = []
    for e in payload.get("data", []):
        out.append({
            "cik": e.get("cik"), "tag": None, "uom": None,
            "period_end": e.get("end"),
            "fiscal_year": e.get("fy"), "fiscal_period": e.get("fp"),
            "value": _num(e.get("val")),
            "form": e.get("form"), "filed": e.get("filed"),
            "accession": e.get("accn"),
        })
    return out


def fetch_frame(tag: str, unit: str, period: str, taxonomy: str = "us-gaap",
                get=_http_get) -> list:
    """GET a frames endpoint for (tag, unit, period). Caller supplies the
    correctly-suffixed period ('...QnI' instant vs '...Qn' duration)."""
    url = f"{_FRAMES}/{taxonomy}/{tag}/{_unit_path(unit)}/{period}.json"
    rows = parse_frame(json.loads(get(url)))
    for r in rows:                                  # stamp the requested tag/uom
        r["tag"], r["uom"] = tag, unit
    return rows


def parse_company_facts(payload: dict, tags) -> list:
    """Pure: walk facts[taxonomy][tag][units][uom][] for the curated tags only.
    Extension/non-curated tags ignored. companyfacts uses val/accn keys."""
    out = []
    for _taxonomy, tagmap in payload.get("facts", {}).items():
        for tag, body in tagmap.items():
            if tag not in tags:
                continue
            for uom, entries in body.get("units", {}).items():
                for e in entries:
                    out.append({
                        "tag": tag, "uom": uom, "period_end": e.get("end"),
                        "fiscal_year": e.get("fy"), "fiscal_period": e.get("fp"),
                        "value": _num(e.get("val")), "form": e.get("form"),
                        "filed": e.get("filed"), "accession": e.get("accn"),
                    })
    return out


def fetch_company_facts(cik: int, get=_http_get) -> dict:
    """GET companyfacts for one CIK. Returns the raw payload (run parses it)."""
    return json.loads(get(f"{_FACTS}/{cik_str(cik)}.json"))


def fetch_submissions(cik: int, get=_http_get) -> dict:
    """GET the submissions (filing history) payload for one CIK."""
    return json.loads(get(f"{_SUBS}/{cik_str(cik)}.json"))


def _iso(ddate: str) -> str:
    """SEC bulk ddate 'YYYYMMDD' -> 'YYYY-MM-DD'."""
    s = str(ddate)
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else s


def parse_bulk(zip_bytes: bytes, tags) -> list:
    """Optional --bulk: num.tsv joined to sub.tsv inside a quarterly ZIP,
    filtered to curated tags, emitting the same fact-row shape. The 2009q1 ZIP is
    a header-only placeholder (sub/num present but no fact rows) -> yields []."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        subs = {}
        with z.open("sub.tsv") as fh:
            for row in csv.DictReader(io.TextIOWrapper(fh, "utf-8"), delimiter="\t"):
                subs[row["adsh"]] = row
        out = []
        with z.open("num.tsv") as fh:
            for row in csv.DictReader(io.TextIOWrapper(fh, "utf-8"), delimiter="\t"):
                if row.get("tag") not in tags:
                    continue
                sub = subs.get(row["adsh"])
                if sub is None:
                    continue
                out.append({
                    "cik": int(sub["cik"]), "tag": row["tag"],
                    "uom": row.get("uom"), "period_end": _iso(row.get("ddate")),
                    "fiscal_year": _int(sub.get("fy")),
                    "fiscal_period": sub.get("fp"), "value": _num(row.get("value")),
                    "form": sub.get("form"), "filed": _iso(sub.get("filed")),
                    "accession": row["adsh"], "name": sub.get("name"),
                    "sic": sub.get("sic"),
                })
    return out


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _bytes_opener(headers: dict, timeout: int = 60, *,
                  limiter=None, limiter_key: str = ""):
    """opener(url)->bytes for the binary quarterly ZIPs (make_opener decodes,
    which would corrupt ZIP bytes). Pays the shared SEC throttle when supplied."""
    def opener(url: str) -> bytes:
        if limiter is not None:
            limiter.acquire(limiter_key)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    return opener


# Same UA + shared SEC bucket as the JSON path (edgar's _urlopen), just no decode.
_bulk_urlopen = _bytes_opener(_UA, limiter=http_client.SEC_RATE_LIMITER,
                              limiter_key=http_client.SEC_HOST_KEY)


def _http_get_bytes(url: str, opener=_bulk_urlopen, attempts: int = _MAX_ATTEMPTS,
                    base_delay: float = _BASE_DELAY, sleep=time.sleep) -> bytes:
    """GET raw bytes with the SEC bounded backoff (403/429/503 + transient)."""
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts,
                                base_delay, sleep)


def bulk_zip_url(year: int, quarter: int, base: str = _BULK_BASE) -> str:
    """URL of the DERA quarterly ZIP for a (year, quarter), e.g. .../2023q2.zip."""
    return f"{base}/{year}q{quarter}.zip"


def fetch_bulk(year: int, quarter: int, get=_http_get_bytes) -> bytes | None:
    """Download one quarter's financial-statement-data-set ZIP. Returns the raw
    bytes, or None on HTTP 404 — an unpublished (future) quarter the run skips.
    Other HTTP errors raise, since they signal a real fetch problem."""
    try:
        return get(bulk_zip_url(year, quarter))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
