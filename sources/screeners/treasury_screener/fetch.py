"""U.S. Treasury Fiscal Data client (paged JSON:API) + the one XML branch for the
par yield-curve feed. Pure parsers separated from HTTP so they unit-test without
network. Key-free; reuses the shared bounded-backoff client."""

import json
import urllib.parse
import xml.etree.ElementTree as ET

import sources.common.http_client as http_client
from sources.common.http_client import DEFAULT_UA, RETRY_THROTTLE_5XX
from sources.common.parse import date_prefix, to_float

API_BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
YIELD_CURVE_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/"
    "interest-rates/pages/xml?data=daily_treasury_yield_curve"
)
_UA = DEFAULT_UA
_RETRY_STATUS = RETRY_THROTTLE_5XX
_urlopen = http_client.make_opener(_UA)


_http_get = http_client.make_getter(_urlopen, _RETRY_STATUS)


def _build_url(
    endpoint, *, fields=None, filter_=None, sort=None, page_size=10000, page_number=1
) -> str:
    params = {"format": "json", "page[size]": page_size, "page[number]": page_number}
    if fields:
        params["fields"] = ",".join(fields)
    if filter_:
        params["filter"] = filter_
    if sort:
        params["sort"] = sort
    return f"{API_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"


def fetch_dataset(endpoint, *, fields=None, since=None, get=_http_get) -> list:
    """Page through the JSON:API `data` arrays until `links.next` is null."""
    filter_ = f"record_date:gte:{since}" if since else None
    records, page = [], 1
    while True:
        url = _build_url(
            endpoint, fields=fields, filter_=filter_, sort="record_date", page_number=page
        )
        payload = json.loads(get(url))
        records.extend(payload.get("data", []))
        if not (payload.get("links") or {}).get("next"):
            break
        page += 1
    return records


def parse_dts_cash(records) -> list:
    return [
        {
            "record_date": date_prefix(r.get("record_date")),
            "account_type": r.get("account_type"),
            "open_balance": to_float(r.get("open_today_bal")),
            "close_balance": to_float(r.get("close_today_bal")),
        }
        for r in records
    ]


def parse_debt_penny(records) -> list:
    return [
        {
            "record_date": date_prefix(r.get("record_date")),
            "tot_pub_debt_out": to_float(r.get("tot_pub_debt_out_amt")),
            "debt_held_public": to_float(r.get("debt_held_public_amt")),
            "intragov_hold": to_float(r.get("intragov_hold_amt")),
        }
        for r in records
    ]


def parse_avg_rates(records) -> list:
    return [
        {
            "record_date": date_prefix(r.get("record_date")),
            "security_type_desc": r.get("security_type_desc"),
            "security_desc": r.get("security_desc"),
            "avg_interest_rate": to_float(r.get("avg_interest_rate_amt")),
        }
        for r in records
    ]


def parse_upcoming_auctions(records) -> list:
    return [
        {
            "cusip": r.get("cusip") or None,
            "security_type": r.get("security_type"),
            "security_term": r.get("security_term"),
            "announcement_date": date_prefix(r.get("announcemt_date")),
            "auction_date": date_prefix(r.get("auction_date")),
            "issue_date": date_prefix(r.get("issue_date")),
        }
        for r in records
    ]


def parse_auction_results(records) -> list:
    return [
        {
            "cusip": r.get("cusip"),
            "auction_date": date_prefix(r.get("auction_date")),
            "security_type": r.get("security_type"),
            "security_term": r.get("security_term"),
            "high_yield": to_float(r.get("high_yield_rate")),
            "bid_to_cover_ratio": to_float(r.get("bid_to_cover_ratio")),
            "offering_amt": to_float(r.get("offering_amt")),
            "total_accepted": to_float(r.get("total_accepted_amt")),
        }
        for r in records
    ]


_TENOR = {
    "BC_1MONTH": "mo1",
    "BC_2MONTH": "mo2",
    "BC_3MONTH": "mo3",
    "BC_4MONTH": "mo4",
    "BC_6MONTH": "mo6",
    "BC_1YEAR": "yr1",
    "BC_2YEAR": "yr2",
    "BC_3YEAR": "yr3",
    "BC_5YEAR": "yr5",
    "BC_7YEAR": "yr7",
    "BC_10YEAR": "yr10",
    "BC_20YEAR": "yr20",
    "BC_30YEAR": "yr30",
}
_YC_COLS = ["record_date"] + list(_TENOR.values())


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def parse_yield_curve(xml_text) -> list:
    """Parse the Treasury par-curve Atom XML → one dict per business day, wide by
    tenor. Namespace-agnostic (matches on local element names).

    Hardening: stdlib xml.etree does not resolve external entities (no XXE), but
    is vulnerable to entity-expansion DoS ('billion laughs'). Those bombs live in
    a DOCTYPE/ENTITY block, which the legitimate Treasury feed never uses — so we
    reject any such declaration before parsing (defusedxml would be cleaner but
    the repo is strictly dependency-free)."""
    if xml_text and ("<!DOCTYPE" in xml_text or "<!ENTITY" in xml_text):
        raise ValueError("refusing XML with a DOCTYPE/ENTITY declaration (entity-expansion guard)")
    root = ET.fromstring(xml_text)
    out: list[dict] = []
    for el in root.iter():
        if _local(el.tag) != "properties":
            continue
        row: dict[str, str | float | None] = dict.fromkeys(_YC_COLS)
        for child in el.iter():
            name = _local(child.tag)
            if name == "NEW_DATE":
                row["record_date"] = date_prefix(child.text)
            elif name in _TENOR:
                row[_TENOR[name]] = to_float(child.text)
        if row["record_date"]:
            out.append(row)
    return out


def fetch_yield_curve(year, get=_http_get) -> list:
    return parse_yield_curve(get(f"{YIELD_CURVE_URL}&field_tdr_date_value={year}"))
